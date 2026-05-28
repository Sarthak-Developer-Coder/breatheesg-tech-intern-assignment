from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.models import (
    ActivityCategory,
    ActivityRecord,
    IngestionJob,
    IngestionJobStatus,
    RawRecord,
    RawRecordStatus,
    Scope,
    SourceType,
    Tenant,
)
from core.services.airports import estimate_flight_distance_km
from core.services.anomalies import detect_anomalies
from core.services.emissions import compute_co2e, find_emission_factor, snapshot_factor
from core.services.parsing import parse_date, parse_decimal
from core.services.units import normalize_unit


@dataclass(frozen=True)
class TravelIngestResult:
    job: IngestionJob


_ALLOWED_FLIGHT_CLASSES = {
    'economy',
    'premium_economy',
    'business',
    'first',
}


def _as_decimal_km(value: Any) -> Decimal | None:
    d = parse_decimal(value)
    if d is None:
        return None

    if d < 0:
        return d

    # Some APIs return meters.
    if d > 20000 and d < 2_000_000:
        # If it looks like meters, convert to km.
        # (This is heuristic; we flag spikes separately.)
        return d / Decimal('1000')

    return d


def ingest_travel_payload(*, tenant: Tenant, payload: dict[str, Any], actor: str = '', source_label: str = '') -> TravelIngestResult:
    """Ingest a Concur/Navan-style API payload pushed to us.

    Ingestion mechanism: API push (realistic for travel platforms with webhooks/exports).
    """

    job = IngestionJob.objects.create(
        tenant=tenant,
        source_type=SourceType.TRAVEL_API,
        status=IngestionJobStatus.PROCESSING,
        created_by=actor or '',
        source_label=source_label or '',
        original_filename='',
        started_at=timezone.now(),
    )

    items = payload.get('transactions') or payload.get('items') or payload.get('data')
    if not isinstance(items, list):
        items = []

    raw_count = parsed_count = failed_count = activity_count = anomaly_count = 0

    with transaction.atomic():
        for idx, item in enumerate(items, start=1):
            raw_count += 1

            raw_payload = item if isinstance(item, dict) else {'value': item}
            raw_text = json.dumps(raw_payload, ensure_ascii=False, separators=(',', ':'))
            raw_hash = hashlib.sha256(raw_text.encode('utf-8')).hexdigest()

            tx_id = str(raw_payload.get('id') or raw_payload.get('transaction_id') or raw_payload.get('expense_id') or '')

            mode_raw = (
                raw_payload.get('type')
                or raw_payload.get('category')
                or raw_payload.get('expense_type')
                or raw_payload.get('mode')
                or ''
            )
            mode = str(mode_raw).strip().lower()

            category = ActivityCategory.TRAVEL
            scope = Scope.SCOPE_3

            activity_date = (
                parse_date(raw_payload.get('date'))
                or parse_date(raw_payload.get('start_date'))
                or parse_date(raw_payload.get('departure_date'))
                or parse_date(raw_payload.get('check_in'))
            )

            subcategory = ''
            normalized_unit = ''
            quantity: Decimal | None = None
            metadata: dict[str, Any] = {
                'travel': {
                    'raw_type': str(mode_raw),
                }
            }

            parse_errors: list[str] = []

            if mode == 'flight':
                origin = str(raw_payload.get('origin_airport') or raw_payload.get('from_airport') or '').upper().strip()
                dest = str(raw_payload.get('destination_airport') or raw_payload.get('to_airport') or '').upper().strip()

                travel_class_raw = str(raw_payload.get('travel_class') or raw_payload.get('cabin_class') or 'economy')
                travel_class = travel_class_raw.strip().lower().replace(' ', '_')
                if travel_class not in _ALLOWED_FLIGHT_CLASSES:
                    travel_class = 'economy'

                subcategory = f"flight_{travel_class}"
                normalized_unit = 'km'

                distance_km = _as_decimal_km(raw_payload.get('distance_km'))
                estimated = False
                if distance_km is None and origin and dest:
                    est = estimate_flight_distance_km(origin, dest)
                    if est is not None:
                        # Small uplift to approximate non-great-circle routing.
                        distance_km = Decimal(str(est)) * Decimal('1.09')
                        estimated = True

                if distance_km is None:
                    parse_errors.append('missing_distance_km')

                quantity = distance_km
                metadata['travel'].update(
                    {
                        'mode': 'flight',
                        'origin_airport': origin,
                        'destination_airport': dest,
                        'travel_class': travel_class,
                        'distance_km_estimated': estimated,
                    }
                )

            elif mode == 'hotel':
                nights = parse_decimal(raw_payload.get('hotel_nights') or raw_payload.get('nights'))
                rooms = parse_decimal(raw_payload.get('rooms') or 1)
                if nights is None:
                    parse_errors.append('missing_hotel_nights')

                subcategory = 'hotel'
                normalized_unit = 'night'
                if nights is not None:
                    quantity = (nights * (rooms or Decimal('1'))).quantize(Decimal('0.000001'))

                metadata['travel'].update(
                    {
                        'mode': 'hotel',
                        'city': raw_payload.get('city') or raw_payload.get('hotel_city') or '',
                        'country': raw_payload.get('country') or raw_payload.get('hotel_country') or '',
                        'hotel_nights': str(nights) if nights is not None else None,
                        'rooms': str(rooms) if rooms is not None else None,
                    }
                )

            else:
                # Ground transport
                # Commonly: taxi, rail, car
                ground_mode = mode if mode else str(raw_payload.get('ground_mode') or 'ground').strip().lower()

                dist = _as_decimal_km(
                    raw_payload.get('ground_distance_km')
                    or raw_payload.get('distance_km')
                    or raw_payload.get('distance')
                )
                if dist is None:
                    parse_errors.append('missing_ground_distance_km')

                subcategory = ground_mode if ground_mode else 'ground'
                normalized_unit = 'km'
                quantity = dist

                metadata['travel'].update(
                    {
                        'mode': 'ground',
                        'ground_mode': ground_mode,
                    }
                )

            if quantity is None or normalized_unit == '' or subcategory == '':
                failed_count += 1
                RawRecord.objects.create(
                    tenant=tenant,
                    ingestion_job=job,
                    source_type=SourceType.TRAVEL_API,
                    row_number=idx,
                    source_external_id=tx_id,
                    raw_payload=raw_payload,
                    raw_text=raw_text,
                    raw_hash_sha256=raw_hash,
                    status=RawRecordStatus.FAILED,
                    parse_errors=parse_errors or ['unparseable_travel_item'],
                )
                continue

            emission_factor = find_emission_factor(
                tenant=tenant,
                category=category,
                subcategory=subcategory,
                unit=normalized_unit,
                at_date=activity_date,
            )
            factor_snapshot = snapshot_factor(emission_factor)
            co2e = compute_co2e(quantity=quantity, factor=emission_factor)

            anomaly = detect_anomalies(
                tenant=tenant,
                category=category,
                subcategory=subcategory,
                normalized_unit=normalized_unit,
                quantity=quantity,
                activity_date=activity_date,
                period_start=None,
                period_end=None,
                plant_id=None,
                metadata=metadata,
                emission_factor_found=emission_factor is not None,
            )

            raw_record = RawRecord.objects.create(
                tenant=tenant,
                ingestion_job=job,
                source_type=SourceType.TRAVEL_API,
                row_number=idx,
                source_external_id=tx_id,
                raw_payload=raw_payload,
                raw_text=raw_text,
                raw_hash_sha256=raw_hash,
                status=RawRecordStatus.PARSED,
                parse_errors=parse_errors,
            )
            parsed_count += 1

            ActivityRecord.objects.create(
                tenant=tenant,
                ingestion_job=job,
                raw_record=raw_record,
                source_type=SourceType.TRAVEL_API,
                source_external_id=tx_id,
                scope=scope,
                category=category,
                subcategory=subcategory,
                plant=None,
                activity_date=activity_date,
                source_quantity=quantity,
                source_unit=normalized_unit,
                quantity=quantity,
                normalized_unit=normalized_unit,
                emission_factor=emission_factor,
                emission_factor_snapshot=factor_snapshot,
                co2e_kg=co2e,
                activity_metadata=metadata,
                anomaly_flags=anomaly.flags,
                confidence_score=anomaly.confidence_score,
            )

            activity_count += 1
            if anomaly.flags:
                anomaly_count += 1

        job.status = IngestionJobStatus.COMPLETED
        job.finished_at = timezone.now()
        job.raw_record_count = raw_count
        job.parsed_record_count = parsed_count
        job.failed_record_count = failed_count
        job.activity_record_count = activity_count
        job.anomaly_record_count = anomaly_count
        job.save(update_fields=[
            'status',
            'finished_at',
            'raw_record_count',
            'parsed_record_count',
            'failed_record_count',
            'activity_record_count',
            'anomaly_record_count',
        ])

    return TravelIngestResult(job=job)

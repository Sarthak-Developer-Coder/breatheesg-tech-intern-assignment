from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from django.db import transaction
from django.utils import timezone

from core.models import (
    ActivityCategory,
    ActivityRecord,
    IngestionJob,
    IngestionJobStatus,
    Plant,
    RawRecord,
    RawRecordStatus,
    Scope,
    SourceType,
    Tenant,
)
from core.services.anomalies import detect_anomalies
from core.services.emissions import compute_co2e, find_emission_factor, snapshot_factor
from core.services.parsing import parse_date, parse_decimal
from core.services.units import convert_quantity, normalize_unit


@dataclass(frozen=True)
class UtilityIngestResult:
    job: IngestionJob


_UTILITY_HEADER_MAP: dict[str, str] = {
    'billing_start': 'billing_start',
    'billingstart': 'billing_start',
    'start_date': 'billing_start',
    'billing_end': 'billing_end',
    'billingend': 'billing_end',
    'end_date': 'billing_end',
    'kwh': 'kwh',
    'usage_kwh': 'kwh',
    'usage(kwh)': 'kwh',
    'peak_usage': 'peak_kwh',
    'peak_kwh': 'peak_kwh',
    'off_peak_usage': 'offpeak_kwh',
    'offpeak_kwh': 'offpeak_kwh',
    'meter_id': 'meter_id',
    'meter': 'meter_id',
    'tariff': 'tariff',
    'tariff_type': 'tariff',
    'plant_code': 'plant_code',
    'site': 'plant_code',
    'facility': 'plant_code',
}


def _canonicalize_header(header: str) -> str:
    return header.strip().lower().replace(' ', '').replace('-', '').replace('_', '')


def _map_headers(headers: Iterable[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for h in headers:
        key = _canonicalize_header(h)
        if key in _UTILITY_HEADER_MAP:
            mapped[h] = _UTILITY_HEADER_MAP[key]
    return mapped


def ingest_utility_csv(*, tenant: Tenant, uploaded_file, actor: str = '', source_label: str = '') -> UtilityIngestResult:
    job = IngestionJob.objects.create(
        tenant=tenant,
        source_type=SourceType.UTILITY_CSV,
        status=IngestionJobStatus.PROCESSING,
        created_by=actor or '',
        source_label=source_label or '',
        original_filename=getattr(uploaded_file, 'name', '') or '',
        started_at=timezone.now(),
    )

    raw_count = parsed_count = failed_count = activity_count = anomaly_count = 0

    raw_bytes = uploaded_file.read()
    try:
        text = raw_bytes.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw_bytes.decode('cp1252', errors='replace')

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ','

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    header_map = _map_headers(reader.fieldnames or [])

    with transaction.atomic():
        for idx, row in enumerate(reader, start=1):
            raw_count += 1

            raw_payload = dict(row)
            raw_text = json.dumps(raw_payload, ensure_ascii=False, separators=(',', ':'))
            raw_hash = hashlib.sha256(raw_text.encode('utf-8')).hexdigest()

            mapped: dict[str, Any] = {}
            for original_header, canonical in header_map.items():
                mapped[canonical] = row.get(original_header)

            billing_start = parse_date(mapped.get('billing_start'))
            billing_end = parse_date(mapped.get('billing_end'))

            meter_id = (mapped.get('meter_id') or '').strip()
            tariff = (mapped.get('tariff') or '').strip()
            plant_code = (mapped.get('plant_code') or '').strip()

            kwh = parse_decimal(mapped.get('kwh'))
            peak = parse_decimal(mapped.get('peak_kwh'))
            offpeak = parse_decimal(mapped.get('offpeak_kwh'))

            if kwh is None and (peak is not None or offpeak is not None):
                kwh = (peak or Decimal('0')) + (offpeak or Decimal('0'))

            # Some exports include a unit column; for this prototype we assume kWh unless it is obvious.
            unit_norm = 'kWh'

            if kwh is None:
                failed_count += 1
                RawRecord.objects.create(
                    tenant=tenant,
                    ingestion_job=job,
                    source_type=SourceType.UTILITY_CSV,
                    row_number=idx,
                    raw_payload=raw_payload,
                    raw_text=raw_text,
                    raw_hash_sha256=raw_hash,
                    status=RawRecordStatus.FAILED,
                    parse_errors=['missing_or_invalid_kwh'],
                )
                continue

            plant = None
            if plant_code:
                plant = Plant.objects.filter(tenant=tenant, code=plant_code).first()

            subcategory = 'grid_electricity'
            category = ActivityCategory.ELECTRICITY
            scope = Scope.SCOPE_2

            emission_factor = find_emission_factor(
                tenant=tenant,
                category=category,
                subcategory=subcategory,
                unit=unit_norm,
                at_date=billing_end or billing_start,
            )
            factor_snapshot = snapshot_factor(emission_factor)
            co2e = compute_co2e(quantity=kwh, factor=emission_factor)

            metadata = {
                'utility': {
                    'meter_id': meter_id,
                    'tariff': tariff,
                    'peak_kwh': str(peak) if peak is not None else None,
                    'offpeak_kwh': str(offpeak) if offpeak is not None else None,
                    'billing_start_raw': str(mapped.get('billing_start') or ''),
                    'billing_end_raw': str(mapped.get('billing_end') or ''),
                    'plant_code_raw': plant_code,
                }
            }

            anomaly = detect_anomalies(
                tenant=tenant,
                category=category,
                subcategory=subcategory,
                normalized_unit=unit_norm,
                quantity=kwh,
                activity_date=None,
                period_start=billing_start,
                period_end=billing_end,
                plant_id=plant.id if plant else None,
                metadata=metadata,
                emission_factor_found=emission_factor is not None,
            )

            raw_record = RawRecord.objects.create(
                tenant=tenant,
                ingestion_job=job,
                source_type=SourceType.UTILITY_CSV,
                row_number=idx,
                raw_payload=raw_payload,
                raw_text=raw_text,
                raw_hash_sha256=raw_hash,
                status=RawRecordStatus.PARSED,
                parse_errors=[],
            )
            parsed_count += 1

            ActivityRecord.objects.create(
                tenant=tenant,
                ingestion_job=job,
                raw_record=raw_record,
                source_type=SourceType.UTILITY_CSV,
                scope=scope,
                category=category,
                subcategory=subcategory,
                plant=plant,
                period_start=billing_start,
                period_end=billing_end,
                source_quantity=kwh,
                source_unit=unit_norm,
                quantity=kwh,
                normalized_unit=unit_norm,
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

    return UtilityIngestResult(job=job)

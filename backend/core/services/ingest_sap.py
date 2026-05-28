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
class SapIngestResult:
    job: IngestionJob


_SAP_HEADER_MAP: dict[str, str] = {
    # German
    'werk': 'plant_code',
    'buchungsdatum': 'date',
    'datum': 'date',
    'brennstofftyp': 'fuel_type',
    'menge': 'quantity',
    'einheit': 'unit',
    'material': 'material_code',
    'materialkurztext': 'material_desc',
    'materialgruppe': 'material_group',
    # English-ish
    'plant': 'plant_code',
    'plantcode': 'plant_code',
    'postingdate': 'date',
    'date': 'date',
    'fueltype': 'fuel_type',
    'qty': 'quantity',
    'quantity': 'quantity',
    'uom': 'unit',
    'unit': 'unit',
    'materialgroup': 'material_group',
}

_FUEL_SUBCATEGORY_MAP: dict[str, str] = {
    'diesel': 'diesel',
    'dieselöl': 'diesel',
    'dieseloel': 'diesel',
    'benzin': 'petrol',
    'gasoline': 'petrol',
    'petrol': 'petrol',
    'erdgas': 'natural_gas',
    'naturalgas': 'natural_gas',
    'heizöl': 'heating_oil',
    'heizoel': 'heating_oil',
    'heatingoil': 'heating_oil',
}

_PROCUREMENT_SUBCATEGORY_HINTS: list[tuple[str, str]] = [
    ('papier', 'paper'),
    ('paper', 'paper'),
    ('stahl', 'steel'),
    ('steel', 'steel'),
    ('plastik', 'plastic'),
    ('plastic', 'plastic'),
    ('chem', 'chemicals'),
]


def _canonicalize_header(header: str) -> str:
    return header.strip().lower().replace(' ', '').replace('-', '').replace('_', '')


def _map_headers(headers: Iterable[str]) -> dict[str, str]:
    mapped: dict[str, str] = {}
    for h in headers:
        key = _canonicalize_header(h)
        if key in _SAP_HEADER_MAP:
            mapped[h] = _SAP_HEADER_MAP[key]
    return mapped


def _guess_procurement_subcategory(material_group_raw: str, material_desc_raw: str) -> str:
    haystack = f"{material_group_raw} {material_desc_raw}".lower()
    for token, subcat in _PROCUREMENT_SUBCATEGORY_HINTS:
        if token in haystack:
            return subcat
    return 'unknown'


def ingest_sap_csv(*, tenant: Tenant, uploaded_file, actor: str = '', source_label: str = '') -> SapIngestResult:
    """Ingest a SAP flat-file CSV export.

    Ingestion mechanism: file upload (SAP exports are frequently delivered this way).
    """

    job = IngestionJob.objects.create(
        tenant=tenant,
        source_type=SourceType.SAP_CSV,
        status=IngestionJobStatus.PROCESSING,
        created_by=actor or '',
        source_label=source_label or '',
        original_filename=getattr(uploaded_file, 'name', '') or '',
        started_at=timezone.now(),
    )

    raw_count = parsed_count = failed_count = activity_count = anomaly_count = 0

    # Decode; SAP exports are often UTF-8 with BOM, or Windows-1252.
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
        dialect.delimiter = ';'

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

            plant_code = (mapped.get('plant_code') or '').strip()
            fuel_type_raw = (mapped.get('fuel_type') or '').strip()
            material_group_raw = (mapped.get('material_group') or '').strip()
            material_desc_raw = (mapped.get('material_desc') or '').strip()

            qty_raw = parse_decimal(mapped.get('quantity'))
            unit_raw = mapped.get('unit')
            unit_norm = normalize_unit(unit_raw)
            source_unit_norm = unit_norm

            dt = parse_date(mapped.get('date'))

            # Decide record type.
            is_fuel = bool(fuel_type_raw)
            if not is_fuel:
                # Heuristic: some clients encode fuel as a material group.
                if 'kraftstoff' in material_group_raw.lower() or 'fuel' in material_group_raw.lower():
                    is_fuel = True

            if is_fuel:
                category = ActivityCategory.FUEL
                scope = Scope.SCOPE_1
                subcategory = _FUEL_SUBCATEGORY_MAP.get(fuel_type_raw.lower().strip(), 'unknown')
                target_unit = 'liter'
            else:
                category = ActivityCategory.PROCUREMENT
                scope = Scope.SCOPE_3
                subcategory = _guess_procurement_subcategory(material_group_raw, material_desc_raw)
                target_unit = 'kg'

            plant = None
            if plant_code:
                plant = Plant.objects.filter(tenant=tenant, code=plant_code).first()

            # Parse success criteria: we need quantity + unit to create an ActivityRecord.
            if qty_raw is None or unit_norm is None:
                failed_count += 1
                RawRecord.objects.create(
                    tenant=tenant,
                    ingestion_job=job,
                    source_type=SourceType.SAP_CSV,
                    row_number=idx,
                    source_external_id='',
                    raw_payload=raw_payload,
                    raw_text=raw_text,
                    raw_hash_sha256=raw_hash,
                    status=RawRecordStatus.FAILED,
                    parse_errors=[
                        *(['missing_or_invalid_quantity'] if qty_raw is None else []),
                        *(['unknown_unit'] if unit_norm is None else []),
                    ],
                )
                continue

            qty_norm = qty_raw
            if unit_norm != target_unit:
                converted = convert_quantity(qty_raw, unit_norm, target_unit)
                if converted is not None:
                    qty_norm = converted
                    unit_norm = target_unit

            emission_factor = find_emission_factor(
                tenant=tenant,
                category=category,
                subcategory=subcategory,
                unit=unit_norm,
                at_date=dt,
            )
            factor_snapshot = snapshot_factor(emission_factor)
            co2e = compute_co2e(quantity=qty_norm, factor=emission_factor)

            metadata = {
                'sap': {
                    'plant_code_raw': plant_code,
                    'fuel_type_raw': fuel_type_raw,
                    'material_group_raw': material_group_raw,
                    'material_desc_raw': material_desc_raw,
                    'unit_raw': str(unit_raw) if unit_raw is not None else '',
                    'date_raw': str(mapped.get('date') or ''),
                }
            }

            anomaly = detect_anomalies(
                tenant=tenant,
                category=category,
                subcategory=subcategory,
                normalized_unit=unit_norm,
                quantity=qty_norm,
                activity_date=dt,
                period_start=None,
                period_end=None,
                plant_id=plant.id if plant else None,
                metadata=metadata,
                emission_factor_found=emission_factor is not None,
            )

            raw_record = RawRecord.objects.create(
                tenant=tenant,
                ingestion_job=job,
                source_type=SourceType.SAP_CSV,
                row_number=idx,
                source_external_id='',
                raw_payload=raw_payload,
                raw_text=raw_text,
                raw_hash_sha256=raw_hash,
                status=RawRecordStatus.PARSED,
                parse_errors=[],
            )
            parsed_count += 1

            activity = ActivityRecord.objects.create(
                tenant=tenant,
                ingestion_job=job,
                raw_record=raw_record,
                source_type=SourceType.SAP_CSV,
                source_external_id='',
                scope=scope,
                category=category,
                subcategory=subcategory,
                plant=plant,
                activity_date=dt,
                source_quantity=qty_raw,
                source_unit=source_unit_norm or '',
                quantity=qty_norm,
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

    return SapIngestResult(job=job)

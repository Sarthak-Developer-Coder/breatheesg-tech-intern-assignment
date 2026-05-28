from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg

from core.models import ActivityRecord, ActivityCategory, Tenant


@dataclass(frozen=True)
class AnomalyResult:
    flags: list[str]
    confidence_score: Decimal


def _clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    if value < low:
        return low
    if value > high:
        return high
    return value


def detect_anomalies(
    *,
    tenant: Tenant,
    category: str,
    subcategory: str,
    normalized_unit: str | None,
    quantity: Decimal | None,
    activity_date: date | None,
    period_start: date | None,
    period_end: date | None,
    plant_id: int | None,
    metadata: dict,
    emission_factor_found: bool,
) -> AnomalyResult:
    flags: list[str] = []

    today = date.today()

    if quantity is None:
        flags.append('missing_quantity')
    else:
        if quantity < 0:
            flags.append('negative_quantity')
        if quantity == 0:
            flags.append('zero_quantity')

    if not normalized_unit:
        flags.append('unknown_unit')

    if activity_date and activity_date > today + timedelta(days=1):
        flags.append('future_date')

    if period_start and period_end:
        if period_end < period_start:
            flags.append('invalid_billing_period')
        if (period_end - period_start).days > 45:
            flags.append('unusually_long_billing_period')

    if category in {ActivityCategory.FUEL, ActivityCategory.ELECTRICITY, ActivityCategory.PROCUREMENT}:
        if plant_id is None:
            flags.append('unknown_plant')

    if category == ActivityCategory.TRAVEL:
        origin = (metadata.get('origin_airport') or '').strip().upper()
        dest = (metadata.get('destination_airport') or '').strip().upper()
        if origin and dest and origin == dest:
            flags.append('invalid_route_same_airport')
        if (metadata.get('mode') == 'flight') and (not origin or not dest):
            flags.append('missing_airports')
        if metadata.get('mode') == 'flight' and metadata.get('distance_km_estimated') is True:
            flags.append('estimated_distance')

    if not emission_factor_found:
        flags.append('missing_emission_factor')

    # Spike detection: compare to the last 90 days of similar records.
    if quantity is not None and quantity > 0 and normalized_unit:
        baseline_qs = ActivityRecord.objects.filter(
            tenant=tenant,
            category=category,
            subcategory=subcategory,
            normalized_unit=normalized_unit,
        )
        if plant_id is not None:
            baseline_qs = baseline_qs.filter(plant_id=plant_id)

        window_start = today - timedelta(days=90)
        baseline_qs = baseline_qs.filter(created_at__date__gte=window_start)

        baseline_avg = baseline_qs.aggregate(avg=Avg('quantity')).get('avg')
        if baseline_avg is not None and baseline_avg > 0:
            if quantity > (baseline_avg * Decimal('10')):
                flags.append('spike_vs_recent_avg')

    # Confidence score: start high, degrade with anomalies.
    score = Decimal('0.95')
    for flag in flags:
        if flag in {'negative_quantity', 'invalid_billing_period', 'missing_emission_factor', 'unknown_unit'}:
            score -= Decimal('0.20')
        elif flag in {'unknown_plant', 'missing_airports'}:
            score -= Decimal('0.15')
        elif flag in {'estimated_distance'}:
            score -= Decimal('0.05')
        else:
            score -= Decimal('0.03')

    return AnomalyResult(flags=flags, confidence_score=_clamp(score, Decimal('0.0'), Decimal('1.0')))

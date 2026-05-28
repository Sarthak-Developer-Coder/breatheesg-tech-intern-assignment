from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Q

from core.models import EmissionFactor, Tenant


@dataclass(frozen=True)
class EmissionComputation:
    factor: EmissionFactor | None
    factor_snapshot: dict
    co2e_kg: Decimal | None


def find_emission_factor(
    *,
    tenant: Tenant,
    category: str,
    subcategory: str,
    unit: str,
    at_date: date | None = None,
) -> EmissionFactor | None:
    """Tenant-first then global emission factor lookup."""

    base = EmissionFactor.objects.filter(
        is_active=True,
        category=category,
        subcategory=subcategory,
        unit=unit,
    ).filter(Q(tenant=tenant) | Q(tenant__isnull=True))

    if at_date is not None:
        base = base.filter(Q(valid_from__isnull=True) | Q(valid_from__lte=at_date)).filter(
            Q(valid_to__isnull=True) | Q(valid_to__gte=at_date)
        )

    # Prefer tenant-specific factors.
    tenant_factor = base.filter(tenant=tenant).order_by('-created_at').first()
    if tenant_factor:
        return tenant_factor

    return base.filter(tenant__isnull=True).order_by('-created_at').first()


def compute_co2e(
    *,
    quantity: Decimal | None,
    factor: EmissionFactor | None,
) -> Decimal | None:
    if quantity is None or factor is None:
        return None

    return (quantity * factor.co2e_kg_per_unit).quantize(Decimal('0.000001'))


def snapshot_factor(factor: EmissionFactor | None) -> dict:
    if factor is None:
        return {}

    return {
        'id': factor.id,
        'tenant_id': factor.tenant_id,
        'scope': factor.scope,
        'category': factor.category,
        'subcategory': factor.subcategory,
        'unit': factor.unit,
        'co2e_kg_per_unit': str(factor.co2e_kg_per_unit),
        'region': factor.region,
        'source': factor.source,
        'valid_from': factor.valid_from.isoformat() if factor.valid_from else None,
        'valid_to': factor.valid_to.isoformat() if factor.valid_to else None,
        'created_at': factor.created_at.isoformat() if factor.created_at else None,
    }

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.models import (
    ActivityChangeLog,
    ActivityChangeType,
    ActivityRecord,
    ReviewDecision,
    ReviewDecisionType,
    ReviewStatus,
)


class LockedActivityError(Exception):
    pass


def snapshot_activity(activity: ActivityRecord) -> dict[str, Any]:
    return {
        'id': activity.id,
        'tenant_id': activity.tenant_id,
        'source_type': activity.source_type,
        'source_external_id': activity.source_external_id,
        'scope': activity.scope,
        'category': activity.category,
        'subcategory': activity.subcategory,
        'plant_id': activity.plant_id,
        'activity_date': activity.activity_date.isoformat() if activity.activity_date else None,
        'period_start': activity.period_start.isoformat() if activity.period_start else None,
        'period_end': activity.period_end.isoformat() if activity.period_end else None,
        'source_quantity': str(activity.source_quantity) if activity.source_quantity is not None else None,
        'source_unit': activity.source_unit,
        'quantity': str(activity.quantity),
        'normalized_unit': activity.normalized_unit,
        'co2e_kg': str(activity.co2e_kg) if activity.co2e_kg is not None else None,
        'emission_factor_id': activity.emission_factor_id,
        'emission_factor_snapshot': activity.emission_factor_snapshot,
        'activity_metadata': activity.activity_metadata,
        'anomaly_flags': activity.anomaly_flags,
        'confidence_score': str(activity.confidence_score),
        'review_status': activity.review_status,
        'approved_at': activity.approved_at.isoformat() if activity.approved_at else None,
        'approved_by': activity.approved_by,
        'locked_at': activity.locked_at.isoformat() if activity.locked_at else None,
        'locked_by': activity.locked_by,
        'updated_at': activity.updated_at.isoformat() if activity.updated_at else None,
    }


_ALLOWED_EDIT_FIELDS = {
    'scope',
    'category',
    'subcategory',
    'plant_id',
    'activity_date',
    'period_start',
    'period_end',
    'quantity',
    'normalized_unit',
    'activity_metadata',
}


def edit_activity(*, activity: ActivityRecord, actor: str, updates: dict[str, Any], reason: str = '') -> ActivityRecord:
    if activity.is_locked:
        raise LockedActivityError('ActivityRecord is locked for audit')

    update_keys = set(updates.keys())
    illegal = sorted(update_keys - _ALLOWED_EDIT_FIELDS)
    if illegal:
        raise ValueError(f"Illegal update fields: {', '.join(illegal)}")

    before = snapshot_activity(activity)

    for key, value in updates.items():
        setattr(activity, key, value)

    activity.last_edited_at = timezone.now()
    activity.last_edited_by = actor

    # Ensure model validation for date/period rules.
    activity.full_clean()

    after = snapshot_activity(activity)
    changed_fields = [k for k in _ALLOWED_EDIT_FIELDS if before.get(k) != after.get(k)]

    with transaction.atomic():
        activity.save()
        ActivityChangeLog.objects.create(
            tenant_id=activity.tenant_id,
            activity_record=activity,
            change_type=ActivityChangeType.EDIT,
            changed_by=actor,
            reason=reason,
            before=before,
            after=after,
            changed_fields=changed_fields,
        )

    return activity


def approve_activity(*, activity: ActivityRecord, actor: str, reason: str = '') -> ActivityRecord:
    if activity.is_locked:
        raise LockedActivityError('ActivityRecord is locked for audit')

    now = timezone.now()

    before = snapshot_activity(activity)

    with transaction.atomic():
        activity.review_status = ReviewStatus.APPROVED
        activity.approved_at = now
        activity.approved_by = actor

        # Prototype behavior: approval locks for audit.
        activity.locked_at = now
        activity.locked_by = actor
        activity.full_clean()
        activity.save()

        ReviewDecision.objects.create(
            tenant_id=activity.tenant_id,
            activity_record=activity,
            decision=ReviewDecisionType.APPROVE,
            decided_by=actor,
            reason=reason,
            activity_snapshot=snapshot_activity(activity),
        )

        ActivityChangeLog.objects.create(
            tenant_id=activity.tenant_id,
            activity_record=activity,
            change_type=ActivityChangeType.EDIT,
            changed_by=actor,
            reason=f"approve: {reason}".strip(),
            before=before,
            after=snapshot_activity(activity),
            changed_fields=['review_status', 'approved_at', 'approved_by', 'locked_at', 'locked_by'],
        )

    return activity


def reject_activity(*, activity: ActivityRecord, actor: str, reason: str = '') -> ActivityRecord:
    if activity.is_locked:
        raise LockedActivityError('ActivityRecord is locked for audit')

    before = snapshot_activity(activity)

    with transaction.atomic():
        activity.review_status = ReviewStatus.REJECTED
        activity.full_clean()
        activity.save()

        ReviewDecision.objects.create(
            tenant_id=activity.tenant_id,
            activity_record=activity,
            decision=ReviewDecisionType.REJECT,
            decided_by=actor,
            reason=reason,
            activity_snapshot=snapshot_activity(activity),
        )

        ActivityChangeLog.objects.create(
            tenant_id=activity.tenant_id,
            activity_record=activity,
            change_type=ActivityChangeType.EDIT,
            changed_by=actor,
            reason=f"reject: {reason}".strip(),
            before=before,
            after=snapshot_activity(activity),
            changed_fields=['review_status'],
        )

    return activity

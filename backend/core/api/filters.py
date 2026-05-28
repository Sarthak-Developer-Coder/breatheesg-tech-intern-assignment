from __future__ import annotations

import django_filters

from core.models import ActivityRecord, IngestionJob


class IngestionJobFilter(django_filters.FilterSet):
    source_type = django_filters.CharFilter(field_name='source_type')
    status = django_filters.CharFilter(field_name='status')

    class Meta:
        model = IngestionJob
        fields = ['source_type', 'status']


class ActivityRecordFilter(django_filters.FilterSet):
    review_status = django_filters.CharFilter(field_name='review_status')
    source_type = django_filters.CharFilter(field_name='source_type')
    category = django_filters.CharFilter(field_name='category')
    subcategory = django_filters.CharFilter(field_name='subcategory')
    plant_code = django_filters.CharFilter(field_name='plant__code')

    has_anomalies = django_filters.BooleanFilter(method='filter_has_anomalies')
    is_locked = django_filters.BooleanFilter(method='filter_is_locked')

    class Meta:
        model = ActivityRecord
        fields = [
            'review_status',
            'source_type',
            'category',
            'subcategory',
            'plant_code',
            'has_anomalies',
            'is_locked',
        ]

    def filter_has_anomalies(self, queryset, name, value):
        if value is True:
            return queryset.exclude(anomaly_flags=[])
        if value is False:
            return queryset.filter(anomaly_flags=[])
        return queryset

    def filter_is_locked(self, queryset, name, value):
        if value is True:
            return queryset.filter(locked_at__isnull=False)
        if value is False:
            return queryset.filter(locked_at__isnull=True)
        return queryset

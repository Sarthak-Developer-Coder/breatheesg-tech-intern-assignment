from __future__ import annotations

from rest_framework import serializers

from core.models import ActivityRecord, IngestionJob, Plant


class IngestionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngestionJob
        fields = [
            'id',
            'tenant_id',
            'source_type',
            'status',
            'created_by',
            'source_label',
            'original_filename',
            'raw_record_count',
            'parsed_record_count',
            'failed_record_count',
            'activity_record_count',
            'anomaly_record_count',
            'started_at',
            'finished_at',
            'error_message',
            'summary',
            'created_at',
            'updated_at',
        ]


class ActivityRecordListSerializer(serializers.ModelSerializer):
    plant_code = serializers.CharField(source='plant.code', read_only=True)
    plant_name = serializers.CharField(source='plant.name', read_only=True)

    class Meta:
        model = ActivityRecord
        fields = [
            'id',
            'tenant_id',
            'ingestion_job_id',
            'raw_record_id',
            'source_type',
            'source_external_id',
            'scope',
            'category',
            'subcategory',
            'plant_id',
            'plant_code',
            'plant_name',
            'activity_date',
            'period_start',
            'period_end',
            'source_quantity',
            'source_unit',
            'quantity',
            'normalized_unit',
            'co2e_kg',
            'anomaly_flags',
            'confidence_score',
            'review_status',
            'approved_at',
            'approved_by',
            'locked_at',
            'locked_by',
            'last_edited_at',
            'last_edited_by',
            'created_at',
            'updated_at',
        ]


class ActivityRecordDetailSerializer(serializers.ModelSerializer):
    plant_code = serializers.CharField(source='plant.code', read_only=True)
    plant_name = serializers.CharField(source='plant.name', read_only=True)

    class Meta:
        model = ActivityRecord
        fields = ActivityRecordListSerializer.Meta.fields + [
            'emission_factor_id',
            'emission_factor_snapshot',
            'activity_metadata',
        ]


class ActivityRecordEditSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(write_only=True)
    reason = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ActivityRecord
        fields = [
            'actor',
            'reason',
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
        ]


class ReviewActionSerializer(serializers.Serializer):
    actor = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True)

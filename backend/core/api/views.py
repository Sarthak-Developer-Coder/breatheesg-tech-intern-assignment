from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from rest_framework import generics, parsers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.filters import ActivityRecordFilter, IngestionJobFilter
from core.api.serializers import (
    ActivityRecordDetailSerializer,
    ActivityRecordEditSerializer,
    ActivityRecordListSerializer,
    IngestionJobSerializer,
    ReviewActionSerializer,
)
from core.models import ActivityRecord, IngestionJob
from core.services.ingest_sap import ingest_sap_csv
from core.services.ingest_travel import ingest_travel_payload
from core.services.ingest_utility import ingest_utility_csv
from core.services.review import LockedActivityError, approve_activity, edit_activity, reject_activity


def _tenant(request):
    return getattr(request, 'tenant', None)


class UploadSapView(APIView):
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        tenant = _tenant(request)
        if tenant is None:
            return Response({'detail': 'Tenant not resolved'}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES.get('file')
        if uploaded_file is None:
            return Response({'detail': 'Missing file'}, status=status.HTTP_400_BAD_REQUEST)

        actor = str(request.data.get('actor') or request.headers.get('X-Actor') or '').strip()
        source_label = str(request.data.get('source_label') or '').strip()

        result = ingest_sap_csv(tenant=tenant, uploaded_file=uploaded_file, actor=actor, source_label=source_label)
        return Response(IngestionJobSerializer(result.job).data, status=status.HTTP_201_CREATED)


class UploadUtilityView(APIView):
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        tenant = _tenant(request)
        if tenant is None:
            return Response({'detail': 'Tenant not resolved'}, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES.get('file')
        if uploaded_file is None:
            return Response({'detail': 'Missing file'}, status=status.HTTP_400_BAD_REQUEST)

        actor = str(request.data.get('actor') or request.headers.get('X-Actor') or '').strip()
        source_label = str(request.data.get('source_label') or '').strip()

        result = ingest_utility_csv(tenant=tenant, uploaded_file=uploaded_file, actor=actor, source_label=source_label)
        return Response(IngestionJobSerializer(result.job).data, status=status.HTTP_201_CREATED)


class UploadTravelView(APIView):
    def post(self, request):
        tenant = _tenant(request)
        if tenant is None:
            return Response({'detail': 'Tenant not resolved'}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(request.data, dict):
            return Response({'detail': 'Expected JSON object'}, status=status.HTTP_400_BAD_REQUEST)

        actor = str(request.data.get('actor') or request.headers.get('X-Actor') or '').strip()
        source_label = str(request.data.get('source_label') or '').strip()

        payload: dict[str, Any] = dict(request.data)
        # Remove non-source wrapper fields
        payload.pop('actor', None)
        payload.pop('source_label', None)

        result = ingest_travel_payload(tenant=tenant, payload=payload, actor=actor, source_label=source_label)
        return Response(IngestionJobSerializer(result.job).data, status=status.HTTP_201_CREATED)


class IngestionJobListView(generics.ListAPIView):
    serializer_class = IngestionJobSerializer
    filterset_class = IngestionJobFilter
    ordering = ['-created_at']

    def get_queryset(self):
        tenant = _tenant(self.request)
        return IngestionJob.objects.filter(tenant=tenant)


class ActivityRecordListView(generics.ListAPIView):
    serializer_class = ActivityRecordListSerializer
    filterset_class = ActivityRecordFilter
    ordering = ['-created_at']

    def get_queryset(self):
        tenant = _tenant(self.request)
        return ActivityRecord.objects.select_related('plant').filter(tenant=tenant)


class ActivityRecordDetailView(generics.RetrieveAPIView):
    serializer_class = ActivityRecordDetailSerializer

    def get_queryset(self):
        tenant = _tenant(self.request)
        return ActivityRecord.objects.select_related('plant').filter(tenant=tenant)


class ActivityRecordEditView(APIView):
    """Edit an ActivityRecord before approval.

    Uses a thin API layer; the actual write + audit log are in core.services.review.
    """

    def patch(self, request, pk: int):
        tenant = _tenant(request)
        activity = get_object_or_404(ActivityRecord, tenant=tenant, pk=pk)

        serializer = ActivityRecordEditSerializer(activity, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        actor = serializer.validated_data.pop('actor')
        reason = serializer.validated_data.pop('reason', '')

        try:
            updated = edit_activity(activity=activity, actor=actor, updates=serializer.validated_data, reason=reason)
        except LockedActivityError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(ActivityRecordDetailSerializer(updated).data)


class ReviewQueueView(generics.ListAPIView):
    serializer_class = ActivityRecordListSerializer
    filterset_class = ActivityRecordFilter
    ordering = ['-created_at']

    def get_queryset(self):
        tenant = _tenant(self.request)
        return (
            ActivityRecord.objects.select_related('plant')
            .filter(tenant=tenant, review_status='pending')
        )


class ApproveView(APIView):
    def post(self, request, pk: int):
        tenant = _tenant(request)
        activity = get_object_or_404(ActivityRecord, tenant=tenant, pk=pk)

        serializer = ReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = approve_activity(
                activity=activity,
                actor=serializer.validated_data['actor'],
                reason=serializer.validated_data.get('reason', ''),
            )
        except LockedActivityError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(ActivityRecordDetailSerializer(updated).data)


class RejectView(APIView):
    def post(self, request, pk: int):
        tenant = _tenant(request)
        activity = get_object_or_404(ActivityRecord, tenant=tenant, pk=pk)

        serializer = ReviewActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = reject_activity(
                activity=activity,
                actor=serializer.validated_data['actor'],
                reason=serializer.validated_data.get('reason', ''),
            )
        except LockedActivityError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(ActivityRecordDetailSerializer(updated).data)

from __future__ import annotations

from django.urls import path

from core.api import views


urlpatterns = [
    path('upload/sap', views.UploadSapView.as_view(), name='upload-sap'),
    path('upload/sap/', views.UploadSapView.as_view()),
    path('upload/utility', views.UploadUtilityView.as_view(), name='upload-utility'),
    path('upload/utility/', views.UploadUtilityView.as_view()),
    path('upload/travel', views.UploadTravelView.as_view(), name='upload-travel'),
    path('upload/travel/', views.UploadTravelView.as_view()),

    path('ingestion-jobs', views.IngestionJobListView.as_view(), name='ingestion-jobs'),
    path('ingestion-jobs/', views.IngestionJobListView.as_view()),

    path('activity-records', views.ActivityRecordListView.as_view(), name='activity-records'),
    path('activity-records/', views.ActivityRecordListView.as_view()),
    path('activity-records/<int:pk>', views.ActivityRecordDetailView.as_view(), name='activity-record-detail'),
    path('activity-records/<int:pk>/', views.ActivityRecordDetailView.as_view()),
    path('activity-records/<int:pk>/edit', views.ActivityRecordEditView.as_view(), name='activity-record-edit'),
    path('activity-records/<int:pk>/edit/', views.ActivityRecordEditView.as_view()),

    path('review-queue', views.ReviewQueueView.as_view(), name='review-queue'),
    path('review-queue/', views.ReviewQueueView.as_view()),

    path('review/<int:pk>/approve', views.ApproveView.as_view(), name='review-approve'),
    path('review/<int:pk>/approve/', views.ApproveView.as_view()),
    path('review/<int:pk>/reject', views.RejectView.as_view(), name='review-reject'),
    path('review/<int:pk>/reject/', views.RejectView.as_view()),
]

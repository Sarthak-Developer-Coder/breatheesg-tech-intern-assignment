from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models


class TimeStampedModel(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True


class Tenant(TimeStampedModel):
	"""An enterprise client.

	Deliberately simple tenant isolation: every major entity carries tenant_id.
	"""

	name = models.CharField(max_length=200)
	slug = models.SlugField(max_length=80, unique=True)

	def __str__(self) -> str:
		return self.name


class Plant(TimeStampedModel):
	"""A facility / plant / cost center-like unit within a tenant.

	Used primarily to map SAP `Werk` codes and to group utility meters.
	"""

	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	code = models.CharField(max_length=50)
	name = models.CharField(max_length=200)
	country = models.CharField(max_length=2, blank=True, default='')
	timezone = models.CharField(max_length=64, blank=True, default='')
	metadata = models.JSONField(default=dict, blank=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['tenant', 'code'], name='uq_plant_tenant_code'),
		]
		indexes = [
			models.Index(fields=['tenant', 'code']),
		]

	def __str__(self) -> str:
		return f"{self.tenant.slug}:{self.code}"


class IngestionJobStatus(models.TextChoices):
	RECEIVED = 'received', 'Received'
	PROCESSING = 'processing', 'Processing'
	COMPLETED = 'completed', 'Completed'
	FAILED = 'failed', 'Failed'


class SourceType(models.TextChoices):
	SAP_CSV = 'sap_csv', 'SAP CSV'
	UTILITY_CSV = 'utility_csv', 'Utility CSV'
	TRAVEL_API = 'travel_api', 'Travel API'


class IngestionJob(TimeStampedModel):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)

	source_type = models.CharField(max_length=30, choices=SourceType.choices)
	status = models.CharField(
		max_length=20,
		choices=IngestionJobStatus.choices,
		default=IngestionJobStatus.RECEIVED,
	)

	# Traceability
	created_by = models.CharField(max_length=200, blank=True, default='')
	source_label = models.CharField(max_length=200, blank=True, default='')
	original_filename = models.CharField(max_length=255, blank=True, default='')

	# Summary counters (duplicated on purpose for fast dashboards)
	raw_record_count = models.PositiveIntegerField(default=0)
	parsed_record_count = models.PositiveIntegerField(default=0)
	failed_record_count = models.PositiveIntegerField(default=0)
	activity_record_count = models.PositiveIntegerField(default=0)
	anomaly_record_count = models.PositiveIntegerField(default=0)

	started_at = models.DateTimeField(null=True, blank=True)
	finished_at = models.DateTimeField(null=True, blank=True)

	error_message = models.TextField(blank=True, default='')
	summary = models.JSONField(default=dict, blank=True)

	class Meta:
		indexes = [
			models.Index(fields=['tenant', 'created_at']),
			models.Index(fields=['tenant', 'source_type', 'status']),
		]

	def __str__(self) -> str:
		return f"{self.tenant.slug}:{self.source_type}:{self.id}"


class RawRecordStatus(models.TextChoices):
	PARSED = 'parsed', 'Parsed'
	FAILED = 'failed', 'Failed'


class RawRecord(TimeStampedModel):
	"""Raw source record stored exactly as received.

	This is the foundation for auditability: normalization *adds* an ActivityRecord
	but never mutates or discards the raw input.
	"""

	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	ingestion_job = models.ForeignKey(IngestionJob, on_delete=models.CASCADE, related_name='raw_records')

	source_type = models.CharField(max_length=30, choices=SourceType.choices)
	row_number = models.PositiveIntegerField(null=True, blank=True)
	source_external_id = models.CharField(max_length=200, blank=True, default='')

	# Raw payload & integrity
	raw_payload = models.JSONField()
	raw_text = models.TextField(blank=True, default='')
	raw_hash_sha256 = models.CharField(max_length=64, blank=True, default='')

	status = models.CharField(max_length=20, choices=RawRecordStatus.choices, default=RawRecordStatus.PARSED)
	parse_errors = models.JSONField(default=list, blank=True)

	class Meta:
		indexes = [
			models.Index(fields=['tenant', 'ingestion_job', 'status']),
			models.Index(fields=['tenant', 'source_type', 'created_at']),
		]


class Scope(models.TextChoices):
	SCOPE_1 = 'scope_1', 'Scope 1'
	SCOPE_2 = 'scope_2', 'Scope 2'
	SCOPE_3 = 'scope_3', 'Scope 3'


class ActivityCategory(models.TextChoices):
	FUEL = 'fuel_combustion', 'Fuel combustion'
	ELECTRICITY = 'purchased_electricity', 'Purchased electricity'
	TRAVEL = 'business_travel', 'Business travel'
	PROCUREMENT = 'procurement', 'Procurement'


class ReviewStatus(models.TextChoices):
	PENDING = 'pending', 'Pending'
	APPROVED = 'approved', 'Approved'
	REJECTED = 'rejected', 'Rejected'


class EmissionFactor(TimeStampedModel):
	"""Emission factor catalog.

	For this prototype we keep it small and versionable.
	`tenant` is nullable: null == shared/global factor.
	"""

	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)

	scope = models.CharField(max_length=20, choices=Scope.choices)
	category = models.CharField(max_length=40, choices=ActivityCategory.choices)
	subcategory = models.CharField(max_length=60)

	# e.g. 'kWh', 'liter', 'km', 'night'
	unit = models.CharField(max_length=30)

	# kgCO2e per unit
	co2e_kg_per_unit = models.DecimalField(max_digits=18, decimal_places=6)

	region = models.CharField(max_length=50, blank=True, default='')
	source = models.CharField(max_length=200, blank=True, default='')
	valid_from = models.DateField(null=True, blank=True)
	valid_to = models.DateField(null=True, blank=True)
	is_active = models.BooleanField(default=True)

	class Meta:
		indexes = [
			models.Index(fields=['tenant', 'category', 'subcategory', 'unit']),
			models.Index(fields=['is_active', 'valid_from', 'valid_to']),
		]

	def __str__(self) -> str:
		tenant_part = self.tenant.slug if self.tenant_id else 'global'
		return f"{tenant_part}:{self.category}:{self.subcategory}:{self.unit}"


class ActivityRecord(TimeStampedModel):
	"""Canonical ESG activity row created from a RawRecord.

	This is what analysts review/edit/approve. RawRecord remains immutable.
	Once locked, ActivityRecord is treated as immutable through the API.
	"""

	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	ingestion_job = models.ForeignKey(IngestionJob, on_delete=models.SET_NULL, null=True, blank=True)
	raw_record = models.OneToOneField(RawRecord, on_delete=models.PROTECT, related_name='activity_record')

	source_type = models.CharField(max_length=30, choices=SourceType.choices)
	source_external_id = models.CharField(max_length=200, blank=True, default='')

	scope = models.CharField(max_length=20, choices=Scope.choices)
	category = models.CharField(max_length=40, choices=ActivityCategory.choices)
	subcategory = models.CharField(max_length=60)

	plant = models.ForeignKey(Plant, on_delete=models.SET_NULL, null=True, blank=True)

	activity_date = models.DateField(null=True, blank=True)
	period_start = models.DateField(null=True, blank=True)
	period_end = models.DateField(null=True, blank=True)

	# Source values as received/parsed
	source_quantity = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
	source_unit = models.CharField(max_length=30, blank=True, default='')

	# Normalized values
	quantity = models.DecimalField(max_digits=20, decimal_places=6)
	normalized_unit = models.CharField(max_length=30)

	# Derived emissions
	emission_factor = models.ForeignKey(EmissionFactor, on_delete=models.SET_NULL, null=True, blank=True)
	emission_factor_snapshot = models.JSONField(default=dict, blank=True)
	co2e_kg = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)

	# Category-specific details that don’t belong as global columns.
	# Examples: meter_id/tariff, airports/cabin, etc.
	activity_metadata = models.JSONField(default=dict, blank=True)

	anomaly_flags = models.JSONField(default=list, blank=True)
	confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0.500)

	review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)

	approved_at = models.DateTimeField(null=True, blank=True)
	approved_by = models.CharField(max_length=200, blank=True, default='')

	locked_at = models.DateTimeField(null=True, blank=True)
	locked_by = models.CharField(max_length=200, blank=True, default='')

	last_edited_at = models.DateTimeField(null=True, blank=True)
	last_edited_by = models.CharField(max_length=200, blank=True, default='')

	class Meta:
		indexes = [
			models.Index(fields=['tenant', 'review_status', 'created_at']),
			models.Index(fields=['tenant', 'category', 'subcategory']),
			models.Index(fields=['tenant', 'source_type', 'activity_date']),
		]

	@property
	def is_locked(self) -> bool:
		return self.locked_at is not None

	def clean(self) -> None:
		if self.period_start and self.period_end and self.period_end < self.period_start:
			raise ValidationError({'period_end': 'period_end must be on/after period_start'})

		if self.activity_date and (self.period_start or self.period_end):
			# Allow either point-in-time or period-based activities, but not both.
			raise ValidationError('Use either activity_date or a billing period, not both.')


class ReviewDecisionType(models.TextChoices):
	APPROVE = 'approve', 'Approve'
	REJECT = 'reject', 'Reject'


class ReviewDecision(TimeStampedModel):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	activity_record = models.ForeignKey(ActivityRecord, on_delete=models.CASCADE, related_name='review_decisions')

	decision = models.CharField(max_length=20, choices=ReviewDecisionType.choices)
	decided_by = models.CharField(max_length=200)
	reason = models.TextField(blank=True, default='')

	# Immutable audit snapshot of the ActivityRecord at decision time.
	activity_snapshot = models.JSONField(default=dict)

	class Meta:
		indexes = [
			models.Index(fields=['tenant', 'decision', 'created_at']),
		]


class ActivityChangeType(models.TextChoices):
	EDIT = 'edit', 'Edit'
	SYSTEM_RECALC = 'system_recalc', 'System recalculation'


class ActivityChangeLog(TimeStampedModel):
	tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
	activity_record = models.ForeignKey(ActivityRecord, on_delete=models.CASCADE, related_name='change_logs')

	change_type = models.CharField(max_length=30, choices=ActivityChangeType.choices)
	changed_by = models.CharField(max_length=200)
	reason = models.TextField(blank=True, default='')

	before = models.JSONField(default=dict)
	after = models.JSONField(default=dict)
	changed_fields = models.JSONField(default=list)

	class Meta:
		indexes = [
			models.Index(fields=['tenant', 'activity_record', 'created_at']),
		]

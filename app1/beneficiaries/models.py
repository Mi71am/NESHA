from django.db import models
from decimal import Decimal


class Beneficiary(models.Model):
	class AllocationStatus(models.TextChoices):
		ACTIVE = "active", "Active"
		PENDING_APPROVAL = "pending_approval", "Pending Approval"
		NOT_ELIGIBLE = "not_eligible", "Not Eligible"
		FLAGGED = "flagged", "Flagged for Reassessment"

	class ReassessmentStatus(models.TextChoices):
		NOT_REQUIRED = "not_required", "Not Required"
		PENDING_REASSESSMENT = "pending_reassessment", "Pending Reassessment"
		FLAGGED = "flagged", "Flagged"

	beneficiary_id = models.AutoField(primary_key=True)
	representative = models.ForeignKey(
		"accounts.SchoolRepresentative",
		on_delete=models.CASCADE,
		db_column="representative_id",
		related_name="beneficiaries",
		blank=True,
		null=True,
	)
	learner_name = models.CharField(max_length=100, blank=True, null=True)
	learner_gender = models.CharField(max_length=16, blank=True, null=True)
	tap2eat_acc_no = models.CharField(max_length=50, blank=True, null=True)
	eligibility_score = models.IntegerField(blank=True, null=True)
	allocation_status = models.CharField(
		max_length=32,
		choices=AllocationStatus.choices,
		default=AllocationStatus.PENDING_APPROVAL,
	)
	support_cycle_count = models.IntegerField(default=0)
	pending_half_cycle = models.BooleanField(default=False)
	reassessment_status = models.CharField(
		max_length=32,
		choices=ReassessmentStatus.choices,
		default=ReassessmentStatus.NOT_REQUIRED,
	)
	reassessment_due_date = models.DateField(blank=True, null=True)
	last_allocation_date = models.DateField(blank=True, null=True)
	rejection_reason = models.CharField(max_length=255, blank=True)
	is_removed = models.BooleanField(default=False)
	removal_reason = models.CharField(max_length=255, blank=True)
	removal_date = models.DateField(blank=True, null=True)
	registration_date = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "beneficiary"

	@property
	def effective_cycle_count(self):
		return Decimal(self.support_cycle_count) + (Decimal("0.5") if self.pending_half_cycle else Decimal("0.0"))


class EligibilityAssessment(models.Model):
	class Status(models.TextChoices):
		DRAFT = "draft", "Draft"
		SUBMITTED = "submitted", "Submitted"

	assessment_id = models.AutoField(primary_key=True)
	beneficiary = models.ForeignKey(
		Beneficiary,
		on_delete=models.CASCADE,
		db_column="beneficiary_id",
		related_name="assessments",
	)
	questionnaire_score = models.IntegerField(blank=True, null=True)
	total_score = models.IntegerField(blank=True, null=True)
	is_eligible = models.BooleanField(default=False)
	inconsistency_flagged = models.BooleanField(default=False)
	inconsistency_notes = models.TextField(blank=True)
	status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
	answers = models.JSONField(default=dict, blank=True)
	evidence_statement_1 = models.TextField(blank=True)
	evidence_statement_2 = models.TextField(blank=True)
	verification_confirmed = models.BooleanField(default=False)
	assessment_date = models.DateTimeField(auto_now_add=True)
	remarks = models.TextField(blank=True, null=True)

	class Meta:
		db_table = "eligibility_assessment"


class Allocation(models.Model):
	allocation_id = models.AutoField(primary_key=True)
	beneficiary = models.ForeignKey(
		Beneficiary,
		on_delete=models.CASCADE,
		db_column="beneficiary_id",
		related_name="allocations",
	)
	batch = models.ForeignKey(
		"donations.DistributionBatch",
		on_delete=models.CASCADE,
		db_column="batch_id",
		related_name="allocations",
	)
	allocation_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	allocation_date = models.DateTimeField(auto_now_add=True)
	priority_level = models.CharField(max_length=20, blank=True, null=True)

	class Meta:
		db_table = "allocation"


class ReassessmentRecord(models.Model):
	class Outcome(models.TextChoices):
		REMOVE = "remove", "Remove from programme"
		UNDER_REVIEW = "under_review", "Continue under review"
		CONTINUE_SUPPORT = "continue_support", "Continue support"
		HIGH_PRIORITY = "high_priority", "High-priority beneficiary"

	record_id = models.AutoField(primary_key=True)
	beneficiary = models.ForeignKey(
		Beneficiary,
		on_delete=models.CASCADE,
		db_column="beneficiary_id",
		related_name="reassessments",
	)
	answers = models.JSONField(default=dict, blank=True)
	evidence_statement_1 = models.TextField(blank=True)
	evidence_statement_2 = models.TextField(blank=True)
	verification_confirmed = models.BooleanField(default=False)
	total_score = models.IntegerField(blank=True, null=True)
	outcome = models.CharField(max_length=32, choices=Outcome.choices, blank=True)
	next_review_date = models.DateField(blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "beneficiary_reassessment"

from django.db import models
from django.conf import settings

class AllocationLogicConfig(models.Model):
	config_id = models.AutoField(primary_key=True)
	full_cycle_per_learner = models.DecimalField(max_digits=10, decimal_places=2, default=200)
	half_cycle_per_learner = models.DecimalField(max_digits=10, decimal_places=2, default=100)
	updated_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="allocation_logic_updates",
	)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "allocation_logic_config"


class UrgentSupportMessage(models.Model):
	class SenderRole(models.TextChoices):
		SCHOOL_REPRESENTATIVE = "school_representative", "School Representative"
		CASHIER = "cashier", "Cafeteria Cashier"

	message_id = models.AutoField(primary_key=True)
	sender_user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="urgent_messages_sent",
	)
	sender_role = models.CharField(max_length=32, choices=SenderRole.choices)
	message_text = models.TextField()
	is_completed = models.BooleanField(default=False)
	completed_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="urgent_messages_completed",
	)
	completed_at = models.DateTimeField(blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "urgent_support_message"

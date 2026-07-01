from django.db import models


class Report(models.Model):
	report_id = models.AutoField(primary_key=True)
	admin = models.ForeignKey(
		"accounts.SystemAdministrator",
		on_delete=models.CASCADE,
		db_column="admin_id",
		related_name="reports",
		blank=True,
		null=True,
	)
	report_type = models.CharField(max_length=50, blank=True, null=True)
	generated_date = models.DateTimeField(auto_now_add=True)
	report_status = models.CharField(max_length=20, blank=True, null=True)

	class Meta:
		db_table = "report"

from django.db import models


class Payment(models.Model):
	payment_id = models.AutoField(primary_key=True)
	payer_profile = models.ForeignKey(
		"accounts.AppUserProfile",
		on_delete=models.SET_NULL,
		related_name="payments_made",
		blank=True,
		null=True,
	)
	cashier = models.ForeignKey(
		"accounts.CafeteriaCashier",
		on_delete=models.CASCADE,
		db_column="cashier_id",
		related_name="payments",
		blank=True,
		null=True,
	)
	customer = models.ForeignKey(
		"accounts.CafeteriaCustomer",
		on_delete=models.CASCADE,
		db_column="customer_id",
		related_name="payments",
		blank=True,
		null=True,
	)
	payment_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	payment_date = models.DateTimeField(auto_now_add=True)
	payment_status = models.CharField(max_length=20, blank=True, null=True)
	meal_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	donation_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

	class Meta:
		db_table = "payment"

from django.db import models


class Donation(models.Model):
	donation_id = models.AutoField(primary_key=True)
	payment = models.ForeignKey(
		"payments.Payment",
		on_delete=models.CASCADE,
		db_column="payment_id",
		related_name="donations",
		blank=True,
		null=True,
	)
	customer = models.ForeignKey(
		"accounts.CafeteriaCustomer",
		on_delete=models.CASCADE,
		db_column="customer_id",
		related_name="donations",
	)
	donation_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	donation_type = models.CharField(max_length=30, blank=True, null=True)
	donation_date = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "donation"


class DonationPool(models.Model):
	pool_id = models.AutoField(primary_key=True)
	current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
	last_distribution_date = models.DateTimeField(blank=True, null=True)
	status = models.CharField(max_length=20, blank=True, null=True)

	class Meta:
		db_table = "donation_pool"


class DistributionBatch(models.Model):
	batch_id = models.AutoField(primary_key=True)
	distribution_date = models.DateTimeField(auto_now_add=True)
	total_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
	beneficiary_count = models.IntegerField(blank=True, null=True)

	class Meta:
		db_table = "distribution_batch"


class DonationGoal(models.Model):
	year = models.PositiveIntegerField(unique=True)
	annual_target = models.DecimalField(max_digits=12, decimal_places=2, default=100000.00)

	class Meta:
		db_table = "donation_goal"

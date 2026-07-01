from django.db import models
from django.conf import settings


class SystemUser(models.Model):
	user_id = models.AutoField(primary_key=True)
	full_name = models.CharField(max_length=100)
	email = models.EmailField(max_length=100, unique=True)
	password_hash = models.CharField(max_length=255)
	role = models.CharField(max_length=50, default="CAFETERIA_CUSTOMER")
	phone_number = models.CharField(max_length=20, blank=True, null=True)
	account_status = models.CharField(max_length=20, blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "system_user"


class CafeteriaCustomer(models.Model):
	customer_id = models.AutoField(primary_key=True)
	user = models.OneToOneField(
		SystemUser,
		on_delete=models.CASCADE,
		db_column="user_id",
		related_name="cafeteria_customer",
	)
	donor_status = models.CharField(max_length=20, blank=True, null=True)
	total_donations = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

	class Meta:
		db_table = "cafeteria_customer"


class CafeteriaCashier(models.Model):
	cashier_id = models.AutoField(primary_key=True)
	user = models.OneToOneField(
		SystemUser,
		on_delete=models.CASCADE,
		db_column="user_id",
		related_name="cafeteria_cashier",
	)
	workstation_number = models.CharField(max_length=20, blank=True, null=True)
	national_id = models.CharField(max_length=20, blank=True, null=True)
	employee_number = models.CharField(max_length=30, blank=True, null=True)
	institution_name = models.CharField(max_length=100, blank=True, null=True)
	years_of_service = models.IntegerField(blank=True, null=True)

	class Meta:
		db_table = "cafeteria_cashier"


class SchoolRepresentative(models.Model):
	representative_id = models.AutoField(primary_key=True)
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="school_representative",
	)
	school_name = models.CharField(max_length=255, blank=True, null=True)
	school_code = models.CharField(max_length=120, unique=True, blank=True, null=True)
	tsc_number = models.CharField(max_length=120, blank=True, null=True)
	national_id_number = models.CharField(max_length=120, blank=True, null=True)
	position = models.CharField(max_length=120, blank=True, null=True)
	years_of_service = models.PositiveIntegerField(blank=True, null=True)

	class Meta:
		db_table = "school_representative"


class SystemAdministrator(models.Model):
	admin_id = models.AutoField(primary_key=True)
	user = models.OneToOneField(
		SystemUser,
		on_delete=models.CASCADE,
		db_column="user_id",
		related_name="system_administrator",
	)
	access_level = models.CharField(max_length=50, blank=True, null=True)

	class Meta:
		db_table = "system_administrator"


class SystemLog(models.Model):
	log_id = models.AutoField(primary_key=True)
	user = models.ForeignKey(
		SystemUser,
		on_delete=models.CASCADE,
		db_column="user_id",
		related_name="system_logs",
		blank=True,
		null=True,
	)
	activity_type = models.CharField(max_length=100, blank=True, null=True)
	activity_time = models.DateTimeField(auto_now_add=True)
	ip_address = models.CharField(max_length=100, blank=True, null=True)

	class Meta:
		db_table = "system_logs"


class AppUserProfile(models.Model):
	class Role(models.TextChoices):
		CUSTOMER_DONOR = "customer_donor", "Cafeteria Customer (Donor)"
		CASHIER = "cashier", "Cafeteria Cashier"
		SCHOOL_REPRESENTATIVE = "school_representative", "School Representative"
		SYSTEM_ADMIN = "system_admin", "System Administrator"

	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="app_profile",
	)
	full_name = models.CharField(max_length=150)
	phone_number = models.CharField(max_length=32, unique=True)
	role = models.CharField(max_length=32, choices=Role.choices, default=Role.CUSTOMER_DONOR)
	can_manage_beneficiaries = models.BooleanField(default=True)
	can_initiate_cycles = models.BooleanField(default=False)
	can_manage_users = models.BooleanField(default=False)
	can_view_reports = models.BooleanField(default=True)
	status_note = models.CharField(max_length=200, blank=True, default="")
	profile_picture = models.ImageField(upload_to="profile_pictures/", blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "app_user_profile"

	def __str__(self):
		return f"{self.full_name} ({self.role})"

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class UserProfile(models.Model):
    class Role(models.TextChoices):
        CUSTOMER_DONOR = "customer_donor", "Cafeteria Customer (Donor)"
        CASHIER = "cashier", "Cafeteria Cashier"
        SCHOOL_REPRESENTATIVE = "school_representative", "School Representative"
        SYSTEM_ADMIN = "system_admin", "System Administrator"

    class AccountStatus(models.TextChoices):
        ACTIVE = "Active", "Active"
        PENDING = "Pending", "Pending"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.CUSTOMER_DONOR,
    )
    phone_number = models.CharField(max_length=32, unique=True, null=True, blank=True)
    account_status = models.CharField(
        max_length=16,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    class Meta:
        db_table = "system_user"


class CafeteriaCustomer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cafeteria_customer",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cafeteria_customer"


class CafeteriaCashier(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cafeteria_cashier",
    )
    national_id_number = models.CharField(max_length=120)
    employee_number = models.CharField(max_length=120)
    workstation_number = models.CharField(max_length=120)
    institution_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cafeteria_cashier"


class SchoolRepresentative(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="school_representative",
    )
    school_name = models.CharField(max_length=255)
    school_code = models.CharField(max_length=120, unique=True)
    tsc_number = models.CharField(max_length=120)
    national_id_number = models.CharField(max_length=120)
    position = models.CharField(max_length=120)
    years_of_service = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "school_representative"


class RoleUpgradeRequest(models.Model):
    class RequestedRole(models.TextChoices):
        SCHOOL_REPRESENTATIVE = "school_representative", "School Representative"
        CASHIER = "cashier", "Cashier"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="role_upgrade_requests",
    )
    requested_role = models.CharField(max_length=32, choices=RequestedRole.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    school_name = models.CharField(max_length=255, blank=True)
    institution_name = models.CharField(max_length=255, blank=True)
    institution_details = models.TextField(blank=True)
    verification_info = models.TextField(blank=True)

    cashier_id = models.CharField(max_length=120, blank=True)
    national_id = models.CharField(max_length=120, blank=True)

    review_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_role_upgrade_requests",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        errors = {}

        if self.requested_role == self.RequestedRole.SCHOOL_REPRESENTATIVE:
            if not self.school_name:
                errors["school_name"] = "School name is required for School Representative requests."
            if not self.institution_name:
                errors["institution_name"] = "Institution name is required for School Representative requests."
            if not self.institution_details:
                errors["institution_details"] = "Institution details are required for School Representative requests."
        elif self.requested_role == self.RequestedRole.CASHIER:
            if not self.cashier_id:
                errors["cashier_id"] = "Cashier ID is required for Cashier requests."
            if not self.institution_name:
                errors["institution_name"] = "Institution name is required for Cashier requests."
            if not self.national_id:
                errors["national_id"] = "National ID is required for Cashier requests."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.user.username} -> {self.get_requested_role_display()} ({self.get_status_display()})"

import re

from django import forms
from django.contrib.auth import get_user_model

from .models import RoleUpgradeRequest, SchoolRepresentative, UserProfile

User = get_user_model()


class SignupForm(forms.Form):
    full_name = forms.CharField(max_length=150)
    email = forms.EmailField(max_length=254)
    phone_number = forms.CharField(max_length=32)
    role = forms.ChoiceField(
        choices=[
            (UserProfile.Role.CUSTOMER_DONOR, "Cafeteria Customer (Donor)"),
            (UserProfile.Role.CASHIER, "Cafeteria Cashier"),
            (UserProfile.Role.SCHOOL_REPRESENTATIVE, "School Representative"),
        ]
    )

    cashier_national_id_number = forms.CharField(max_length=120, required=False)
    cashier_employee_number = forms.CharField(max_length=120, required=False)
    cashier_workstation_number = forms.CharField(max_length=120, required=False)
    cashier_institution_name = forms.CharField(max_length=255, required=False)

    school_name = forms.CharField(max_length=255, required=False)
    school_code = forms.CharField(max_length=120, required=False)
    tsc_number = forms.CharField(max_length=120, required=False)
    school_national_id_number = forms.CharField(max_length=120, required=False)
    school_position = forms.CharField(max_length=120, required=False)
    school_years_of_service = forms.IntegerField(min_value=0, required=False)

    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"].strip()
        if UserProfile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone_number

    def clean_password(self):
        password = self.cleaned_data["password"]
        errors = []

        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        if not re.search(r"[A-Z]", password):
            errors.append("Password must include at least one uppercase letter.")
        if not re.search(r"[a-z]", password):
            errors.append("Password must include at least one lowercase letter.")
        if not re.search(r"\d", password):
            errors.append("Password must include at least one numeric digit.")
        if not re.search(r"[^A-Za-z0-9]", password):
            errors.append("Password must include at least one special character.")

        if errors:
            raise forms.ValidationError(errors)

        return password

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match")

        if role == UserProfile.Role.CASHIER:
            required_cashier_fields = {
                "cashier_national_id_number": "National ID Number is required.",
                "cashier_employee_number": "Employee Number is required.",
                "cashier_workstation_number": "Workstation Number is required.",
                "cashier_institution_name": "Institution Name is required.",
            }
            for field_name, message in required_cashier_fields.items():
                if cleaned_data.get(field_name) in (None, ""):
                    self.add_error(field_name, message)

        if role == UserProfile.Role.SCHOOL_REPRESENTATIVE:
            required_school_fields = {
                "school_name": "School Name is required.",
                "school_code": "School Code is required.",
                "tsc_number": "TSC Number is required.",
                "school_national_id_number": "National ID Number is required.",
                "school_position": "Position is required.",
                "school_years_of_service": "Years of Service is required.",
            }
            for field_name, message in required_school_fields.items():
                if cleaned_data.get(field_name) in (None, ""):
                    self.add_error(field_name, message)

            school_code = cleaned_data.get("school_code")
            if school_code and SchoolRepresentative.objects.filter(school_code__iexact=school_code.strip()).exists():
                self.add_error(
                    "school_code",
                    "A representative for this school has already been registered.",
                )

        return cleaned_data


class LoginForm(forms.Form):
    email = forms.EmailField(max_length=254)
    password = forms.CharField(widget=forms.PasswordInput)


class RoleUpgradeRequestForm(forms.ModelForm):
    class Meta:
        model = RoleUpgradeRequest
        fields = [
            "requested_role",
            "school_name",
            "institution_name",
            "institution_details",
            "verification_info",
            "cashier_id",
            "national_id",
        ]

    def clean(self):
        cleaned_data = super().clean()
        requested_role = cleaned_data.get("requested_role")

        if requested_role == RoleUpgradeRequest.RequestedRole.SCHOOL_REPRESENTATIVE:
            required = {
                "school_name": "School name is required.",
                "institution_name": "Institution name is required.",
                "institution_details": "Institution details are required.",
            }
            for field_name, error_message in required.items():
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, error_message)

        if requested_role == RoleUpgradeRequest.RequestedRole.CASHIER:
            required = {
                "cashier_id": "Cashier ID is required.",
                "institution_name": "Institution name is required.",
                "national_id": "National ID is required.",
            }
            for field_name, error_message in required.items():
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, error_message)

        return cleaned_data

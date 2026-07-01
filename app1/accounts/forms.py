import re

from django import forms
from django.contrib.auth import get_user_model

from .models import AppUserProfile, SchoolRepresentative

User = get_user_model()


def _validate_password_strength(password):
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


class SignupForm(forms.Form):
    full_name = forms.CharField(max_length=150)
    email = forms.EmailField(max_length=254)
    phone_number = forms.CharField(max_length=32)
    role = forms.ChoiceField(
        choices=[
            (AppUserProfile.Role.CUSTOMER_DONOR, "Cafeteria Customer (Donor)"),
            (AppUserProfile.Role.CASHIER, "Cafeteria Cashier"),
            (AppUserProfile.Role.SCHOOL_REPRESENTATIVE, "School Representative"),
        ]
    )
    profile_picture = forms.ImageField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    school_national_id_number = forms.CharField(max_length=120, required=False)
    school_name = forms.CharField(max_length=255, required=False)
    school_code = forms.CharField(max_length=120, required=False)
    tsc_number = forms.CharField(max_length=120, required=False)
    school_position = forms.CharField(max_length=120, required=False)
    school_years_of_service = forms.IntegerField(min_value=0, required=False)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"].strip()
        if AppUserProfile.objects.filter(phone_number=phone_number).exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone_number

    def clean_password(self):
        return _validate_password_strength(self.cleaned_data["password"])

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        role = cleaned_data.get("role")

        if role == AppUserProfile.Role.SYSTEM_ADMIN:
            self.add_error("role", "Administrator accounts cannot be created from signup.")
            return cleaned_data

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match")

        if role == AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
            required_school_fields = {
                "school_national_id_number": "National ID Number is required for school representatives.",
                "school_name": "School Name is required.",
                "school_code": "School Code is required.",
                "tsc_number": "TSC Number is required.",
                "school_position": "Position is required.",
                "school_years_of_service": "Years of Service is required.",
            }
            for field_name, error_message in required_school_fields.items():
                value = cleaned_data.get(field_name)
                if value in (None, ""):
                    self.add_error(field_name, error_message)

            school_code = (cleaned_data.get("school_code") or "").strip()
            if school_code and SchoolRepresentative.objects.filter(school_code__iexact=school_code).exists():
                self.add_error("school_code", "This school code is already registered.")

        return cleaned_data


class LoginForm(forms.Form):
    email = forms.EmailField(max_length=254)
    password = forms.CharField(widget=forms.PasswordInput)


class ProfileUpdateForm(forms.Form):
    full_name = forms.CharField(max_length=150)
    email = forms.EmailField(max_length=254)
    phone_number = forms.CharField(max_length=32)
    profile_picture = forms.ImageField(required=False)
    new_password = forms.CharField(widget=forms.PasswordInput, required=False)
    confirm_new_password = forms.CharField(widget=forms.PasswordInput, required=False)

    def __init__(self, *args, user=None, profile=None, **kwargs):
        self.user = user
        self.profile = profile
        super().__init__(*args, **kwargs)

    def clean_full_name(self):
        return " ".join(self.cleaned_data["full_name"].split())

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        existing = User.objects.filter(email__iexact=email)
        if self.user is not None:
            existing = existing.exclude(pk=self.user.pk)
        if existing.exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data["phone_number"].strip()
        existing = AppUserProfile.objects.filter(phone_number=phone_number)
        if self.profile is not None:
            existing = existing.exclude(pk=self.profile.pk)
        if existing.exists():
            raise forms.ValidationError("An account with this phone number already exists.")
        return phone_number

    def clean_new_password(self):
        new_password = self.cleaned_data.get("new_password", "")
        if not new_password:
            return ""
        return _validate_password_strength(new_password)

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_new_password = cleaned_data.get("confirm_new_password")

        if new_password and not confirm_new_password:
            self.add_error("confirm_new_password", "Please confirm your new password.")
        if confirm_new_password and not new_password:
            self.add_error("new_password", "Please enter a new password first.")
        if new_password and confirm_new_password and new_password != confirm_new_password:
            self.add_error("confirm_new_password", "Passwords do not match")

        return cleaned_data

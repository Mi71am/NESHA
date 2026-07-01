from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from .forms import LoginForm, ProfileUpdateForm, SignupForm
from .models import AppUserProfile, SchoolRepresentative

User = get_user_model()


def _generate_unique_username(email):
	base = email.split("@", 1)[0].strip().lower() or "user"
	candidate = base[:150]
	index = 1

	while User.objects.filter(username__iexact=candidate).exists():
		suffix = str(index)
		allowed = 150 - len(suffix) - 1
		candidate = f"{base[:allowed]}_{suffix}"
		index += 1

	return candidate


def _redirect_for_role(profile):
	role = profile.role if profile else AppUserProfile.Role.CUSTOMER_DONOR

	if role == AppUserProfile.Role.CASHIER:
		return "dashboard:cashier"
	if role == AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
		return "dashboard:school_representative"
	if role == AppUserProfile.Role.SYSTEM_ADMIN:
		return "dashboard:administrator"
	return "dashboard:customer"


def onboarding_view(request):
	if request.user.is_authenticated:
		profile = getattr(request.user, "app_profile", None)
		return redirect(_redirect_for_role(profile))
	return render(request, "onboarding.html")


@never_cache
def signup_view(request):
	if request.user.is_authenticated:
		profile = getattr(request.user, "app_profile", None)
		return redirect(_redirect_for_role(profile))

	form = SignupForm(request.POST or None, request.FILES or None)

	if request.method == "POST" and form.is_valid():
		cleaned = form.cleaned_data
		full_name = cleaned["full_name"].strip()
		name_parts = full_name.split(maxsplit=1)
		first_name = name_parts[0]
		last_name = name_parts[1] if len(name_parts) > 1 else ""

		with transaction.atomic():
			user = User.objects.create_user(
				username=_generate_unique_username(cleaned["email"]),
				email=cleaned["email"].strip().lower(),
				password=cleaned["password"],
				first_name=first_name,
				last_name=last_name,
			)

			AppUserProfile.objects.create(
				user=user,
				full_name=full_name,
				phone_number=cleaned["phone_number"].strip(),
				role=cleaned["role"],
				profile_picture=cleaned.get("profile_picture"),
			)

			if cleaned["role"] == AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
				SchoolRepresentative.objects.create(
					user=user,
					school_name=cleaned["school_name"].strip(),
					school_code=cleaned["school_code"].strip(),
					tsc_number=cleaned["tsc_number"].strip(),
					national_id_number=cleaned["school_national_id_number"].strip(),
					position=cleaned["school_position"].strip(),
					years_of_service=cleaned["school_years_of_service"],
				)

		messages.success(request, "Registration successful. You can now log in.")
		return redirect("accounts:login")

	return render(request, "auth/signup.html", {"form": form})


@never_cache
def login_view(request):
	if request.user.is_authenticated:
		profile = getattr(request.user, "app_profile", None)
		return redirect(_redirect_for_role(profile))

	form = LoginForm(request.POST or None)

	if request.method == "POST" and form.is_valid():
		email = form.cleaned_data["email"].strip().lower()
		password = form.cleaned_data["password"]

		try:
			user_obj = User.objects.get(email__iexact=email)
		except User.DoesNotExist:
			user_obj = None

		user = None
		profile = getattr(user_obj, "app_profile", None) if user_obj else None
		is_suspended_school_rep = bool(
			user_obj
			and not user_obj.is_active
			and profile
			and profile.role == AppUserProfile.Role.SCHOOL_REPRESENTATIVE
		)
		if user_obj:
			user = authenticate(request, username=user_obj.username, password=password)

		if user is None:
			if is_suspended_school_rep:
				form.add_error(
					None,
					"This school representative account is suspended after repeated inconsistent submissions. Please contact NESHA administrators for re-application guidance.",
				)
			else:
				form.add_error(None, "Invalid email or password.")
		else:
			login(request, user)
			messages.success(request, "Login successful.")
			profile = getattr(user, "app_profile", None)
			return redirect(_redirect_for_role(profile))

	return render(request, "auth/login.html", {"form": form})


@login_required
def logout_view(request):
	logout(request)
	messages.success(request, "You have been logged out.")
	return redirect("accounts:login")


@login_required
@never_cache
def profile_update_view(request):
	profile = getattr(request.user, "app_profile", None)
	if profile is None:
		profile = AppUserProfile.objects.create(
			user=request.user,
			full_name=(request.user.get_full_name() or request.user.username).strip(),
			phone_number=f"pending-{request.user.id}",
			role=AppUserProfile.Role.CUSTOMER_DONOR,
		)

	initial = {
		"full_name": profile.full_name,
		"email": request.user.email,
		"phone_number": profile.phone_number,
	}

	form = ProfileUpdateForm(
		request.POST or None,
		request.FILES or None,
		user=request.user,
		profile=profile,
		initial=initial,
	)

	if request.method == "POST" and form.is_valid():
		cleaned = form.cleaned_data
		full_name = cleaned["full_name"].strip()
		name_parts = full_name.split(maxsplit=1)
		first_name = name_parts[0] if name_parts else ""
		last_name = name_parts[1] if len(name_parts) > 1 else ""

		request.user.email = cleaned["email"]
		request.user.first_name = first_name
		request.user.last_name = last_name
		new_password = cleaned.get("new_password", "")
		if new_password:
			request.user.set_password(new_password)
		request.user.save(update_fields=["email", "first_name", "last_name", "password"] if new_password else ["email", "first_name", "last_name"])

		profile.full_name = full_name
		profile.phone_number = cleaned["phone_number"].strip()
		if cleaned.get("profile_picture"):
			profile.profile_picture = cleaned["profile_picture"]
		profile.save()

		if new_password:
			messages.success(request, "Profile updated. Please log in again with your new password.")
			logout(request)
			return redirect("accounts:login")

		messages.success(request, "Profile updated successfully.")
		return redirect("accounts:profile")

	return render(
		request,
		"auth/profile_edit.html",
		{
			"form": form,
			"profile": profile,
			"display_role": profile.get_role_display(),
			"dashboard_route": _redirect_for_role(profile),
			"school_rep": getattr(request.user, "school_representative", None),
		},
	)

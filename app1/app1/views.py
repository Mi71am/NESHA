from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import LoginForm, RoleUpgradeRequestForm, SignupForm
from .models import (
    CafeteriaCashier,
    CafeteriaCustomer,
    RoleUpgradeRequest,
    SchoolRepresentative,
    UserProfile,
)

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


def onboarding_view(request):
    return render(request, 'onboarding.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('onboarding')

    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        email = form.cleaned_data['email'].strip().lower()
        password = form.cleaned_data['password']

        try:
            user_obj = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            user_obj = None

        user = None
        if user_obj:
            user = authenticate(request, username=user_obj.username, password=password)

        if user is None:
            form.add_error(None, 'Invalid email or password.')
        else:
            login(request, user)
            messages.success(request, 'Login successful.')
            return redirect('onboarding')

    return render(request, 'auth/login.html', {'form': form})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('onboarding')

    form = SignupForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        cleaned = form.cleaned_data
        full_name = cleaned['full_name'].strip()
        name_parts = full_name.split(maxsplit=1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        selected_role = cleaned['role']

        with transaction.atomic():
            user = User.objects.create_user(
                username=_generate_unique_username(cleaned['email']),
                email=cleaned['email'].strip().lower(),
                password=cleaned['password'],
                first_name=first_name,
                last_name=last_name,
            )

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = selected_role
            profile.phone_number = cleaned['phone_number']
            profile.account_status = UserProfile.AccountStatus.ACTIVE
            profile.save(update_fields=['role', 'phone_number', 'account_status', 'updated_at'])

            if selected_role == UserProfile.Role.CUSTOMER_DONOR:
                CafeteriaCustomer.objects.create(user=user)
            elif selected_role == UserProfile.Role.CASHIER:
                CafeteriaCashier.objects.create(
                    user=user,
                    national_id_number=cleaned['cashier_national_id_number'].strip(),
                    employee_number=cleaned['cashier_employee_number'].strip(),
                    workstation_number=cleaned['cashier_workstation_number'].strip(),
                    institution_name=cleaned['cashier_institution_name'].strip(),
                )
            elif selected_role == UserProfile.Role.SCHOOL_REPRESENTATIVE:
                SchoolRepresentative.objects.create(
                    user=user,
                    school_name=cleaned['school_name'].strip(),
                    school_code=cleaned['school_code'].strip(),
                    tsc_number=cleaned['tsc_number'].strip(),
                    national_id_number=cleaned['school_national_id_number'].strip(),
                    position=cleaned['school_position'].strip(),
                    years_of_service=cleaned['school_years_of_service'],
                )

        messages.success(request, 'Registration successful. You can now log in.')
        return redirect('login')

    return render(request, 'auth/signup.html', {'form': form})


@login_required
def role_upgrade_request_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if profile.role == UserProfile.Role.SYSTEM_ADMIN:
        messages.error(request, 'Administrator accounts cannot submit role upgrade requests.')
        return redirect('onboarding')

    form = RoleUpgradeRequestForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        upgrade_request = form.save(commit=False)
        upgrade_request.user = request.user
        upgrade_request.status = RoleUpgradeRequest.Status.PENDING
        upgrade_request.save()

        profile.account_status = UserProfile.AccountStatus.PENDING
        profile.save(update_fields=['account_status', 'updated_at'])

        messages.success(request, 'Your role upgrade request has been submitted and is pending admin review.')
        return redirect('onboarding')

    return render(request, 'auth/role_upgrade_request.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')

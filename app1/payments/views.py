import json
from decimal import Decimal, InvalidOperation
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import AppUserProfile
from donations.models import DonationPool

from .models import Payment


MAX_PAYMENT_AMOUNT = Decimal("1000000")


def _parse_positive_decimal(raw_value):
	raw = str(raw_value or "").strip()
	if not raw:
		return Decimal("0")
	raw = raw.replace(",", "")
	try:
		value = Decimal(raw)
	except InvalidOperation:
		return Decimal("0")
	if value < 0:
		return Decimal("0")
	if value > MAX_PAYMENT_AMOUNT:
		return MAX_PAYMENT_AMOUNT
	return value


def _digits_only(raw_value):
	return "".join(ch for ch in str(raw_value or "") if ch.isdigit())


def _get_or_create_profile(user):
	profile = getattr(user, "app_profile", None)
	if profile is None:
		profile = AppUserProfile.objects.create(
			user=user,
			full_name=(user.get_full_name() or user.username).strip(),
			phone_number=f"pending-{user.id}",
			role=AppUserProfile.Role.CUSTOMER_DONOR,
		)
	return profile


@login_required
def index(request):
	profile = _get_or_create_profile(request.user)

	source = request.GET.get("source", "donation").strip().lower()
	if source not in {"donation", "dashboard"}:
		source = "donation"

	amount = _parse_positive_decimal(request.GET.get("amount", ""))
	meal_amount = _parse_positive_decimal(request.GET.get("meal_amount", ""))
	donation_amount = _parse_positive_decimal(request.GET.get("donation_amount", ""))
	package_name = request.GET.get("package", "").strip().upper()

	if source == "donation":
		meal_amount = Decimal("0")
		donation_amount = amount
		if not package_name:
			package_name = "CUSTOM CONTRIBUTION"
	else:
		if meal_amount == 0 and donation_amount == 0:
			meal_amount = amount
		amount = meal_amount + donation_amount

	initial_phone = _digits_only(profile.phone_number)

	return render(
		request,
		"payments/index.html",
		{
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": request.user.email,
			"source": source,
			"amount": str(amount),
			"meal_amount": str(meal_amount),
			"donation_amount": str(donation_amount),
			"package_name": package_name,
			"initial_phone": initial_phone,
		},
	)


@login_required
def history(request):
	profile = _get_or_create_profile(request.user)
	if profile.role == AppUserProfile.Role.CASHIER:
		return redirect("payments:cashier_history")
	transactions = (
		Payment.objects.filter(payer_profile=profile)
		.order_by("-payment_date", "-payment_id")[:15]
	)

	return render(
		request,
		"payments/history.html",
		{
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": request.user.email,
			"transactions": transactions,
		},
	)


@login_required
def cashier_history(request):
	profile = _get_or_create_profile(request.user)
	if profile.role != AppUserProfile.Role.CASHIER:
		return redirect("dashboard:home")

	start_date = (request.GET.get("start_date") or "").strip()
	end_date = (request.GET.get("end_date") or "").strip()
	min_amount_raw = (request.GET.get("min_amount") or "").strip()
	max_amount_raw = (request.GET.get("max_amount") or "").strip()

	transactions_qs = (
		Payment.objects.filter(meal_amount__gt=0)
		.select_related("payer_profile", "payer_profile__user")
		.order_by("-payment_date", "-payment_id")
	)

	if start_date:
		transactions_qs = transactions_qs.filter(payment_date__date__gte=start_date)
	if end_date:
		transactions_qs = transactions_qs.filter(payment_date__date__lte=end_date)

	min_amount = _parse_positive_decimal(min_amount_raw) if min_amount_raw else None
	max_amount = _parse_positive_decimal(max_amount_raw) if max_amount_raw else None
	if min_amount is not None:
		transactions_qs = transactions_qs.filter(meal_amount__gte=min_amount)
	if max_amount is not None and max_amount > 0:
		transactions_qs = transactions_qs.filter(meal_amount__lte=max_amount)

	transactions = transactions_qs[:300]

	today = timezone.localdate()
	week_start = today - timedelta(days=6)
	weekly_rows = (
		transactions_qs.filter(payment_date__date__gte=week_start)
		.annotate(day=TruncDate("payment_date"))
		.values("day")
		.annotate(total=Sum("meal_amount"))
	)
	weekly_map = {row["day"]: float(row["total"] or 0) for row in weekly_rows}
	weekly_labels = []
	weekly_values = []
	for i in range(7):
		day = week_start + timedelta(days=i)
		weekly_labels.append(day.strftime("%a"))
		weekly_values.append(round(weekly_map.get(day, 0), 2))

	now = timezone.now()
	month_starts = []
	for offset in range(5, -1, -1):
		month = now.month - offset
		year = now.year
		while month <= 0:
			month += 12
			year -= 1
		month_starts.append((year, month))

	six_months_ago = timezone.make_aware(
		timezone.datetime(month_starts[0][0], month_starts[0][1], 1)
	)
	monthly_rows = (
		transactions_qs.filter(payment_date__gte=six_months_ago)
		.annotate(month=TruncMonth("payment_date"))
		.values("month")
		.annotate(total=Sum("meal_amount"))
	)
	monthly_map = {
		(row["month"].year, row["month"].month): float(row["total"] or 0)
		for row in monthly_rows
	}
	trend_labels = []
	trend_values = []
	for year, month in month_starts:
		trend_labels.append(f"{timezone.datetime(year, month, 1).strftime('%b')} {str(year)[-2:]}")
		trend_values.append(round(monthly_map.get((year, month), 0), 2))

	daily_totals = (
		transactions_qs.annotate(day=TruncDate("payment_date"))
		.values("day")
		.annotate(total=Sum("meal_amount"))
		.order_by("-day")[:12]
	)
	monthly_totals = (
		transactions_qs.annotate(month=TruncMonth("payment_date"))
		.values("month")
		.annotate(total=Sum("meal_amount"))
		.order_by("-month")[:12]
	)

	return render(
		request,
		"payments/cashier_history.html",
		{
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": request.user.email,
			"transactions": transactions,
			"start_date": start_date,
			"end_date": end_date,
			"min_amount": min_amount_raw,
			"max_amount": max_amount_raw,
			"weekly_labels": weekly_labels,
			"weekly_values": weekly_values,
			"trend_labels": trend_labels,
			"trend_values": trend_values,
			"daily_totals": daily_totals,
			"monthly_totals": monthly_totals,
		},
	)


@login_required
@require_POST
def confirm_payment(request):
	profile = _get_or_create_profile(request.user)

	try:
		payload = json.loads(request.body.decode("utf-8"))
	except (json.JSONDecodeError, UnicodeDecodeError):
		return JsonResponse({"ok": False, "message": "Invalid request payload."}, status=400)

	source = str(payload.get("source", "")).strip().lower()
	if source not in {"donation", "dashboard"}:
		return JsonResponse({"ok": False, "message": "Invalid payment source."}, status=400)

	amount = _parse_positive_decimal(payload.get("amount", ""))
	meal_amount = _parse_positive_decimal(payload.get("meal_amount", ""))
	donation_amount = _parse_positive_decimal(payload.get("donation_amount", ""))
	package_name = str(payload.get("package_name", "")).strip().upper()
	phone_number = _digits_only(payload.get("phone_number", ""))

	if source == "donation":
		meal_amount = Decimal("0")
		donation_amount = amount
		if not package_name:
			package_name = "CUSTOM CONTRIBUTION"
	else:
		amount = meal_amount + donation_amount

	if amount <= 0:
		return JsonResponse({"ok": False, "message": "Amount must be greater than zero."}, status=400)
	if amount > MAX_PAYMENT_AMOUNT or meal_amount > MAX_PAYMENT_AMOUNT or donation_amount > MAX_PAYMENT_AMOUNT:
		return JsonResponse(
			{"ok": False, "message": "Maximum allowed payment is Ksh 1,000,000."},
			status=400,
		)
	if len(phone_number) != 10 or not phone_number.startswith("0"):
		return JsonResponse(
			{"ok": False, "message": "Enter a valid phone number in this format: 07XXXXXXXX"},
			status=400,
		)

	with transaction.atomic():
		payment = Payment.objects.create(
			payer_profile=profile,
			payment_amount=amount,
			payment_status="COMPLETED",
			meal_amount=meal_amount,
			donation_amount=donation_amount,
		)

		if donation_amount > 0:
			pool = DonationPool.objects.select_for_update().first()
			if pool is None:
				pool = DonationPool.objects.create(current_balance=Decimal("0"), status="ACTIVE")
			pool.current_balance = (pool.current_balance or Decimal("0")) + donation_amount
			pool.save(update_fields=["current_balance"])

		profile.phone_number = phone_number
		profile.save(update_fields=["phone_number"])

	return JsonResponse(
		{
			"ok": True,
			"message": "Payment received.",
			"receipt_number": payment.payment_id,
			"amount": str(amount),
			"meal_amount": str(meal_amount),
			"donation_amount": str(donation_amount),
			"source": source,
			"package_name": package_name,
		}
	)

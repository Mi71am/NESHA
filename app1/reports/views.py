import calendar
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.shortcuts import render
from django.utils import timezone

from accounts.models import AppUserProfile
from donations.models import DonationGoal, DonationPool
from payments.models import Payment


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
	user_payments = Payment.objects.filter(payer_profile=profile).order_by("-payment_date", "-payment_id")

	totals = user_payments.aggregate(
		total_donations=Sum("donation_amount"),
		total_meals_paid=Sum("meal_amount"),
	)
	total_donations = totals["total_donations"] or Decimal("0")
	total_meals_paid = totals["total_meals_paid"] or Decimal("0")
	meals_supported = int(total_donations // Decimal("20"))

	recent_donation_payment = user_payments.filter(donation_amount__gt=0).first()
	recent_donation = recent_donation_payment.donation_amount if recent_donation_payment else Decimal("0")

	today = timezone.localdate()
	week_start = today - timedelta(days=6)
	weekly_rows = (
		user_payments.filter(payment_date__date__gte=week_start)
		.annotate(day=TruncDate("payment_date"))
		.values("day")
		.annotate(total=Sum("donation_amount"))
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
		user_payments.filter(payment_date__gte=six_months_ago)
		.annotate(month=TruncMonth("payment_date"))
		.values("month")
		.annotate(
			donation_total=Sum("donation_amount"),
			meal_total=Sum("meal_amount"),
		)
	)
	monthly_map = {
		(row["month"].year, row["month"].month): (
			float(row["donation_total"] or 0),
			float(row["meal_total"] or 0),
		)
		for row in monthly_rows
	}

	trend_labels = []
	donation_trend = []
	meal_trend = []
	for year, month in month_starts:
		trend_labels.append(f"{calendar.month_abbr[month]} {str(year)[-2:]}")
		don_val, meal_val = monthly_map.get((year, month), (0.0, 0.0))
		donation_trend.append(round(don_val, 2))
		meal_trend.append(round(meal_val, 2))

	six_month_total_donations = Decimal(str(sum(donation_trend)))
	average_monthly_donation = six_month_total_donations / Decimal("6")
	highest_single_donation = (
		user_payments.filter(donation_amount__gt=0).order_by("-donation_amount").values_list("donation_amount", flat=True).first()
		or Decimal("0")
	)
	month_start = timezone.make_aware(timezone.datetime(now.year, now.month, 1))
	this_month_total = (
		user_payments.filter(payment_date__gte=month_start).aggregate(total=Sum("payment_amount"))["total"]
		or Decimal("0")
	)

	current_year = timezone.now().year
	goal, _ = DonationGoal.objects.get_or_create(
		year=current_year,
		defaults={"annual_target": Decimal("100000.00")},
	)
	pool = DonationPool.objects.first()
	if pool is None:
		pool = DonationPool.objects.create(current_balance=Decimal("0"), status="ACTIVE")

	annual_target = goal.annual_target or Decimal("100000")
	community_total = pool.current_balance or Decimal("0")
	community_progress_percent = 0
	if annual_target > 0:
		community_progress_percent = min(100, round((community_total / annual_target) * 100, 2))
	average_meal_cost = Decimal("20")
	community_meals_equivalent = int(community_total // average_meal_cost)
	distributable_pool = (community_total // average_meal_cost) * average_meal_cost
	carry_forward_balance = community_total - distributable_pool

	return render(
		request,
		"reports/index.html",
		{
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": request.user.email,
			"total_donations": total_donations,
			"meals_supported": meals_supported,
			"recent_donation": recent_donation,
			"weekly_labels": weekly_labels,
			"weekly_values": weekly_values,
			"trend_labels": trend_labels,
			"donation_trend": donation_trend,
			"meal_trend": meal_trend,
			"average_monthly_donation": average_monthly_donation,
			"highest_single_donation": highest_single_donation,
			"this_month_total": this_month_total,
			"community_total": community_total,
			"annual_target": annual_target,
			"community_progress_percent": community_progress_percent,
			"community_meals_equivalent": community_meals_equivalent,
			"average_meal_cost": average_meal_cost,
			"distributable_pool": distributable_pool,
			"carry_forward_balance": carry_forward_balance,
		},
	)

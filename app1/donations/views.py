from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from accounts.models import AppUserProfile
from donations.models import DonationGoal, DonationPool


@login_required
def index(request):
	profile = getattr(request.user, "app_profile", None)
	if profile is None:
		profile = AppUserProfile.objects.create(
			user=request.user,
			full_name=(request.user.get_full_name() or request.user.username).strip(),
			phone_number=f"pending-{request.user.id}",
			role=AppUserProfile.Role.CUSTOMER_DONOR,
		)

	current_year = timezone.now().year
	goal, _ = DonationGoal.objects.get_or_create(
		year=current_year,
		defaults={"annual_target": 100000.00},
	)

	pool = DonationPool.objects.first()
	if pool is None:
		pool = DonationPool.objects.create(current_balance=30000.00, status="ACTIVE")
	elif pool.current_balance <= 0:
		pool.current_balance = 30000.00
		pool.save(update_fields=["current_balance"])

	annual_target = float(goal.annual_target)
	current_total = float(pool.current_balance)
	progress_percent = 0
	if annual_target > 0:
		progress_percent = min(100, round((current_total / annual_target) * 100))

	return render(
		request,
		"donations/index.html",
		{
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": request.user.email,
			"annual_target": annual_target,
			"current_total": current_total,
			"progress_percent": progress_percent,
		},
	)

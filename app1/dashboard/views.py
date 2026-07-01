from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from accounts.models import AppUserProfile, SchoolRepresentative
from beneficiaries.models import Allocation, Beneficiary, EligibilityAssessment
from django.contrib.auth import get_user_model
from donations.models import DistributionBatch, DonationPool
from donations.models import DonationGoal
from .models import AllocationLogicConfig, UrgentSupportMessage
from payments.models import Payment

User = get_user_model()


def home(request):
	return HttpResponse("NESHA Dashboard Module")


@login_required
def customer_dashboard(request):
	profile = getattr(request.user, "app_profile", None)

	if profile is None:
		profile = AppUserProfile.objects.create(
			user=request.user,
			full_name=(request.user.get_full_name() or request.user.username).strip(),
			phone_number=f"pending-{request.user.id}",
			role=AppUserProfile.Role.CUSTOMER_DONOR,
		)

	recent_transactions = (
		Payment.objects.filter(payer_profile=profile)
		.order_by("-payment_date", "-payment_id")[:5]
	)

	return render(
		request,
		"customer/Cdashboard.html",
		{
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": request.user.email,
			"recent_transactions": recent_transactions,
		},
	)


@login_required
def cashier_dashboard(request):
	profile = getattr(request.user, "app_profile", None)
	if profile is None:
		profile = AppUserProfile.objects.create(
			user=request.user,
			full_name=(request.user.get_full_name() or request.user.username).strip(),
			phone_number=f"pending-{request.user.id}",
			role=AppUserProfile.Role.CASHIER,
		)

	meal_payments = (
		Payment.objects.filter(meal_amount__gt=0)
		.select_related("payer_profile")
		.order_by("-payment_date", "-payment_id")
	)
	recent_payments = meal_payments[:8]

	today = timezone.localdate()

	today_meal_total = (
		meal_payments.filter(payment_date__date=today).aggregate(total=Sum("meal_amount")).get("total")
		or Decimal("0.00")
	)
	total_meal_value = meal_payments.aggregate(total=Sum("meal_amount")).get("total") or Decimal("0.00")
	total_meal_transactions = meal_payments.count()

	return render(
		request,
		"cashier/dashboard.html",
		{
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": request.user.email,
			"recent_payments": recent_payments,
			"today_meal_total": today_meal_total,
			"total_meal_value": total_meal_value,
			"total_meal_transactions": total_meal_transactions,
		},
	)


@login_required
def school_representative_dashboard(request):
	profile = getattr(request.user, "app_profile", None)
	if profile is None:
		profile = AppUserProfile.objects.create(
			user=request.user,
			full_name=(request.user.get_full_name() or request.user.username).strip(),
			phone_number=f"pending-{request.user.id}",
			role=AppUserProfile.Role.SCHOOL_REPRESENTATIVE,
		)

	rep = getattr(request.user, "school_representative", None)
	if rep is None:
		rep = SchoolRepresentative.objects.create(
			user=request.user,
			school_name="School not set",
			school_code=f"AUTO-{request.user.id}",
			tsc_number="Not set",
			national_id_number="Not set",
			position="Teacher",
			years_of_service=0,
		)

	active_beneficiaries = Beneficiary.objects.filter(
		representative=rep,
		allocation_status=Beneficiary.AllocationStatus.ACTIVE,
	).count()
	pending_questionnaires = EligibilityAssessment.objects.filter(
		beneficiary__representative=rep,
		status=EligibilityAssessment.Status.DRAFT,
	).count()
	flagged_beneficiaries = Beneficiary.objects.filter(
		representative=rep,
		support_cycle_count__gte=20,
	).count()

	support_overview = Beneficiary.objects.filter(
		representative=rep,
		allocation_status=Beneficiary.AllocationStatus.ACTIVE,
	).order_by("learner_name")[:12]

	rejected_beneficiaries = Beneficiary.objects.filter(
		representative=rep,
		allocation_status=Beneficiary.AllocationStatus.NOT_ELIGIBLE,
	).order_by("learner_name")[:12]

	return render(
		request,
		"school/dashboard.html",
		{
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": request.user.email,
			"school_name": rep.school_name,
			"tsc_number": rep.tsc_number,
			"active_beneficiaries": active_beneficiaries,
			"pending_questionnaires": pending_questionnaires,
			"flagged_beneficiaries": flagged_beneficiaries,
			"support_overview": support_overview,
			"rejected_beneficiaries": rejected_beneficiaries,
		},
	)


@login_required
@require_POST
def send_urgent_message(request):
	profile = getattr(request.user, "app_profile", None)
	if profile is None:
		return redirect("dashboard:home")

	if profile.role not in {AppUserProfile.Role.SCHOOL_REPRESENTATIVE, AppUserProfile.Role.CASHIER}:
		return redirect("dashboard:home")

	message_text = (request.POST.get("message_text") or "").strip()
	if not message_text:
		messages.error(request, "Please enter a message before sending.")
		if profile.role == AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
			return redirect("dashboard:school_representative")
		return redirect("dashboard:cashier")

	role_value = (
		UrgentSupportMessage.SenderRole.SCHOOL_REPRESENTATIVE
		if profile.role == AppUserProfile.Role.SCHOOL_REPRESENTATIVE
		else UrgentSupportMessage.SenderRole.CASHIER
	)

	UrgentSupportMessage.objects.create(
		sender_user=request.user,
		sender_role=role_value,
		message_text=message_text[:1000],
	)
	messages.success(request, "Urgent message sent to all administrators.")
	if profile.role == AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
		return redirect("dashboard:school_representative")
	return redirect("dashboard:cashier")


@login_required
@never_cache
def administrator_dashboard(request):
	allocation_config = AllocationLogicConfig.objects.order_by("-config_id").first()
	if allocation_config is None:
		allocation_config = AllocationLogicConfig.objects.create(
			full_cycle_per_learner=Decimal("200"),
			half_cycle_per_learner=Decimal("100"),
		)

	full_cycle_per_learner = allocation_config.full_cycle_per_learner
	half_cycle_per_learner = allocation_config.half_cycle_per_learner

	profile = getattr(request.user, "app_profile", None)
	if profile is None:
		profile = AppUserProfile.objects.create(
			user=request.user,
			full_name=(request.user.get_full_name() or request.user.username).strip(),
			phone_number=f"pending-{request.user.id}",
			role=AppUserProfile.Role.SYSTEM_ADMIN,
		)

	if profile.role != AppUserProfile.Role.SYSTEM_ADMIN:
		return render(request, "admin/dashboard.html", {
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": request.user.email,
			"admin_id": f"ADM-{profile.user_id:05d}",
			"pool_balance": Decimal("0.00"),
			"year_total_donations": Decimal("0.00"),
			"active_beneficiaries": 0,
			"pending_questionnaires": 0,
			"schools_registered": 0,
			"reassessments_due": 0,
			"last_distribution_date": None,
			"distribution_batches": 0,
			"rejected_applicants": 0,
		})

	if request.method == "POST" and request.POST.get("action") == "initiate_cycle":
		if not (profile.can_initiate_cycles or profile.role == AppUserProfile.Role.SYSTEM_ADMIN):
			messages.error(request, "You do not have permission to initiate allocation cycles.")
			return redirect("dashboard:administrator")

		with transaction.atomic():
			pool = DonationPool.objects.select_for_update().order_by("-pool_id").first()
			if pool is None:
				pool = DonationPool.objects.create(current_balance=Decimal("0.00"), status="ACTIVE")

			active_qs = Beneficiary.objects.select_for_update().filter(
				allocation_status=Beneficiary.AllocationStatus.ACTIVE,
				is_removed=False,
			).order_by("beneficiary_id")
			active_list = list(active_qs)
			active_count = len(active_list)

			if active_count == 0:
				messages.warning(request, "No active beneficiaries found. Cycle was not initiated.")
			else:
				pool_balance = pool.current_balance or Decimal("0.00")
				required_full = full_cycle_per_learner * active_count
				required_half = half_cycle_per_learner * active_count

				if pool_balance >= required_full:
					per_learner_amount = full_cycle_per_learner
					cycle_label = "1.0 cycle"
				elif pool_balance >= required_half:
					per_learner_amount = half_cycle_per_learner
					cycle_label = "0.5 cycle"
				else:
					messages.warning(
						request,
						f"Skipped cycle: pool balance is KES {pool_balance:.2f}. Required at least KES {required_half:.2f} for a half cycle.",
					)
					per_learner_amount = None

				if per_learner_amount is not None:
					total_amount = per_learner_amount * active_count
					batch = DistributionBatch.objects.create(
						total_amount=total_amount,
						beneficiary_count=active_count,
					)

					Allocation.objects.bulk_create(
						[
							Allocation(
								beneficiary=beneficiary,
								batch=batch,
								allocation_amount=per_learner_amount,
								priority_level=cycle_label,
							)
							for beneficiary in active_list
						]
					)

					today = timezone.localdate()
					for beneficiary in active_list:
						if cycle_label == "0.5 cycle":
							if beneficiary.pending_half_cycle:
								beneficiary.support_cycle_count = (beneficiary.support_cycle_count or 0) + 1
								beneficiary.pending_half_cycle = False
							else:
								beneficiary.pending_half_cycle = True
						else:
							beneficiary.support_cycle_count = (beneficiary.support_cycle_count or 0) + 1

						effective_cycles = (beneficiary.support_cycle_count or 0) + (0.5 if beneficiary.pending_half_cycle else 0.0)
						if effective_cycles >= 20.5:
							beneficiary.reassessment_status = Beneficiary.ReassessmentStatus.PENDING_REASSESSMENT
							beneficiary.reassessment_due_date = today

						beneficiary.last_allocation_date = today
					beneficiary_updates = ["support_cycle_count", "pending_half_cycle", "reassessment_status", "reassessment_due_date", "last_allocation_date"]
					Beneficiary.objects.bulk_update(active_list, beneficiary_updates)

					pool.current_balance = pool_balance - total_amount
					pool.last_distribution_date = timezone.now()
					if not pool.status:
						pool.status = "ACTIVE"
					pool.save(update_fields=["current_balance", "last_distribution_date", "status"])

					messages.success(
						request,
						f"Cycle initiated successfully: {cycle_label}. Allocated KES {per_learner_amount:.2f} each to {active_count} beneficiaries (Total KES {total_amount:.2f}).",
					)

	pool = DonationPool.objects.order_by("-pool_id").first()
	pool_balance = pool.current_balance if pool else Decimal("0.00")

	current_year = timezone.now().year
	year_total_donations = (
		Payment.objects.filter(payment_date__year=current_year)
		.aggregate(total=Sum("donation_amount"))
		.get("total")
		or Decimal("0.00")
	)

	active_beneficiaries = Beneficiary.objects.filter(
		allocation_status=Beneficiary.AllocationStatus.ACTIVE,
		is_removed=False,
	).count()
	average_meal_amount = Decimal("20.00")
	one_week_target = average_meal_amount * active_beneficiaries
	two_week_target = one_week_target * Decimal("2")

	if two_week_target > 0:
		funding_progress_pct = int(min(Decimal("100"), (pool_balance / two_week_target) * Decimal("100")))
	else:
		funding_progress_pct = 0

	if pool_balance >= two_week_target and two_week_target > 0:
		funding_stage = "full"
	elif pool_balance >= one_week_target and one_week_target > 0:
		funding_stage = "half"
	else:
		funding_stage = "wait"

	over_target_amount = (pool_balance - two_week_target) if two_week_target > 0 and pool_balance > two_week_target else Decimal("0.00")
	active_cashiers = AppUserProfile.objects.filter(
		role=AppUserProfile.Role.CASHIER,
		user__is_active=True,
	).count()
	pending_questionnaires = EligibilityAssessment.objects.filter(
		status=EligibilityAssessment.Status.DRAFT,
	).count()
	schools_registered = SchoolRepresentative.objects.count()
	reassessments_due = Beneficiary.objects.filter(
		allocation_status=Beneficiary.AllocationStatus.ACTIVE,
		is_removed=False,
		reassessment_due_date__isnull=False,
		reassessment_due_date__lte=timezone.localdate(),
	).count()
	rejected_applicants = Beneficiary.objects.filter(
		allocation_status=Beneficiary.AllocationStatus.NOT_ELIGIBLE,
		is_removed=False,
	).count()

	distribution_batches = DistributionBatch.objects.count()
	last_batch = DistributionBatch.objects.order_by("-distribution_date").first()
	last_distribution_date = last_batch.distribution_date if last_batch else None
	recent_cycles = DistributionBatch.objects.order_by("-distribution_date", "-batch_id")[:12]
	recent_school_reps = (
		SchoolRepresentative.objects.select_related("user", "user__app_profile")
		.order_by("school_name", "representative_id")[:8]
	)
	urgent_messages = list(
		UrgentSupportMessage.objects.select_related("sender_user", "sender_user__app_profile", "completed_by")
		.order_by("is_completed", "-created_at")[:20]
	)
	urgent_rejected = list(
		Beneficiary.objects.select_related("representative")
		.filter(allocation_status=Beneficiary.AllocationStatus.NOT_ELIGIBLE, is_removed=False)
		.order_by("-registration_date")[:5]
	)
	urgent_reassessments = list(
		Beneficiary.objects.select_related("representative")
		.filter(
			allocation_status=Beneficiary.AllocationStatus.ACTIVE,
			is_removed=False,
			reassessment_due_date__isnull=False,
			reassessment_due_date__lte=timezone.localdate(),
		)
		.order_by("reassessment_due_date")[:5]
	)
	urgent_inconsistent = list(
		EligibilityAssessment.objects.select_related("beneficiary", "beneficiary__representative")
		.filter(status=EligibilityAssessment.Status.SUBMITTED, inconsistency_flagged=True)
		.order_by("-assessment_date")[:5]
	)

	return render(
		request,
		"admin/dashboard.html",
		{
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": request.user.email,
			"admin_id": f"ADM-{profile.user_id:05d}",
			"pool_balance": pool_balance,
			"average_meal_amount": average_meal_amount,
			"one_week_target": one_week_target,
			"two_week_target": two_week_target,
			"funding_progress_pct": funding_progress_pct,
			"funding_stage": funding_stage,
			"over_target_amount": over_target_amount,
			"year_total_donations": year_total_donations,
			"active_beneficiaries": active_beneficiaries,
			"active_cashiers": active_cashiers,
			"pending_questionnaires": pending_questionnaires,
			"schools_registered": schools_registered,
			"reassessments_due": reassessments_due,
			"rejected_applicants": rejected_applicants,
			"last_distribution_date": last_distribution_date,
			"distribution_batches": distribution_batches,
			"recent_cycles": recent_cycles,
			"recent_school_reps": recent_school_reps,
			"urgent_messages": urgent_messages,
			"urgent_rejected": urgent_rejected,
			"urgent_reassessments": urgent_reassessments,
			"urgent_inconsistent": urgent_inconsistent,
		},
	)


@login_required
@require_POST
def complete_urgent_message(request):
	profile = getattr(request.user, "app_profile", None)
	if profile is None or profile.role != AppUserProfile.Role.SYSTEM_ADMIN:
		return redirect("dashboard:home")

	message = get_object_or_404(UrgentSupportMessage, message_id=request.POST.get("message_id"))
	if message.is_completed:
		messages.info(request, "Message is already marked completed.")
		return redirect("dashboard:administrator")

	message.is_completed = True
	message.completed_by = request.user
	message.completed_at = timezone.now()
	message.save(update_fields=["is_completed", "completed_by", "completed_at"])
	messages.success(request, "Urgent message marked as completed.")
	return redirect("dashboard:administrator")


@login_required
@never_cache
def admin_monitoring(request):
	profile = getattr(request.user, "app_profile", None)
	if profile is None or profile.role != AppUserProfile.Role.SYSTEM_ADMIN:
		return redirect("dashboard:home")

	allocation_config = AllocationLogicConfig.objects.order_by("-config_id").first()
	if allocation_config is None:
		allocation_config = AllocationLogicConfig.objects.create(
			full_cycle_per_learner=Decimal("200"),
			half_cycle_per_learner=Decimal("100"),
		)

	current_year = timezone.now().year
	goal, _ = DonationGoal.objects.get_or_create(
		year=current_year,
		defaults={"annual_target": Decimal("100000.00")},
	)

	if request.method == "POST" and request.POST.get("action") == "save_allocation_logic":
		full_value = (request.POST.get("full_cycle_per_learner") or "").strip()
		half_value = (request.POST.get("half_cycle_per_learner") or "").strip()
		try:
			new_full = Decimal(full_value)
			new_half = Decimal(half_value)
		except Exception:
			messages.error(request, "Invalid cycle values. Enter valid numeric amounts.")
			return redirect("dashboard:admin_monitoring")

		if new_full <= 0 or new_half <= 0:
			messages.error(request, "Cycle values must be greater than zero.")
			return redirect("dashboard:admin_monitoring")

		if new_half >= new_full:
			messages.error(request, "Half cycle amount must be less than full cycle amount.")
			return redirect("dashboard:admin_monitoring")

		allocation_config.full_cycle_per_learner = new_full
		allocation_config.half_cycle_per_learner = new_half
		allocation_config.updated_by = request.user
		allocation_config.save(update_fields=["full_cycle_per_learner", "half_cycle_per_learner", "updated_by", "updated_at"])
		messages.success(request, "Allocation logic updated successfully.")
		return redirect("dashboard:admin_monitoring")

	if request.method == "POST" and request.POST.get("action") == "save_annual_goal":
		goal_value = (request.POST.get("annual_target") or "").strip()
		try:
			annual_target = Decimal(goal_value)
		except Exception:
			messages.error(request, "Invalid annual goal amount.")
			return redirect("dashboard:admin_monitoring")

		if annual_target <= 0:
			messages.error(request, "Annual goal must be greater than zero.")
			return redirect("dashboard:admin_monitoring")

		goal.annual_target = annual_target
		goal.save(update_fields=["annual_target"])
		messages.success(request, "Annual donation goal updated.")
		return redirect("dashboard:admin_monitoring")

	year_total_donations = (
		Payment.objects.filter(payment_date__year=current_year)
		.aggregate(total=Sum("donation_amount"))
		.get("total")
		or Decimal("0.00")
	)

	annual_target = goal.annual_target or Decimal("100000.00")
	community_progress_percent = Decimal("0.00")
	if annual_target > 0:
		community_progress_percent = min(
			Decimal("100.00"),
			(year_total_donations / annual_target) * Decimal("100"),
		)

	top_contributors = list(
		Payment.objects.filter(payment_date__year=current_year, payer_profile__isnull=False)
		.values("payer_profile", "payer_profile__full_name")
		.annotate(total=Coalesce(Sum("donation_amount"), Decimal("0.00")))
		.order_by("-total", "payer_profile__full_name")[:12]
	)

	return render(
		request,
		"admin/monitoring.html",
		{
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": profile.user.email,
			"allocation_config": allocation_config,
			"current_year": current_year,
			"annual_target": annual_target,
			"community_total": year_total_donations,
			"community_progress_percent": round(community_progress_percent, 2),
			"top_contributors": top_contributors,
		},
	)


@login_required
def admin_users(request):
	profile = getattr(request.user, "app_profile", None)
	if profile is None or profile.role != AppUserProfile.Role.SYSTEM_ADMIN:
		return redirect("dashboard:home")

	if request.method == "POST":
		action = request.POST.get("action")
		if action == "apply_role_privileges":
			target_role = (request.POST.get("target_role") or "").strip()
			allowed_roles = {
				AppUserProfile.Role.CUSTOMER_DONOR,
				AppUserProfile.Role.CASHIER,
				AppUserProfile.Role.SCHOOL_REPRESENTATIVE,
			}
			if target_role not in allowed_roles:
				messages.error(request, "Please select a valid role category.")
				return redirect("dashboard:admin_users")

			updated = AppUserProfile.objects.filter(role=target_role).update(
				can_manage_beneficiaries=bool(request.POST.get("role_can_manage_beneficiaries")),
				can_initiate_cycles=bool(request.POST.get("role_can_initiate_cycles")),
				can_manage_users=bool(request.POST.get("role_can_manage_users")),
				can_view_reports=bool(request.POST.get("role_can_view_reports")),
			)
			messages.success(request, f"Applied category privilege template to {updated} users.")
			return redirect("dashboard:admin_users")

		if action in {"approve_beneficiary", "revoke_beneficiary"}:
			target_beneficiary = get_object_or_404(Beneficiary, beneficiary_id=request.POST.get("target_beneficiary_id"))
			if action == "approve_beneficiary":
				target_beneficiary.allocation_status = Beneficiary.AllocationStatus.ACTIVE
				target_beneficiary.rejection_reason = ""
				target_beneficiary.is_removed = False
				target_beneficiary.removal_reason = ""
				target_beneficiary.removal_date = None
				target_beneficiary.reassessment_status = Beneficiary.ReassessmentStatus.NOT_REQUIRED
				target_beneficiary.save(update_fields=[
					"allocation_status",
					"rejection_reason",
					"is_removed",
					"removal_reason",
					"removal_date",
					"reassessment_status",
				])
				messages.success(request, f"Approved beneficiary {target_beneficiary.learner_name} for support.")
			else:
				reason = (request.POST.get("eligibility_reason") or "").strip()
				if not reason:
					reason = "Eligibility revoked by administrator after review."
				target_beneficiary.allocation_status = Beneficiary.AllocationStatus.NOT_ELIGIBLE
				target_beneficiary.rejection_reason = reason[:255]
				target_beneficiary.save(update_fields=["allocation_status", "rejection_reason"])
				messages.success(request, f"Revoked eligibility for {target_beneficiary.learner_name}.")
		else:
			target_user = get_object_or_404(User, id=request.POST.get("target_user_id"))
			target_profile = getattr(target_user, "app_profile", None)
			if target_profile is None:
				messages.error(request, "Target profile not found.")
				return redirect("dashboard:admin_users")

			if target_profile.role == AppUserProfile.Role.SYSTEM_ADMIN and target_user.id == request.user.id:
				messages.warning(request, "You cannot modify your own admin privileges from this panel.")
				return redirect("dashboard:admin_users")

			if action == "toggle_active":
				target_user.is_active = not target_user.is_active
				target_user.save(update_fields=["is_active"])
				if not target_user.is_active and not target_profile.status_note:
					target_profile.status_note = "Account set inactive by administrator."
					target_profile.save(update_fields=["status_note"])
				messages.success(request, f"Updated active status for {target_profile.full_name}.")

			elif action == "revoke_school_rep":
				if target_profile.role == AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
					if hasattr(target_user, "school_representative"):
						target_user.school_representative.delete()
					target_profile.role = AppUserProfile.Role.CUSTOMER_DONOR
					target_profile.status_note = "School representative privilege revoked by administrator."
					target_profile.save(update_fields=["role", "status_note"])
					messages.success(request, f"Revoked school representative role for {target_profile.full_name}.")
				else:
					messages.info(request, "Selected user is not a school representative.")

			elif action == "save_privileges":
				target_profile.can_manage_beneficiaries = bool(request.POST.get("can_manage_beneficiaries"))
				target_profile.can_initiate_cycles = bool(request.POST.get("can_initiate_cycles"))
				target_profile.can_manage_users = bool(request.POST.get("can_manage_users"))
				target_profile.can_view_reports = bool(request.POST.get("can_view_reports"))
				target_profile.status_note = (request.POST.get("status_note") or "").strip()[:200]
				target_profile.save(update_fields=[
					"can_manage_beneficiaries",
					"can_initiate_cycles",
					"can_manage_users",
					"can_view_reports",
					"status_note",
				])
				messages.success(request, f"Privileges updated for {target_profile.full_name}.")

			elif action == "reset_password":
				new_password = (request.POST.get("new_password") or "").strip()
				if len(new_password) < 8:
					messages.error(request, "Password must be at least 8 characters long.")
				else:
					target_user.set_password(new_password)
					target_user.save(update_fields=["password"])
					messages.success(request, f"Password reset for {target_profile.full_name}.")

			elif action == "delete_user":
				if target_user.id == request.user.id:
					messages.error(request, "You cannot delete your own account.")
				else:
					name = target_profile.full_name
					target_user.delete()
					messages.success(request, f"Deleted user {name}.")

		return redirect("dashboard:admin_users")

	q = (request.GET.get("q") or "").strip()
	school = (request.GET.get("school") or "").strip()
	role = (request.GET.get("role") or "").strip()
	status = (request.GET.get("status") or "").strip().lower()
	beneficiary_status = (request.GET.get("beneficiary_status") or "").strip().lower()

	users = User.objects.select_related("app_profile").all().order_by("app_profile__full_name", "id")
	users = users.exclude(app_profile__isnull=True)

	if q:
		users = users.filter(
			Q(app_profile__full_name__icontains=q)
			| Q(email__icontains=q)
			| Q(id__icontains=q)
		)

	if school:
		users = users.filter(school_representative__school_name__icontains=school)

	if role:
		users = users.filter(app_profile__role=role)

	if status == "active":
		users = users.filter(is_active=True)
	elif status == "inactive":
		users = users.filter(is_active=False)

	beneficiaries = Beneficiary.objects.select_related("representative").order_by("learner_name", "beneficiary_id")
	if q:
		if q.isdigit():
			beneficiaries = beneficiaries.filter(Q(beneficiary_id=int(q)) | Q(learner_name__icontains=q))
		else:
			beneficiaries = beneficiaries.filter(learner_name__icontains=q)

	if school:
		beneficiaries = beneficiaries.filter(representative__school_name__icontains=school)

	if beneficiary_status == "active":
		beneficiaries = beneficiaries.filter(allocation_status=Beneficiary.AllocationStatus.ACTIVE, is_removed=False)
	elif beneficiary_status == "flagged":
		beneficiaries = beneficiaries.filter(
			Q(allocation_status=Beneficiary.AllocationStatus.FLAGGED)
			| Q(reassessment_status=Beneficiary.ReassessmentStatus.PENDING_REASSESSMENT)
			| Q(reassessment_status=Beneficiary.ReassessmentStatus.FLAGGED)
		)
	elif beneficiary_status == "rejected":
		beneficiaries = beneficiaries.filter(allocation_status=Beneficiary.AllocationStatus.NOT_ELIGIBLE, is_removed=False)
	elif beneficiary_status == "deleted":
		beneficiaries = beneficiaries.filter(is_removed=True)

	results = []
	for user in users[:120]:
		p = user.app_profile
		rep = getattr(user, "school_representative", None)
		results.append({
			"user_id": user.id,
			"full_name": p.full_name,
			"email": user.email,
			"role": p.get_role_display(),
			"role_value": p.role,
			"school_name": rep.school_name if rep else "-",
			"status": "Active" if user.is_active else "Inactive",
			"status_note": p.status_note,
			"can_manage_beneficiaries": p.can_manage_beneficiaries,
			"can_initiate_cycles": p.can_initiate_cycles,
			"can_manage_users": p.can_manage_users,
			"can_view_reports": p.can_view_reports,
		})

	beneficiary_results = []
	for learner in beneficiaries[:120]:
		if learner.is_removed:
			status_label = "Deleted"
		elif learner.allocation_status == Beneficiary.AllocationStatus.NOT_ELIGIBLE:
			status_label = "Rejected"
		elif learner.allocation_status == Beneficiary.AllocationStatus.FLAGGED or learner.reassessment_status in {
			Beneficiary.ReassessmentStatus.PENDING_REASSESSMENT,
			Beneficiary.ReassessmentStatus.FLAGGED,
		}:
			status_label = "Flagged"
		else:
			status_label = "Active"

		beneficiary_results.append({
			"beneficiary_id": learner.beneficiary_id,
			"learner_name": learner.learner_name,
			"school_name": (learner.representative.school_name if learner.representative else "-") or "-",
			"status": status_label,
			"reason": learner.rejection_reason or learner.removal_reason or "",
			"evidence_statement_1": latest_assessment.evidence_statement_1 if (latest_assessment := learner.assessments.order_by("-assessment_date").first()) else "",
			"evidence_statement_2": latest_assessment.evidence_statement_2 if latest_assessment else "",
			"inconsistency_notes": latest_assessment.inconsistency_notes if latest_assessment else "",
		})

	school_options = list(
		SchoolRepresentative.objects.exclude(school_name__isnull=True)
		.exclude(school_name__exact="")
		.values_list("school_name", flat=True)
		.distinct()
		.order_by("school_name")
	)

	return render(
		request,
		"admin/users.html",
		{
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": profile.user.email,
			"results": results,
			"q": q,
			"school": school,
			"role": role,
			"status": status,
			"beneficiary_status": beneficiary_status,
			"school_options": school_options,
			"role_options": AppUserProfile.Role.choices,
			"role_options_bulk": [
				(choice_value, choice_label)
				for choice_value, choice_label in AppUserProfile.Role.choices
				if choice_value != AppUserProfile.Role.SYSTEM_ADMIN
			],
			"beneficiary_results": beneficiary_results,
		},
	)

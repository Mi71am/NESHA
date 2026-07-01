from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
import re
from datetime import timedelta
from django.utils import timezone
import json

from accounts.models import AppUserProfile, SchoolRepresentative

from .assessment_logic import QUESTION_KEYS, evaluate_assessment
from .models import Beneficiary, EligibilityAssessment, ReassessmentRecord
from .reassessment_logic import REASSESSMENT_KEYS, evaluate_reassessment


QUESTION_SECTIONS = [
	{
		"title": "Section 1: Household Structure",
		"question_numbers": [1, 2, 3],
	},
	{
		"title": "Section 2: Household Economic Stability",
		"question_numbers": [4, 5, 6],
	},
	{
		"title": "Section 3: Food Security",
		"question_numbers": [7, 8, 9],
	},
	{
		"title": "Section 4: Attendance & Learning",
		"question_numbers": [10, 11, 12],
	},
	{
		"title": "Section 5: Living Conditions",
		"question_numbers": [13, 14, 15],
	},
	{
		"title": "Section 6: Vulnerability Indicators",
		"question_numbers": [16, 17, 18],
	},
	{
		"title": "Section 7: Existing Support",
		"question_numbers": [19, 20, 21],
	},
	{
		"title": "Section 8: School Assessment",
		"question_numbers": [22, 23, 24],
	},
]

QUESTION_TEXT = {
	1: "Who does the learner primarily reside with?",
	2: "How many school-going children depend on the same household income?",
	3: "What is the highest education level attained by the primary caregiver?",
	4: "What best describes the household's primary source of income?",
	5: "How stable is the household income throughout the year?",
	6: "In the past 12 months, has the household experienced loss of income?",
	7: "How often is the learner observed bringing or accessing meals during school days?",
	8: "How often has the learner reported food-related challenges?",
	9: "Have staff observed signs that may indicate food insecurity?",
	10: "Learner attendance over the previous term:",
	11: "Has the learner missed school due to financial challenges?",
	12: "Teachers rate the learner's classroom engagement as:",
	13: "Type of housing occupied by household:",
	14: "Access to electricity:",
	15: "Access to clean water:",
	16: "Learner's caregiving situation:",
	17: "Is the learner responsible for caregiving duties at home?",
	18: "Has the learner experienced a major adverse event in the last two years?",
	19: "Does the learner currently receive any educational assistance?",
	20: "Does the household receive external assistance?",
	21: "How dependent is the learner on school-based support programs?",
	22: "Teacher recommendation level:",
	23: "Welfare committee recommendation:",
	24: "Overall observed vulnerability level:",
}

QUESTION_OPTIONS = {
	1: ["Both parents", "Single parent", "Grandparent(s)", "Other relative(s)", "Guardian / Foster arrangement", "Child-headed household"],
	2: ["1-2", "3-4", "5-6", "7-8", "9+"],
	3: ["University/College", "Secondary", "Primary", "No formal education", "Unknown"],
	4: ["Formal employment", "Small business", "Casual labour", "Farming/subsistence activities", "No consistent source"],
	5: ["Very stable", "Mostly stable", "Occasionally unstable", "Frequently unstable", "No predictable income"],
	6: ["No", "Minor reduction", "Moderate reduction", "Significant reduction", "Complete loss"],
	7: ["Always", "Usually", "Sometimes", "Rarely", "Never"],
	8: ["Never", "Rarely", "Sometimes", "Frequently", "Very frequently"],
	9: ["No observations", "Isolated observations", "Occasional observations", "Repeated observations", "Consistent observations"],
	10: ["Excellent", "Good", "Fair", "Poor", "Very poor"],
	11: ["Never", "Once", "Occasionally", "Frequently", "Very frequently"],
	12: ["Excellent", "Good", "Average", "Below average", "Significantly affected"],
	13: ["Permanent", "Semi-permanent", "Temporary", "Shared shelter", "Unstable/no permanent residence"],
	14: ["Consistent", "Intermittent", "Rare", "None", "Unknown"],
	15: ["Reliable", "Mostly reliable", "Limited", "Very limited", "Unreliable"],
	16: ["Stable", "Minor challenges", "Moderate challenges", "Significant challenges", "High-risk circumstances"],
	17: ["Never", "Rarely", "Sometimes", "Frequently", "Daily"],
	18: ["None", "One minor event", "One major event", "Multiple events", "Ongoing severe circumstances"],
	19: ["Comprehensive support", "Significant support", "Moderate support", "Minimal support", "No support"],
	20: ["Consistent support", "Occasional support", "Limited support", "Rare support", "No support"],
	21: ["Not dependent", "Slightly dependent", "Moderately dependent", "Highly dependent", "Critically dependent"],
	22: ["Not recommended", "Slightly recommended", "Recommended", "Strongly recommended", "Urgently recommended"],
	23: ["Not recommended", "Low priority", "Moderate priority", "High priority", "Critical priority"],
	24: ["Very low", "Low", "Moderate", "High", "Very high"],
}


REASSESSMENT_QUESTION_TEXT = {
	1: "Compared to the previous assessment, the household's financial situation is:",
	2: "Has the household gained any new stable source of income?",
	3: "Has the number of household dependents changed?",
	4: "How consistently does the learner access meals outside school?",
	5: "During the past school term, how often has the learner experienced food-related challenges?",
	6: "School staff observations indicate the learner currently appears:",
	7: "Attendance since the previous assessment has:",
	8: "Teachers describe classroom engagement as:",
	9: "Has the learner continued to require meal support throughout the review period?",
	10: "Is the learner now receiving support from another programme?",
	11: "Has the household received any new financial assistance?",
	12: "Overall dependence on NESHA meal support is currently:",
	13: "Based on current observations, continued support should be:",
	14: "Current vulnerability level is:",
	15: "The learner's circumstances compared to the previous assessment are:",
}

REASSESSMENT_OPTIONS = {
	1: ["Significantly improved", "Slightly improved", "No significant change", "Slightly worsened", "Significantly worsened"],
	2: ["Yes, stable employment", "Yes, seasonal income", "Small improvement only", "No", "Household income has reduced"],
	3: ["Reduced significantly", "Reduced slightly", "No change", "Increased slightly", "Increased significantly"],
	4: ["Always", "Usually", "Sometimes", "Rarely", "Almost never"],
	5: ["Never", "Rarely", "Sometimes", "Frequently", "Very frequently"],
	6: ["Well nourished", "Generally healthy", "Occasionally affected", "Frequently affected", "Severely affected"],
	7: ["Improved significantly", "Improved slightly", "Remained stable", "Declined slightly", "Declined significantly"],
	8: ["Excellent", "Good", "Average", "Below average", "Severely affected by socioeconomic challenges"],
	9: ["Rarely", "Occasionally", "Sometimes", "Frequently", "Continuously"],
	10: ["Comprehensive support", "Significant support", "Moderate support", "Minimal support", "No external support"],
	11: ["Significant improvement", "Moderate improvement", "Minor improvement", "None", "Household situation has worsened"],
	12: ["Very low", "Low", "Moderate", "High", "Critical"],
	13: ["Discontinued", "Reduced", "Maintained temporarily", "Continued", "Continued as high priority"],
	14: ["Very Low", "Low", "Moderate", "High", "Very High"],
	15: ["Much improved", "Slightly improved", "Unchanged", "Slightly worse", "Significantly worse"],
}


def _word_count(value):
	return len(re.findall(r"\\b[\\w'-]+\\b", value or ""))


def _school_required(request):
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
	return profile, rep


def _school_sidebar_context(profile, rep, active_key):
	return {
		"profile": profile,
		"display_name": profile.full_name.upper(),
		"display_email": profile.user.email,
		"tsc_number": rep.tsc_number,
		"school_name": rep.school_name,
		"active_nav": active_key,
	}


def _beneficiary_status_summary(beneficiary):
	if beneficiary.is_removed:
		return "Deleted", beneficiary.removal_reason or "No reason provided."

	if beneficiary.allocation_status == Beneficiary.AllocationStatus.NOT_ELIGIBLE:
		return "Rejected", beneficiary.rejection_reason or "Did not meet eligibility threshold."

	if beneficiary.allocation_status == Beneficiary.AllocationStatus.FLAGGED:
		return "Flagged", "Marked for reassessment."

	if beneficiary.reassessment_status in {
		Beneficiary.ReassessmentStatus.PENDING_REASSESSMENT,
		Beneficiary.ReassessmentStatus.FLAGGED,
	}:
		return "Flagged", "Pending reassessment review."

	return "Active", ""


def _beneficiary_detail_context(beneficiary):
	total_allocations = (
		beneficiary.allocations.aggregate(total=Sum("allocation_amount")).get("total")
		or 0
	)
	allocations = list(
		beneficiary.allocations.order_by("allocation_date", "allocation_id")
	)
	allocation_chart_labels = [a.allocation_date.strftime("%d %b %Y") for a in allocations]
	allocation_chart_amounts = [float(a.allocation_amount or 0) for a in allocations]
	status_label, status_reason = _beneficiary_status_summary(beneficiary)

	return {
		"beneficiary": beneficiary,
		"status_label": status_label,
		"status_reason": status_reason,
		"total_allocations": total_allocations,
		"allocation_chart_labels_json": json.dumps(allocation_chart_labels),
		"allocation_chart_amounts_json": json.dumps(allocation_chart_amounts),
	}


def index(request):
	return redirect("beneficiaries:view")


@login_required
def register(request):
	profile, rep = _school_required(request)
	if profile.role != AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
		return redirect("dashboard:home")

	step = int(request.GET.get("step", "1"))
	step = max(1, min(9, step))
	resume_from = request.GET.get("resume_from")
	if resume_from == "db":
		stored_form = request.session.get("beneficiary_form", {})
		answered_count = sum(1 for key in QUESTION_KEYS if stored_form.get(key))
		if answered_count == 0:
			step = 1
		else:
			step = min(9, (answered_count // 3) + 1)

	if request.method == "POST":
		form_data = request.session.get("beneficiary_form", {})
		for q_key in QUESTION_KEYS:
			if q_key in request.POST:
				form_data[q_key] = request.POST.get(q_key)

		for field in ["learner_name", "learner_gender", "tap2eat_acc_no", "evidence_statement_1", "evidence_statement_2"]:
			if field in request.POST:
				form_data[field] = request.POST.get(field, "").strip()

		form_data["verification_confirmed"] = request.POST.get("verification_confirmed") == "on"
		request.session["beneficiary_form"] = form_data

		action = request.POST.get("action", "next")
		if action == "save_draft":
			beneficiary = Beneficiary.objects.create(
				representative=rep,
				learner_name=form_data.get("learner_name", "Draft Learner") or "Draft Learner",
				learner_gender=form_data.get("learner_gender", "") or None,
				tap2eat_acc_no=form_data.get("tap2eat_acc_no", ""),
				allocation_status=Beneficiary.AllocationStatus.PENDING_APPROVAL,
			)
			EligibilityAssessment.objects.create(
				beneficiary=beneficiary,
				status=EligibilityAssessment.Status.DRAFT,
				answers={k: form_data.get(k, "") for k in QUESTION_KEYS},
				evidence_statement_1=form_data.get("evidence_statement_1", ""),
				evidence_statement_2=form_data.get("evidence_statement_2", ""),
				verification_confirmed=form_data.get("verification_confirmed", False),
			)
			messages.success(request, "Draft saved to pending questionnaires.")
			request.session.pop("beneficiary_form", None)
			return redirect("dashboard:school_representative")

		if action == "submit":
			if not form_data.get("learner_name"):
				messages.error(request, "Learner name is required before submission.")
				return redirect(f"{request.path}?step=1")
			if form_data.get("learner_gender") not in {"female", "male"}:
				messages.error(request, "Please select learner gender before submission.")
				return redirect(f"{request.path}?step=1")
			if not form_data.get("verification_confirmed"):
				messages.error(request, "Please confirm the verification statement before submission.")
				return redirect(f"{request.path}?step=9")

			result = evaluate_assessment(
				{k: form_data.get(k, "") for k in QUESTION_KEYS},
				learner_gender=form_data.get("learner_gender", ""),
			)
			allocation_status = Beneficiary.AllocationStatus.ACTIVE if result.is_eligible else Beneficiary.AllocationStatus.NOT_ELIGIBLE
			rejection_reason = ""
			if not result.is_eligible:
				rejection_reason = "Eligibility score threshold was not met. Girls require at least 67 and boys require at least 70."

			beneficiary = Beneficiary.objects.create(
				representative=rep,
				learner_name=form_data.get("learner_name"),
				learner_gender=form_data.get("learner_gender", "") or None,
				tap2eat_acc_no=form_data.get("tap2eat_acc_no", ""),
				eligibility_score=result.total_score,
				allocation_status=allocation_status,
				reassessment_status=Beneficiary.ReassessmentStatus.NOT_REQUIRED,
				rejection_reason=rejection_reason,
			)

			EligibilityAssessment.objects.create(
				beneficiary=beneficiary,
				questionnaire_score=result.total_score,
				total_score=result.total_score,
				is_eligible=result.is_eligible,
				inconsistency_flagged=result.inconsistency_flagged,
				inconsistency_notes=result.inconsistency_notes,
				status=EligibilityAssessment.Status.SUBMITTED,
				answers={k: form_data.get(k, "") for k in QUESTION_KEYS},
				evidence_statement_1=form_data.get("evidence_statement_1", ""),
				evidence_statement_2=form_data.get("evidence_statement_2", ""),
				verification_confirmed=True,
			)

			if result.inconsistency_flagged:
				inconsistent_count = EligibilityAssessment.objects.filter(
					beneficiary__representative=rep,
					inconsistency_flagged=True,
					status=EligibilityAssessment.Status.SUBMITTED,
				).count()
				if result.is_eligible:
					messages.success(request, f"Approved: {beneficiary.learner_name} has been enrolled as a beneficiary.")
				else:
					messages.error(request, f"Rejected: {beneficiary.learner_name} did not meet the eligibility threshold. See reason below.")
				messages.warning(request, "Record also flagged for admin consistency review.")
				if inconsistent_count >= 5:
					profile.user.is_active = False
					profile.user.save(update_fields=["is_active"])
					messages.error(request, "Account suspended after repeated inconsistent submissions. School should re-apply with another representative.")
					request.session.pop("beneficiary_form", None)
					return redirect("accounts:logout")
			else:
				if result.is_eligible:
					messages.success(request, f"Approved: {beneficiary.learner_name} has been enrolled as a beneficiary.")
				else:
					messages.error(request, f"Rejected: {beneficiary.learner_name} did not meet the eligibility threshold. See reason below.")
			request.session.pop("beneficiary_form", None)
			return redirect("beneficiaries:view")

		if action == "prev":
			step = max(1, step - 1)
		else:
			step = min(9, step + 1)

		return redirect(f"{request.path}?step={step}")

	stored = request.session.get("beneficiary_form", {})
	sections = []
	if step <= 8:
		section_meta = QUESTION_SECTIONS[step - 1]
		question_items = []
		for number in section_meta["question_numbers"]:
			options = QUESTION_OPTIONS[number]
			question_items.append(
				{
					"number": number,
					"text": QUESTION_TEXT[number],
					"key": f"q{number}",
					"selected": stored.get(f"q{number}", ""),
					"options": [
						{"value": str(idx + 1), "label": label} for idx, label in enumerate(options)
					],
				}
			)
		sections.append({"title": section_meta["title"], "questions": question_items})

	context = _school_sidebar_context(profile, rep, "register")
	context.update(
		{
			"step": step,
			"sections": sections,
			"draft": stored,
			"title": "NESHA BENEFICIARY ELIGIBILITY ASSESSMENT",
		}
	)
	return render(request, "school/register_beneficiary.html", context)


@login_required
def pending_questionnaires(request):
	profile, rep = _school_required(request)
	if profile.role != AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
		return redirect("dashboard:home")

	pending = Beneficiary.objects.filter(
		representative=rep,
		allocation_status=Beneficiary.AllocationStatus.PENDING_APPROVAL,
		assessments__status=EligibilityAssessment.Status.DRAFT,
	).distinct().order_by("-registration_date")

	context = _school_sidebar_context(profile, rep, "pending")
	context.update({"pending": pending})
	return render(request, "school/pending_questionnaires.html", context)


@login_required
def resume_questionnaire(request, beneficiary_id):
	profile, rep = _school_required(request)
	if profile.role != AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
		return redirect("dashboard:home")

	beneficiary = get_object_or_404(
		Beneficiary,
		beneficiary_id=beneficiary_id,
		representative=rep,
		allocation_status=Beneficiary.AllocationStatus.PENDING_APPROVAL,
	)
	draft_assessment = beneficiary.assessments.filter(
		status=EligibilityAssessment.Status.DRAFT,
	).order_by("-assessment_date").first()

	if draft_assessment is None:
		messages.error(request, "No saved draft was found for this learner.")
		return redirect("beneficiaries:pending")

	request.session["beneficiary_form"] = {
		**(draft_assessment.answers or {}),
		"learner_name": beneficiary.learner_name or "",
		"learner_gender": beneficiary.learner_gender or "",
		"tap2eat_acc_no": beneficiary.tap2eat_acc_no or "",
		"evidence_statement_1": draft_assessment.evidence_statement_1 or "",
		"evidence_statement_2": draft_assessment.evidence_statement_2 or "",
		"verification_confirmed": bool(draft_assessment.verification_confirmed),
	}

	messages.success(request, f"Draft loaded for {beneficiary.learner_name}. Continue and submit when ready.")
	return redirect(f"{reverse('beneficiaries:register')}?resume_from=db")


@login_required
def view_beneficiaries(request):
	profile, rep = _school_required(request)
	if profile.role != AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
		return redirect("dashboard:home")

	approved = Beneficiary.objects.filter(
		representative=rep,
		allocation_status=Beneficiary.AllocationStatus.ACTIVE,
	).order_by("learner_name")

	not_eligible = Beneficiary.objects.filter(
		representative=rep,
		allocation_status=Beneficiary.AllocationStatus.NOT_ELIGIBLE,
	).order_by("learner_name")

	context = _school_sidebar_context(profile, rep, "view")
	context.update(
		{
			"approved": approved,
			"not_eligible": not_eligible,
		}
	)
	return render(request, "school/view_beneficiaries.html", context)


@login_required
def reassess_beneficiaries(request):
	profile, rep = _school_required(request)
	if profile.role != AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
		return redirect("dashboard:home")

	flagged = Beneficiary.objects.filter(
		representative=rep,
		allocation_status=Beneficiary.AllocationStatus.ACTIVE,
		is_removed=False,
	).filter(
		reassessment_due_date__isnull=False,
		reassessment_due_date__lte=timezone.localdate(),
	).order_by("-support_cycle_count", "learner_name")

	if request.method == "POST":
		beneficiary = get_object_or_404(flagged, beneficiary_id=request.POST.get("beneficiary_id"))
		if request.POST.get("action") == "start_reassessment":
			return redirect("beneficiaries:reassess_form", beneficiary_id=beneficiary.beneficiary_id)
		if request.POST.get("action") == "remove":
			reason = (request.POST.get("removal_reason") or "").strip()
			if not reason:
				messages.error(request, "Removal reason is required.")
				return redirect("beneficiaries:reassess")
			if _word_count(reason) > 20:
				messages.error(request, "Removal reason must be 20 words or fewer.")
				return redirect("beneficiaries:reassess")
			beneficiary.is_removed = True
			beneficiary.removal_reason = reason
			beneficiary.removal_date = timezone.localdate()
			beneficiary.allocation_status = Beneficiary.AllocationStatus.NOT_ELIGIBLE
			beneficiary.reassessment_status = Beneficiary.ReassessmentStatus.NOT_REQUIRED
			beneficiary.save(update_fields=["is_removed", "removal_reason", "removal_date", "allocation_status", "reassessment_status"])
			messages.success(request, f"{beneficiary.learner_name} removed from active beneficiaries.")
		return redirect("beneficiaries:reassess")

	context = _school_sidebar_context(profile, rep, "reassess")
	context.update({"flagged": flagged})
	return render(request, "school/reassess_beneficiaries.html", context)


@login_required
def reassessment_form(request, beneficiary_id):
	profile, rep = _school_required(request)
	if profile.role != AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
		return redirect("dashboard:home")

	beneficiary = get_object_or_404(
		Beneficiary,
		beneficiary_id=beneficiary_id,
		representative=rep,
		allocation_status=Beneficiary.AllocationStatus.ACTIVE,
		is_removed=False,
	)

	if request.method == "POST":
		answers = {key: request.POST.get(key, "") for key in REASSESSMENT_KEYS}
		evidence_statement_1 = (request.POST.get("evidence_statement_1") or "").strip()
		evidence_statement_2 = (request.POST.get("evidence_statement_2") or "").strip()
		verification_confirmed = request.POST.get("verification_confirmed") == "on"

		if not verification_confirmed:
			messages.error(request, "Please confirm the verification statement before submitting reassessment.")
			return redirect("beneficiaries:reassess_form", beneficiary_id=beneficiary_id)

		result = evaluate_reassessment(answers)
		next_review_date = None
		if result.next_review_in_days > 0:
			next_review_date = timezone.localdate() + timedelta(days=result.next_review_in_days)

		ReassessmentRecord.objects.create(
			beneficiary=beneficiary,
			answers=answers,
			evidence_statement_1=evidence_statement_1,
			evidence_statement_2=evidence_statement_2,
			verification_confirmed=verification_confirmed,
			total_score=result.total_score,
			outcome=result.outcome,
			next_review_date=next_review_date,
		)

		if result.outcome == ReassessmentRecord.Outcome.REMOVE:
			beneficiary.is_removed = True
			beneficiary.removal_reason = "Removed after reassessment outcome."
			beneficiary.removal_date = timezone.localdate()
			beneficiary.allocation_status = Beneficiary.AllocationStatus.NOT_ELIGIBLE
			beneficiary.reassessment_status = Beneficiary.ReassessmentStatus.NOT_REQUIRED
			beneficiary.reassessment_due_date = None
			beneficiary.save(update_fields=["is_removed", "removal_reason", "removal_date", "allocation_status", "reassessment_status", "reassessment_due_date"])
			messages.success(request, f"{beneficiary.learner_name} was removed from programme after reassessment.")
		elif result.outcome == ReassessmentRecord.Outcome.UNDER_REVIEW:
			beneficiary.reassessment_status = Beneficiary.ReassessmentStatus.PENDING_REASSESSMENT
			beneficiary.reassessment_due_date = next_review_date
			beneficiary.save(update_fields=["reassessment_status", "reassessment_due_date"])
			messages.warning(request, f"{beneficiary.learner_name} remains under review. Next reassessment available in one month.")
		else:
			beneficiary.reassessment_status = Beneficiary.ReassessmentStatus.NOT_REQUIRED
			beneficiary.reassessment_due_date = None
			beneficiary.save(update_fields=["reassessment_status", "reassessment_due_date"])
			if result.outcome == ReassessmentRecord.Outcome.HIGH_PRIORITY:
				messages.success(request, f"{beneficiary.learner_name} marked as high-priority beneficiary.")
			else:
				messages.success(request, f"{beneficiary.learner_name} continues receiving support.")

		return redirect("beneficiaries:reassess")

	questions = []
	for number in range(1, 16):
		questions.append(
			{
				"number": number,
				"text": REASSESSMENT_QUESTION_TEXT[number],
				"key": f"r{number}",
				"options": [
					{"value": str(idx + 1), "label": label}
					for idx, label in enumerate(REASSESSMENT_OPTIONS[number])
				],
			}
		)

	context = _school_sidebar_context(profile, rep, "reassess")
	context.update({"beneficiary": beneficiary, "questions": questions})
	return render(request, "school/reassessment_form.html", context)


@login_required
def beneficiary_detail(request, beneficiary_id):
	profile = getattr(request.user, "app_profile", None)
	if profile is None:
		return redirect("dashboard:home")

	beneficiary_qs = Beneficiary.objects.select_related("representative")

	if profile.role == AppUserProfile.Role.SCHOOL_REPRESENTATIVE:
		rep = getattr(request.user, "school_representative", None)
		if rep is None:
			return redirect("dashboard:home")
		beneficiary = get_object_or_404(beneficiary_qs, beneficiary_id=beneficiary_id, representative=rep)
		context = _school_sidebar_context(profile, rep, "view")
		context.update(_beneficiary_detail_context(beneficiary))
		context.update({"is_admin": False})
		return render(request, "beneficiaries/detail.html", context)

	if profile.role == AppUserProfile.Role.SYSTEM_ADMIN:
		beneficiary = get_object_or_404(beneficiary_qs, beneficiary_id=beneficiary_id)
		context = {
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": profile.user.email,
			"is_admin": True,
		}
		context.update(_beneficiary_detail_context(beneficiary))
		return render(request, "beneficiaries/detail.html", context)

	return redirect("dashboard:home")


@login_required
def admin_beneficiaries(request):
	profile = getattr(request.user, "app_profile", None)
	if profile is None or profile.role != AppUserProfile.Role.SYSTEM_ADMIN:
		return redirect("dashboard:home")

	q = (request.GET.get("q") or "").strip()
	school = (request.GET.get("school") or "").strip()
	status = (request.GET.get("status") or "").strip().lower()

	beneficiaries = Beneficiary.objects.select_related("representative").order_by("learner_name", "beneficiary_id")

	if q:
		if q.isdigit():
			beneficiaries = beneficiaries.filter(Q(beneficiary_id=int(q)) | Q(learner_name__icontains=q))
		else:
			beneficiaries = beneficiaries.filter(learner_name__icontains=q)

	if school:
		beneficiaries = beneficiaries.filter(representative__school_name__icontains=school)

	if status == "active":
		beneficiaries = beneficiaries.filter(
			allocation_status=Beneficiary.AllocationStatus.ACTIVE,
			is_removed=False,
			reassessment_status=Beneficiary.ReassessmentStatus.NOT_REQUIRED,
		)
	elif status == "flagged":
		beneficiaries = beneficiaries.filter(
			Q(allocation_status=Beneficiary.AllocationStatus.FLAGGED)
			| Q(reassessment_status=Beneficiary.ReassessmentStatus.PENDING_REASSESSMENT)
			| Q(reassessment_status=Beneficiary.ReassessmentStatus.FLAGGED)
		)
	elif status == "rejected":
		beneficiaries = beneficiaries.filter(allocation_status=Beneficiary.AllocationStatus.NOT_ELIGIBLE, is_removed=False)
	elif status == "deleted":
		beneficiaries = beneficiaries.filter(is_removed=True)

	results = []
	for learner in beneficiaries[:100]:
		status_label, _ = _beneficiary_status_summary(learner)
		results.append({
			"beneficiary_id": learner.beneficiary_id,
			"learner_name": learner.learner_name,
			"school_name": (learner.representative.school_name if learner.representative else "-") or "-",
			"status_label": status_label,
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
		"admin/beneficiaries.html",
		{
			"profile": profile,
			"display_name": profile.full_name.upper(),
			"display_email": profile.user.email,
			"results": results,
			"q": q,
			"school": school,
			"status": status,
			"school_options": school_options,
		},
	)

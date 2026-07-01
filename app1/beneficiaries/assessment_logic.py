from dataclasses import dataclass


QUESTION_KEYS = [f"q{i}" for i in range(1, 25)]


@dataclass
class AssessmentResult:
    total_score: int
    is_eligible: bool
    inconsistency_flagged: bool
    inconsistency_notes: str


def _option_to_points(option_value: str) -> int:
    # Option values are expected to be "1" to "5", scoring 0 to 4.
    try:
        numeric = int(option_value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(4, numeric - 1))


def evaluate_assessment(answers: dict, learner_gender: str = "") -> AssessmentResult:
    base_total = 0
    for key in QUESTION_KEYS:
        base_total += _option_to_points(answers.get(key))

    # Replace raw Q22/Q23 scores with weighted values (x1.5 each).
    q22_raw = _option_to_points(answers.get("q22"))
    q23_raw = _option_to_points(answers.get("q23"))
    weighted_total = base_total - q22_raw - q23_raw + int(round(q22_raw * 1.5 + q23_raw * 1.5))

    total_score = max(0, min(100, weighted_total))
    normalized_gender = (learner_gender or "").strip().lower()
    threshold = 67 if normalized_gender in {"girl", "female"} else 70
    is_eligible = total_score >= threshold

    inconsistencies = []
    if answers.get("q10") == "1" and answers.get("q22") in {"4", "5"} and answers.get("q24") in {"1", "2"}:
        inconsistencies.append(
            "Attendance appears strong while recommendation urgency is high and overall vulnerability is low."
        )
    if answers.get("q6") in {"1", "2"} and answers.get("q8") in {"4", "5"}:
        inconsistencies.append(
            "Reported food challenges are severe despite minimal household income-loss indicators."
        )
    if answers.get("q14") in {"1", "2"} and answers.get("q15") in {"1", "2"} and answers.get("q16") in {"4", "5"}:
        inconsistencies.append(
            "Living-condition indicators appear stable while caregiving risk is marked as high."
        )

    flagged = len(inconsistencies) > 0
    notes = " ".join(inconsistencies)

    return AssessmentResult(
        total_score=total_score,
        is_eligible=is_eligible,
        inconsistency_flagged=flagged,
        inconsistency_notes=notes,
    )

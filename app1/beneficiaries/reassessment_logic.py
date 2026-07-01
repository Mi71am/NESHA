from dataclasses import dataclass


REASSESSMENT_KEYS = [f"r{i}" for i in range(1, 16)]


@dataclass
class ReassessmentResult:
    total_score: int
    outcome: str
    next_review_in_days: int


def _option_to_points(option_value: str) -> int:
    try:
        numeric = int(option_value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(4, numeric - 1))


def evaluate_reassessment(answers: dict) -> ReassessmentResult:
    base_total = 0
    for key in [f"r{i}" for i in range(1, 13)]:
        base_total += _option_to_points(answers.get(key))

    q13 = _option_to_points(answers.get("r13")) * 2
    q14 = _option_to_points(answers.get("r14")) * 2
    q15 = _option_to_points(answers.get("r15")) * 2

    total_score = max(0, min(72, base_total + q13 + q14 + q15))

    if total_score <= 39:
        return ReassessmentResult(total_score=total_score, outcome="remove", next_review_in_days=0)
    if total_score <= 54:
        return ReassessmentResult(total_score=total_score, outcome="under_review", next_review_in_days=30)
    if total_score <= 63:
        return ReassessmentResult(total_score=total_score, outcome="continue_support", next_review_in_days=0)
    return ReassessmentResult(total_score=total_score, outcome="high_priority", next_review_in_days=0)

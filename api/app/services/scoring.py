from __future__ import annotations


def calculate_mastery(score_obtained_total: float, score_max_total: float) -> float:
    if score_max_total <= 0:
        return 0.5
    return round(score_obtained_total / score_max_total, 4)


def calculate_confidence(answered_question_count: int, mapped_question_count: int) -> float:
    if mapped_question_count <= 0:
        return 0.35
    confidence = answered_question_count / mapped_question_count
    return round(min(0.95, confidence), 4)


def weakness_band(mastery_score: float) -> str:
    if mastery_score >= 0.75:
        return "strong"
    if mastery_score >= 0.60:
        return "borderline"
    return "weak"

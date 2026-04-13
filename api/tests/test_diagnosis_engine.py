from __future__ import annotations

from app.services.diagnosis import DiagnosisEngine


def sample_paths() -> list[list[dict]]:
    return [
        [
            {"id": "ALG-001", "name": "Number operations review", "description": ""},
            {"id": "ALG-002", "name": "Arithmetic order of operations", "description": ""},
            {"id": "ALG-004", "name": "Substitution in expressions", "description": ""},
            {"id": "ALG-005", "name": "Simplifying like terms", "description": ""},
            {"id": "ALG-007", "name": "Solving one-step equations", "description": ""},
            {"id": "ALG-008", "name": "Solving two-step equations", "description": ""}
        ]
    ]


def test_diagnosis_is_deterministic_and_prioritizes_early_weakness() -> None:
    engine = DiagnosisEngine()
    latest_scores = {
        "ALG-001": {"mastery_score": 0.34, "confidence": 0.9},
        "ALG-002": {"mastery_score": 0.49, "confidence": 0.85},
        "ALG-004": {"mastery_score": 0.55, "confidence": 0.9},
        "ALG-005": {"mastery_score": 0.58, "confidence": 0.9},
        "ALG-007": {"mastery_score": 0.62, "confidence": 0.8},
        "ALG-008": {"mastery_score": 0.52, "confidence": 0.88}
    }
    recent_scores_by_concept = {
        "ALG-001": [
            {"assessment_date": "2026-03-01", "mastery_score": 0.34, "confidence": 0.9},
            {"assessment_date": "2026-02-01", "mastery_score": 0.46, "confidence": 0.88},
        ],
        "ALG-002": [
            {"assessment_date": "2026-03-01", "mastery_score": 0.49, "confidence": 0.85},
            {"assessment_date": "2026-02-01", "mastery_score": 0.42, "confidence": 0.83},
        ],
    }
    result_a = engine.run(
        student_id="STU-001",
        student={"id": "STU-001", "full_name": "Student 001", "cohort": "8A"},
        target_concept={"id": "ALG-008", "name": "Solving two-step equations", "description": ""},
        prerequisite_paths=sample_paths(),
        latest_scores=latest_scores,
        recent_scores_by_concept=recent_scores_by_concept,
        assessment_summary={"assessment_count": 4, "latest_assessment_date": "2026-03-01"},
        cohort_target_mastery=0.71,
    )
    result_b = engine.run(
        student_id="STU-001",
        student={"id": "STU-001", "full_name": "Student 001", "cohort": "8A"},
        target_concept={"id": "ALG-008", "name": "Solving two-step equations", "description": ""},
        prerequisite_paths=sample_paths(),
        latest_scores=latest_scores,
        recent_scores_by_concept=recent_scores_by_concept,
        assessment_summary={"assessment_count": 4, "latest_assessment_date": "2026-03-01"},
        cohort_target_mastery=0.71,
    )
    assert result_a.root_cause_candidates[0].concept_id == "ALG-001"
    assert result_a.concept_trends[0].direction == "declining"
    assert result_a.readiness.status == "watch"
    assert result_a.model_dump() == result_b.model_dump()


def test_missing_data_degrades_gracefully() -> None:
    engine = DiagnosisEngine()
    result = engine.run(
        student_id="STU-404",
        student={"id": "STU-404", "full_name": "Student 404", "cohort": "8B"},
        target_concept={"id": "ALG-008", "name": "Solving two-step equations", "description": ""},
        prerequisite_paths=sample_paths(),
        latest_scores={},
        recent_scores_by_concept={},
        assessment_summary={"assessment_count": 0, "latest_assessment_date": None},
        cohort_target_mastery=None,
    )
    assert result.weak_concepts
    assert result.weak_concepts[0].confidence == 0.35
    assert result.readiness.status == "needs_immediate_support"
    assert "earliest weak prerequisite" in result.explanation

from __future__ import annotations

from app.services.diagnosis import DiagnosisEngine


def sample_paths() -> list[list[dict]]:
    return [
        [
            {"id": "ENG-001", "subject_id": "OL-ENG", "name": "Core vocabulary", "description": ""},
            {"id": "ENG-002", "subject_id": "OL-ENG", "name": "Sentence grammar", "description": ""},
            {"id": "ENG-005", "subject_id": "OL-ENG", "name": "Paragraph structure", "description": ""},
            {"id": "ENG-006", "subject_id": "OL-ENG", "name": "Guided writing", "description": ""},
            {"id": "ENG-010", "subject_id": "OL-ENG", "name": "Extended writing", "description": ""}
        ]
    ]


def test_diagnosis_is_deterministic_and_prioritizes_early_weakness() -> None:
    engine = DiagnosisEngine()
    latest_scores = {
        "ENG-001": {"mastery_score": 0.34, "confidence": 0.9},
        "ENG-002": {"mastery_score": 0.49, "confidence": 0.85},
        "ENG-005": {"mastery_score": 0.55, "confidence": 0.9},
        "ENG-006": {"mastery_score": 0.62, "confidence": 0.8},
        "ENG-010": {"mastery_score": 0.52, "confidence": 0.88}
    }
    recent_scores_by_concept = {
        "ENG-001": [
            {"assessment_date": "2026-03-01", "mastery_score": 0.34, "confidence": 0.9},
            {"assessment_date": "2026-02-01", "mastery_score": 0.46, "confidence": 0.88},
        ],
        "ENG-002": [
            {"assessment_date": "2026-03-01", "mastery_score": 0.49, "confidence": 0.85},
            {"assessment_date": "2026-02-01", "mastery_score": 0.42, "confidence": 0.83},
        ],
    }
    result_a = engine.run(
        student_id="STU-001",
        student={"id": "STU-001", "full_name": "Student 001", "cohort": "10A"},
        target_concept={"id": "ENG-010", "subject_id": "OL-ENG", "name": "Extended writing", "description": ""},
        prerequisite_paths=sample_paths(),
        latest_scores=latest_scores,
        recent_scores_by_concept=recent_scores_by_concept,
        assessment_summary={"assessment_count": 4, "latest_assessment_date": "2026-03-01"},
        cohort_target_mastery=0.71,
    )
    result_b = engine.run(
        student_id="STU-001",
        student={"id": "STU-001", "full_name": "Student 001", "cohort": "10A"},
        target_concept={"id": "ENG-010", "subject_id": "OL-ENG", "name": "Extended writing", "description": ""},
        prerequisite_paths=sample_paths(),
        latest_scores=latest_scores,
        recent_scores_by_concept=recent_scores_by_concept,
        assessment_summary={"assessment_count": 4, "latest_assessment_date": "2026-03-01"},
        cohort_target_mastery=0.71,
    )
    assert result_a.root_cause_candidates[0].concept_id == "ENG-001"
    assert result_a.concept_trends[0].direction == "declining"
    assert result_a.readiness.status == "needs_immediate_support"
    assert result_a.model_dump() == result_b.model_dump()


def test_missing_data_degrades_gracefully() -> None:
    engine = DiagnosisEngine()
    result = engine.run(
        student_id="STU-404",
        student={"id": "STU-404", "full_name": "Student 404", "cohort": "10B"},
        target_concept={"id": "ENG-010", "subject_id": "OL-ENG", "name": "Extended writing", "description": ""},
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

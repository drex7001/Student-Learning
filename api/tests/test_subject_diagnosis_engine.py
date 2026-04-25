from __future__ import annotations

from app.services.subject_diagnosis import SubjectDiagnosisEngine


def sample_subject() -> dict:
    return {
        "id": "OL-MATH",
        "name": "Mathematics",
        "name_si": "ගණිතය",
        "description": "",
        "description_si": "",
        "default_concept_id": "MATH-004",
    }


def sample_student() -> dict:
    return {"id": "STU-001", "full_name": "Student 001", "cohort": "10A"}


def sample_concepts() -> list[dict]:
    return [
        {"id": "MATH-001", "subject_id": "OL-MATH", "name": "Number operations", "description": ""},
        {"id": "MATH-002", "subject_id": "OL-MATH", "name": "Algebraic notation", "description": ""},
        {"id": "MATH-003", "subject_id": "OL-MATH", "name": "Linear equations", "description": ""},
        {"id": "MATH-004", "subject_id": "OL-MATH", "name": "Applied problem solving", "description": ""},
    ]


def sample_edges() -> list[dict]:
    return [
        {"source_id": "MATH-001", "target_id": "MATH-002"},
        {"source_id": "MATH-002", "target_id": "MATH-003"},
        {"source_id": "MATH-003", "target_id": "MATH-004"},
    ]


def test_subject_map_scores_all_concepts_and_recommends_early_weakness() -> None:
    result = SubjectDiagnosisEngine().run(
        student=sample_student(),
        subject=sample_subject(),
        concepts=sample_concepts(),
        edges=sample_edges(),
        latest_scores={
            "MATH-001": {"mastery_score": 0.42, "confidence": 0.92},
            "MATH-002": {"mastery_score": 0.56, "confidence": 0.9},
            "MATH-003": {"mastery_score": 0.72, "confidence": 0.86},
            "MATH-004": {"mastery_score": 0.81, "confidence": 0.91},
        },
    )

    assert len(result.concepts) == 4
    assert len(result.edges) == 4 - 1
    assert result.summary.support_now == 2
    assert result.summary.watch == 1
    assert result.summary.ready == 1
    assert result.recommended_concept_id == "MATH-001"
    assert result.concepts[0].downstream_impact == 3


def test_missing_scores_are_marked_with_fallback_confidence() -> None:
    result = SubjectDiagnosisEngine().run(
        student=sample_student(),
        subject=sample_subject(),
        concepts=sample_concepts(),
        edges=sample_edges(),
        latest_scores={
            "MATH-001": {"mastery_score": 0.82, "confidence": 0.9},
            "MATH-002": {"mastery_score": 0.78, "confidence": 0.88},
        },
    )

    missing = {node.id: node for node in result.concepts if node.status == "missing_evidence"}
    assert set(missing) == {"MATH-003", "MATH-004"}
    assert missing["MATH-003"].mastery_score is None
    assert missing["MATH-003"].confidence == 0.35
    assert result.summary.missing_evidence == 2


def test_observed_weakness_is_recommended_before_missing_evidence() -> None:
    result = SubjectDiagnosisEngine().run(
        student=sample_student(),
        subject=sample_subject(),
        concepts=sample_concepts(),
        edges=sample_edges(),
        latest_scores={
            "MATH-001": {"mastery_score": 0.81, "confidence": 0.9},
            "MATH-002": {"mastery_score": 0.54, "confidence": 0.82},
        },
    )

    assert result.recommended_concept_id == "MATH-002"

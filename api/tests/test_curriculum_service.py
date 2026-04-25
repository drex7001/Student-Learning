from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.curriculum_service import CurriculumValidationError, validate_curriculum


ROOT = Path(__file__).resolve().parents[2]


def load_curriculum() -> dict:
    path = ROOT / "data" / "curriculum" / "ol_subject_curriculum.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_curriculum_scope_is_subject_aware() -> None:
    curriculum = load_curriculum()
    summary = validate_curriculum(curriculum)
    assert summary["subject_count"] == 4
    assert summary["concept_count"] == 40
    assert summary["edge_count"] > 40


def test_subjects_include_sri_lankan_ol_set() -> None:
    curriculum = load_curriculum()
    subject_ids = {subject["id"] for subject in curriculum["subjects"]}
    assert subject_ids == {"OL-MATH", "OL-SCI", "OL-ENG", "OL-ICT"}
    assert any(subject["name_si"] for subject in curriculum["subjects"])


def test_cycle_detection_rejects_invalid_curriculum() -> None:
    curriculum = load_curriculum()
    curriculum["edges"].append(["MATH-010", "MATH-001"])
    with pytest.raises(CurriculumValidationError):
        validate_curriculum(curriculum)


def test_cross_subject_edges_are_rejected() -> None:
    curriculum = load_curriculum()
    curriculum["edges"].append(["MATH-001", "SCI-001"])
    with pytest.raises(CurriculumValidationError):
        validate_curriculum(curriculum)

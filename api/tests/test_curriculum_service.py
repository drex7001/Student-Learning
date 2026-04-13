from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.curriculum_service import CurriculumValidationError, validate_curriculum


ROOT = Path(__file__).resolve().parents[2]


def load_curriculum() -> dict:
    path = ROOT / "data" / "curriculum" / "grade8_algebra_curriculum.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_curriculum_scope_is_within_locked_range() -> None:
    curriculum = load_curriculum()
    summary = validate_curriculum(curriculum)
    assert summary["concept_count"] == 24
    assert summary["edge_count"] > 20


def test_cycle_detection_rejects_invalid_curriculum() -> None:
    curriculum = load_curriculum()
    curriculum["edges"].append(["ALG-024", "ALG-001"])
    with pytest.raises(CurriculumValidationError):
        validate_curriculum(curriculum)

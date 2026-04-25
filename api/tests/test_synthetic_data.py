from __future__ import annotations

import json
from pathlib import Path

from app.services.synthetic_data import generate_synthetic_dataset


ROOT = Path(__file__).resolve().parents[2]


def load_curriculum() -> dict:
    path = ROOT / "data" / "curriculum" / "ol_subject_curriculum.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_synthetic_generation_is_deterministic() -> None:
    curriculum = load_curriculum()
    dataset_a = generate_synthetic_dataset(
        curriculum=curriculum,
        config_path=ROOT / "data" / "seeds" / "generator_config.json",
        seed_override=99,
        student_count_override=40,
    )
    dataset_b = generate_synthetic_dataset(
        curriculum=curriculum,
        config_path=ROOT / "data" / "seeds" / "generator_config.json",
        seed_override=99,
        student_count_override=40,
    )
    assert dataset_a.question_results[0].score_obtained == dataset_b.question_results[0].score_obtained
    assert dataset_a.concept_scores[-1].mastery_score == dataset_b.concept_scores[-1].mastery_score


def test_generated_concepts_match_curriculum() -> None:
    curriculum = load_curriculum()
    dataset = generate_synthetic_dataset(
        curriculum=curriculum,
        config_path=ROOT / "data" / "seeds" / "generator_config.json",
        student_count_override=20,
    )
    curriculum_ids = {concept["id"] for concept in curriculum["concepts"]}
    generated_ids = {score.concept_id for score in dataset.concept_scores}
    assert generated_ids.issubset(curriculum_ids)

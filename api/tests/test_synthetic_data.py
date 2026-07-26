from __future__ import annotations

import json
from pathlib import Path

from app.services.synthetic_data import StudentAcademicProfile, generate_synthetic_dataset

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "data" / "seeds" / "generator_config.json"


def load_curriculum() -> dict:
    path = ROOT / "data" / "curriculum" / "ol_subject_curriculum.json"
    return json.loads(path.read_text(encoding="utf-8"))


def make_profiles(count: int, penalty: float = 0.0) -> list[StudentAcademicProfile]:
    return [
        StudentAcademicProfile(student_id=f"STU-{index + 1:03d}", academic_penalty=penalty)
        for index in range(count)
    ]


def test_synthetic_generation_is_deterministic() -> None:
    curriculum = load_curriculum()
    dataset_a = generate_synthetic_dataset(
        curriculum=curriculum,
        config_path=CONFIG,
        profiles=make_profiles(40),
        seed_override=99,
    )
    dataset_b = generate_synthetic_dataset(
        curriculum=curriculum,
        config_path=CONFIG,
        profiles=make_profiles(40),
        seed_override=99,
    )
    assert (
        dataset_a.question_results[0].score_obtained
        == dataset_b.question_results[0].score_obtained
    )
    assert dataset_a.concept_scores[-1].mastery_score == dataset_b.concept_scores[-1].mastery_score


def test_generated_concepts_match_curriculum() -> None:
    curriculum = load_curriculum()
    dataset = generate_synthetic_dataset(
        curriculum=curriculum,
        config_path=CONFIG,
        profiles=make_profiles(20),
    )
    curriculum_ids = {concept["id"] for concept in curriculum["concepts"]}
    generated_ids = {score.concept_id for score in dataset.concept_scores}
    assert generated_ids.issubset(curriculum_ids)


def test_evidence_generated_for_seeded_students_only() -> None:
    """The generator no longer invents learners; it attaches evidence to the roster."""
    curriculum = load_curriculum()
    profiles = make_profiles(12)
    dataset = generate_synthetic_dataset(
        curriculum=curriculum, config_path=CONFIG, profiles=profiles
    )
    assert dataset.student_count == 12
    expected = {profile.student_id for profile in profiles}
    assert {row.student_id for row in dataset.assessments} == expected
    assert {row.student_id for row in dataset.concept_scores} == expected


def test_academic_penalty_lowers_mastery() -> None:
    """A learner's circumstances feed through to their concept scores, so the academic
    and wellbeing pictures describe the same child."""
    curriculum = load_curriculum()
    without = generate_synthetic_dataset(
        curriculum=curriculum,
        config_path=CONFIG,
        profiles=make_profiles(10, penalty=0.0),
        seed_override=7,
    )
    with_penalty = generate_synthetic_dataset(
        curriculum=curriculum,
        config_path=CONFIG,
        profiles=make_profiles(10, penalty=0.25),
        seed_override=7,
    )

    def mean_mastery(dataset) -> float:
        scores = [row.mastery_score for row in dataset.concept_scores]
        return sum(scores) / len(scores)

    assert mean_mastery(with_penalty) < mean_mastery(without)

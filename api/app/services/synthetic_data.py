from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from app.db import models
from app.services.scoring import calculate_confidence, calculate_mastery


@dataclass
class StudentAcademicProfile:
    """What the academic generator needs to know about an already-seeded learner.

    ``academic_penalty`` comes from the learner's wellbeing evidence
    (``school_seed._academic_penalty``), so a student who studies alone in an
    under-resourced school is the same student whose concept scores are weak.
    """

    student_id: str
    academic_penalty: float = 0.0


@dataclass
class SyntheticDataset:
    assessments: list[models.Assessment]
    questions: list[models.Question]
    question_results: list[models.QuestionResult]
    concept_scores: list[models.ConceptScore]
    seed: int
    student_count: int


def _load_generator_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _descendant_distance(root: str, target: str, edges: list[tuple[str, str]]) -> int | None:
    frontier = [(root, 0)]
    seen = {root}
    adjacency: dict[str, list[str]] = {}
    for source, destination in edges:
        adjacency.setdefault(source, []).append(destination)
    while frontier:
        node, distance = frontier.pop(0)
        if node == target:
            return distance
        for neighbor in adjacency.get(node, []):
            if neighbor not in seen:
                seen.add(neighbor)
                frontier.append((neighbor, distance + 1))
    return None


def generate_synthetic_dataset(
    *,
    curriculum: dict,
    config_path: Path,
    profiles: list[StudentAcademicProfile],
    seed_override: int | None = None,
) -> SyntheticDataset:
    """Generate assessment evidence for learners that already exist.

    Students are no longer invented here -- they come from the school roster seed, so
    this function only produces the academic evidence attached to them.
    """
    config = _load_generator_config(config_path)
    seed = seed_override if seed_override is not None else config["seed"]
    rng = random.Random(seed)

    concepts = curriculum["concepts"]
    edges = [tuple(edge) for edge in curriculum["edges"]]
    concept_ids = [concept["id"] for concept in concepts]

    questions = [
        models.Question(
            id=f"Q-{concept['id']}",
            concept_id=concept["id"],
            prompt=f"Assess {concept['name']}",
            score_max=10.0,
        )
        for concept in concepts
    ]

    assessments: list[models.Assessment] = []
    question_results: list[models.QuestionResult] = []
    concept_scores: list[models.ConceptScore] = []

    base_date = date(2026, 1, 20)
    weakness_profiles = config["weakness_profiles"]

    for index, profile in enumerate(profiles):
        student_id = profile.student_id
        weakness = weakness_profiles[index % len(weakness_profiles)]
        root_concepts = weakness["root_concepts"]
        range_low, range_high = weakness["mastery_range"]
        # Adverse circumstances depress mastery across the board, on top of the
        # prerequisite-shaped weakness pattern.
        penalty = profile.academic_penalty

        for attempt in range(config["assessment_attempts"]):
            assessment_id = f"ASM-{index + 1:03d}-{attempt + 1}"
            assessment_date = base_date + timedelta(days=attempt * 21)
            assessments.append(
                models.Assessment(
                    id=assessment_id,
                    student_id=student_id,
                    assessment_date=assessment_date,
                    attempt_number=attempt + 1,
                )
            )

            for concept_id in concept_ids:
                weakness_penalty = 0.0
                for root in root_concepts:
                    distance = _descendant_distance(root, concept_id, edges)
                    if distance is None:
                        continue
                    if distance == 0:
                        weakness_penalty = max(weakness_penalty, rng.uniform(0.35, 0.52))
                    else:
                        weakness_penalty = max(
                            weakness_penalty, max(0.0, 0.42 - (distance * 0.07))
                        )

                trend_boost = min(0.18, attempt * 0.035)
                random_noise = rng.uniform(-0.05, 0.05)
                base_mastery = (
                    rng.uniform(0.68, 0.9) - weakness_penalty + trend_boost + random_noise
                )
                if concept_id in root_concepts:
                    base_mastery = rng.uniform(range_low, range_high) + trend_boost + random_noise
                mastery = max(0.18, min(0.97, base_mastery - penalty))

                score_obtained = round(10.0 * mastery, 2)
                question_results.append(
                    models.QuestionResult(
                        id=f"RES-{assessment_id}-{concept_id}",
                        assessment_id=assessment_id,
                        question_id=f"Q-{concept_id}",
                        concept_id=concept_id,
                        score_obtained=score_obtained,
                        score_max=10.0,
                    )
                )
                concept_scores.append(
                    models.ConceptScore(
                        id=f"CS-{assessment_id}-{concept_id}",
                        student_id=student_id,
                        assessment_id=assessment_id,
                        concept_id=concept_id,
                        mastery_score=calculate_mastery(score_obtained, 10.0),
                        confidence=calculate_confidence(1, 1),
                        computed_at=datetime.combine(assessment_date, datetime.min.time()),
                    )
                )

    return SyntheticDataset(
        assessments=assessments,
        questions=questions,
        question_results=question_results,
        concept_scores=concept_scores,
        seed=seed,
        student_count=len(profiles),
    )

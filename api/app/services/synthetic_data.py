from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from app.db import models
from app.services.scoring import calculate_confidence, calculate_mastery


@dataclass
class SyntheticDataset:
    students: list[models.Student]
    assessments: list[models.Assessment]
    questions: list[models.Question]
    question_results: list[models.QuestionResult]
    concept_scores: list[models.ConceptScore]
    seed: int


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
    seed_override: int | None = None,
    student_count_override: int | None = None,
) -> SyntheticDataset:
    config = _load_generator_config(config_path)
    seed = seed_override if seed_override is not None else config["seed"]
    student_count = student_count_override if student_count_override is not None else config["student_count"]
    rng = random.Random(seed)

    concepts = curriculum["concepts"]
    edges = [tuple(edge) for edge in curriculum["edges"]]
    concept_ids = [concept["id"] for concept in concepts]
    cohorts = config["cohorts"]

    questions = [
        models.Question(
            id=f"Q-{concept['id']}",
            concept_id=concept["id"],
            prompt=f"Assess {concept['name']}",
            score_max=10.0,
        )
        for concept in concepts
    ]

    students: list[models.Student] = []
    assessments: list[models.Assessment] = []
    question_results: list[models.QuestionResult] = []
    concept_scores: list[models.ConceptScore] = []

    base_date = date(2026, 1, 20)
    profiles = config["weakness_profiles"]

    for index in range(student_count):
        student_id = f"STU-{index + 1:03d}"
        profile = profiles[index % len(profiles)]
        students.append(
            models.Student(
                id=student_id,
                full_name=f"Student {index + 1:03d}",
                cohort=cohorts[index % len(cohorts)],
            )
        )

        root_concepts = profile["root_concepts"]
        range_low, range_high = profile["mastery_range"]

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
                        weakness_penalty = max(weakness_penalty, max(0.0, 0.42 - (distance * 0.07)))

                trend_boost = min(0.18, attempt * 0.035)
                random_noise = rng.uniform(-0.05, 0.05)
                base_mastery = rng.uniform(0.68, 0.9) - weakness_penalty + trend_boost + random_noise
                if concept_id in root_concepts:
                    base_mastery = rng.uniform(range_low, range_high) + trend_boost + random_noise
                mastery = max(0.18, min(0.97, base_mastery))

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
        students=students,
        assessments=assessments,
        questions=questions,
        question_results=question_results,
        concept_scores=concept_scores,
        seed=seed,
    )

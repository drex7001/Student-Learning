from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.postgres import get_session
from app.repositories.graph_repository import GraphRepository
from app.repositories.postgres_repository import PostgresRepository
from app.schemas.internal import (
    GenerateSyntheticDataRequest,
    GenerateSyntheticDataResponse,
    ImportCurriculumResponse,
    TrainSupportModelResponse,
)
from app.services.curriculum_service import load_json, validate_curriculum
from app.services.student_support import StudentSupportEngine
from app.services.student_support_model import TrainingExample, synthetic_support_label, train_support_model
from app.services.synthetic_data import generate_synthetic_dataset


router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/import/curriculum", response_model=ImportCurriculumResponse)
def import_curriculum() -> ImportCurriculumResponse:
    curriculum = load_json(settings.curriculum_path)
    validate_curriculum(curriculum)
    repository = GraphRepository()
    try:
        summary = repository.import_curriculum(
            curriculum["subjects"],
            curriculum["concepts"],
            [tuple(edge) for edge in curriculum["edges"]],
        )
    finally:
        repository.close()
    return ImportCurriculumResponse(**summary, source=str(settings.curriculum_path))


@router.post("/generate/synthetic-data", response_model=GenerateSyntheticDataResponse)
def generate_synthetic_data(
    payload: GenerateSyntheticDataRequest,
    session: Session = Depends(get_session),
) -> GenerateSyntheticDataResponse:
    curriculum = load_json(settings.curriculum_path)
    dataset = generate_synthetic_dataset(
        curriculum=curriculum,
        config_path=settings.generator_config_path,
        seed_override=payload.seed,
        student_count_override=payload.student_count,
    )
    repository = PostgresRepository(session)
    summary = repository.replace_seed_data(
        students=dataset.students,
        assessments=dataset.assessments,
        questions=dataset.questions,
        question_results=dataset.question_results,
        concept_scores=dataset.concept_scores,
    )
    return GenerateSyntheticDataResponse(seed=dataset.seed, **summary)


@router.post("/train/support-model", response_model=TrainSupportModelResponse)
def train_support_model_endpoint(session: Session = Depends(get_session)) -> TrainSupportModelResponse:
    examples, subject_count = _collect_support_training_examples(session)
    try:
        summary = train_support_model(examples)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrainSupportModelResponse(subject_count=subject_count, **summary)


def _collect_support_training_examples(session: Session) -> tuple[list[TrainingExample], int]:
    postgres_repository = PostgresRepository(session)
    students = postgres_repository.list_students(limit=1000)
    engine = StudentSupportEngine()
    examples: list[TrainingExample] = []

    graph_repository = GraphRepository()
    try:
        subjects = graph_repository.list_subjects()
        for subject in subjects:
            concepts = graph_repository.list_concepts(subject["id"])
            if not concepts:
                continue
            edges = graph_repository.get_subject_edges(subject["id"])
            concept_ids = [concept["id"] for concept in concepts]
            cohort_mastery_cache: dict[tuple[str, str], float | None] = {}

            for student in students:
                latest_scores = postgres_repository.get_latest_scores_for_student(student["id"])
                if not latest_scores:
                    continue
                recent_scores_by_concept = postgres_repository.get_recent_scores_for_student(
                    student["id"],
                    concept_ids,
                    limit_per_concept=2,
                )
                cohort_mastery_by_concept: dict[str, float | None] = {}
                for concept_id in concept_ids:
                    cache_key = (student["cohort"], concept_id)
                    if cache_key not in cohort_mastery_cache:
                        cohort_mastery_cache[cache_key] = postgres_repository.get_latest_cohort_mastery(
                            student["cohort"],
                            concept_id,
                        )
                    cohort_mastery_by_concept[concept_id] = cohort_mastery_cache[cache_key]

                features = engine.build_features(
                    concepts=concepts,
                    edges=edges,
                    latest_scores=latest_scores,
                    recent_scores_by_concept=recent_scores_by_concept,
                    cohort_mastery_by_concept=cohort_mastery_by_concept,
                    assessment_summary=postgres_repository.get_student_assessment_summary(student["id"]),
                )
                examples.append(
                    TrainingExample(
                        student_id=student["id"],
                        subject_id=subject["id"],
                        features=features,
                        label=synthetic_support_label(features),
                    )
                )
    finally:
        graph_repository.close()

    return examples, len(subjects)

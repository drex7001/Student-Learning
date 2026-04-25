from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.postgres import get_session
from app.repositories.graph_repository import GraphRepository
from app.repositories.postgres_repository import PostgresRepository
from app.schemas.internal import (
    GenerateSyntheticDataRequest,
    GenerateSyntheticDataResponse,
    ImportCurriculumResponse,
)
from app.services.curriculum_service import load_json, validate_curriculum
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

from __future__ import annotations

from pydantic import BaseModel, Field


class ImportCurriculumResponse(BaseModel):
    subject_count: int
    concept_count: int
    edge_count: int
    source: str


class GenerateSyntheticDataRequest(BaseModel):
    seed: int | None = Field(default=None)
    student_count: int | None = Field(default=None, ge=30, le=1000)


class GenerateSyntheticDataResponse(BaseModel):
    seed: int
    student_count: int
    assessment_count: int
    concept_score_count: int


class TrainSupportModelResponse(BaseModel):
    model_version: str
    label_strategy: str
    subject_count: int
    training_examples: int
    label_counts: dict[str, int]
    accuracy: float
    f1_macro: float
    model_path: str
    metrics_path: str

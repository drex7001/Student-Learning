from __future__ import annotations

from pydantic import BaseModel, Field


class ImportCurriculumResponse(BaseModel):
    subject_count: int
    concept_count: int
    edge_count: int
    source: str


class ImportRiskModelResponse(BaseModel):
    model_variant: str
    model_fingerprint: str
    factor_count: int
    influence_count: int


class SeedSchoolDataRequest(BaseModel):
    seed: int | None = Field(default=None)
    students_per_class: int | None = Field(default=None, ge=5, le=45)


class DemoCredential(BaseModel):
    role: str
    username: str
    password: str
    display_name: str
    school: str
    role_title: str


class SeedSchoolDataResponse(BaseModel):
    seed: int
    school_count: int
    class_count: int
    teacher_count: int
    student_count: int
    user_count: int
    evidence_count: int
    demo_credentials: list[DemoCredential]


class GenerateSyntheticDataRequest(BaseModel):
    seed: int | None = Field(default=None)


class GenerateSyntheticDataResponse(BaseModel):
    seed: int
    student_count: int
    assessment_count: int
    concept_score_count: int


class DeriveEvidenceResponse(BaseModel):
    term_id: str
    derived_count: int
    variable: str


class ProjectGraphResponse(BaseModel):
    school_count: int
    class_count: int
    teacher_count: int
    student_count: int
    mastery_edge_count: int
    evidence_edge_count: int
    peer_edge_count: int

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.schemas.diagnosis import StudentSummary, SubjectNode

RiskBand = Literal["high_support", "watch", "stable"]
ImpactDirection = Literal["increases_risk", "reduces_risk"]


class SupportRiskFeatures(BaseModel):
    avg_mastery: float
    weak_concept_count: int
    borderline_concept_count: int
    strong_concept_count: int
    missing_evidence_count: int
    avg_confidence: float
    low_confidence_count: int
    mastery_decline_count: int
    cohort_gap_avg: float | None = None
    root_cause_count: int
    concept_count: int
    assessment_count: int
    recent_accuracy: float


class SupportRisk(BaseModel):
    score: float
    band: RiskBand
    confidence: float


class SupportRiskFactor(BaseModel):
    feature: str
    label: str
    value: float | int | str | None
    impact: float
    direction: ImpactDirection
    explanation: str


class StudentSupportEntry(BaseModel):
    student_id: str
    student_name: str
    cohort: str
    risk_score: float
    risk_band: RiskBand
    confidence: float
    top_reason: str | None = None
    recommended_action: str


class StudentSupportSummary(BaseModel):
    total_students: int
    high_support: int
    watch: int
    stable: int
    average_confidence: float


class StudentSupportListResponse(BaseModel):
    subject: SubjectNode
    summary: StudentSupportSummary
    students: list[StudentSupportEntry]


class StudentSupportProfileResponse(BaseModel):
    student: StudentSummary
    subject: SubjectNode
    risk: SupportRisk
    features: SupportRiskFeatures
    explanation_method: str
    explanation_summary: str
    factors: list[SupportRiskFactor]
    recommended_actions: list[str]

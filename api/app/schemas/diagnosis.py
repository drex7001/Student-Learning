from __future__ import annotations

from pydantic import BaseModel


class ConceptNode(BaseModel):
    id: str
    name: str
    description: str | None = None


class StudentSummary(BaseModel):
    id: str
    full_name: str
    cohort: str


class PathSegment(BaseModel):
    path_index: int
    nodes: list[ConceptNode]


class WeakConcept(BaseModel):
    concept_id: str
    concept_name: str
    mastery_score: float
    confidence: float
    depth: int
    evidence: str


class RootCauseCandidate(BaseModel):
    concept_id: str
    concept_name: str
    severity_score: float
    rationale: str


class RemediationStep(BaseModel):
    order: int
    concept_id: str
    concept_name: str
    action: str


class TrendPoint(BaseModel):
    assessment_date: str
    mastery_score: float
    confidence: float


class ConceptTrend(BaseModel):
    concept_id: str
    concept_name: str
    direction: str
    delta: float
    latest_mastery: float
    prior_mastery: float | None = None
    points: list[TrendPoint]


class StudentReadiness(BaseModel):
    status: str
    readiness_score: float
    target_mastery: float
    cohort_mastery: float | None = None
    cohort_gap: float | None = None
    latest_assessment_date: str | None = None
    assessments_considered: int = 0


class DiagnosisResponse(BaseModel):
    student_id: str
    student: StudentSummary
    target_concept: ConceptNode
    readiness: StudentReadiness
    prerequisite_paths: list[PathSegment]
    weak_concepts: list[WeakConcept]
    concept_trends: list[ConceptTrend]
    root_cause_candidates: list[RootCauseCandidate]
    remediation_order: list[RemediationStep]
    explanation: str


class PrerequisiteResponse(BaseModel):
    concept: ConceptNode
    prerequisite_paths: list[PathSegment]
    downstream_concepts: list[ConceptNode]


class SelectorOptionsResponse(BaseModel):
    students: list[StudentSummary]
    concepts: list[ConceptNode]


class SupportQueueEntry(BaseModel):
    student_id: str
    student_name: str
    cohort: str
    readiness_status: str
    readiness_score: float
    target_mastery: float
    cohort_gap: float | None = None
    latest_assessment_date: str | None = None
    top_root_cause: str | None = None


class SupportQueueSummary(BaseModel):
    total_students: int
    support_now: int
    watch_list: int
    ready_to_progress: int


class SupportQueueResponse(BaseModel):
    concept: ConceptNode
    summary: SupportQueueSummary
    students: list[SupportQueueEntry]

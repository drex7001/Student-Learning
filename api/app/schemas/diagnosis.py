from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ConceptNode(BaseModel):
    id: str
    subject_id: str | None = None
    name: str
    name_si: str | None = None
    description: str | None = None
    description_si: str | None = None


class ConceptSupportEdge(BaseModel):
    source_id: str
    target_id: str


class ConceptSupportNode(BaseModel):
    id: str
    subject_id: str
    name: str
    name_si: str | None = None
    description: str | None = None
    description_si: str | None = None
    mastery_score: float | None = None
    confidence: float
    status: str
    priority_score: float
    depth: int
    downstream_impact: int
    evidence: str


class SubjectSupportSummary(BaseModel):
    total_concepts: int
    support_now: int
    watch: int
    ready: int
    missing_evidence: int


class SubjectNode(BaseModel):
    id: str
    name: str
    name_si: str | None = None
    description: str | None = None
    description_si: str | None = None
    default_concept_id: str


class StudentSummary(BaseModel):
    # Tolerates the richer student dict from PostgresRepository without every caller
    # having to strip it down.
    model_config = ConfigDict(extra="ignore")

    id: str
    full_name: str
    full_name_si: str | None = None
    cohort: str
    school_id: str | None = None
    class_id: str | None = None
    grade: int | None = None
    medium: str | None = None


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


class SubjectDiagnosisMapResponse(BaseModel):
    student: StudentSummary
    subject: SubjectNode
    concepts: list[ConceptSupportNode]
    edges: list[ConceptSupportEdge]
    summary: SubjectSupportSummary
    recommended_concept_id: str | None = None
    explanation: str


class PrerequisiteResponse(BaseModel):
    concept: ConceptNode
    prerequisite_paths: list[PathSegment]
    downstream_concepts: list[ConceptNode]


class SelectorOptionsResponse(BaseModel):
    students: list[StudentSummary]
    concepts: list[ConceptNode]
    subjects: list[SubjectNode] = []


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

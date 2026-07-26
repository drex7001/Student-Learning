"""Response models for the disengagement risk screen.

``ModelProvenance`` is required on every response that carries a number, not optional.
The engine attaches provenance, caveat, fingerprint and interpretation to each result
precisely so a downstream UI cannot detach the warning from the figure -- keeping them
required here preserves that guarantee through the API boundary.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelProvenance(BaseModel):
    model_variant: str
    model_fingerprint: str
    #: "observational_conditional" or "interventional_do" -- never conflate the two.
    interpretation: str
    provenance: str
    caveat: str
    computed_at: str


class RiskFactorState(BaseModel):
    value: str
    label: str
    label_si: str | None = None
    concern: bool


class RiskFactorNode(BaseModel):
    # `register` shadows a BaseModel attribute; the alias keeps the wire name while
    # the field is addressed as `is_register` in Python.
    model_config = ConfigDict(populate_by_name=True)

    id: str
    label: str
    label_si: str | None = None
    group: str
    group_si: str | None = None
    states: list[RiskFactorState]
    modifiable: bool
    protected: bool
    is_register: bool = Field(default=False, alias="register", serialization_alias="register")
    action: dict | None = None
    why_not_actionable: str | None = None


class RiskModelEdge(BaseModel):
    source: str
    target: str
    evidence_level: str | None = None
    mechanism: str | None = None


class RiskModelResponse(BaseModel):
    target: str
    target_states: list[str]
    factors: list[RiskFactorNode]
    edges: list[RiskModelEdge]
    register_fields: list[str]
    guardrail_message: str
    prior_p_high: float
    watch_threshold: float
    attention_threshold: float
    provenance: ModelProvenance


class PosteriorBar(BaseModel):
    state: str
    label: str
    label_si: str | None = None
    probability: float


class RiskContribution(BaseModel):
    variable: str
    label: str
    label_si: str | None = None
    group: str
    state: str | None = None
    state_label: str | None = None
    state_label_si: str | None = None
    delta: float
    #: True when the number came from a do() intervention rather than conditioning.
    causal: bool


class RiskActionCandidate(BaseModel):
    variable: str
    label: str
    label_si: str | None = None
    action: str
    action_si: str | None = None
    owner: str
    detail: str | None = None
    caveat: str | None = None
    target_state: str
    delta: float


class EvidenceItem(BaseModel):
    variable: str
    label: str
    label_si: str | None = None
    group: str
    state: str | None = None
    state_label: str | None = None
    state_label_si: str | None = None
    concern: bool = False
    source: str | None = None
    recorded_at: str | None = None
    modifiable: bool = False
    protected: bool = False


class CircumstanceGap(BaseModel):
    register_p_high: float
    circumstance_p_high: float
    gap: float
    ahead: bool


class StudentRiskSummary(BaseModel):
    student_id: str
    student_name: str
    student_name_si: str | None = None
    cohort: str
    class_id: str | None = None
    school_id: str | None = None
    p_high: float
    band: str
    alert_tier: str
    gap: float
    circumstances_ahead: bool
    top_driver: str | None = None
    recorded_count: int
    unrecorded_count: int


class RiskCaseloadSummary(BaseModel):
    total_students: int
    needs_attention: int
    watch: int
    not_marked: int
    circumstances_ahead: int
    threshold: float
    flagged_at_threshold: int
    flagged_share: float


class RiskCaseloadResponse(BaseModel):
    summary: RiskCaseloadSummary
    students: list[StudentRiskSummary]
    provenance: ModelProvenance
    basis: str


class RiskProfileResponse(BaseModel):
    student: StudentRiskSummary
    posterior: list[PosteriorBar]
    basis: str
    gap_detail: CircumstanceGap
    drivers: list[RiskContribution]
    actions: list[RiskActionCandidate]
    worth_asking: list[RiskContribution]
    evidence: list[EvidenceItem]
    attendance: list[dict]
    locked_factors: list[RiskFactorNode]
    provenance: ModelProvenance


class WhatIfRequest(BaseModel):
    evidence: dict[str, str] | None = Field(default=None)
    intervention: dict[str, str] | None = Field(default=None)


class WhatIfResponse(BaseModel):
    posterior: list[PosteriorBar]
    p_high: float
    band: str
    alert_tier: str
    evidence_used: dict[str, str]
    intervention_used: dict[str, str] | None = None
    provenance: ModelProvenance


class PlanRequest(BaseModel):
    variables: list[str]


class PlanResponse(BaseModel):
    variables: list[str]
    baseline_p_high: float
    planned_p_high: float
    joint_delta: float
    sum_of_parts: float
    note: str
    provenance: ModelProvenance


class RoutePath(BaseModel):
    nodes: list[str]
    labels: list[str]


class RoutesResponse(BaseModel):
    variable: str
    label: str
    paths: list[RoutePath]
    note: str


class EvidenceUpdateItem(BaseModel):
    variable: str
    #: ``null`` clears the record -- "not recorded" is a real answer, not a gap to fill.
    state: str | None = None
    note: str | None = None


class EvidenceUpdateRequest(BaseModel):
    updates: list[EvidenceUpdateItem]


class FactorCohortMember(BaseModel):
    student_id: str
    student_name: str
    cohort: str
    class_id: str | None = None


class FactorCohortResponse(BaseModel):
    variable: str
    label: str
    state: str
    state_label: str
    school_id: str | None
    total_recorded: int
    affected: int
    share: float
    interpretation: str
    students: list[FactorCohortMember]


class ScreeningCell(BaseModel):
    current_attendance: str
    school_engagement: str
    grade_band: str
    p_high: float
    band: str


class ScreeningMatrixResponse(BaseModel):
    cells: list[ScreeningCell]
    note: str
    provenance: ModelProvenance

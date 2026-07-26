/**
 * API response types.
 *
 * One definition each, mirroring the Pydantic schemas in `api/app/schemas`. These
 * were previously re-declared inside every component and had drifted apart.
 */

export type Role = "student" | "teacher" | "counsellor" | "admin";
export type RiskBand = "needs_attention" | "watch" | "not_marked";
export type AlertTier = "High" | "Moderate" | "Low";
export type SupportStatus = "support_now" | "watch" | "ready" | "missing_evidence";
export type ReadinessStatus = "needs_immediate_support" | "watch" | "ready_to_progress";
export type Locale = "en" | "si";

export type CurrentUser = {
  id: string;
  username: string;
  role: Role;
  display_name: string;
  display_name_si: string | null;
  locale: Locale;
  school_id: string | null;
  school_name: string | null;
  student_id: string | null;
  teacher_id: string | null;
  role_title: string | null;
  home_path: string;
};

/** Required on every response that carries a number. The caveat travels with the figure. */
export type ModelProvenance = {
  model_variant: string;
  model_fingerprint: string;
  interpretation: "observational_conditional" | "interventional_do";
  provenance: string;
  caveat: string;
  computed_at: string;
};

export type SubjectNode = {
  id: string;
  name: string;
  name_si?: string | null;
  description?: string | null;
  description_si?: string | null;
  default_concept_id?: string | null;
};

export type ConceptNode = {
  id: string;
  subject_id: string;
  name: string;
  name_si?: string | null;
  description?: string | null;
  description_si?: string | null;
};

export type StudentSummary = {
  id: string;
  full_name: string;
  full_name_si?: string | null;
  cohort: string;
  school_id?: string | null;
  class_id?: string | null;
  grade?: number | null;
  medium?: string | null;
};

// -- risk ---------------------------------------------------------------

export type RiskFactorState = {
  value: string;
  label: string;
  label_si: string | null;
  concern: boolean;
};

export type RiskFactorNode = {
  id: string;
  label: string;
  label_si: string | null;
  group: string;
  group_si: string | null;
  states: RiskFactorState[];
  modifiable: boolean;
  protected: boolean;
  register: boolean;
  action: RiskAction | null;
  why_not_actionable: string | null;
};

export type RiskAction = {
  action: string;
  action_si?: string | null;
  owner: string;
  target: string;
  detail?: string;
  caveat?: string;
};

export type RiskModelResponse = {
  target: string;
  target_states: string[];
  factors: RiskFactorNode[];
  edges: { source: string; target: string; evidence_level: string | null }[];
  register_fields: string[];
  guardrail_message: string;
  prior_p_high: number;
  watch_threshold: number;
  attention_threshold: number;
  provenance: ModelProvenance;
};

export type PosteriorBar = {
  state: string;
  label: string;
  label_si: string | null;
  probability: number;
};

export type RiskContribution = {
  variable: string;
  label: string;
  label_si: string | null;
  group: string;
  state: string | null;
  state_label: string | null;
  state_label_si: string | null;
  delta: number;
  causal: boolean;
};

export type RiskActionCandidate = {
  variable: string;
  label: string;
  label_si: string | null;
  action: string;
  action_si: string | null;
  owner: string;
  detail: string | null;
  caveat: string | null;
  target_state: string;
  delta: number;
};

export type EvidenceItem = {
  variable: string;
  label: string;
  label_si: string | null;
  group: string;
  state: string | null;
  state_label: string | null;
  state_label_si: string | null;
  concern: boolean;
  source: string | null;
  recorded_at: string | null;
  modifiable: boolean;
  protected: boolean;
};

export type CircumstanceGap = {
  register_p_high: number;
  circumstance_p_high: number;
  gap: number;
  ahead: boolean;
};

export type StudentRiskSummary = {
  student_id: string;
  student_name: string;
  student_name_si: string | null;
  cohort: string;
  class_id: string | null;
  school_id: string | null;
  p_high: number;
  band: RiskBand;
  alert_tier: AlertTier;
  gap: number;
  circumstances_ahead: boolean;
  top_driver: string | null;
  recorded_count: number;
  unrecorded_count: number;
};

export type RiskCaseloadResponse = {
  summary: {
    total_students: number;
    needs_attention: number;
    watch: number;
    not_marked: number;
    circumstances_ahead: number;
    threshold: number;
    flagged_at_threshold: number;
    flagged_share: number;
  };
  students: StudentRiskSummary[];
  provenance: ModelProvenance;
  basis: string;
};

export type AttendanceRow = {
  term_id: string;
  term_label: string;
  days_present: number;
  days_total: number;
  rate: number;
  max_consecutive_absences: number;
};

export type RiskProfileResponse = {
  student: StudentRiskSummary;
  posterior: PosteriorBar[];
  basis: string;
  gap_detail: CircumstanceGap;
  drivers: RiskContribution[];
  actions: RiskActionCandidate[];
  worth_asking: RiskContribution[];
  evidence: EvidenceItem[];
  attendance: AttendanceRow[];
  locked_factors: RiskFactorNode[];
  provenance: ModelProvenance;
};

export type WhatIfResponse = {
  posterior: PosteriorBar[];
  p_high: number;
  band: RiskBand;
  alert_tier: AlertTier;
  evidence_used: Record<string, string>;
  intervention_used: Record<string, string> | null;
  provenance: ModelProvenance;
};

export type PlanResponse = {
  variables: string[];
  baseline_p_high: number;
  planned_p_high: number;
  joint_delta: number;
  sum_of_parts: number;
  note: string;
  provenance: ModelProvenance;
};

export type ScreeningMatrixResponse = {
  cells: {
    current_attendance: string;
    school_engagement: string;
    grade_band: string;
    p_high: number;
    band: RiskBand;
  }[];
  note: string;
  provenance: ModelProvenance;
};

export type FactorCohortResponse = {
  variable: string;
  label: string;
  state: string;
  state_label: string;
  school_id: string | null;
  total_recorded: number;
  affected: number;
  share: number;
  interpretation: string;
  students: { student_id: string; student_name: string; cohort: string; class_id: string | null }[];
};

// -- graph --------------------------------------------------------------

export type CausalPathsResponse = {
  variable: string;
  label: string;
  target: string;
  path_count: number;
  paths: {
    nodes: { id: string; label: string; label_si: string | null; modifiable: boolean; protected: boolean }[];
    steps: { evidence: string | null; mechanism: string | null }[];
    length: number;
  }[];
  note: string;
};

export type SharedFactorsResponse = {
  school_id: string | null;
  class_id: string | null;
  population: number;
  factors: {
    variable: string;
    label: string;
    label_si: string | null;
    grouping: string;
    modifiable: boolean;
    state_label: string;
    affected: number;
    share: number;
    school_level: boolean;
  }[];
  note: string;
};

export type PeerNetworkResponse = {
  nodes: { id: string; name: string; risk_band: RiskBand | null; p_high: number | null; ties: number }[];
  edges: { source: string; target: string }[];
  summary: { class_id: string; students: number; average_ties: number; few_ties: number };
  note: string;
};

export type NeighbourhoodResponse = {
  student: { id: string; name: string; name_si: string | null; cohort: string; grade: number; p_high: number | null; risk_band: RiskBand | null };
  class: { id: string; label: string; grade: number; medium: string } | null;
  school: { id: string; name: string; sector: string; district: string } | null;
  teachers: { id: string; name: string; role_title: string }[];
  weak_concepts: { id: string; name: string; name_si: string | null; subject_id: string; score: number; band: string }[];
  concern_factors: { id: string; label: string; label_si: string | null; group: string; modifiable: boolean; state: string; state_label: string }[];
  peers: { id: string; name: string; risk_band: RiskBand | null }[];
  root_causes: { concept_id: string; concept_name: string; subject_id: string; score: number; root_concept: { id: string; name: string }; depth: number }[];
};

// -- learning / diagnosis (existing surfaces) ---------------------------

export type SelectorOptionsResponse = {
  subjects: SubjectNode[];
  concepts: ConceptNode[];
  students: StudentSummary[];
};

export type ConceptSupportNode = {
  id: string;
  subject_id: string;
  name: string;
  name_si?: string | null;
  description?: string | null;
  description_si?: string | null;
  mastery_score: number | null;
  confidence: number;
  status: SupportStatus;
  priority_score: number;
  depth: number;
  downstream_impact: number;
  evidence: string;
};

export type ConceptSupportEdge = { source_id: string; target_id: string };

export type SubjectDiagnosisMapResponse = {
  student: StudentSummary;
  subject: SubjectNode;
  concepts: ConceptSupportNode[];
  edges: ConceptSupportEdge[];
  summary: Record<string, number>;
  recommended_concept_id: string | null;
  explanation: string;
};

export type LessonCard = {
  concept_id: string;
  name: string;
  name_si?: string | null;
  status: SupportStatus;
  mastery_score: number | null;
  why_it_matters: string;
  study_tips: string[];
  question_count: number;
};

export type LearningProfileResponse = {
  student: StudentSummary;
  subject: SubjectNode;
  summary: Record<string, number>;
  lesson_cards: LessonCard[];
  recommended_quiz: {
    concept_ids: string[];
    /** How many questions exist — for display. */
    question_count: number;
    /** How many to ask, already within the endpoint's allowed range — send this. */
    recommended_length: number;
  };
  explanation: string;
};

export type QuizQuestion = {
  /** The question's own id. Named `id` by the API, not `question_id`. */
  id: string;
  concept_id: string;
  concept_name: string;
  prompt: string;
  prompt_si?: string | null;
  options: string[];
  options_si?: string[] | null;
  difficulty: number;
};

export type QuizAttemptResponse = {
  attempt_id: string;
  student_id: string;
  subject_id: string;
  concept_ids: string[];
  status: string;
  questions: QuizQuestion[];
};

export type QuizSubmitResponse = {
  attempt_id: string;
  status: string;
  score_obtained: number;
  score_max: number;
  /** A fraction in 0..1 despite the name — pass straight to `percent()`. */
  percentage: number;
  results: {
    question_id: string;
    concept_id: string;
    prompt: string;
    prompt_si?: string | null;
    is_correct: boolean;
    correct_option_index: number;
    selected_option_index: number | null;
    score_obtained: number;
    score_max: number;
    explanation: string;
    explanation_si?: string | null;
  }[];
  updated_concepts: {
    concept_id: string;
    mastery_score: number;
    confidence: number;
  }[];
};

"use client";

import Link from "next/link";
import {
  startTransition,
  useDeferredValue,
  useEffect,
  useEffectEvent,
  useState,
  type FormEvent,
} from "react";
import {
  SubjectSupportCanvas,
  type ConceptSupportEdge,
  type ConceptSupportNode,
} from "@/components/subject-support-canvas";

type ConceptNode = {
  id: string;
  subject_id?: string | null;
  name: string;
  name_si?: string | null;
  description?: string | null;
  description_si?: string | null;
};

type SubjectNode = {
  id: string;
  name: string;
  name_si?: string | null;
  description?: string | null;
  description_si?: string | null;
  default_concept_id: string;
};

type StudentSummary = {
  id: string;
  full_name: string;
  cohort: string;
};

type StudentReadiness = {
  status: "needs_immediate_support" | "watch" | "ready_to_progress";
  readiness_score: number;
  target_mastery: number;
  cohort_mastery?: number | null;
  cohort_gap?: number | null;
  latest_assessment_date?: string | null;
  assessments_considered: number;
};

type RootCauseCandidate = {
  concept_id: string;
  concept_name: string;
  severity_score: number;
  rationale: string;
};

type WeakConcept = {
  concept_id: string;
  concept_name: string;
  mastery_score: number;
  confidence: number;
  depth: number;
  evidence: string;
};

type RemediationStep = {
  order: number;
  concept_id: string;
  concept_name: string;
  action: string;
};

type TrendPoint = {
  assessment_date: string;
  mastery_score: number;
  confidence: number;
};

type ConceptTrend = {
  concept_id: string;
  concept_name: string;
  direction: "improving" | "declining" | "stable" | "limited_history";
  delta: number;
  latest_mastery: number;
  prior_mastery?: number | null;
  points: TrendPoint[];
};

type PathSegment = {
  path_index: number;
  nodes: ConceptNode[];
};

type DiagnosisResponse = {
  student_id: string;
  student: StudentSummary;
  target_concept: ConceptNode;
  readiness: StudentReadiness;
  prerequisite_paths: PathSegment[];
  weak_concepts: WeakConcept[];
  concept_trends: ConceptTrend[];
  root_cause_candidates: RootCauseCandidate[];
  remediation_order: RemediationStep[];
  explanation: string;
};

type SelectorOptionsResponse = {
  students: StudentSummary[];
  subjects: SubjectNode[];
  concepts: ConceptNode[];
};

type SubjectDiagnosisMapResponse = {
  student: StudentSummary;
  subject: SubjectNode;
  concepts: ConceptSupportNode[];
  edges: ConceptSupportEdge[];
  summary: {
    total_concepts: number;
    support_now: number;
    watch: number;
    ready: number;
    missing_evidence: number;
  };
  recommended_concept_id?: string | null;
  explanation: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const DEFAULT_SUBJECT_ID = "OL-MATH";

function displayName(item: { name: string; name_si?: string | null }) {
  return item.name_si ? `${item.name} / ${item.name_si}` : item.name;
}

function formatReadinessStatus(status: StudentReadiness["status"]): string {
  if (status === "needs_immediate_support") {
    return "Needs immediate support";
  }
  if (status === "ready_to_progress") {
    return "Ready to progress";
  }
  return "Watch closely";
}

function readinessToneClasses(status: StudentReadiness["status"]): string {
  if (status === "needs_immediate_support") {
    return "border-[rgba(217,97,61,0.22)] bg-[rgba(217,97,61,0.12)] text-accent";
  }
  if (status === "ready_to_progress") {
    return "border-[rgba(27,127,138,0.2)] bg-[rgba(27,127,138,0.1)] text-teal";
  }
  return "border-[rgba(225,176,75,0.3)] bg-[rgba(225,176,75,0.14)] text-[#8b640c]";
}

function formatTrendDirection(direction: ConceptTrend["direction"]): string {
  if (direction === "limited_history") {
    return "Limited history";
  }
  return direction.charAt(0).toUpperCase() + direction.slice(1);
}

function buildMiniTrendPath(points: TrendPoint[]): string {
  if (!points.length) {
    return "";
  }
  const ordered = [...points].reverse();
  const max = Math.max(...ordered.map((point) => point.mastery_score), 1);
  const min = Math.min(...ordered.map((point) => point.mastery_score), 0);
  const range = Math.max(max - min, 0.12);
  return ordered
    .map((point, index) => {
      const x = ordered.length === 1 ? 50 : (index / (ordered.length - 1)) * 100;
      const y = 100 - ((point.mastery_score - min) / range) * 100;
      return `${x},${y}`;
    })
    .join(" ");
}

function selectedSupportNode(
  map: SubjectDiagnosisMapResponse | null,
  selectedConceptId: string | null,
) {
  if (!map || !selectedConceptId) {
    return null;
  }
  return map.concepts.find((concept) => concept.id === selectedConceptId) ?? null;
}

export function DiagnosisWorkspace({
  initialSubjectId = DEFAULT_SUBJECT_ID,
  initialStudentId = "STU-001",
  initialConceptId,
}: {
  initialSubjectId?: string;
  initialStudentId?: string;
  initialConceptId?: string;
}) {
  const [subjectId, setSubjectId] = useState(initialSubjectId);
  const [studentId, setStudentId] = useState(initialStudentId);
  const [selectedConceptId, setSelectedConceptId] = useState<string | null>(initialConceptId ?? null);
  const [students, setStudents] = useState<StudentSummary[]>([]);
  const [subjects, setSubjects] = useState<SubjectNode[]>([]);
  const [subjectMap, setSubjectMap] = useState<SubjectDiagnosisMapResponse | null>(null);
  const [diagnosis, setDiagnosis] = useState<DiagnosisResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [message, setMessage] = useState("Loading learner support map...");

  const stableSubjectMap = useDeferredValue(subjectMap);
  const stableDiagnosis = useDeferredValue(diagnosis);

  async function fetchOptions(nextSubjectId: string) {
    const response = await fetch(`${API_BASE_URL}/api/options?subject_id=${nextSubjectId}`);
    if (!response.ok) {
      throw new Error("Unable to load student and subject options.");
    }
    return (await response.json()) as SelectorOptionsResponse;
  }

  async function fetchSubjectMap(nextStudentId: string, nextSubjectId: string) {
    const response = await fetch(`${API_BASE_URL}/api/diagnosis/student/${nextStudentId}/subject/${nextSubjectId}/map`);
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? "Unable to load subject support map.");
    }
    return (await response.json()) as SubjectDiagnosisMapResponse;
  }

  async function fetchDiagnosis(nextStudentId: string, nextConceptId: string) {
    const response = await fetch(
      `${API_BASE_URL}/api/diagnosis/student/${nextStudentId}/concept/${nextConceptId}`,
    );
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? "Diagnosis request failed.");
    }
    return (await response.json()) as DiagnosisResponse;
  }

  async function loadWorkspace(
    nextSubjectId: string,
    nextStudentId: string,
    requestedConceptId?: string | null,
  ) {
    setStatus("loading");
    setMessage("Loading the learner's subject support map...");
    try {
      const optionsPayload = await fetchOptions(nextSubjectId);
      const resolvedSubject =
        optionsPayload.subjects.find((subject) => subject.id === nextSubjectId) ??
        optionsPayload.subjects[0];
      const resolvedStudentId =
        optionsPayload.students.find((student) => student.id === nextStudentId)?.id ??
        optionsPayload.students[0]?.id ??
        nextStudentId;
      const resolvedSubjectId = resolvedSubject?.id ?? nextSubjectId;

      setSubjects(optionsPayload.subjects);
      setStudents(optionsPayload.students);
      setSubjectId(resolvedSubjectId);
      setStudentId(resolvedStudentId);

      const mapPayload = await fetchSubjectMap(resolvedStudentId, resolvedSubjectId);
      setSubjectMap(mapPayload);

      const conceptId =
        mapPayload.concepts.find((concept) => concept.id === requestedConceptId)?.id ??
        mapPayload.recommended_concept_id ??
        mapPayload.concepts[0]?.id ??
        null;
      setSelectedConceptId(conceptId);

      if (conceptId) {
        const diagnosisPayload = await fetchDiagnosis(resolvedStudentId, conceptId);
        setDiagnosis(diagnosisPayload);
      } else {
        setDiagnosis(null);
      }

      setStatus("idle");
      setMessage("Support map updated from the latest stored assessment evidence.");
    } catch (error) {
      setSubjectMap(null);
      setDiagnosis(null);
      setSelectedConceptId(null);
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Unable to load diagnosis.");
    }
  }

  async function loadConceptDiagnosis(nextConceptId: string) {
    setSelectedConceptId(nextConceptId);
    setStatus("loading");
    setMessage("Opening concept details...");
    try {
      const diagnosisPayload = await fetchDiagnosis(studentId, nextConceptId);
      setDiagnosis(diagnosisPayload);
      setStatus("idle");
      setMessage("Concept details updated.");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Unable to load concept details.");
    }
  }

  const loadInitialWorkspace = useEffectEvent(() => {
    void loadWorkspace(subjectId, studentId, selectedConceptId);
  });

  useEffect(() => {
    startTransition(() => {
      loadInitialWorkspace();
    });
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    startTransition(() => {
      void loadWorkspace(subjectId, studentId, selectedConceptId);
    });
  }

  function handleSubjectChange(nextSubjectId: string) {
    setSubjectId(nextSubjectId);
    startTransition(() => {
      void loadWorkspace(nextSubjectId, studentId, null);
    });
  }

  function handleStudentChange(nextStudentId: string) {
    setStudentId(nextStudentId);
    startTransition(() => {
      void loadWorkspace(subjectId, nextStudentId, selectedConceptId);
    });
  }

  function handleSelectConcept(nextConceptId: string) {
    startTransition(() => {
      void loadConceptDiagnosis(nextConceptId);
    });
  }

  const currentMap = stableSubjectMap;
  const currentDiagnosis = stableDiagnosis;
  const selectedNode = selectedSupportNode(currentMap, selectedConceptId);
  const recommendedNode =
    currentMap?.concepts.find((concept) => concept.id === currentMap.recommended_concept_id) ?? null;
  const topRootCause = currentDiagnosis?.root_cause_candidates[0] ?? null;
  const primaryAction = currentDiagnosis?.remediation_order[0] ?? null;
  const selectedTrend =
    currentDiagnosis?.concept_trends.find((trend) => trend.concept_id === selectedConceptId) ??
    currentDiagnosis?.concept_trends[0] ??
    null;

  return (
    <div className="grid gap-6">
      <section className="rounded-[2rem] border border-line bg-white/86 p-4 shadow-[0_20px_80px_rgba(19,32,52,0.08)] md:p-5">
        <form className="grid gap-4 xl:grid-cols-[1fr_1fr_auto_1.1fr]" onSubmit={handleSubmit}>
          <label className="grid gap-2">
            <span className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Subject</span>
            <select
              className="rounded-2xl border border-line bg-surface-strong px-4 py-3 outline-none"
              value={subjectId}
              onChange={(event) => handleSubjectChange(event.target.value)}
            >
              {subjects.map((subject) => (
                <option key={subject.id} value={subject.id}>
                  {displayName(subject)}
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-2">
            <span className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Student</span>
            <select
              className="rounded-2xl border border-line bg-surface-strong px-4 py-3 outline-none"
              value={studentId}
              onChange={(event) => handleStudentChange(event.target.value)}
            >
              {students.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.full_name} · {student.cohort}
                </option>
              ))}
            </select>
          </label>

          <button
            className="rounded-2xl bg-foreground px-5 py-3 text-sm font-medium text-white transition-transform duration-200 hover:-translate-y-0.5 xl:self-end"
            type="submit"
          >
            Refresh map
          </button>

          <div className="rounded-[1.6rem] border border-line bg-[#fffaf1] px-4 py-4 xl:self-end">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Session</p>
            <p className="mt-2 text-sm leading-6 text-foreground">{message}</p>
            <span className="mt-3 inline-flex rounded-full bg-white px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-muted">
              {status === "loading" ? "Loading" : status === "error" ? "Attention needed" : "Ready"}
            </span>
          </div>
        </form>
      </section>

      <section className="grid gap-5 xl:grid-cols-4">
        <div className="rounded-[1.8rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Learner</p>
          <strong className="mt-2 block text-2xl text-foreground">
            {currentMap?.student.full_name ?? "Loading learner"}
          </strong>
          <p className="mt-2 text-sm text-muted">
            {currentMap ? `${currentMap.student.id} · ${currentMap.student.cohort}` : "Waiting for learner data"}
          </p>
        </div>
        <div className="rounded-[1.8rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Support now</p>
          <strong className="mt-2 block text-3xl text-accent">{currentMap?.summary.support_now ?? 0}</strong>
        </div>
        <div className="rounded-[1.8rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Watch</p>
          <strong className="mt-2 block text-3xl text-[#8b640c]">{currentMap?.summary.watch ?? 0}</strong>
        </div>
        <div className="rounded-[1.8rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Recommended start</p>
          <strong className="mt-2 block text-xl text-foreground">
            {recommendedNode ? displayName(recommendedNode) : "No support need"}
          </strong>
        </div>
      </section>

      {currentMap ? (
        <section className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(360px,0.45fr)]">
          <SubjectSupportCanvas
            nodes={currentMap.concepts}
            edges={currentMap.edges}
            selectedConceptId={selectedConceptId}
            recommendedConceptId={currentMap.recommended_concept_id ?? null}
            onSelectConcept={handleSelectConcept}
          />

          <aside className="rounded-[2rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Selected concept</p>
            <strong className="mt-2 block text-3xl tracking-tight text-foreground">
              {selectedNode ? displayName(selectedNode) : "Choose a concept"}
            </strong>
            {selectedNode ? (
              <div className="mt-4 grid gap-3">
                <div className={`rounded-[1.4rem] border px-4 py-4 ${readinessToneClasses(currentDiagnosis?.readiness.status ?? "watch")}`}>
                  <p className="font-mono text-[11px] uppercase tracking-[0.16em]">Readiness</p>
                  <strong className="mt-2 block text-2xl">
                    {currentDiagnosis?.readiness
                      ? formatReadinessStatus(currentDiagnosis.readiness.status)
                      : selectedNode.status.replaceAll("_", " ")}
                  </strong>
                </div>
                <div className="rounded-[1.4rem] border border-line bg-white p-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Observed signal</p>
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    <div>
                      <p className="text-xs text-muted">Mastery</p>
                      <strong>{selectedNode.mastery_score == null ? "N/A" : `${Math.round(selectedNode.mastery_score * 100)}%`}</strong>
                    </div>
                    <div>
                      <p className="text-xs text-muted">Confidence</p>
                      <strong>{Math.round(selectedNode.confidence * 100)}%</strong>
                    </div>
                    <div>
                      <p className="text-xs text-muted">Priority</p>
                      <strong>{selectedNode.priority_score.toFixed(2)}</strong>
                    </div>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-muted">{selectedNode.evidence}</p>
                </div>
              </div>
            ) : null}

            <div className="mt-5 rounded-[1.4rem] border border-line bg-white p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Teacher summary</p>
              <p className="mt-2 text-sm leading-7 text-muted">
                {currentDiagnosis?.explanation ?? currentMap.explanation}
              </p>
            </div>

            <div className="mt-5 grid gap-3">
              <div className="rounded-[1.4rem] border border-line bg-white p-4">
                <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Start here</p>
                <strong className="mt-2 block text-xl text-foreground">
                  {topRootCause?.concept_name ?? selectedNode?.name ?? "No bottleneck detected"}
                </strong>
                <p className="mt-2 text-sm leading-6 text-muted">
                  {primaryAction?.action ?? currentMap.explanation}
                </p>
              </div>
              <Link
                href={`/concepts?subject=${subjectId}&concept=${selectedConceptId ?? currentMap.recommended_concept_id ?? ""}`}
                className="inline-flex justify-center rounded-full bg-accent-soft px-4 py-3 text-sm text-accent"
              >
                Open concept map
              </Link>
            </div>
          </aside>
        </section>
      ) : (
        <section className="rounded-[2rem] border border-dashed border-line bg-surface p-8 text-sm text-muted">
          {status === "loading" ? "Loading subject support map..." : "No subject support map available."}
        </section>
      )}

      <section className="grid gap-5 xl:grid-cols-[1fr_1fr]">
        <article className="rounded-[2rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Teaching sequence</p>
          <div className="mt-4 grid gap-3">
            {currentDiagnosis?.remediation_order.length ? (
              currentDiagnosis.remediation_order.slice(0, 5).map((step) => (
                <button
                  key={step.concept_id}
                  type="button"
                  onClick={() => handleSelectConcept(step.concept_id)}
                  className="rounded-[1.4rem] border border-line bg-white p-4 text-left transition-colors hover:bg-[#f8f6f1]"
                >
                  <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-teal">Step {step.order}</p>
                  <strong className="mt-2 block text-lg text-foreground">{step.concept_name}</strong>
                  <p className="mt-2 text-sm leading-6 text-muted">{step.action}</p>
                </button>
              ))
            ) : (
              <div className="rounded-[1.4rem] border border-dashed border-line bg-white p-4 text-sm text-muted">
                No remediation sequence is needed for the selected concept.
              </div>
            )}
          </div>
        </article>

        <article className="rounded-[2rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Trend</p>
          {selectedTrend ? (
            <div className="mt-4 rounded-[1.4rem] border border-line bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <strong className="block text-xl text-foreground">{selectedTrend.concept_name}</strong>
                <span className="rounded-full bg-[#f8f6f1] px-3 py-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                  {formatTrendDirection(selectedTrend.direction)}
                </span>
              </div>
              <div className="mt-5 rounded-[1.4rem] bg-[linear-gradient(180deg,#f5f3ec,#eff5f3)] p-4">
                <svg className="h-24 w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                  <polyline
                    fill="none"
                    points={buildMiniTrendPath(selectedTrend.points)}
                    stroke="rgba(27,127,138,0.82)"
                    strokeWidth="4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <p className="mt-4 text-sm leading-6 text-muted">
                Latest {(selectedTrend.latest_mastery * 100).toFixed(0)}%
                {selectedTrend.prior_mastery == null
                  ? " with limited history."
                  : `, prior ${(selectedTrend.prior_mastery * 100).toFixed(0)}%, change ${
                      selectedTrend.delta > 0 ? "+" : ""
                    }${(selectedTrend.delta * 100).toFixed(0)} points.`}
              </p>
            </div>
          ) : (
            <div className="mt-4 rounded-[1.4rem] border border-dashed border-line bg-white p-4 text-sm text-muted">
              Trend signals appear when multiple assessment points exist for a flagged concept.
            </div>
          )}
        </article>
      </section>
    </div>
  );
}

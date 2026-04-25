"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import {
  startTransition,
  useDeferredValue,
  useEffect,
  useEffectEvent,
  useState,
  type FormEvent,
} from "react";

type ConceptNode = {
  id: string;
  subject_id?: string | null;
  name: string;
  name_si?: string | null;
  description?: string;
  description_si?: string | null;
};

type SubjectNode = {
  id: string;
  name: string;
  name_si?: string | null;
  description?: string | null;
  default_concept_id: string;
};

type StudentSummary = {
  id: string;
  full_name: string;
  cohort: string;
};

type WeakConcept = {
  concept_id: string;
  concept_name: string;
  mastery_score: number;
  confidence: number;
  depth: number;
  evidence: string;
};

type RootCauseCandidate = {
  concept_id: string;
  concept_name: string;
  severity_score: number;
  rationale: string;
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

type StudentReadiness = {
  status: "needs_immediate_support" | "watch" | "ready_to_progress";
  readiness_score: number;
  target_mastery: number;
  cohort_mastery?: number | null;
  cohort_gap?: number | null;
  latest_assessment_date?: string | null;
  assessments_considered: number;
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

type PrerequisiteResponse = {
  concept: ConceptNode;
  prerequisite_paths: PathSegment[];
  downstream_concepts: ConceptNode[];
};

type PositionedNode = {
  id: string;
  name: string;
  x: number;
  y: number;
  tone: "upstream" | "focus" | "downstream";
};

type Edge = {
  key: string;
  from: string;
  to: string;
  dashed?: boolean;
};

const StudentScene = dynamic(
  () => import("@/components/student-scene").then((mod) => mod.StudentScene),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full min-h-[460px] items-center justify-center rounded-[2rem] bg-[rgba(7,13,22,0.96)] text-sm text-white/70">
        Initializing student scene...
      </div>
    ),
  },
);

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
    return "border-[rgba(217,97,61,0.24)] bg-[rgba(217,97,61,0.12)] text-[#ffd5cb]";
  }
  if (status === "ready_to_progress") {
    return "border-[rgba(82,208,197,0.28)] bg-[rgba(27,127,138,0.18)] text-[#c5fff6]";
  }
  return "border-[rgba(225,176,75,0.24)] bg-[rgba(225,176,75,0.14)] text-[#fff0bd]";
}

function formatTrendDirection(direction: ConceptTrend["direction"]): string {
  if (direction === "limited_history") {
    return "Limited history";
  }
  return direction.charAt(0).toUpperCase() + direction.slice(1);
}

function trendToneClasses(direction: ConceptTrend["direction"]): string {
  if (direction === "declining") {
    return "border-[rgba(217,97,61,0.18)] bg-[rgba(217,97,61,0.08)] text-accent";
  }
  if (direction === "improving") {
    return "border-[rgba(27,127,138,0.18)] bg-[rgba(27,127,138,0.10)] text-teal";
  }
  if (direction === "limited_history") {
    return "border-[rgba(225,176,75,0.22)] bg-[rgba(225,176,75,0.12)] text-[#8b640c]";
  }
  return "border-[rgba(19,32,52,0.1)] bg-white/70 text-muted";
}

function distributeYPositions(count: number): number[] {
  if (count <= 0) {
    return [];
  }
  if (count === 1) {
    return [50];
  }
  const start = 16;
  const span = 68;
  return Array.from({ length: count }, (_, index) => start + (span / (count - 1)) * index);
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

function buildDependencyMap(drilldown: PrerequisiteResponse | null): {
  nodes: PositionedNode[];
  edges: Edge[];
} {
  if (!drilldown) {
    return { nodes: [], edges: [] };
  }

  const focus = drilldown.concept;
  const upstreamById = new Map<string, { node: ConceptNode; distance: number }>();
  const edges = new Map<string, Edge>();

  for (const path of drilldown.prerequisite_paths) {
    path.nodes.forEach((node, index) => {
      const distance = path.nodes.length - index - 1;
      if (distance > 0) {
        const current = upstreamById.get(node.id);
        if (!current || distance < current.distance) {
          upstreamById.set(node.id, { node, distance });
        }
      }
      if (index < path.nodes.length - 1) {
        const from = path.nodes[index].id;
        const to = path.nodes[index + 1].id;
        edges.set(`${from}->${to}`, { key: `${from}->${to}`, from, to });
      }
    });
  }

  const upstreamEntries = Array.from(upstreamById.values()).sort((left, right) => {
    if (left.distance !== right.distance) {
      return right.distance - left.distance;
    }
    return left.node.name.localeCompare(right.node.name);
  });
  const maxDistance = Math.max(1, ...upstreamEntries.map((entry) => entry.distance));
  const positionedNodes = new Map<string, PositionedNode>();
  const groups = new Map<number, ConceptNode[]>();

  for (const entry of upstreamEntries) {
    const group = groups.get(entry.distance) ?? [];
    group.push(entry.node);
    groups.set(entry.distance, group);
  }

  for (const [distance, nodes] of groups.entries()) {
    const ys = distributeYPositions(nodes.length);
    nodes.forEach((node, index) => {
      const x = maxDistance === 1 ? 24 : 10 + ((maxDistance - distance) / (maxDistance - 1)) * 34;
      positionedNodes.set(node.id, {
        id: node.id,
        name: node.name,
        x,
        y: ys[index],
        tone: "upstream",
      });
    });
  }

  positionedNodes.set(focus.id, {
    id: focus.id,
    name: focus.name,
    x: 58,
    y: 50,
    tone: "focus",
  });

  const downstream = drilldown.downstream_concepts.filter((node) => node.id !== focus.id).slice(0, 6);
  const downstreamRows = distributeYPositions(Math.min(3, Math.max(downstream.length, 1)));
  downstream.forEach((node, index) => {
    const columnIndex = index >= 3 ? 1 : 0;
    const rowIndex = index % 3;
    positionedNodes.set(node.id, {
      id: node.id,
      name: node.name,
      x: columnIndex === 0 ? 81 : 93,
      y: downstreamRows[rowIndex] ?? 50,
      tone: "downstream",
    });
    edges.set(`${focus.id}->${node.id}`, {
      key: `${focus.id}->${node.id}`,
      from: focus.id,
      to: node.id,
      dashed: true,
    });
  });

  return {
    nodes: Array.from(positionedNodes.values()),
    edges: Array.from(edges.values()).filter(
      (edge) => positionedNodes.has(edge.from) && positionedNodes.has(edge.to),
    ),
  };
}

function DependencyMap({ drilldown }: { drilldown: PrerequisiteResponse | null }) {
  const { nodes, edges } = buildDependencyMap(drilldown);
  const nodeById = new Map(nodes.map((node) => [node.id, node]));

  if (!drilldown) {
    return (
      <div className="rounded-[1.5rem] border border-dashed border-line p-5 text-sm text-muted">
        Choose a focus concept to inspect the prerequisite route.
      </div>
    );
  }

  return (
    <div className="rounded-[1.75rem] border border-line bg-[linear-gradient(180deg,#ffffff,rgba(244,246,245,0.84))] p-4 shadow-[0_16px_48px_rgba(19,32,52,0.07)]">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Concept route</p>
          <strong className="mt-2 block text-xl text-foreground">{displayName(drilldown.concept)}</strong>
        </div>
        <span className="rounded-full bg-accent-soft px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-accent">
          {drilldown.downstream_concepts.length} downstream links
        </span>
      </div>

      <div className="relative mt-4 h-[420px] overflow-hidden rounded-[1.5rem] bg-[radial-gradient(circle_at_top_left,rgba(27,127,138,0.16),transparent_34%),radial-gradient(circle_at_right,rgba(217,97,61,0.12),transparent_34%),linear-gradient(180deg,#132034,#101825)]">
        <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          {edges.map((edge) => {
            const from = nodeById.get(edge.from);
            const to = nodeById.get(edge.to);
            if (!from || !to) {
              return null;
            }
            return (
              <line
                key={edge.key}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke={edge.dashed ? "rgba(225,176,75,0.52)" : "rgba(255,255,255,0.18)"}
                strokeDasharray={edge.dashed ? "2.6 2" : undefined}
                strokeWidth={edge.dashed ? 0.44 : 0.38}
              />
            );
          })}
        </svg>

        {nodes.map((node) => {
          const toneClasses =
            node.tone === "focus"
              ? "border-[rgba(225,176,75,0.42)] bg-[rgba(225,176,75,0.18)] text-white"
              : node.tone === "downstream"
                ? "border-[rgba(27,127,138,0.22)] bg-[rgba(27,127,138,0.18)] text-white/92"
                : "border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.07)] text-white/86";

          return (
            <div
              key={node.id}
              className={`absolute w-[138px] -translate-x-1/2 -translate-y-1/2 rounded-2xl border px-3 py-3 ${toneClasses}`}
              style={{ left: `${node.x}%`, top: `${node.y}%` }}
            >
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/52">
                {node.id}
              </p>
              <strong className="mt-2 block text-sm leading-5">{node.name}</strong>
            </div>
          );
        })}
      </div>
    </div>
  );
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
  const [conceptId, setConceptId] = useState(initialConceptId ?? "");
  const [diagnosis, setDiagnosis] = useState<DiagnosisResponse | null>(null);
  const [focusDrilldown, setFocusDrilldown] = useState<PrerequisiteResponse | null>(null);
  const [selectedDrilldownConceptId, setSelectedDrilldownConceptId] = useState<string | null>(null);
  const [students, setStudents] = useState<StudentSummary[]>([]);
  const [subjects, setSubjects] = useState<SubjectNode[]>([]);
  const [concepts, setConcepts] = useState<ConceptNode[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [message, setMessage] = useState("Loading the diagnosis surface...");
  const [activePanel, setActivePanel] = useState<"overview" | "route" | "trend">("overview");

  const stableDiagnosis = useDeferredValue(diagnosis);
  const stableDrilldown = useDeferredValue(focusDrilldown);

  async function fetchOptions(nextSubjectId: string) {
    const response = await fetch(`${API_BASE_URL}/api/options?subject_id=${nextSubjectId}`);
    if (!response.ok) {
      throw new Error("Unable to load student and concept options.");
    }
    return (await response.json()) as SelectorOptionsResponse;
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

  async function fetchDrilldown(nextConceptId: string) {
    const response = await fetch(`${API_BASE_URL}/api/concepts/${nextConceptId}/prerequisites`);
    if (!response.ok) {
      throw new Error("Unable to load concept drill-down.");
    }
    return (await response.json()) as PrerequisiteResponse;
  }

  async function loadDrilldown(nextConceptId: string) {
    setSelectedDrilldownConceptId(nextConceptId);
    const drilldownPayload = await fetchDrilldown(nextConceptId);
    setFocusDrilldown(drilldownPayload);
  }

  async function loadOptionsAndDiagnosis(
    nextSubjectId: string,
    nextStudentId: string,
    nextConceptId?: string,
  ) {
    setStatus("loading");
    setMessage("Loading learner, subject, and concept evidence...");
    try {
      const optionsPayload = await fetchOptions(nextSubjectId);
      setStudents(optionsPayload.students);
      setSubjects(optionsPayload.subjects);
      setConcepts(optionsPayload.concepts);
      const selectedSubject =
        optionsPayload.subjects.find((subject) => subject.id === nextSubjectId) ??
        optionsPayload.subjects[0];

      const resolvedStudentId =
        optionsPayload.students.find((student) => student.id === nextStudentId)?.id ??
        optionsPayload.students[0]?.id ??
        nextStudentId;
      const resolvedConceptId =
        optionsPayload.concepts.find((concept) => concept.id === nextConceptId)?.id ??
        optionsPayload.concepts.find((concept) => concept.id === selectedSubject?.default_concept_id)?.id ??
        optionsPayload.concepts[0]?.id ??
        nextConceptId ??
        "";

      setSubjectId(selectedSubject?.id ?? nextSubjectId);
      setStudentId(resolvedStudentId);
      setConceptId(resolvedConceptId);

      const diagnosisPayload = await fetchDiagnosis(resolvedStudentId, resolvedConceptId);
      setDiagnosis(diagnosisPayload);

      const initialFocusConceptId =
        diagnosisPayload.root_cause_candidates[0]?.concept_id ??
        diagnosisPayload.weak_concepts[0]?.concept_id ??
        null;

      if (initialFocusConceptId) {
        await loadDrilldown(initialFocusConceptId);
      } else {
        setSelectedDrilldownConceptId(null);
        setFocusDrilldown(null);
      }

      setStatus("idle");
      setMessage("Diagnosis updated from the latest stored evidence.");
    } catch (error) {
      setDiagnosis(null);
      setFocusDrilldown(null);
      setSelectedDrilldownConceptId(null);
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Unable to load diagnosis.");
    }
  }

  async function loadDiagnosis(nextStudentId: string, nextConceptId: string) {
    setStatus("loading");
    setMessage("Updating the intervention recommendation...");
    try {
      const diagnosisPayload = await fetchDiagnosis(nextStudentId, nextConceptId);
      setDiagnosis(diagnosisPayload);

      const focusConceptId =
        diagnosisPayload.root_cause_candidates[0]?.concept_id ??
        diagnosisPayload.weak_concepts[0]?.concept_id ??
        null;

      if (focusConceptId) {
        await loadDrilldown(focusConceptId);
      } else {
        setSelectedDrilldownConceptId(null);
        setFocusDrilldown(null);
      }

      setStatus("idle");
      setMessage("Diagnosis updated.");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Unable to load diagnosis.");
    }
  }

  const loadInitialWorkspace = useEffectEvent(() => {
    void loadOptionsAndDiagnosis(subjectId, studentId, conceptId);
  });

  useEffect(() => {
    startTransition(() => {
      loadInitialWorkspace();
    });
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    startTransition(() => {
      void loadDiagnosis(studentId, conceptId);
    });
  }

  function handleInspectConcept(nextConceptId: string) {
    startTransition(() => {
      void loadDrilldown(nextConceptId)
        .then(() => {
          setMessage("Focused on the selected concept.");
        })
        .catch((error) => {
          setStatus("error");
          setMessage(error instanceof Error ? error.message : "Unable to inspect concept.");
        });
    });
  }

  const currentDiagnosis = stableDiagnosis;
  const currentDrilldown = stableDrilldown;
  const topRootCause = currentDiagnosis?.root_cause_candidates[0] ?? null;
  const teacherAlert = currentDiagnosis?.weak_concepts[0] ?? null;
  const selectedTrend =
    currentDiagnosis?.concept_trends.find((trend) => trend.concept_id === selectedDrilldownConceptId) ??
    currentDiagnosis?.concept_trends[0] ??
    null;
  const selectedWeakConcept =
    currentDiagnosis?.weak_concepts.find((concept) => concept.concept_id === selectedDrilldownConceptId) ??
    teacherAlert ??
    null;
  const primaryAction = currentDiagnosis?.remediation_order[0] ?? null;
  const focusCandidates = currentDiagnosis
    ? Array.from(
        new Map(
          [
            ...currentDiagnosis.root_cause_candidates.map((candidate) => ({
              concept_id: candidate.concept_id,
              concept_name: candidate.concept_name,
              meta: `severity ${candidate.severity_score.toFixed(2)}`,
            })),
            ...currentDiagnosis.weak_concepts.map((concept) => ({
              concept_id: concept.concept_id,
              concept_name: concept.concept_name,
              meta: `mastery ${concept.mastery_score.toFixed(2)}`,
            })),
          ].map((item) => [item.concept_id, item]),
        ).values(),
      ).slice(0, 6)
    : [];
  const explorerConceptId = selectedDrilldownConceptId ?? conceptId;

  return (
    <div className="grid gap-6">
      <section className="rounded-[2rem] border border-line bg-white/86 p-4 shadow-[0_20px_80px_rgba(19,32,52,0.08)] md:p-5">
        <form className="grid gap-4 xl:grid-cols-[1fr_1fr_1fr_auto_1fr]" onSubmit={handleSubmit}>
          <label className="grid gap-2">
            <span className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Subject</span>
            <select
              className="rounded-2xl border border-line bg-surface-strong px-4 py-3 outline-none"
              value={subjectId}
              onChange={(event) => {
                const nextSubjectId = event.target.value;
                setSubjectId(nextSubjectId);
                startTransition(() => {
                  void loadOptionsAndDiagnosis(nextSubjectId, studentId);
                });
              }}
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
              onChange={(event) => setStudentId(event.target.value)}
            >
              {students.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.full_name} · {student.cohort}
                </option>
              ))}
            </select>
          </label>

          <label className="grid gap-2">
            <span className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Target concept</span>
            <select
              className="rounded-2xl border border-line bg-surface-strong px-4 py-3 outline-none"
              value={conceptId}
              onChange={(event) => setConceptId(event.target.value)}
            >
              {concepts.map((concept) => (
                <option key={concept.id} value={concept.id}>
                  {displayName(concept)}
                </option>
              ))}
            </select>
          </label>

          <button
            className="rounded-2xl bg-foreground px-5 py-3 text-sm font-medium text-white transition-transform duration-200 hover:-translate-y-0.5 xl:self-end"
            type="submit"
          >
            Refresh diagnosis
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

      <section className="rounded-[2.6rem] border border-[#1f3149] bg-[radial-gradient(circle_at_top,rgba(82,208,197,0.18),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(225,176,75,0.18),transparent_30%),linear-gradient(180deg,#0f1b2a,#07121e)] p-4 shadow-[0_28px_120px_rgba(9,18,30,0.24)] md:p-5">
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-[1.5rem] border border-white/12 bg-white/8 px-4 py-4 backdrop-blur">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-white/54">Selected learner</p>
            <strong className="mt-2 block text-2xl text-white">
              {currentDiagnosis?.student.full_name ?? "Loading learner"}
            </strong>
            <p className="mt-2 text-sm text-white/70">
              {currentDiagnosis
                ? `${currentDiagnosis.student.id} · ${currentDiagnosis.student.cohort}`
                : "Waiting for learner data"}
            </p>
          </div>

          <div className="rounded-[1.5rem] border border-white/12 bg-white/8 px-4 py-4 backdrop-blur">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-white/54">Target concept</p>
            <strong className="mt-2 block text-2xl text-white">
              {currentDiagnosis ? displayName(currentDiagnosis.target_concept) : "Loading target"}
            </strong>
            <p className="mt-2 text-sm leading-6 text-white/70">
              {currentDiagnosis?.target_concept.description ?? "Waiting for concept detail"}
            </p>
          </div>

          <div className="rounded-[1.5rem] border border-white/12 bg-white/8 px-4 py-4 backdrop-blur">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-white/54">
                  Intervention outlook
                </p>
                <strong className="mt-2 block text-2xl text-white">
                  {currentDiagnosis?.readiness
                    ? formatReadinessStatus(currentDiagnosis.readiness.status)
                    : "Loading"}
                </strong>
              </div>
              {currentDiagnosis?.readiness ? (
                <span
                  className={`rounded-full border px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] ${readinessToneClasses(
                    currentDiagnosis.readiness.status,
                  )}`}
                >
                  {currentDiagnosis.readiness.status.replaceAll("_", " ")}
                </span>
              ) : null}
            </div>
          </div>
        </div>

        <div className="relative mt-4 min-h-[460px] overflow-hidden rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.06),transparent_46%),linear-gradient(180deg,rgba(9,15,23,0.18),rgba(9,15,23,0.42))] xl:min-h-[620px]">
          {currentDiagnosis?.readiness ? (
            <StudentScene
              readinessStatus={currentDiagnosis.readiness.status}
              readinessScore={currentDiagnosis.readiness.readiness_score}
              cohortGap={currentDiagnosis.readiness.cohort_gap ?? null}
            />
          ) : (
            <div className="flex h-full min-h-[460px] items-center justify-center text-sm text-white/70">
              Scene will render once diagnosis data is available.
            </div>
          )}

          <div className="absolute left-4 top-4 max-w-[340px] rounded-[1.5rem] border border-white/12 bg-[rgba(15,27,42,0.78)] px-4 py-4 text-white backdrop-blur">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-gold">Start here</p>
            <strong className="mt-2 block text-2xl">
              {topRootCause?.concept_name ?? "No bottleneck detected"}
            </strong>
            <p className="mt-2 text-sm leading-6 text-white/74">
              {primaryAction?.action ?? currentDiagnosis?.explanation ?? "Waiting for diagnosis summary."}
            </p>
          </div>

          <div className="absolute bottom-4 left-4 right-4 rounded-[1.6rem] border border-white/10 bg-[rgba(15,27,42,0.76)] px-4 py-4 text-white backdrop-blur">
            <div className="grid gap-4 lg:grid-cols-[1.25fr_0.75fr_0.75fr_0.75fr]">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/54">Teacher summary</p>
                <p className="mt-2 text-sm leading-6 text-white/78">
                  {currentDiagnosis?.explanation ?? "Diagnosis summary will appear here once the student scene loads."}
                </p>
              </div>
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/54">Readiness</p>
                <strong className="mt-2 block text-2xl">
                  {currentDiagnosis?.readiness
                    ? `${(currentDiagnosis.readiness.readiness_score * 100).toFixed(0)}%`
                    : "--"}
                </strong>
              </div>
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/54">Cohort gap</p>
                <strong className="mt-2 block text-2xl">
                  {currentDiagnosis?.readiness?.cohort_gap == null
                    ? "N/A"
                    : `${currentDiagnosis.readiness.cohort_gap > 0 ? "+" : ""}${(
                        currentDiagnosis.readiness.cohort_gap * 100
                      ).toFixed(0)} pts`}
                </strong>
              </div>
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/54">Evidence window</p>
                <strong className="mt-2 block text-2xl">
                  {currentDiagnosis?.readiness?.assessments_considered ?? 0}
                </strong>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-[2rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Teaching focus</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
              Inspect only the concepts worth discussing next
            </h2>
          </div>
          <Link
            href={`/concepts?subject=${subjectId}&concept=${explorerConceptId}`}
            className="inline-flex rounded-full bg-accent-soft px-4 py-2 text-sm text-accent"
          >
            Open full concept explorer
          </Link>
        </div>

        <div className="mt-5 flex flex-wrap gap-3">
          {focusCandidates.length ? (
            focusCandidates.map((candidate) => {
              const selected = selectedDrilldownConceptId === candidate.concept_id;
              return (
                <button
                  key={candidate.concept_id}
                  type="button"
                  onClick={() => handleInspectConcept(candidate.concept_id)}
                  className={`rounded-full border px-4 py-3 text-left transition-colors ${
                    selected
                      ? "border-transparent bg-foreground text-white"
                      : "border-line bg-white text-foreground hover:bg-[#f5efe8]"
                  }`}
                >
                  <strong className="block text-sm">{candidate.concept_name}</strong>
                  <span className={`mt-1 block font-mono text-[11px] uppercase tracking-[0.16em] ${selected ? "text-gold" : "text-muted"}`}>
                    {candidate.meta}
                  </span>
                </button>
              );
            })
          ) : (
            <div className="rounded-2xl border border-dashed border-line p-4 text-sm text-muted">
              Focus concepts will appear after diagnosis loads.
            </div>
          )}
        </div>
      </section>

      <section className="rounded-[2.2rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)] md:p-6">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Details</p>
            <h3 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
              Reveal the deeper analysis only when needed
            </h3>
          </div>

          <div className="flex flex-wrap gap-2">
            {[
              { id: "overview", label: "Overview" },
              { id: "route", label: "Route" },
              { id: "trend", label: "Trend" },
            ].map((panel) => (
              <button
                key={panel.id}
                type="button"
                onClick={() => setActivePanel(panel.id as "overview" | "route" | "trend")}
                className={`rounded-full px-4 py-2 text-sm transition-colors ${
                  activePanel === panel.id
                    ? "bg-foreground text-white"
                    : "bg-white text-muted hover:bg-[#f5efe8] hover:text-foreground"
                }`}
              >
                {panel.label}
              </button>
            ))}
          </div>
        </div>

        {activePanel === "overview" ? (
          <div className="mt-6 grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
            <article className="rounded-[1.8rem] border border-line bg-white p-5">
              <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Why this is the first move</p>
              <strong className="mt-3 block text-3xl text-foreground">
                {topRootCause?.concept_name ?? "No root cause detected"}
              </strong>
              <p className="mt-4 text-sm leading-7 text-muted">
                {currentDiagnosis?.explanation ?? "Diagnosis summary will appear here after the scene updates."}
              </p>

              <div className="mt-5 flex flex-wrap gap-3">
                {currentDiagnosis?.weak_concepts.slice(0, 5).map((concept) => (
                  <button
                    key={concept.concept_id}
                    type="button"
                    onClick={() => handleInspectConcept(concept.concept_id)}
                    className="rounded-2xl border border-line bg-[#f8f6f1] px-4 py-3 text-left"
                  >
                    <strong className="block text-sm text-foreground">{concept.concept_name}</strong>
                    <span className="mt-1 block text-sm text-muted">
                      Mastery {concept.mastery_score.toFixed(2)} · Confidence {concept.confidence.toFixed(2)}
                    </span>
                  </button>
                ))}
              </div>
            </article>

            <article className="rounded-[1.8rem] border border-line bg-white p-5">
              <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Immediate teaching sequence</p>
              <div className="mt-4 grid gap-3">
                {currentDiagnosis?.remediation_order.slice(0, 4).map((step) => (
                  <div key={step.concept_id} className="rounded-[1.4rem] border border-line bg-[#fbfaf6] p-4">
                    <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-teal">Step {step.order}</p>
                    <strong className="mt-2 block text-lg text-foreground">{step.concept_name}</strong>
                    <p className="mt-2 text-sm leading-6 text-muted">{step.action}</p>
                  </div>
                ))}
              </div>
            </article>
          </div>
        ) : null}

        {activePanel === "route" ? (
          <div className="mt-6 grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
            <DependencyMap drilldown={currentDrilldown} />

            <article className="rounded-[1.8rem] border border-line bg-white p-5">
              <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Focused concept</p>
              <strong className="mt-3 block text-3xl text-foreground">
                {currentDrilldown ? displayName(currentDrilldown.concept) : topRootCause?.concept_name ?? "Awaiting focus"}
              </strong>
              <p className="mt-3 text-sm leading-7 text-muted">
                {currentDrilldown?.concept.description ?? "Choose a bottleneck concept to inspect its route."}
              </p>

              <div className="mt-5 grid gap-3 md:grid-cols-2">
                <div className="rounded-[1.4rem] bg-[#fff9ef] p-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Prerequisite paths</p>
                  <strong className="mt-2 block text-3xl text-foreground">
                    {currentDrilldown?.prerequisite_paths.length ?? 0}
                  </strong>
                </div>
                <div className="rounded-[1.4rem] bg-[#f4faf8] p-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Downstream concepts</p>
                  <strong className="mt-2 block text-3xl text-foreground">
                    {currentDrilldown?.downstream_concepts.length ?? 0}
                  </strong>
                </div>
              </div>

              {selectedWeakConcept ? (
                <div className="mt-5 rounded-[1.4rem] border border-line bg-[#fbfaf6] p-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Observed signal</p>
                  <p className="mt-2 text-sm leading-6 text-muted">
                    {selectedWeakConcept.evidence}. Mastery {selectedWeakConcept.mastery_score.toFixed(2)} with confidence{" "}
                    {selectedWeakConcept.confidence.toFixed(2)}.
                  </p>
                </div>
              ) : null}
            </article>
          </div>
        ) : null}

        {activePanel === "trend" ? (
          <div className="mt-6 grid gap-4">
            {selectedTrend ? (
              <article className="rounded-[1.8rem] border border-line bg-white p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Focused trend</p>
                    <strong className="mt-2 block text-3xl text-foreground">{selectedTrend.concept_name}</strong>
                  </div>
                  <span
                    className={`rounded-full border px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] ${trendToneClasses(
                      selectedTrend.direction,
                    )}`}
                  >
                    {formatTrendDirection(selectedTrend.direction)}
                  </span>
                </div>

                <div className="mt-5 rounded-[1.6rem] bg-[linear-gradient(180deg,#f5f3ec,#eff5f3)] p-4">
                  <svg className="h-20 w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
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
              </article>
            ) : null}

            <div className="grid gap-4 xl:grid-cols-2">
              {currentDiagnosis?.concept_trends.length ? (
                currentDiagnosis.concept_trends.map((trend) => (
                  <button
                    key={trend.concept_id}
                    type="button"
                    onClick={() => handleInspectConcept(trend.concept_id)}
                    className="rounded-[1.6rem] border border-line bg-white p-4 text-left"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <strong className="block text-lg text-foreground">{trend.concept_name}</strong>
                        <p className="mt-2 text-sm text-muted">
                          Latest {(trend.latest_mastery * 100).toFixed(0)}%
                          {trend.prior_mastery == null
                            ? " with limited history"
                            : `, prior ${(trend.prior_mastery * 100).toFixed(0)}%`}
                        </p>
                      </div>
                      <span
                        className={`rounded-full border px-2 py-1 font-mono text-[11px] uppercase tracking-[0.12em] ${trendToneClasses(
                          trend.direction,
                        )}`}
                      >
                        {formatTrendDirection(trend.direction)}
                      </span>
                    </div>
                  </button>
                ))
              ) : (
                <div className="rounded-[1.6rem] border border-dashed border-line p-5 text-sm text-muted">
                  Trend signals appear when multiple assessment points exist for a flagged concept.
                </div>
              )}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}

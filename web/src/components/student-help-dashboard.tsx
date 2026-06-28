"use client";

import Link from "next/link";
import { startTransition, useEffect, useEffectEvent, useState } from "react";

type SubjectNode = {
  id: string;
  name: string;
  name_si?: string | null;
  description?: string | null;
  default_concept_id: string;
};

type SelectorOptionsResponse = {
  subjects: SubjectNode[];
  concepts: unknown[];
  students: { id: string; full_name: string; cohort: string }[];
};

type RiskBand = "high_support" | "watch" | "stable";

type StudentSupportEntry = {
  student_id: string;
  student_name: string;
  cohort: string;
  risk_score: number;
  risk_band: RiskBand;
  confidence: number;
  top_reason?: string | null;
  recommended_action: string;
};

type StudentSupportListResponse = {
  subject: SubjectNode;
  summary: {
    total_students: number;
    high_support: number;
    watch: number;
    stable: number;
    average_confidence: number;
  };
  students: StudentSupportEntry[];
};

type SupportRiskFactor = {
  feature: string;
  label: string;
  value: number | string | null;
  impact: number;
  direction: "increases_risk" | "reduces_risk";
  explanation: string;
};

type StudentSupportProfileResponse = {
  student: { id: string; full_name: string; cohort: string };
  subject: SubjectNode;
  risk: { score: number; band: RiskBand; confidence: number };
  features: {
    avg_mastery: number;
    weak_concept_count: number;
    borderline_concept_count: number;
    strong_concept_count: number;
    missing_evidence_count: number;
    avg_confidence: number;
    low_confidence_count: number;
    mastery_decline_count: number;
    cohort_gap_avg?: number | null;
    root_cause_count: number;
    concept_count: number;
    assessment_count: number;
    recent_accuracy: number;
  };
  explanation_method: string;
  explanation_summary: string;
  factors: SupportRiskFactor[];
  recommended_actions: string[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const DEFAULT_SUBJECT_ID = "OL-MATH";

function displayName(item: { name: string; name_si?: string | null }) {
  return item.name_si ? `${item.name} / ${item.name_si}` : item.name;
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `${(value * 100).toFixed(0)}%`;
}

function riskLabel(band: RiskBand) {
  if (band === "high_support") {
    return "High support";
  }
  if (band === "watch") {
    return "Watch";
  }
  return "Stable";
}

function riskTone(band: RiskBand) {
  if (band === "high_support") {
    return "bg-[rgba(217,97,61,0.12)] text-accent";
  }
  if (band === "watch") {
    return "bg-[rgba(225,176,75,0.16)] text-[#8b640c]";
  }
  return "bg-[rgba(27,127,138,0.12)] text-teal";
}

function impactWidth(impact: number) {
  return `${Math.min(Math.abs(impact) * 260, 100).toFixed(0)}%`;
}

export function StudentHelpDashboard({ initialSubjectId = DEFAULT_SUBJECT_ID }: { initialSubjectId?: string }) {
  const [subjectId, setSubjectId] = useState(initialSubjectId);
  const [subjects, setSubjects] = useState<SubjectNode[]>([]);
  const [supportList, setSupportList] = useState<StudentSupportListResponse | null>(null);
  const [profile, setProfile] = useState<StudentSupportProfileResponse | null>(null);
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [message, setMessage] = useState("Loading student support risks...");

  async function fetchOptions(nextSubjectId: string) {
    const response = await fetch(`${API_BASE_URL}/api/options?subject_id=${nextSubjectId}`);
    if (!response.ok) {
      throw new Error("Unable to load subject options.");
    }
    return (await response.json()) as SelectorOptionsResponse;
  }

  async function fetchSupportList(nextSubjectId: string) {
    const response = await fetch(`${API_BASE_URL}/api/support/subjects/${nextSubjectId}/students?limit=40`);
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? "Unable to load student help list.");
    }
    return (await response.json()) as StudentSupportListResponse;
  }

  async function fetchProfile(studentId: string, nextSubjectId: string) {
    const response = await fetch(`${API_BASE_URL}/api/support/students/${studentId}/subjects/${nextSubjectId}`);
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? "Unable to load student support profile.");
    }
    return (await response.json()) as StudentSupportProfileResponse;
  }

  async function loadDashboard(nextSubjectId: string, requestedStudentId?: string) {
    setStatus("loading");
    setMessage("Building support-risk list from latest concept evidence...");
    try {
      const options = await fetchOptions(nextSubjectId);
      const selectedSubject = options.subjects.find((subject) => subject.id === nextSubjectId) ?? options.subjects[0];
      const resolvedSubjectId = selectedSubject?.id ?? nextSubjectId;
      const listPayload = await fetchSupportList(resolvedSubjectId);
      const resolvedStudentId =
        listPayload.students.find((student) => student.student_id === requestedStudentId)?.student_id ??
        listPayload.students[0]?.student_id ??
        "";

      setSubjects(options.subjects);
      setSubjectId(resolvedSubjectId);
      setSupportList(listPayload);
      setSelectedStudentId(resolvedStudentId);

      if (resolvedStudentId) {
        setProfile(await fetchProfile(resolvedStudentId, resolvedSubjectId));
      } else {
        setProfile(null);
      }
      setStatus("idle");
      setMessage("Student help view updated from stored assessment evidence.");
    } catch (error) {
      setSupportList(null);
      setProfile(null);
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Unable to load student help view.");
    }
  }

  async function selectStudent(studentId: string) {
    setSelectedStudentId(studentId);
    setStatus("loading");
    setMessage("Loading explanation for selected learner...");
    try {
      setProfile(await fetchProfile(studentId, subjectId));
      setStatus("idle");
      setMessage("Explanation loaded for selected learner.");
    } catch (error) {
      setProfile(null);
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Unable to load explanation.");
    }
  }

  const loadInitialDashboard = useEffectEvent(() => {
    void loadDashboard(subjectId, selectedStudentId);
  });

  useEffect(() => {
    startTransition(() => {
      loadInitialDashboard();
    });
  }, []);

  return (
    <div className="grid gap-6">
      <section className="rounded-[2.4rem] border border-line bg-[linear-gradient(135deg,#132034,#20324b)] p-6 text-white shadow-[0_24px_100px_rgba(19,32,52,0.16)] md:p-8">
        <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr] xl:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-gold">Student Help</p>
            <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight md:text-5xl">
              Explainable support-risk dashboard.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-8 text-white/76">
              Rank learners by academic support risk, then show why each learner was flagged and what
              the teacher should do next.
            </p>
          </div>

          <div className="rounded-[1.8rem] border border-white/10 bg-white/8 p-5 backdrop-blur">
            <label className="grid gap-3">
              <span className="font-mono text-xs uppercase tracking-[0.22em] text-white/60">Subject</span>
              <select
                className="rounded-2xl border border-white/10 bg-white/92 px-4 py-3 text-foreground outline-none"
                value={subjectId}
                onChange={(event) => {
                  const nextSubjectId = event.target.value;
                  startTransition(() => {
                    void loadDashboard(nextSubjectId);
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
            <p className="mt-4 text-sm leading-7 text-white/70">{message}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <div className="rounded-[2rem] border border-line bg-[#fff9ef] p-5">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">High support</p>
          <strong className="mt-3 block text-4xl text-foreground">{supportList?.summary.high_support ?? 0}</strong>
        </div>
        <div className="rounded-[2rem] border border-line bg-[#f5f5fb] p-5">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Watch</p>
          <strong className="mt-3 block text-4xl text-foreground">{supportList?.summary.watch ?? 0}</strong>
        </div>
        <div className="rounded-[2rem] border border-line bg-[#f4faf8] p-5">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Stable</p>
          <strong className="mt-3 block text-4xl text-foreground">{supportList?.summary.stable ?? 0}</strong>
        </div>
        <div className="rounded-[2rem] border border-line bg-white p-5">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Avg confidence</p>
          <strong className="mt-3 block text-4xl text-foreground">
            {formatPercent(supportList?.summary.average_confidence)}
          </strong>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1fr_0.8fr]">
        <div className="rounded-[2rem] border border-line bg-surface p-3 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <div className="grid gap-2">
            {supportList?.students.length ? (
              supportList.students.map((student, index) => (
                <button
                  key={student.student_id}
                  type="button"
                  onClick={() => {
                    startTransition(() => {
                      void selectStudent(student.student_id);
                    });
                  }}
                  className={`grid w-full gap-4 rounded-[1.4rem] border px-4 py-4 text-left transition-colors md:grid-cols-[54px_minmax(0,1.2fr)_0.72fr_0.72fr_minmax(0,1fr)] md:items-center ${
                    selectedStudentId === student.student_id
                      ? "border-foreground bg-white"
                      : "border-line bg-white/82 hover:bg-white"
                  }`}
                >
                  <div className="rounded-full bg-[#f3efe5] px-3 py-3 text-center font-mono text-xs uppercase tracking-[0.18em] text-muted">
                    {index + 1}
                  </div>
                  <div>
                    <strong className="block text-lg text-foreground">{student.student_name}</strong>
                    <p className="mt-1 text-sm text-muted">
                      {student.student_id} · {student.cohort}
                    </p>
                  </div>
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Risk</p>
                    <span className={`mt-2 inline-flex rounded-full px-3 py-2 text-sm ${riskTone(student.risk_band)}`}>
                      {riskLabel(student.risk_band)}
                    </span>
                  </div>
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Score</p>
                    <strong className="mt-2 block text-lg text-foreground">{formatPercent(student.risk_score)}</strong>
                  </div>
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Main reason</p>
                    <p className="mt-2 text-sm leading-6 text-foreground">{student.top_reason ?? "No major risk factor"}</p>
                  </div>
                </button>
              ))
            ) : (
              <div className="rounded-[1.5rem] border border-dashed border-line p-5 text-sm text-muted">
                {status === "loading" ? "Loading support-risk list..." : "No support-risk results available."}
              </div>
            )}
          </div>
        </div>

        <aside className="rounded-[2rem] border border-line bg-white p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          {profile ? (
            <div className="grid gap-5">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Selected learner</p>
                <h2 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
                  {profile.student.full_name}
                </h2>
                <p className="mt-2 text-sm text-muted">
                  {profile.student.id} · {profile.student.cohort} · {displayName(profile.subject)}
                </p>
              </div>

              <div className="rounded-[1.5rem] border border-line bg-[#fbf7f0] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className={`rounded-full px-3 py-2 text-sm ${riskTone(profile.risk.band)}`}>
                    {riskLabel(profile.risk.band)}
                  </span>
                  <strong className="text-3xl text-foreground">{formatPercent(profile.risk.score)}</strong>
                </div>
                <p className="mt-3 text-sm leading-7 text-muted">{profile.explanation_summary}</p>
              </div>

              <div>
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Why flagged?</p>
                <div className="mt-3 grid gap-3">
                  {profile.factors.slice(0, 5).map((factor) => (
                    <div key={factor.feature} className="rounded-[1.3rem] border border-line p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <strong className="block text-foreground">{factor.label}</strong>
                          <p className="mt-1 text-sm leading-6 text-muted">{factor.explanation}</p>
                        </div>
                        <span className="font-mono text-xs text-muted">{factor.impact.toFixed(3)}</span>
                      </div>
                      <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#eee8dc]">
                        <div
                          className={`h-full rounded-full ${
                            factor.direction === "increases_risk" ? "bg-accent" : "bg-teal"
                          }`}
                          style={{ width: impactWidth(factor.impact) }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-[1.5rem] border border-line bg-surface p-4">
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Feature snapshot</p>
                <div className="mt-4 grid gap-3 text-sm text-muted sm:grid-cols-2">
                  <span>Avg mastery: {formatPercent(profile.features.avg_mastery)}</span>
                  <span>Weak concepts: {profile.features.weak_concept_count}</span>
                  <span>Root causes: {profile.features.root_cause_count}</span>
                  <span>Evidence confidence: {formatPercent(profile.features.avg_confidence)}</span>
                  <span>Declines: {profile.features.mastery_decline_count}</span>
                  <span>Cohort gap: {formatPercent(profile.features.cohort_gap_avg)}</span>
                </div>
              </div>

              <div>
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Recommended actions</p>
                <div className="mt-3 grid gap-2">
                  {profile.recommended_actions.map((action) => (
                    <p key={action} className="rounded-[1.2rem] bg-[#f4faf8] px-4 py-3 text-sm leading-6 text-foreground">
                      {action}
                    </p>
                  ))}
                </div>
              </div>

              <Link
                href={`/diagnosis?subject=${subjectId}&student=${profile.student.id}`}
                className="inline-flex justify-center rounded-full bg-foreground px-5 py-3 text-sm text-white"
              >
                Open full diagnosis
              </Link>
            </div>
          ) : (
            <div className="rounded-[1.5rem] border border-dashed border-line p-5 text-sm leading-7 text-muted">
              Select a learner to see support-risk explanation and next actions.
            </div>
          )}
        </aside>
      </section>
    </div>
  );
}

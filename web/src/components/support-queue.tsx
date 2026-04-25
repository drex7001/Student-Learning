"use client";

import Link from "next/link";
import { startTransition, useEffect, useEffectEvent, useState } from "react";

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

type SelectorOptionsResponse = {
  students: { id: string; full_name: string; cohort: string }[];
  subjects: SubjectNode[];
  concepts: ConceptNode[];
};

type SupportQueueEntry = {
  student_id: string;
  student_name: string;
  cohort: string;
  readiness_status: "needs_immediate_support" | "watch" | "ready_to_progress";
  readiness_score: number;
  target_mastery: number;
  cohort_gap?: number | null;
  latest_assessment_date?: string | null;
  top_root_cause?: string | null;
};

type SupportQueueResponse = {
  concept: ConceptNode;
  summary: {
    total_students: number;
    support_now: number;
    watch_list: number;
    ready_to_progress: number;
  };
  students: SupportQueueEntry[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const DEFAULT_SUBJECT_ID = "OL-MATH";

function displayName(item: { name: string; name_si?: string | null }) {
  return item.name_si ? `${item.name} / ${item.name_si}` : item.name;
}

function statusLabel(status: SupportQueueEntry["readiness_status"]) {
  if (status === "needs_immediate_support") {
    return "Support now";
  }
  if (status === "ready_to_progress") {
    return "Ready";
  }
  return "Watch";
}

function statusTone(status: SupportQueueEntry["readiness_status"]) {
  if (status === "needs_immediate_support") {
    return "bg-[rgba(217,97,61,0.12)] text-accent";
  }
  if (status === "ready_to_progress") {
    return "bg-[rgba(27,127,138,0.12)] text-teal";
  }
  return "bg-[rgba(225,176,75,0.16)] text-[#8b640c]";
}

export function SupportQueue({
  initialSubjectId = DEFAULT_SUBJECT_ID,
  initialConceptId,
}: {
  initialSubjectId?: string;
  initialConceptId?: string;
}) {
  const [subjectId, setSubjectId] = useState(initialSubjectId);
  const [conceptId, setConceptId] = useState(initialConceptId ?? "");
  const [subjects, setSubjects] = useState<SubjectNode[]>([]);
  const [concepts, setConcepts] = useState<ConceptNode[]>([]);
  const [queue, setQueue] = useState<SupportQueueResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [message, setMessage] = useState("Loading concept queue...");

  async function fetchOptions(nextSubjectId: string) {
    const response = await fetch(`${API_BASE_URL}/api/options?subject_id=${nextSubjectId}`);
    if (!response.ok) {
      throw new Error("Unable to load concept options.");
    }
    return (await response.json()) as SelectorOptionsResponse;
  }

  async function fetchQueue(nextConceptId: string) {
    const response = await fetch(`${API_BASE_URL}/api/overview/concept/${nextConceptId}?limit=18`);
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? "Unable to load support queue.");
    }
    return (await response.json()) as SupportQueueResponse;
  }

  async function loadQueue(nextSubjectId: string, nextConceptId?: string) {
    setStatus("loading");
    setMessage("Ranking learners for the selected concept...");
    try {
      const optionsPayload = await fetchOptions(nextSubjectId);
      setSubjects(optionsPayload.subjects);
      setConcepts(optionsPayload.concepts);
      const selectedSubject =
        optionsPayload.subjects.find((subject) => subject.id === nextSubjectId) ??
        optionsPayload.subjects[0];
      const resolvedConceptId =
        optionsPayload.concepts.find((concept) => concept.id === nextConceptId)?.id ??
        optionsPayload.concepts.find((concept) => concept.id === selectedSubject?.default_concept_id)?.id ??
        optionsPayload.concepts[0]?.id ??
        nextConceptId ??
        "";
      setSubjectId(selectedSubject?.id ?? nextSubjectId);
      setConceptId(resolvedConceptId);

      const queuePayload = await fetchQueue(resolvedConceptId);
      setQueue(queuePayload);
      setStatus("idle");
      setMessage("Queue updated from the latest stored assessment evidence.");
    } catch (error) {
      setQueue(null);
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Unable to load support queue.");
    }
  }

  const loadInitialQueue = useEffectEvent(() => {
    void loadQueue(subjectId, conceptId);
  });

  useEffect(() => {
    startTransition(() => {
      loadInitialQueue();
    });
  }, []);

  return (
    <div className="grid gap-6">
      <section className="rounded-[2.4rem] border border-line bg-[linear-gradient(135deg,#132034,#20324b)] p-6 text-white shadow-[0_24px_100px_rgba(19,32,52,0.16)] md:p-8">
        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-gold">Support Queue</p>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight md:text-5xl">
              Find the learners who need support first.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-8 text-white/76">
              Choose an O/L subject and concept, then review the students ranked by readiness for
              the next lesson or revision session.
            </p>
          </div>

          <div className="rounded-[1.8rem] border border-white/10 bg-white/8 p-5 backdrop-blur">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="grid gap-3">
                <span className="font-mono text-xs uppercase tracking-[0.22em] text-white/60">
                  Subject
                </span>
                <select
                  className="rounded-2xl border border-white/10 bg-white/92 px-4 py-3 text-foreground outline-none"
                  value={subjectId}
                  onChange={(event) => {
                    const nextSubjectId = event.target.value;
                    setSubjectId(nextSubjectId);
                    startTransition(() => {
                      void loadQueue(nextSubjectId);
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

              <label className="grid gap-3">
                <span className="font-mono text-xs uppercase tracking-[0.22em] text-white/60">
                  Concept
                </span>
                <select
                  className="rounded-2xl border border-white/10 bg-white/92 px-4 py-3 text-foreground outline-none"
                  value={conceptId}
                  onChange={(event) => {
                    const nextConceptId = event.target.value;
                    setConceptId(nextConceptId);
                    startTransition(() => {
                      void loadQueue(subjectId, nextConceptId);
                    });
                  }}
                >
                  {concepts.map((concept) => (
                    <option key={concept.id} value={concept.id}>
                      {displayName(concept)}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="mt-4 text-sm leading-7 text-white/70">{message}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[0.82fr_1.18fr]">
        <div className="rounded-[2rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Queue summary</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
            {queue ? displayName(queue.concept) : "Loading concept"}
          </h2>
          <p className="mt-3 text-sm leading-7 text-muted">
            {queue?.concept.description ?? "Loading concept summary."}
          </p>

          <div className="mt-6 grid gap-3">
            <div className="rounded-[1.5rem] bg-[#fff9ef] p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Support now</p>
              <strong className="mt-2 block text-3xl text-foreground">
                {queue?.summary.support_now ?? 0}
              </strong>
            </div>
            <div className="rounded-[1.5rem] bg-[#f4faf8] p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Watch list</p>
              <strong className="mt-2 block text-3xl text-foreground">
                {queue?.summary.watch_list ?? 0}
              </strong>
            </div>
            <div className="rounded-[1.5rem] bg-[#f5f5fb] p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Ready</p>
              <strong className="mt-2 block text-3xl text-foreground">
                {queue?.summary.ready_to_progress ?? 0}
              </strong>
            </div>
          </div>
        </div>

        <div className="rounded-[2rem] border border-line bg-surface p-3 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <div className="grid gap-2">
            {queue?.students.length ? (
              queue.students.map((student, index) => (
                <div
                  key={student.student_id}
                  className="grid gap-4 rounded-[1.4rem] border border-line bg-white px-4 py-4 md:grid-cols-[56px_minmax(0,1.2fr)_0.8fr_0.8fr_0.8fr_auto] md:items-center"
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
                    <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Status</p>
                    <span className={`mt-2 inline-flex rounded-full px-3 py-2 text-sm ${statusTone(student.readiness_status)}`}>
                      {statusLabel(student.readiness_status)}
                    </span>
                  </div>
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Readiness</p>
                    <strong className="mt-2 block text-lg text-foreground">
                      {(student.readiness_score * 100).toFixed(0)}%
                    </strong>
                  </div>
                  <div>
                    <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Likely cause</p>
                    <p className="mt-2 text-sm leading-6 text-foreground">
                      {student.top_root_cause ?? "No root cause flagged"}
                    </p>
                  </div>
                  <div className="md:justify-self-end">
                    <Link
                      href={`/diagnosis?subject=${subjectId}&student=${student.student_id}&concept=${conceptId}`}
                      className="inline-flex rounded-full bg-foreground px-4 py-2 text-sm text-white"
                    >
                      Open diagnosis
                    </Link>
                  </div>
                </div>
              ))
            ) : (
              <div className="rounded-[1.5rem] border border-dashed border-line p-5 text-sm text-muted">
                {status === "loading"
                  ? "Loading ranked learners..."
                  : "No queue results available for this concept."}
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

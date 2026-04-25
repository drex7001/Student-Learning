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

type ConceptNode = {
  id: string;
  subject_id?: string | null;
  name: string;
  name_si?: string | null;
  description?: string | null;
};

type SelectorOptionsResponse = {
  subjects: SubjectNode[];
  concepts: ConceptNode[];
  students: { id: string; full_name: string; cohort: string }[];
};

type SupportQueueResponse = {
  concept: ConceptNode;
  summary: {
    total_students: number;
    support_now: number;
    watch_list: number;
    ready_to_progress: number;
  };
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const DEFAULT_SUBJECT_ID = "OL-MATH";

function displayName(item: { name: string; name_si?: string | null }) {
  return item.name_si ? `${item.name} / ${item.name_si}` : item.name;
}

export function TeacherDashboard() {
  const [subjectId, setSubjectId] = useState(DEFAULT_SUBJECT_ID);
  const [conceptId, setConceptId] = useState("");
  const [subjects, setSubjects] = useState<SubjectNode[]>([]);
  const [concepts, setConcepts] = useState<ConceptNode[]>([]);
  const [queue, setQueue] = useState<SupportQueueResponse | null>(null);
  const [message, setMessage] = useState("Loading O/L subject data...");

  async function fetchOptions(nextSubjectId: string) {
    const response = await fetch(`${API_BASE_URL}/api/options?subject_id=${nextSubjectId}`);
    if (!response.ok) {
      throw new Error("Unable to load subjects and concepts.");
    }
    return (await response.json()) as SelectorOptionsResponse;
  }

  async function fetchQueue(nextConceptId: string) {
    const response = await fetch(`${API_BASE_URL}/api/overview/concept/${nextConceptId}?limit=6`);
    if (!response.ok) {
      throw new Error("Unable to load the support summary.");
    }
    return (await response.json()) as SupportQueueResponse;
  }

  async function loadDashboard(nextSubjectId: string, requestedConceptId?: string) {
    setMessage("Loading O/L subject data...");
    try {
      const options = await fetchOptions(nextSubjectId);
      const selectedSubject =
        options.subjects.find((subject) => subject.id === nextSubjectId) ?? options.subjects[0];
      const resolvedConceptId =
        options.concepts.find((concept) => concept.id === requestedConceptId)?.id ??
        options.concepts.find((concept) => concept.id === selectedSubject?.default_concept_id)?.id ??
        options.concepts[0]?.id ??
        "";

      setSubjects(options.subjects);
      setConcepts(options.concepts);
      setSubjectId(selectedSubject?.id ?? nextSubjectId);
      setConceptId(resolvedConceptId);

      if (resolvedConceptId) {
        setQueue(await fetchQueue(resolvedConceptId));
        setMessage("Summary updated from the latest stored assessment evidence.");
      } else {
        setQueue(null);
        setMessage("Import the curriculum and generate synthetic data to load the dashboard.");
      }
    } catch (error) {
      setQueue(null);
      setMessage(error instanceof Error ? error.message : "Unable to load dashboard.");
    }
  }

  const loadInitialDashboard = useEffectEvent(() => {
    void loadDashboard(subjectId, conceptId);
  });

  useEffect(() => {
    startTransition(() => {
      loadInitialDashboard();
    });
  }, []);

  const selectedSubject = subjects.find((subject) => subject.id === subjectId);
  const selectedConcept = concepts.find((concept) => concept.id === conceptId);

  return (
    <main className="flex w-full flex-1 flex-col px-4 py-5 md:px-6 xl:px-8">
      <section className="overflow-hidden rounded-[2.4rem] border border-line bg-[linear-gradient(135deg,#132034,#20324b)] px-6 py-8 text-white shadow-[0_24px_100px_rgba(19,32,52,0.16)] md:px-10 md:py-10">
        <div className="grid gap-8 xl:grid-cols-[1fr_0.9fr] xl:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-gold">Sri Lankan O/L</p>
            <h1 className="mt-5 max-w-4xl text-4xl font-semibold tracking-tight md:text-6xl">
              Teacher support dashboard
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-8 text-white/76 md:text-lg">
              Select a subject and concept to see who needs help, then open a focused diagnosis or
              review the learning path.
            </p>
          </div>

          <div className="rounded-[1.8rem] border border-white/10 bg-white/8 p-5 backdrop-blur">
            <div className="grid gap-4 md:grid-cols-2">
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

              <label className="grid gap-3">
                <span className="font-mono text-xs uppercase tracking-[0.22em] text-white/60">Concept</span>
                <select
                  className="rounded-2xl border border-white/10 bg-white/92 px-4 py-3 text-foreground outline-none"
                  value={conceptId}
                  onChange={(event) => {
                    const nextConceptId = event.target.value;
                    setConceptId(nextConceptId);
                    startTransition(() => {
                      void loadDashboard(subjectId, nextConceptId);
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

      <section className="mt-6 grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-[2rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Current focus</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-foreground">
            {selectedSubject ? displayName(selectedSubject) : "Loading subject"}
          </h2>
          <p className="mt-3 text-sm leading-7 text-muted">
            {selectedSubject?.description ?? "Choose a subject to begin."}
          </p>
          <div className="mt-5 rounded-[1.5rem] border border-line bg-white p-4">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Selected concept</p>
            <strong className="mt-2 block text-xl text-foreground">
              {selectedConcept ? displayName(selectedConcept) : "No concept selected"}
            </strong>
            <p className="mt-2 text-sm leading-6 text-muted">{selectedConcept?.description}</p>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-[2rem] border border-line bg-[#fff9ef] p-5">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Support now</p>
            <strong className="mt-3 block text-4xl text-foreground">{queue?.summary.support_now ?? 0}</strong>
          </div>
          <div className="rounded-[2rem] border border-line bg-[#f4faf8] p-5">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Watch list</p>
            <strong className="mt-3 block text-4xl text-foreground">{queue?.summary.watch_list ?? 0}</strong>
          </div>
          <div className="rounded-[2rem] border border-line bg-[#f5f5fb] p-5">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Ready</p>
            <strong className="mt-3 block text-4xl text-foreground">{queue?.summary.ready_to_progress ?? 0}</strong>
          </div>
        </div>
      </section>

      <section className="mt-6 grid gap-5 xl:grid-cols-4">
        <Link
          href={`/students?subject=${subjectId}&concept=${conceptId}`}
          className="rounded-[2rem] border border-line bg-white p-6 shadow-[0_20px_80px_rgba(19,32,52,0.08)] transition-transform duration-200 hover:-translate-y-1"
        >
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Support Queue</p>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight">Prioritise learners</h2>
          <p className="mt-4 text-sm leading-7 text-muted">
            See the ranked list for the selected O/L concept and open individual diagnoses.
          </p>
        </Link>
        <Link
          href={`/diagnosis?subject=${subjectId}&concept=${conceptId}`}
          className="rounded-[2rem] border border-line bg-white p-6 shadow-[0_20px_80px_rgba(19,32,52,0.08)] transition-transform duration-200 hover:-translate-y-1"
        >
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Student Diagnosis</p>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight">Find the root cause</h2>
          <p className="mt-4 text-sm leading-7 text-muted">
            Select a learner and identify the prerequisite concept to revise first.
          </p>
        </Link>
        <Link
          href={`/learn?subject=${subjectId}`}
          className="rounded-[2rem] border border-line bg-white p-6 shadow-[0_20px_80px_rgba(19,32,52,0.08)] transition-transform duration-200 hover:-translate-y-1"
        >
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Learn</p>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight">Practice weak areas</h2>
          <p className="mt-4 text-sm leading-7 text-muted">
            Open the student portal for lesson cards and a personalized quiz.
          </p>
        </Link>
        <Link
          href={`/concepts?subject=${subjectId}&concept=${conceptId}`}
          className="rounded-[2rem] border border-line bg-white p-6 shadow-[0_20px_80px_rgba(19,32,52,0.08)] transition-transform duration-200 hover:-translate-y-1"
        >
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Concept Map</p>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight">Review the pathway</h2>
          <p className="mt-4 text-sm leading-7 text-muted">
            Inspect prerequisite links and downstream topics for the selected concept.
          </p>
        </Link>
      </section>
    </main>
  );
}

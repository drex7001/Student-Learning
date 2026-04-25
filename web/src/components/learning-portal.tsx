"use client";

import { startTransition, useEffect, useEffectEvent, useState } from "react";

type StudentSummary = {
  id: string;
  full_name: string;
  cohort: string;
};

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
};

type SelectorOptionsResponse = {
  students: StudentSummary[];
  subjects: SubjectNode[];
  concepts: ConceptNode[];
};

type LessonCard = {
  concept_id: string;
  concept_name: string;
  concept_name_si?: string | null;
  status: "support_now" | "watch" | "ready" | "missing_evidence";
  mastery_score?: number | null;
  confidence: number;
  priority_score: number;
  why_it_matters: string;
  study_tips: string[];
};

type LearningProfileResponse = {
  student: StudentSummary;
  subject: SubjectNode;
  summary: {
    total_concepts: number;
    support_now: number;
    watch: number;
    ready: number;
    missing_evidence: number;
  };
  lesson_cards: LessonCard[];
  recommended_quiz: {
    concept_ids: string[];
    question_count: number;
    reason: string;
  };
};

type QuizQuestionItem = {
  id: string;
  concept_id: string;
  concept_name: string;
  prompt: string;
  prompt_si?: string | null;
  options: string[];
  options_si?: string[] | null;
  difficulty: number;
};

type QuizAttemptResponse = {
  attempt_id: string;
  student_id: string;
  subject_id: string;
  concept_ids: string[];
  status: string;
  questions: QuizQuestionItem[];
};

type QuizSubmitResponse = {
  attempt_id: string;
  status: string;
  score_obtained: number;
  score_max: number;
  percentage: number;
  results: {
    question_id: string;
    concept_id: string;
    prompt: string;
    prompt_si?: string | null;
    selected_option_index?: number | null;
    correct_option_index: number;
    is_correct: boolean;
    explanation: string;
    explanation_si?: string | null;
  }[];
  updated_concepts: {
    concept_id: string;
    mastery_score: number;
    confidence: number;
    answered_question_count: number;
    mapped_question_count: number;
  }[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const DEFAULT_SUBJECT_ID = "OL-MATH";
type QuizLanguage = "en" | "si";

function displayName(item: { name: string; name_si?: string | null }) {
  return item.name_si ? `${item.name} / ${item.name_si}` : item.name;
}

function lessonDisplayName(card: LessonCard) {
  return card.concept_name_si ? `${card.concept_name} / ${card.concept_name_si}` : card.concept_name;
}

function statusLabel(status: LessonCard["status"]) {
  if (status === "support_now") {
    return "Support now";
  }
  if (status === "missing_evidence") {
    return "Needs evidence";
  }
  if (status === "ready") {
    return "Ready";
  }
  return "Watch";
}

function statusTone(status: LessonCard["status"]) {
  if (status === "support_now") {
    return "border-[rgba(217,97,61,0.2)] bg-[rgba(217,97,61,0.1)] text-accent";
  }
  if (status === "watch") {
    return "border-[rgba(225,176,75,0.28)] bg-[rgba(225,176,75,0.14)] text-[#8b640c]";
  }
  if (status === "ready") {
    return "border-[rgba(27,127,138,0.18)] bg-[rgba(27,127,138,0.1)] text-teal";
  }
  return "border-line bg-[#f8f6f1] text-muted";
}

function localizedText(english: string, sinhala: string | null | undefined, language: QuizLanguage) {
  return language === "si" && sinhala ? sinhala : english;
}

function localizedOptions(english: string[], sinhala: string[] | null | undefined, language: QuizLanguage) {
  return language === "si" && sinhala?.length === english.length ? sinhala : english;
}

export function LearningPortal({
  initialSubjectId = DEFAULT_SUBJECT_ID,
  initialStudentId = "STU-001",
}: {
  initialSubjectId?: string;
  initialStudentId?: string;
}) {
  const [subjectId, setSubjectId] = useState(initialSubjectId);
  const [studentId, setStudentId] = useState(initialStudentId);
  const [students, setStudents] = useState<StudentSummary[]>([]);
  const [subjects, setSubjects] = useState<SubjectNode[]>([]);
  const [profile, setProfile] = useState<LearningProfileResponse | null>(null);
  const [attempt, setAttempt] = useState<QuizAttemptResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [result, setResult] = useState<QuizSubmitResponse | null>(null);
  const [quizLanguage, setQuizLanguage] = useState<QuizLanguage>("en");
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [message, setMessage] = useState("Loading your learning plan...");

  async function fetchOptions(nextSubjectId: string) {
    const response = await fetch(`${API_BASE_URL}/api/options?subject_id=${nextSubjectId}`);
    if (!response.ok) {
      throw new Error("Unable to load students and subjects.");
    }
    return (await response.json()) as SelectorOptionsResponse;
  }

  async function fetchProfile(nextStudentId: string, nextSubjectId: string) {
    const response = await fetch(`${API_BASE_URL}/api/learn/student/${nextStudentId}/subject/${nextSubjectId}`);
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? "Unable to load learning profile.");
    }
    return (await response.json()) as LearningProfileResponse;
  }

  async function loadPortal(nextStudentId: string, nextSubjectId: string) {
    setStatus("loading");
    setMessage("Loading your learning plan...");
    try {
      const options = await fetchOptions(nextSubjectId);
      const resolvedSubject =
        options.subjects.find((subject) => subject.id === nextSubjectId) ?? options.subjects[0];
      const resolvedStudent =
        options.students.find((student) => student.id === nextStudentId) ?? options.students[0];
      const resolvedSubjectId = resolvedSubject?.id ?? nextSubjectId;
      const resolvedStudentId = resolvedStudent?.id ?? nextStudentId;
      setSubjects(options.subjects);
      setStudents(options.students);
      setSubjectId(resolvedSubjectId);
      setStudentId(resolvedStudentId);
      if (resolvedSubjectId === "OL-ENG") {
        setQuizLanguage("en");
      }
      setProfile(await fetchProfile(resolvedStudentId, resolvedSubjectId));
      setAttempt(null);
      setResult(null);
      setAnswers({});
      setStatus("idle");
      setMessage("Learning plan updated from your latest practice evidence.");
    } catch (error) {
      setProfile(null);
      setAttempt(null);
      setResult(null);
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Unable to load learning portal.");
    }
  }

  async function startQuiz(conceptIds?: string[]) {
    if (!profile) {
      return;
    }
    setStatus("loading");
    setMessage("Preparing your personalized quiz...");
    try {
      const response = await fetch(`${API_BASE_URL}/api/learn/quiz/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_id: studentId,
          subject_id: subjectId,
          concept_ids: conceptIds ?? profile.recommended_quiz.concept_ids,
          quiz_length: 8,
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Unable to start quiz.");
      }
      setAttempt((await response.json()) as QuizAttemptResponse);
      setResult(null);
      setAnswers({});
      setStatus("idle");
      setMessage("Answer each question, then submit to update your mastery.");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Unable to start quiz.");
    }
  }

  async function submitQuiz() {
    if (!attempt) {
      return;
    }
    setStatus("loading");
    setMessage("Checking your answers...");
    try {
      const response = await fetch(`${API_BASE_URL}/api/learn/quiz/${attempt.attempt_id}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answers: attempt.questions.map((question) => ({
            question_id: question.id,
            selected_option_index: answers[question.id] ?? null,
          })),
        }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail ?? "Unable to submit quiz.");
      }
      setResult((await response.json()) as QuizSubmitResponse);
      setProfile(await fetchProfile(studentId, subjectId));
      setStatus("idle");
      setMessage("Quiz submitted. Your learning plan now uses the updated mastery evidence.");
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Unable to submit quiz.");
    }
  }

  const loadInitialPortal = useEffectEvent(() => {
    void loadPortal(studentId, subjectId);
  });

  useEffect(() => {
    startTransition(() => {
      loadInitialPortal();
    });
  }, []);

  const canShowSinhala = subjectId !== "OL-ENG";

  return (
    <main className="flex w-full flex-1 flex-col px-4 py-5 md:px-6 xl:px-8">
      <section className="rounded-[2.4rem] border border-line bg-[linear-gradient(135deg,#132034,#20324b)] p-6 text-white shadow-[0_24px_100px_rgba(19,32,52,0.16)] md:p-8">
        <div className="grid gap-6 xl:grid-cols-[1fr_1fr] xl:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-gold">Student learning</p>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight md:text-5xl">
              Practice from the concepts that need attention.
            </h1>
            <p className="mt-4 max-w-3xl text-base leading-8 text-white/76">
              See your weak areas, revise the short lesson cards, then take a quiz that updates your mastery.
            </p>
          </div>

          <div className="rounded-[1.8rem] border border-white/10 bg-white/8 p-5 backdrop-blur">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="grid gap-3">
                <span className="font-mono text-xs uppercase tracking-[0.22em] text-white/60">Student</span>
                <select
                  className="rounded-2xl border border-white/10 bg-white/92 px-4 py-3 text-foreground outline-none"
                  value={studentId}
                  onChange={(event) => {
                    const nextStudentId = event.target.value;
                    startTransition(() => {
                      void loadPortal(nextStudentId, subjectId);
                    });
                  }}
                >
                  {students.map((student) => (
                    <option key={student.id} value={student.id}>
                      {student.full_name} · {student.cohort}
                    </option>
                  ))}
                </select>
              </label>

              <label className="grid gap-3">
                <span className="font-mono text-xs uppercase tracking-[0.22em] text-white/60">Subject</span>
                <select
                  className="rounded-2xl border border-white/10 bg-white/92 px-4 py-3 text-foreground outline-none"
                  value={subjectId}
                  onChange={(event) => {
                    const nextSubjectId = event.target.value;
                    startTransition(() => {
                      void loadPortal(studentId, nextSubjectId);
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
            </div>
            <p className="mt-4 text-sm leading-7 text-white/70">{message}</p>
          </div>
        </div>
      </section>

      <section className="mt-6 grid gap-5 xl:grid-cols-4">
        <div className="rounded-[1.8rem] border border-line bg-surface p-5">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Learner</p>
          <strong className="mt-2 block text-2xl">{profile?.student.full_name ?? "Loading"}</strong>
          <p className="mt-2 text-sm text-muted">{profile ? `${profile.student.id} · ${profile.student.cohort}` : ""}</p>
        </div>
        <div className="rounded-[1.8rem] border border-line bg-[#fff9ef] p-5">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Support now</p>
          <strong className="mt-2 block text-3xl text-accent">{profile?.summary.support_now ?? 0}</strong>
        </div>
        <div className="rounded-[1.8rem] border border-line bg-[#f4faf8] p-5">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Watch</p>
          <strong className="mt-2 block text-3xl text-[#8b640c]">{profile?.summary.watch ?? 0}</strong>
        </div>
        <div className="rounded-[1.8rem] border border-line bg-[#f5f5fb] p-5">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted">Ready</p>
          <strong className="mt-2 block text-3xl text-teal">{profile?.summary.ready ?? 0}</strong>
        </div>
      </section>

      <section className="mt-6 grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[2rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Lesson cards</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight">Revise these first</h2>
            </div>
            <button
              type="button"
              onClick={() => startTransition(() => void startQuiz())}
              disabled={!profile?.recommended_quiz.question_count || status === "loading"}
              className="rounded-full bg-foreground px-5 py-3 text-sm text-white disabled:opacity-40"
            >
              Start recommended quiz
            </button>
          </div>

          <div className="mt-5 grid gap-4">
            {profile?.lesson_cards.length ? (
              profile.lesson_cards.map((card) => (
                <article key={card.concept_id} className="rounded-[1.6rem] border border-line bg-white p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{card.concept_id}</p>
                      <h3 className="mt-2 text-2xl font-semibold tracking-tight">{lessonDisplayName(card)}</h3>
                    </div>
                    <span className={`rounded-full border px-3 py-2 font-mono text-[11px] uppercase tracking-[0.14em] ${statusTone(card.status)}`}>
                      {statusLabel(card.status)}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-7 text-muted">{card.why_it_matters}</p>
                  <div className="mt-4 grid gap-2 md:grid-cols-3">
                    {card.study_tips.map((tip) => (
                      <div key={tip} className="rounded-[1.2rem] bg-[#f8f6f1] p-3 text-sm leading-6 text-muted">
                        {tip}
                      </div>
                    ))}
                  </div>
                </article>
              ))
            ) : (
              <div className="rounded-[1.5rem] border border-dashed border-line bg-white p-5 text-sm text-muted">
                {status === "loading" ? "Loading lesson cards..." : "No lesson cards available."}
              </div>
            )}
          </div>
        </div>

        <div className="rounded-[2rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Personalized quiz</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight">Practice now</h2>
            </div>
            {canShowSinhala ? (
              <div className="inline-flex rounded-full border border-line bg-white p-1">
                {(["en", "si"] as QuizLanguage[]).map((language) => (
                  <button
                    key={language}
                    type="button"
                    onClick={() => setQuizLanguage(language)}
                    className={`rounded-full px-4 py-2 text-sm ${
                      quizLanguage === language ? "bg-foreground text-white" : "text-muted"
                    }`}
                  >
                    {language === "en" ? "English" : "සිංහල"}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
          <p className="mt-3 text-sm leading-7 text-muted">
            {profile?.recommended_quiz.reason ?? "Quiz recommendation will appear after your profile loads."}
          </p>
          <div className="mt-5 rounded-[1.5rem] bg-white p-4">
            <p className="text-sm text-muted">Recommended questions</p>
            <strong className="mt-1 block text-3xl">{profile?.recommended_quiz.question_count ?? 0}</strong>
          </div>

          {attempt ? (
            <div className="mt-5 grid gap-4">
              <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted">Attempt {attempt.attempt_id}</p>
              {attempt.questions.map((question, index) => {
                const resultItem = result?.results.find((item) => item.question_id === question.id);
                const prompt = localizedText(question.prompt, question.prompt_si, quizLanguage);
                const options = localizedOptions(question.options, question.options_si, quizLanguage);
                const explanation = resultItem
                  ? localizedText(resultItem.explanation, resultItem.explanation_si, quizLanguage)
                  : null;
                return (
                  <article key={question.id} className="rounded-[1.4rem] border border-line bg-white p-4">
                    <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">
                      Question {index + 1} · {question.concept_name}
                    </p>
                    <strong className="mt-2 block text-lg">{prompt}</strong>
                    <div className="mt-3 grid gap-2">
                      {options.map((option, optionIndex) => {
                        const selected = answers[question.id] === optionIndex;
                        const correct = resultItem?.correct_option_index === optionIndex;
                        const wrongSelected = resultItem && selected && !correct;
                        return (
                          <label
                            key={`${question.id}-${optionIndex}`}
                            className={`rounded-2xl border px-4 py-3 text-sm ${
                              correct
                                ? "border-[rgba(27,127,138,0.25)] bg-[rgba(27,127,138,0.1)]"
                                : wrongSelected
                                  ? "border-[rgba(217,97,61,0.25)] bg-[rgba(217,97,61,0.1)]"
                                  : selected
                                    ? "border-foreground bg-[#f8f6f1]"
                                    : "border-line bg-white"
                            }`}
                          >
                            <input
                              type="radio"
                              className="mr-2"
                              name={question.id}
                              disabled={!!result}
                              checked={selected}
                              onChange={() => setAnswers((current) => ({ ...current, [question.id]: optionIndex }))}
                            />
                            {option}
                          </label>
                        );
                      })}
                    </div>
                    {resultItem ? (
                      <p className="mt-3 text-sm leading-6 text-muted">{explanation}</p>
                    ) : null}
                  </article>
                );
              })}

              {!result ? (
                <button
                  type="button"
                  onClick={() => startTransition(() => void submitQuiz())}
                  className="rounded-full bg-foreground px-5 py-3 text-sm text-white"
                >
                  Submit quiz
                </button>
              ) : (
                <div className="rounded-[1.4rem] border border-line bg-white p-4">
                  <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-muted">Result</p>
                  <strong className="mt-2 block text-3xl">
                    {Math.round(result.percentage * 100)}%
                  </strong>
                  <p className="mt-2 text-sm text-muted">
                    {result.score_obtained} out of {result.score_max} marks. Updated {result.updated_concepts.length} concept score(s).
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="mt-5 rounded-[1.5rem] border border-dashed border-line bg-white p-5 text-sm text-muted">
              Start a quiz to see questions here.
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

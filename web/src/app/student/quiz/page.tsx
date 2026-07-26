"use client";

import { Check, X } from "lucide-react";
import { useState } from "react";

import {
  EmptyState,
  ErrorNote,
  Eyebrow,
  Loading,
  Panel,
  PanelHeader,
  StatTile,
  buttonClass,
  controlClass,
  primaryButtonClass,
} from "@/components/ui";
import { api } from "@/lib/api";
import { cn, percent } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/use-api";
import type {
  CurrentUser,
  LearningProfileResponse,
  QuizAttemptResponse,
  QuizSubmitResponse,
  SubjectNode,
} from "@/lib/types";

export default function QuizPage() {
  const { t, pick, locale } = useI18n();
  const { data: user } = useApi<CurrentUser>("/api/auth/me");
  const [subjectId, setSubjectId] = useState("OL-MATH");
  const [attempt, setAttempt] = useState<QuizAttemptResponse | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [result, setResult] = useState<QuizSubmitResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const subjects = useApi<SubjectNode[]>("/api/subjects");
  const profile = useApi<LearningProfileResponse>(
    user?.student_id ? `/api/learn/student/${user.student_id}/subject/${subjectId}` : null,
    [user?.student_id, subjectId],
  );

  // English is assessed in English; other subjects offer the Sinhala rendering when
  // the bank has one.
  const canShowSinhala = subjectId !== "OL-ENG" && locale === "si";

  async function start() {
    if (!user?.student_id || !profile.data) return;
    setBusy(true);
    setError(null);
    setResult(null);
    setAnswers({});
    try {
      setAttempt(
        await api.post<QuizAttemptResponse>("/api/learn/quiz/start", {
          student_id: user.student_id,
          subject_id: subjectId,
          concept_ids: profile.data.recommended_quiz.concept_ids,
          quiz_length: profile.data.recommended_quiz.question_count || 8,
        }),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (!attempt) return;
    setBusy(true);
    try {
      setResult(
        await api.post<QuizSubmitResponse>(`/api/learn/quiz/${attempt.attempt_id}/submit`, {
          answers: attempt.questions.map((question) => ({
            question_id: question.question_id,
            selected_option_index: answers[question.question_id] ?? null,
          })),
        }),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("common.error"));
    } finally {
      setBusy(false);
    }
  }

  const resultsByQuestion = new Map(result?.results.map((row) => [row.question_id, row]) ?? []);

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-[22px] font-semibold tracking-tight">{t("nav.quiz")}</h1>
        <label className="grid gap-1">
          <Eyebrow>{t("common.subject")}</Eyebrow>
          <select
            className={cn(controlClass, "min-w-[170px]")}
            value={subjectId}
            onChange={(event) => {
              setSubjectId(event.target.value);
              setAttempt(null);
              setResult(null);
            }}
          >
            {(subjects.data ?? []).map((subject) => (
              <option key={subject.id} value={subject.id}>
                {pick(subject.name, subject.name_si)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? <ErrorNote message={error} /> : null}

      {result ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <StatTile
            label={t("learn.yourScore")}
            value={`${result.score} / ${result.score_max}`}
            hint={percent(result.score / Math.max(result.score_max, 1))}
          />
          <div className="grid place-items-start">
            <button type="button" onClick={start} className={primaryButtonClass} disabled={busy}>
              {t("learn.tryAgain")}
            </button>
          </div>
        </div>
      ) : null}

      {!attempt ? (
        <Panel>
          <PanelHeader
            title={t("learn.startQuiz")}
            note={profile.data?.explanation}
          />
          <div className="p-4">
            {profile.loading ? (
              <Loading label={t("common.loading")} />
            ) : profile.data && profile.data.recommended_quiz.question_count > 0 ? (
              <button type="button" onClick={start} className={primaryButtonClass} disabled={busy}>
                {busy ? t("common.loading") : t("learn.startQuiz")}
              </button>
            ) : (
              <EmptyState>{t("learn.noQuiz")}</EmptyState>
            )}
          </div>
        </Panel>
      ) : (
        <Panel>
          <PanelHeader title={`${attempt.questions.length} questions`} />
          <ol className="grid gap-4 p-4">
            {attempt.questions.map((question, index) => {
              const outcome = resultsByQuestion.get(question.question_id);
              const options =
                canShowSinhala &&
                question.options_si &&
                question.options_si.length === question.options.length
                  ? question.options_si
                  : question.options;
              return (
                <li key={question.question_id} className="rounded-card border border-rule p-4">
                  <p className="num text-[10.5px] uppercase tracking-[0.12em] text-ink-muted">
                    {index + 1} / {attempt.questions.length} · {question.concept_name}
                  </p>
                  <p className="mt-1.5 text-[14.5px] font-medium">
                    {canShowSinhala && question.prompt_si ? question.prompt_si : question.prompt}
                  </p>

                  <fieldset className="mt-3 grid gap-1.5">
                    <legend className="sr-only">{question.prompt}</legend>
                    {options.map((option, optionIndex) => {
                      const selected = answers[question.question_id] === optionIndex;
                      const correct = outcome && outcome.correct_option_index === optionIndex;
                      const wrong = outcome && selected && !outcome.is_correct;
                      return (
                        <label
                          key={optionIndex}
                          className={cn(
                            "flex cursor-pointer items-start gap-2.5 rounded-chip border px-3 py-2 text-[13.5px] transition-colors",
                            correct && "border-indigo/40 bg-indigo-soft",
                            wrong && "border-attention/40 bg-attention-soft",
                            !outcome && selected && "border-indigo/40 bg-indigo-soft",
                            !outcome && !selected && "border-rule hover:border-rule-strong",
                            outcome && !correct && !wrong && "border-rule",
                          )}
                        >
                          <input
                            type="radio"
                            name={question.question_id}
                            checked={selected}
                            disabled={Boolean(result)}
                            onChange={() =>
                              setAnswers((current) => ({
                                ...current,
                                [question.question_id]: optionIndex,
                              }))
                            }
                            className="mt-0.5 size-3.5 shrink-0 accent-[var(--indigo)]"
                          />
                          <span className="min-w-0 flex-1">{option}</span>
                          {correct ? <Check className="size-4 shrink-0 text-indigo" aria-label="correct" /> : null}
                          {wrong ? <X className="size-4 shrink-0 text-attention" aria-label="incorrect" /> : null}
                        </label>
                      );
                    })}
                  </fieldset>

                  {outcome ? (
                    <p className="mt-2.5 border-t border-rule pt-2.5 text-[12.5px] text-ink-secondary">
                      {canShowSinhala && outcome.explanation_si
                        ? outcome.explanation_si
                        : outcome.explanation}
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ol>

          {!result ? (
            <div className="flex gap-2 border-t border-rule p-4">
              <button type="button" onClick={submit} className={primaryButtonClass} disabled={busy}>
                {busy ? t("common.loading") : t("learn.submitQuiz")}
              </button>
              <button type="button" onClick={() => setAttempt(null)} className={buttonClass}>
                {t("common.cancel")}
              </button>
            </div>
          ) : null}
        </Panel>
      )}
    </div>
  );
}

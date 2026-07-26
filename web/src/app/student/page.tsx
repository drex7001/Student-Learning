"use client";

import { BookOpen, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import {
  Chip,
  EmptyState,
  ErrorNote,
  Eyebrow,
  Loading,
  Meter,
  Panel,
  PanelHeader,
  StatTile,
  controlClass,
} from "@/components/ui";
import { cn, score, statusStyle } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/use-api";
import type { CurrentUser, LearningProfileResponse, SubjectNode } from "@/lib/types";

/**
 * The student's own view. Progress, strengths and what to practise — no risk score,
 * no band, no flag. That is enforced by the API, not just omitted here.
 */
export default function StudentProgressPage() {
  const { t, pick } = useI18n();
  const { data: user } = useApi<CurrentUser>("/api/auth/me");
  const [subjectId, setSubjectId] = useState("OL-MATH");

  const subjects = useApi<SubjectNode[]>("/api/subjects");
  const profile = useApi<LearningProfileResponse>(
    user?.student_id ? `/api/learn/student/${user.student_id}/subject/${subjectId}` : null,
    [user?.student_id, subjectId],
  );

  const strong = (profile.data?.lesson_cards ?? []).filter((card) => card.status === "ready");
  const practise = (profile.data?.lesson_cards ?? []).filter((card) => card.status !== "ready");

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">
            {t("learn.progress")}
          </h1>
          <p className="mt-1 text-[13px] text-ink-secondary">
            {user ? pick(user.display_name, user.display_name_si) : ""}
          </p>
        </div>
        <label className="grid gap-1">
          <Eyebrow>{t("common.subject")}</Eyebrow>
          <select
            className={cn(controlClass, "min-w-[170px]")}
            value={subjectId}
            onChange={(event) => setSubjectId(event.target.value)}
          >
            {(subjects.data ?? []).map((subject) => (
              <option key={subject.id} value={subject.id}>
                {pick(subject.name, subject.name_si)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Students do not see the subject-level "support" framing either — the
          summary is expressed as what is going well and what to practise. */}
      {profile.error ? (
        <ErrorNote message={profile.error} onRetry={profile.refresh} retryLabel={t("common.retry")} />
      ) : null}

      {profile.data ? (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <StatTile label={t("learn.strong")} value={strong.length} />
            <StatTile label={t("learn.practise")} value={practise.length} emphasis="watch" />
            <StatTile
              label="Practice questions ready"
              value={profile.data.recommended_quiz.question_count}
            />
          </div>

          <Panel>
            <PanelHeader
              title={t("learn.practise")}
              note={profile.data.explanation}
              action={
                <Link href="/student/quiz" className="text-[13px] text-indigo underline underline-offset-2">
                  {t("learn.startQuiz")} →
                </Link>
              }
            />
            <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">
              {practise.length === 0 ? (
                <div className="md:col-span-2 xl:col-span-3">
                  <EmptyState>Nothing needs practice in this subject right now.</EmptyState>
                </div>
              ) : (
                practise.map((card) => (
                  <article key={card.concept_id} className="rounded-card border border-rule p-3.5">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="num text-[10.5px] uppercase tracking-[0.12em] text-ink-muted">
                          {card.concept_id}
                        </p>
                        <h3 className="mt-0.5 text-[14.5px] font-semibold leading-tight">
                          {pick(card.name, card.name_si)}
                        </h3>
                      </div>
                      <Chip className={statusStyle[card.status].chip}>
                        {t(`status.${card.status}`)}
                      </Chip>
                    </div>

                    <div className="mt-3">
                      <div className="flex items-baseline justify-between">
                        <Eyebrow>Your score</Eyebrow>
                        <span className="num text-[13px] font-medium">
                          {score(card.mastery_score)}
                        </span>
                      </div>
                      <div className="mt-1.5">
                        <Meter
                          value={card.mastery_score ?? 0}
                          tone={card.status === "support_now" ? "attention" : "watch"}
                        />
                      </div>
                    </div>

                    <p className="mt-3 text-[12.5px] text-ink-secondary">{card.why_it_matters}</p>

                    {card.study_tips.length > 0 ? (
                      <ul className="mt-2.5 grid gap-1 border-t border-rule pt-2.5">
                        {card.study_tips.map((tip) => (
                          <li key={tip} className="flex gap-1.5 text-[12.5px] text-ink-secondary">
                            <Sparkles className="mt-0.5 size-3 shrink-0 text-ink-muted" aria-hidden />
                            {tip}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </article>
                ))
              )}
            </div>
          </Panel>

          {strong.length > 0 ? (
            <Panel>
              <PanelHeader
                title={
                  <span className="flex items-center gap-2">
                    <BookOpen className="size-4 text-ink-muted" aria-hidden />
                    {t("learn.strong")}
                  </span>
                }
              />
              <div className="flex flex-wrap gap-2 p-4">
                {strong.map((card) => (
                  <Chip key={card.concept_id} className="border-rule bg-sunken text-ink-secondary">
                    {pick(card.name, card.name_si)}{" "}
                    <span className="num">{score(card.mastery_score)}</span>
                  </Chip>
                ))}
              </div>
            </Panel>
          ) : null}
        </>
      ) : profile.loading ? (
        <Loading label={t("common.loading")} />
      ) : null}
    </div>
  );
}

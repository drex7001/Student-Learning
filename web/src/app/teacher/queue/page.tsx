"use client";

import Link from "next/link";
import { useState } from "react";

import {
  Chip,
  DivergingBar,
  EmptyState,
  ErrorNote,
  Eyebrow,
  Loading,
  Panel,
  PanelHeader,
  StatTile,
  Table,
  Td,
  Th,
  controlClass,
} from "@/components/ui";
import { query } from "@/lib/api";
import { cn, percent, points } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/use-api";
import type { SelectorOptionsResponse } from "@/lib/types";

type SupportListResponse = {
  subject: { id: string; name: string; name_si?: string | null };
  summary: {
    total_students: number;
    high_support: number;
    watch: number;
    stable: number;
    average_confidence: number;
  };
  students: {
    student_id: string;
    student_name: string;
    cohort: string;
    risk_score: number;
    risk_band: "high_support" | "watch" | "stable";
    confidence: number;
    top_reason: string;
    recommended_action: string;
  }[];
};

type SupportProfileResponse = {
  student: { id: string; full_name: string; cohort: string };
  risk: { score: number; band: string; confidence: number };
  explanation_method: string;
  explanation_summary: string;
  factors: {
    feature: string;
    label: string;
    impact: number;
    direction: "increases_risk" | "reduces_risk";
    explanation: string;
  }[];
  recommended_actions: string[];
};

const bandChip: Record<string, string> = {
  high_support: "bg-attention-soft text-attention border-attention/30",
  watch: "bg-watch-soft text-watch border-watch/30",
  stable: "bg-transparent text-ink-muted border-rule",
};

export default function SupportQueuePage() {
  const { t, pick } = useI18n();
  const [subjectId, setSubjectId] = useState("OL-MATH");
  const [chosenStudentId, setStudentId] = useState<string | null>(null);

  const options = useApi<SelectorOptionsResponse>(
    `/api/options${query({ subject_id: subjectId })}`,
    [subjectId],
  );
  const list = useApi<SupportListResponse>(
    `/api/support/subjects/${subjectId}/students${query({ limit: 40 })}`,
    [subjectId],
  );

  // Derived rather than stored: the top-ranked learner is the default.
  const studentId = chosenStudentId ?? list.data?.students?.[0]?.student_id ?? null;

  const profile = useApi<SupportProfileResponse>(
    studentId ? `/api/support/students/${studentId}/subjects/${subjectId}` : null,
    [studentId, subjectId],
  );

  const maxImpact = Math.max(0.01, ...(profile.data?.factors ?? []).map((f) => Math.abs(f.impact)));

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">{t("nav.queue")}</h1>
          <p className="mt-1 max-w-prose text-[13px] text-ink-secondary">
            Academic support need in one subject — a different question from the disengagement
            screen, and kept separate from it.
          </p>
        </div>
        <label className="grid gap-1">
          <Eyebrow>{t("common.subject")}</Eyebrow>
          <select
            className={cn(controlClass, "min-w-[170px]")}
            value={subjectId}
            onChange={(event) => setSubjectId(event.target.value)}
          >
            {(options.data?.subjects ?? []).map((subject) => (
              <option key={subject.id} value={subject.id}>
                {pick(subject.name, subject.name_si)}
              </option>
            ))}
          </select>
        </label>
      </div>

      {list.error ? (
        <ErrorNote message={list.error} onRetry={list.refresh} retryLabel={t("common.retry")} />
      ) : null}

      {list.data ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile label="High support" value={list.data.summary.high_support} emphasis="attention" />
            <StatTile label="Watch" value={list.data.summary.watch} emphasis="watch" />
            <StatTile label="Stable" value={list.data.summary.stable} />
            <StatTile
              label="Average confidence"
              value={percent(list.data.summary.average_confidence)}
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
            <Panel>
              <PanelHeader title={`${list.data.students.length} learners`} />
              <Table caption="Learners ranked by academic support need">
                <thead>
                  <tr>
                    <Th>{t("common.student")}</Th>
                    <Th className="w-14">{t("common.class")}</Th>
                    <Th className="w-32">Band</Th>
                    <Th>Main reason</Th>
                  </tr>
                </thead>
                <tbody>
                  {list.data.students.map((row) => (
                    <tr
                      key={row.student_id}
                      className={cn(
                        "cursor-pointer transition-colors hover:bg-sunken/60",
                        row.student_id === studentId && "bg-sunken",
                      )}
                      onClick={() => setStudentId(row.student_id)}
                    >
                      <Td className="font-medium">{row.student_name}</Td>
                      <Td className="num">{row.cohort}</Td>
                      <Td>
                        <Chip className={bandChip[row.risk_band]}>
                          {row.risk_band.replace(/_/g, " ")}
                        </Chip>
                      </Td>
                      <Td className="text-ink-secondary">{row.top_reason}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Panel>

            <Panel as="aside">
              <PanelHeader title="Why this learner" note={profile.data?.explanation_summary} />
              <div className="p-4">
                {profile.data ? (
                  <div className="grid gap-4">
                    <ul className="grid gap-2.5">
                      {profile.data.factors.slice(0, 6).map((factor) => (
                        <li key={factor.feature} className="grid gap-1.5">
                          <div className="flex items-baseline justify-between gap-3">
                            <span className="text-[13px]">{factor.label}</span>
                            <span
                              className={cn(
                                "num shrink-0 text-[12.5px]",
                                factor.direction === "increases_risk" ? "text-attention" : "text-indigo",
                              )}
                            >
                              {points(
                                factor.direction === "increases_risk"
                                  ? Math.abs(factor.impact)
                                  : -Math.abs(factor.impact),
                              )}
                            </span>
                          </div>
                          <DivergingBar
                            value={
                              factor.direction === "increases_risk"
                                ? Math.abs(factor.impact)
                                : -Math.abs(factor.impact)
                            }
                            max={maxImpact}
                            ariaLabel={factor.label}
                          />
                          <p className="text-[11.5px] text-ink-secondary">{factor.explanation}</p>
                        </li>
                      ))}
                    </ul>

                    <div className="border-t border-rule pt-3">
                      <Eyebrow>Recommended actions</Eyebrow>
                      <ul className="mt-1.5 grid gap-1.5">
                        {profile.data.recommended_actions.map((action) => (
                          <li key={action} className="text-[13px] text-ink-secondary">
                            • {action}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <Link
                      href={`/teacher/students/${profile.data.student.id}`}
                      className="text-[13px] text-indigo underline underline-offset-2"
                    >
                      {t("common.viewRecord")} →
                    </Link>
                  </div>
                ) : profile.loading ? (
                  <Loading label={t("common.loading")} />
                ) : (
                  <EmptyState>Select a learner.</EmptyState>
                )}
              </div>
            </Panel>
          </div>
        </>
      ) : list.loading ? (
        <Loading label={t("common.loading")} />
      ) : null}
    </div>
  );
}

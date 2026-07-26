"use client";

import { useState } from "react";

import { ConceptGraph, ConceptLegend } from "@/components/concept-graph";
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
import { query } from "@/lib/api";
import { cn, score, statusStyle } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/use-api";
import type {
  CurrentUser,
  SelectorOptionsResponse,
  SubjectDiagnosisMapResponse,
  SupportStatus,
} from "@/lib/types";

export default function ConceptMapPage() {
  const { t, pick } = useI18n();
  const { data: user } = useApi<CurrentUser>("/api/auth/me");
  const [subjectId, setSubjectId] = useState("OL-MATH");
  const [chosenStudentId, setStudentId] = useState<string | null>(null);
  const [conceptId, setConceptId] = useState<string | null>(null);

  const options = useApi<SelectorOptionsResponse>(
    `/api/options${query({ subject_id: subjectId })}`,
    [subjectId],
  );

  // Derived rather than stored: the first learner is the default until one is picked.
  const studentId = chosenStudentId ?? options.data?.students?.[0]?.id ?? null;

  const map = useApi<SubjectDiagnosisMapResponse>(
    studentId ? `/api/diagnosis/student/${studentId}/subject/${subjectId}/map` : null,
    [studentId, subjectId],
  );

  const selected =
    map.data?.concepts.find((concept) => concept.id === conceptId) ??
    map.data?.concepts.find((concept) => concept.id === map.data?.recommended_concept_id) ??
    null;

  const statusLabels: Record<SupportStatus, string> = {
    support_now: t("status.support_now"),
    watch: t("status.watch"),
    ready: t("status.ready"),
    missing_evidence: t("status.missing_evidence"),
  };

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">{t("nav.concepts")}</h1>
          <p className="mt-1 text-[13px] text-ink-secondary">{user?.school_name}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <label className="grid gap-1">
            <Eyebrow>{t("common.subject")}</Eyebrow>
            <select
              className={cn(controlClass, "min-w-[170px]")}
              value={subjectId}
              onChange={(event) => {
                setSubjectId(event.target.value);
                setConceptId(null);
              }}
            >
              {(options.data?.subjects ?? []).map((subject) => (
                <option key={subject.id} value={subject.id}>
                  {pick(subject.name, subject.name_si)}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-1">
            <Eyebrow>{t("common.student")}</Eyebrow>
            <select
              className={cn(controlClass, "min-w-[200px]")}
              value={studentId ?? ""}
              onChange={(event) => setStudentId(event.target.value)}
            >
              {(options.data?.students ?? []).map((student) => (
                <option key={student.id} value={student.id}>
                  {student.full_name} · {student.cohort}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {map.error ? (
        <ErrorNote message={map.error} onRetry={map.refresh} retryLabel={t("common.retry")} />
      ) : null}

      {map.data ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile
              label={t("status.support_now")}
              value={map.data.summary.support_now ?? 0}
              emphasis="attention"
            />
            <StatTile label={t("status.watch")} value={map.data.summary.watch ?? 0} emphasis="watch" />
            <StatTile label={t("status.ready")} value={map.data.summary.ready ?? 0} />
            <StatTile
              label={t("status.missing_evidence")}
              value={map.data.summary.missing_evidence ?? 0}
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,0.6fr)]">
            <Panel>
              <PanelHeader
                title={pick(map.data.subject.name, map.data.subject.name_si)}
                note={map.data.explanation}
              />
              <div className="p-4">
                <ConceptGraph
                  concepts={map.data.concepts}
                  edges={map.data.edges}
                  recommendedId={map.data.recommended_concept_id}
                  selectedId={selected?.id ?? null}
                  onSelect={setConceptId}
                />
                <div className="mt-3">
                  <ConceptLegend labels={statusLabels} />
                </div>
              </div>
            </Panel>

            <Panel as="aside">
              <PanelHeader title="Selected concept" />
              <div className="p-4">
                {selected ? (
                  <div className="grid gap-3">
                    <div>
                      <p className="num text-[11px] uppercase tracking-[0.12em] text-ink-muted">
                        {selected.id}
                      </p>
                      <h3 className="mt-0.5 text-[16px] font-semibold">
                        {pick(selected.name, selected.name_si)}
                      </h3>
                      <Chip className={cn("mt-2", statusStyle[selected.status].chip)}>
                        {statusLabels[selected.status]}
                      </Chip>
                    </div>

                    {selected.description ? (
                      <p className="text-[13px] text-ink-secondary">
                        {pick(selected.description, selected.description_si)}
                      </p>
                    ) : null}

                    <dl className="grid gap-2.5 border-t border-rule pt-3">
                      <div>
                        <Eyebrow>Mastery</Eyebrow>
                        <p className="num mt-0.5 text-[18px] font-semibold">
                          {score(selected.mastery_score)}
                        </p>
                        <div className="mt-1.5">
                          <Meter
                            value={selected.mastery_score ?? 0}
                            tone={
                              selected.status === "support_now"
                                ? "attention"
                                : selected.status === "watch"
                                  ? "watch"
                                  : "calm"
                            }
                          />
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <Eyebrow>Confidence</Eyebrow>
                          <p className="num mt-0.5 text-[14px]">{score(selected.confidence)}</p>
                        </div>
                        <div>
                          <Eyebrow>Unlocks</Eyebrow>
                          <p className="num mt-0.5 text-[14px]">{selected.downstream_impact}</p>
                        </div>
                      </div>
                    </dl>

                    <p className="border-t border-rule pt-3 text-[12.5px] text-ink-secondary">
                      {selected.evidence}
                    </p>
                  </div>
                ) : (
                  <EmptyState>Select a concept on the map.</EmptyState>
                )}
              </div>
            </Panel>
          </div>
        </>
      ) : map.loading ? (
        <Loading label={t("common.loading")} />
      ) : null}
    </div>
  );
}

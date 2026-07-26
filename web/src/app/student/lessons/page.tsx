"use client";

import { useState } from "react";

import { ConceptGraph, ConceptLegend } from "@/components/concept-graph";
import {
  ErrorNote,
  Eyebrow,
  Loading,
  Panel,
  PanelHeader,
  controlClass,
} from "@/components/ui";
import { cn } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/use-api";
import type {
  CurrentUser,
  SubjectDiagnosisMapResponse,
  SubjectNode,
  SupportStatus,
} from "@/lib/types";

/**
 * The learner's own map of a subject: what they have, what comes next, and what
 * each topic unlocks. Same renderer as the teacher's concept map, framed for the
 * person doing the learning.
 */
export default function LessonsPage() {
  const { t, pick } = useI18n();
  const { data: user } = useApi<CurrentUser>("/api/auth/me");
  const [subjectId, setSubjectId] = useState("OL-MATH");

  const subjects = useApi<SubjectNode[]>("/api/subjects");
  const map = useApi<SubjectDiagnosisMapResponse>(
    user?.student_id ? `/api/diagnosis/student/${user.student_id}/subject/${subjectId}/map` : null,
    [user?.student_id, subjectId],
  );

  const statusLabels: Record<SupportStatus, string> = {
    support_now: t("learn.practise"),
    watch: t("status.watch"),
    ready: t("learn.strong"),
    missing_evidence: t("status.missing_evidence"),
  };

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-[22px] font-semibold tracking-tight">{t("nav.myLessons")}</h1>
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

      {map.error ? (
        <ErrorNote message={map.error} onRetry={map.refresh} retryLabel={t("common.retry")} />
      ) : null}

      {map.data ? (
        <Panel>
          <PanelHeader
            title={pick(map.data.subject.name, map.data.subject.name_si)}
            note="Each topic connects to the ones it unlocks. Start where the arrows begin."
          />
          <div className="p-4">
            <ConceptGraph
              concepts={map.data.concepts}
              edges={map.data.edges}
              recommendedId={map.data.recommended_concept_id}
            />
            <div className="mt-3">
              <ConceptLegend labels={statusLabels} />
            </div>
          </div>
        </Panel>
      ) : map.loading ? (
        <Loading label={t("common.loading")} />
      ) : null}
    </div>
  );
}

"use client";

import { Building2, Wrench } from "lucide-react";
import Link from "next/link";

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
  Table,
  Td,
  Th,
} from "@/components/ui";
import { query } from "@/lib/api";
import { bandStyle, cn, percent } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/use-api";
import type {
  CurrentUser,
  RiskCaseloadResponse,
  ScreeningMatrixResponse,
  SharedFactorsResponse,
} from "@/lib/types";

export default function TeacherOverviewPage() {
  const { t, pick } = useI18n();
  const { data: user } = useApi<CurrentUser>("/api/auth/me");
  const schoolId = user?.school_id ?? null;

  const caseload = useApi<RiskCaseloadResponse>(
    schoolId ? `/api/risk/caseload${query({ school_id: schoolId })}` : null,
    [schoolId],
  );
  const shared = useApi<SharedFactorsResponse>(
    schoolId ? `/api/graph/shared-factors${query({ school_id: schoolId })}` : null,
    [schoolId],
  );
  const screening = useApi<ScreeningMatrixResponse>("/api/risk/screening-matrix");

  const summary = caseload.data?.summary;

  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">{t("nav.overview")}</h1>
        <p className="mt-1 text-[13px] text-ink-secondary">{user?.school_name}</p>
      </div>

      {caseload.error ? (
        <ErrorNote message={caseload.error} onRetry={caseload.refresh} retryLabel={t("common.retry")} />
      ) : null}

      {summary ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatTile label={t("band.needs_attention")} value={summary.needs_attention} emphasis="attention" />
          <StatTile label={t("band.watch")} value={summary.watch} emphasis="watch" />
          <StatTile label={t("band.not_marked")} value={summary.not_marked} />
          <StatTile
            label={t("risk.ahead")}
            value={summary.circumstances_ahead}
            hint={t("risk.aheadNote")}
          />
        </div>
      ) : caseload.loading ? (
        <Loading label={t("common.loading")} />
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        {/* Shared conditions — the school-level reading. */}
        <Panel>
          <PanelHeader
            title={
              <span className="flex items-center gap-2">
                <Building2 className="size-4 text-ink-muted" aria-hidden />
                {t("shared.title")}
              </span>
            }
            note={t("shared.note")}
          />
          <div className="p-4">
            {shared.data && shared.data.factors.length > 0 ? (
              <ul className="grid gap-3">
                {shared.data.factors.slice(0, 8).map((factor) => (
                  <li key={`${factor.variable}-${factor.state_label}`} className="grid gap-1.5">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="text-[13.5px] font-medium">
                        {pick(factor.label, factor.label_si)}
                        <span className="ml-2 font-normal text-ink-secondary">
                          {factor.state_label}
                        </span>
                      </span>
                      <span className="num shrink-0 text-[12.5px]">
                        {factor.affected} / {shared.data!.population} ({percent(factor.share)})
                      </span>
                    </div>
                    <Meter
                      value={factor.share}
                      tone={factor.school_level ? "attention" : "calm"}
                      ariaLabel={`${factor.label}: ${percent(factor.share)}`}
                    />
                    {factor.school_level ? (
                      <Chip className="w-fit border-attention/30 bg-attention-soft text-attention" icon={<Wrench className="size-3" aria-hidden />}>
                        {t("shared.schoolLevel")}
                      </Chip>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : shared.loading ? (
              <Loading label={t("common.loading")} />
            ) : (
              <EmptyState>No shared conditions recorded.</EmptyState>
            )}
          </div>
        </Panel>

        {/* The whole screen, in twelve numbers. */}
        <Panel>
          <PanelHeader title={t("risk.screening")} note={screening.data?.note} />
          <div className="p-4">
            {screening.data ? (
              <Table caption="Screening matrix: outcome by register pattern">
                <thead>
                  <tr>
                    <Th>Attendance</Th>
                    <Th>Engagement</Th>
                    <Th>Grade band</Th>
                    <Th className="text-right">Share</Th>
                  </tr>
                </thead>
                <tbody>
                  {screening.data.cells.map((cell, index) => (
                    <tr key={index}>
                      <Td>{cell.current_attendance}</Td>
                      <Td>{cell.school_engagement}</Td>
                      <Td className="text-ink-secondary">
                        {cell.grade_band.replace(/_/g, " ")}
                      </Td>
                      <Td className="text-right">
                        <span className="inline-flex items-center gap-2">
                          <span className="num font-medium">{percent(cell.p_high, 1)}</span>
                          <span
                            aria-hidden
                            className={cn("size-2 rounded-full", bandStyle[cell.band].bar)}
                          />
                        </span>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            ) : (
              <Loading label={t("common.loading")} />
            )}
          </div>
        </Panel>
      </div>

      {/* Top of the caseload, as a shortcut. */}
      {caseload.data ? (
        <Panel>
          <PanelHeader
            title={t("caseload.title")}
            action={
              <Link href="/teacher/caseload" className="text-[13px] text-indigo underline underline-offset-2">
                See all {caseload.data.summary.total_students}
              </Link>
            }
          />
          <Table caption="Highest-ranked learners">
            <thead>
              <tr>
                <Th>{t("common.student")}</Th>
                <Th className="w-16">{t("common.class")}</Th>
                <Th className="w-24">{t("risk.pHigh")}</Th>
                <Th>{t("risk.drivers")}</Th>
              </tr>
            </thead>
            <tbody>
              {caseload.data.students.slice(0, 8).map((row) => (
                <tr key={row.student_id} className="transition-colors hover:bg-sunken/60">
                  <Td>
                    <Link
                      href={`/teacher/students/${row.student_id}`}
                      className="font-medium hover:underline underline-offset-2"
                    >
                      {pick(row.student_name, row.student_name_si)}
                    </Link>
                  </Td>
                  <Td className="num">{row.cohort}</Td>
                  <Td className="num">{percent(row.p_high)}</Td>
                  <Td className="text-ink-secondary">{row.top_driver ?? "—"}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Panel>
      ) : null}

      <p className="text-[11.5px] text-ink-muted">
        <Eyebrow className="inline">Model</Eyebrow>{" "}
        {caseload.data?.provenance.model_variant} ·{" "}
        <span className="num">{caseload.data?.provenance.model_fingerprint}</span>
      </p>
    </div>
  );
}

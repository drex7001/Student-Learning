"use client";

import { ArrowUpRight, Search } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

import {
  Chip,
  Eyebrow,
  EmptyState,
  ErrorNote,
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
import { bandStyle, cn, percent, points } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/use-api";
import type { CurrentUser, RiskCaseloadResponse } from "@/lib/types";

type Sort = "risk" | "gap" | "name";

export default function CaseloadPage() {
  const { t, pick } = useI18n();
  const [threshold, setThreshold] = useState(0.2);
  const [sort, setSort] = useState<Sort>("risk");
  const [search, setSearch] = useState("");

  const { data: user } = useApi<CurrentUser>("/api/auth/me");
  const schoolId = user?.school_id ?? null;

  const { data, error, loading, refresh } = useApi<RiskCaseloadResponse>(
    schoolId ? `/api/risk/caseload${query({ school_id: schoolId, threshold })}` : null,
    [threshold, schoolId],
  );

  const rows = useMemo(() => {
    if (!data) return [];
    const term = search.trim().toLowerCase();
    const filtered = term
      ? data.students.filter(
          (row) =>
            row.student_name.toLowerCase().includes(term) ||
            row.cohort.toLowerCase().includes(term),
        )
      : data.students;
    const sorted = [...filtered];
    if (sort === "gap") sorted.sort((a, b) => b.gap - a.gap);
    if (sort === "name") sorted.sort((a, b) => a.student_name.localeCompare(b.student_name));
    return sorted;
  }, [data, search, sort]);

  return (
    <div className="grid gap-4">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight">{t("caseload.title")}</h1>
        {data ? (
          <p className="mt-1 max-w-prose text-[13px] text-ink-secondary">{data.basis}</p>
        ) : null}
      </div>

      {error ? <ErrorNote message={error} onRetry={refresh} retryLabel={t("common.retry")} /> : null}

      {data ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatTile
              label={t("band.needs_attention")}
              value={data.summary.needs_attention}
              emphasis="attention"
              hint={`${percent(data.summary.needs_attention / Math.max(data.summary.total_students, 1))} of ${data.summary.total_students}`}
            />
            <StatTile
              label={t("band.watch")}
              value={data.summary.watch}
              emphasis="watch"
              hint={`${percent(data.summary.watch / Math.max(data.summary.total_students, 1))} of ${data.summary.total_students}`}
            />
            <StatTile label={t("band.not_marked")} value={data.summary.not_marked} />
            <StatTile
              label={t("risk.ahead")}
              value={data.summary.circumstances_ahead}
              hint={t("risk.aheadNote")}
            />
          </div>

          {/* Filters in one row above the table. */}
          <Panel>
            <div className="grid gap-4 px-4 py-3 md:grid-cols-[minmax(0,1fr)_auto_auto] md:items-end">
              <div>
                <label htmlFor="threshold" className="block">
                  <Eyebrow>{t("caseload.threshold")}</Eyebrow>
                </label>
                <div className="mt-1.5 flex items-center gap-3">
                  <input
                    id="threshold"
                    type="range"
                    min={0.05}
                    max={0.6}
                    step={0.01}
                    value={threshold}
                    onChange={(event) => setThreshold(Number(event.target.value))}
                    className="h-1.5 w-full max-w-[280px] accent-[var(--indigo)]"
                  />
                  <span className="num w-14 shrink-0 text-[13px]">{percent(threshold)}</span>
                </div>
                <p className="mt-1.5 text-[12px] text-ink-secondary">
                  <span className="num font-medium">{data.summary.flagged_at_threshold}</span>{" "}
                  {t("caseload.flagged")} ({percent(data.summary.flagged_share, 1)})
                </p>
              </div>

              <div className="flex items-center gap-1 rounded-chip border border-rule p-0.5" role="group" aria-label="Sort">
                {(
                  [
                    ["risk", t("caseload.sortRisk")],
                    ["gap", t("caseload.sortGap")],
                    ["name", t("caseload.sortName")],
                  ] as const
                ).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setSort(value)}
                    aria-pressed={sort === value}
                    className={cn(
                      "rounded-chip px-2.5 py-1 text-[12.5px]",
                      sort === value ? "bg-indigo-soft font-medium text-indigo" : "text-ink-secondary",
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-ink-muted" aria-hidden />
                <input
                  type="search"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder={t("caseload.search")}
                  aria-label={t("caseload.search")}
                  className={cn(controlClass, "pl-8 md:w-[220px]")}
                />
              </div>
            </div>
          </Panel>

          <Panel>
            <PanelHeader
              title={`${rows.length} ${rows.length === 1 ? "learner" : "learners"}`}
              note={data.provenance.caveat}
            />
            {rows.length === 0 ? (
              <div className="p-4">
                <EmptyState>{t("caseload.empty")}</EmptyState>
              </div>
            ) : (
              <Table caption="Learners ranked by disengagement screen result">
                <thead>
                  <tr>
                    <Th className="w-10">#</Th>
                    <Th>{t("common.student")}</Th>
                    <Th className="w-16">{t("common.class")}</Th>
                    <Th className="w-32">{t("risk.pHigh")}</Th>
                    <Th className="w-40">Band</Th>
                    <Th>{t("risk.drivers")}</Th>
                    <Th className="w-24 text-right">{t("caseload.sortGap")}</Th>
                    <Th className="w-10"><span className="sr-only">{t("common.viewRecord")}</span></Th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, index) => (
                    <tr key={row.student_id} className="transition-colors hover:bg-sunken/60">
                      <Td className="num text-ink-muted">{index + 1}</Td>
                      <Td>
                        <Link
                          href={`/teacher/students/${row.student_id}`}
                          className="font-medium hover:underline underline-offset-2"
                        >
                          {pick(row.student_name, row.student_name_si)}
                        </Link>
                        <span className="num block text-[11.5px] text-ink-muted">{row.student_id}</span>
                      </Td>
                      <Td className="num">{row.cohort}</Td>
                      <Td>
                        <div className="flex items-center gap-2">
                          <span className="num w-11 shrink-0 font-medium">{percent(row.p_high)}</span>
                          <div className="h-1.5 w-full max-w-[70px] overflow-hidden rounded-full bg-sunken">
                            <div
                              className={cn("h-full rounded-full", bandStyle[row.band].bar)}
                              style={{ width: `${row.p_high * 100}%` }}
                            />
                          </div>
                        </div>
                      </Td>
                      <Td>
                        <Chip className={bandStyle[row.band].chip}>{t(`band.${row.band}`)}</Chip>
                        {row.circumstances_ahead ? (
                          <Chip className="ml-1 border-watch/30 bg-watch-soft text-watch">
                            {t("risk.ahead")}
                          </Chip>
                        ) : null}
                      </Td>
                      <Td className="text-ink-secondary">{row.top_driver ?? "—"}</Td>
                      <Td className="num text-right text-ink-secondary">{points(row.gap)}</Td>
                      <Td>
                        <Link
                          href={`/teacher/students/${row.student_id}`}
                          aria-label={`${t("common.viewRecord")}: ${row.student_name}`}
                          className="inline-flex text-ink-muted hover:text-ink"
                        >
                          <ArrowUpRight className="size-4" aria-hidden />
                        </Link>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </Panel>
        </>
      ) : loading ? (
        <Loading label={t("common.loading")} />
      ) : null}
    </div>
  );
}

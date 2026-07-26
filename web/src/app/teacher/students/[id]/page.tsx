"use client";

/**
 * The record screen, in action-first order.
 *
 * 1  header         — the figure, framed as a share of a cohort, with its basis
 * 2  what's behind  — observational contrasts
 * 3  what would help— true do() interventions, with a joint plan
 * 4  what to ask    — value of information
 * 5  how it reaches — the causal routes, from the graph
 * 6  the record     — every field, editable, "not recorded" always available
 * 7  not a lever    — protected characteristics, with a live refusal
 */

import { AlertTriangle, Check, Lock, ShieldAlert } from "lucide-react";
import { use, useMemo, useState } from "react";

import { CausalGraph } from "@/components/risk/causal-graph";
import {
  Chip,
  DivergingBar,
  EmptyState,
  ErrorNote,
  Eyebrow,
  Loading,
  Meter,
  Panel,
  PanelHeader,
  buttonClass,
  controlClass,
} from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { bandStyle, cn, percent, points, relativeDate } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/use-api";
import type {
  CausalPathsResponse,
  PlanResponse,
  RiskProfileResponse,
} from "@/lib/types";

export default function StudentRecordPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { t, pick } = useI18n();

  const { data, error, loading, refresh } = useApi<RiskProfileResponse>(`/api/risk/students/${id}`);
  const [selectedFactor, setSelectedFactor] = useState<string | null>(null);
  const [planned, setPlanned] = useState<string[]>([]);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [refusal, setRefusal] = useState<string | null>(null);
  const [savingField, setSavingField] = useState<string | null>(null);
  const [savedField, setSavedField] = useState<string | null>(null);

  const routeFactor = selectedFactor ?? data?.drivers[0]?.variable ?? null;
  const { data: routes } = useApi<CausalPathsResponse>(
    routeFactor ? `/api/graph/students/${id}/causal-paths/${routeFactor}` : null,
    [routeFactor],
  );

  const maxDriver = useMemo(
    () => Math.max(0.01, ...(data?.drivers ?? []).map((row) => Math.abs(row.delta))),
    [data],
  );
  const maxAction = useMemo(
    () => Math.max(0.01, ...(data?.actions ?? []).map((row) => Math.abs(row.delta))),
    [data],
  );

  async function togglePlanned(variable: string) {
    const next = planned.includes(variable)
      ? planned.filter((item) => item !== variable)
      : [...planned, variable];
    setPlanned(next);
    if (next.length === 0) {
      setPlan(null);
      return;
    }
    try {
      setPlan(await api.post<PlanResponse>(`/api/risk/students/${id}/plan`, { variables: next }));
    } catch (caught) {
      setPlan(null);
      if (caught instanceof ApiError && caught.isRefusal) setRefusal(caught.message);
    }
  }

  /** Deliberately invokes the engine so the refusal is shown, not described. */
  async function askForbidden(variable: string) {
    setRefusal(null);
    try {
      await api.post(`/api/risk/students/${id}/what-if`, {
        intervention: { [variable]: "Typical" },
      });
      setRefusal("The model answered — the guardrail did not fire. This is a defect.");
    } catch (caught) {
      setRefusal(caught instanceof Error ? caught.message : t("common.error"));
    }
  }

  async function updateEvidence(variable: string, state: string | null) {
    setSavingField(variable);
    setSavedField(null);
    try {
      await api.put(`/api/risk/students/${id}/evidence`, {
        updates: [{ variable, state }],
      });
      setSavedField(variable);
      setPlan(null);
      setPlanned([]);
      refresh();
    } finally {
      setSavingField(null);
    }
  }

  if (loading && !data) return <Loading label={t("common.loading")} />;
  if (error) return <ErrorNote message={error} onRetry={refresh} retryLabel={t("common.retry")} />;
  if (!data) return null;

  const { student, posterior, gap_detail: gap } = data;

  return (
    <div className="grid gap-4">
      {/* 1 — header ---------------------------------------------------- */}
      <Panel className="overflow-hidden">
        <div className="grid gap-5 p-4 lg:grid-cols-[minmax(0,320px)_minmax(0,1fr)] lg:p-5">
          <div>
            <Eyebrow>{t("common.student")}</Eyebrow>
            <h1 className="mt-1 text-[24px] font-semibold leading-tight tracking-tight">
              {pick(student.student_name, student.student_name_si)}
            </h1>
            <p className="num mt-0.5 text-[12.5px] text-ink-muted">
              {student.student_id} · {student.cohort}
            </p>

            <div className="mt-4 flex flex-wrap items-center gap-1.5">
              <Chip className={bandStyle[student.band].chip}>{t(`band.${student.band}`)}</Chip>
              {student.circumstances_ahead ? (
                <Chip className="border-watch/30 bg-watch-soft text-watch" icon={<AlertTriangle className="size-3" aria-hidden />}>
                  {t("risk.ahead")}
                </Chip>
              ) : null}
            </div>

            <p className="num mt-4 text-[44px] font-semibold leading-none">
              {percent(student.p_high, 1)}
            </p>
            <p className="mt-1 text-[12.5px] text-ink-secondary">{t("risk.pHigh")}</p>
          </div>

          <div className="min-w-0">
            {/* Stacked posterior. 2px surface gap between segments. */}
            <Eyebrow>Distribution</Eyebrow>
            <div className="mt-2 flex h-7 gap-[2px] overflow-hidden rounded-chip">
              {posterior.map((bar) => (
                <div
                  key={bar.state}
                  title={`${bar.label}: ${percent(bar.probability, 1)}`}
                  style={{ width: `${Math.max(bar.probability * 100, 1.5)}%` }}
                  className={cn(
                    "grid place-items-center text-[10.5px] font-medium",
                    bar.state === "High" && "bg-attention text-white",
                    bar.state === "Medium" && "bg-watch text-white",
                    bar.state === "Low" && "bg-sunken text-ink-secondary",
                  )}
                >
                  {bar.probability > 0.12 ? percent(bar.probability) : ""}
                </div>
              ))}
            </div>
            <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11.5px] text-ink-secondary">
              {posterior.map((bar) => (
                <li key={bar.state} className="flex items-center gap-1.5">
                  <span
                    aria-hidden
                    className={cn(
                      "size-2 rounded-full",
                      bar.state === "High" && "bg-attention",
                      bar.state === "Medium" && "bg-watch",
                      bar.state === "Low" && "bg-calm",
                    )}
                  />
                  {pick(bar.label, bar.label_si)}{" "}
                  <span className="num">{percent(bar.probability, 1)}</span>
                </li>
              ))}
            </ul>

            <div className="mt-4 border-t border-rule pt-3">
              <Eyebrow>{t("risk.basis")}</Eyebrow>
              <p className="mt-1 max-w-prose text-[13px] text-ink-secondary">{data.basis}</p>
            </div>

            {gap.ahead ? (
              <div className="mt-3 rounded-card border border-watch/30 bg-watch-soft px-3 py-2 text-[12.5px] text-watch">
                {t("risk.aheadNote")} Register <span className="num">{percent(gap.register_p_high)}</span> ·
                circumstances <span className="num">{percent(gap.circumstance_p_high)}</span>.
              </div>
            ) : null}
          </div>
        </div>

        <p className="border-t border-rule bg-sunken px-4 py-2 text-[11.5px] text-ink-muted">
          {data.provenance.caveat} · {data.provenance.provenance}
        </p>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-2">
        {/* 2 — what's behind it ---------------------------------------- */}
        <Panel>
          <PanelHeader title={t("risk.drivers")} note={t("risk.driversNote")} />
          <div className="p-4">
            {data.drivers.length === 0 ? (
              <EmptyState>Nothing recorded is pushing this figure up.</EmptyState>
            ) : (
              <ul className="grid gap-3">
                {data.drivers.map((row) => (
                  <li key={row.variable}>
                    <button
                      type="button"
                      onClick={() => setSelectedFactor(row.variable)}
                      className={cn(
                        "w-full rounded-chip px-2 py-1.5 text-left transition-colors hover:bg-sunken",
                        routeFactor === row.variable && "bg-sunken",
                      )}
                      aria-pressed={routeFactor === row.variable}
                    >
                      <div className="flex items-baseline justify-between gap-3">
                        <span className="text-[13.5px] font-medium">
                          {pick(row.label, row.label_si)}
                        </span>
                        <span className="num shrink-0 text-[12.5px] text-attention">
                          {points(row.delta)}
                        </span>
                      </div>
                      <p className="mb-1.5 text-[12px] text-ink-secondary">
                        {pick(row.state_label, row.state_label_si)}
                      </p>
                      <DivergingBar
                        value={row.delta}
                        max={maxDriver}
                        ariaLabel={`${row.label}: ${points(row.delta)}`}
                      />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Panel>

        {/* 3 — what would help ----------------------------------------- */}
        <Panel>
          <PanelHeader
            title={t("risk.actions")}
            note={t("risk.actionsNote")}
            action={
              plan ? (
                <div className="rounded-chip border border-indigo/30 bg-indigo-soft px-2.5 py-1 text-right">
                  <p className="num text-[13px] font-semibold text-indigo">
                    {points(plan.joint_delta)}
                  </p>
                  <p className="text-[10.5px] text-ink-secondary">{t("risk.jointEffect")}</p>
                </div>
              ) : null
            }
          />
          <div className="p-4">
            {data.actions.length === 0 ? (
              <EmptyState>No modifiable factor is recorded as needing action.</EmptyState>
            ) : (
              <ul className="grid gap-2.5">
                {data.actions.map((row) => {
                  const checked = planned.includes(row.variable);
                  return (
                    <li key={row.variable}>
                      <label
                        className={cn(
                          "grid cursor-pointer gap-1.5 rounded-card border p-3 transition-colors",
                          checked ? "border-indigo/40 bg-indigo-soft" : "border-rule hover:border-rule-strong",
                        )}
                      >
                        <div className="flex items-start gap-2.5">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => togglePlanned(row.variable)}
                            className="mt-0.5 size-4 shrink-0 accent-[var(--indigo)]"
                          />
                          <div className="min-w-0 flex-1">
                            <div className="flex items-baseline justify-between gap-3">
                              <span className="text-[13.5px] font-medium">
                                {pick(row.action, row.action_si)}
                              </span>
                              <span className="num shrink-0 text-[12.5px] font-medium text-indigo">
                                {points(row.delta)}
                              </span>
                            </div>
                            <p className="mt-0.5 text-[11.5px] uppercase tracking-[0.1em] text-ink-muted">
                              {row.owner}
                            </p>
                            {row.detail ? (
                              <p className="mt-1 text-[12.5px] text-ink-secondary">{row.detail}</p>
                            ) : null}
                            {row.caveat ? (
                              <p className="mt-1 border-l-2 border-watch/40 pl-2 text-[12px] text-watch">
                                {row.caveat}
                              </p>
                            ) : null}
                            <div className="mt-2">
                              <Meter value={Math.abs(row.delta) / maxAction} tone="indigo" />
                            </div>
                          </div>
                        </div>
                      </label>
                    </li>
                  );
                })}
              </ul>
            )}

            {plan ? (
              <div className="mt-3 rounded-card border border-rule bg-sunken px-3 py-2.5 text-[12.5px]">
                <div className="flex justify-between gap-3">
                  <span className="text-ink-secondary">{t("risk.jointEffect")}</span>
                  <span className="num font-medium">{points(plan.joint_delta)}</span>
                </div>
                <div className="mt-1 flex justify-between gap-3">
                  <span className="text-ink-secondary">{t("risk.sumOfParts")}</span>
                  <span className="num">{points(plan.sum_of_parts)}</span>
                </div>
                <p className="mt-2 text-[11.5px] text-ink-muted">{plan.note}</p>
              </div>
            ) : null}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
        {/* 4 — what to find out next ----------------------------------- */}
        <Panel>
          <PanelHeader title={t("risk.asking")} note={t("risk.askingNote")} />
          <div className="p-4">
            {data.worth_asking.length === 0 ? (
              <EmptyState>Everything recordable has been recorded.</EmptyState>
            ) : (
              <ul className="grid gap-2.5">
                {data.worth_asking.map((row) => (
                  <li key={row.variable} className="grid gap-1.5">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-[13.5px]">{pick(row.label, row.label_si)}</span>
                      <span className="num shrink-0 text-[12.5px] text-ink-secondary">
                        ±{points(row.delta).replace("+", "")}
                      </span>
                    </div>
                    <Meter value={row.delta / Math.max(...data.worth_asking.map((r) => r.delta), 0.01)} tone="calm" />
                    <span className="text-[11px] uppercase tracking-[0.1em] text-ink-muted">
                      {row.causal ? "causal contrast" : "observational"}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Panel>

        {/* 5 — how it reaches the outcome ------------------------------- */}
        <Panel>
          <PanelHeader
            title={t("risk.routes")}
            note={routes?.note}
            action={
              <select
                className={cn(controlClass, "w-auto py-1 text-[12.5px]")}
                value={routeFactor ?? ""}
                onChange={(event) => setSelectedFactor(event.target.value)}
                aria-label={t("risk.routes")}
              >
                {data.drivers.map((row) => (
                  <option key={row.variable} value={row.variable}>
                    {row.label}
                  </option>
                ))}
                {data.locked_factors.map((factor) => (
                  <option key={factor.id} value={factor.id}>
                    {factor.label}
                  </option>
                ))}
              </select>
            }
          />
          <div className="p-4">
            {routes && routes.paths.length > 0 ? (
              <>
                <CausalGraph data={routes} />
                <p className="mt-2 text-[12px] text-ink-secondary">
                  <span className="num">{routes.path_count}</span> route
                  {routes.path_count === 1 ? "" : "s"} from{" "}
                  <span className="font-medium">{routes.label}</span> to the outcome.
                </p>
              </>
            ) : (
              <EmptyState>Select a factor to see how it reaches the outcome.</EmptyState>
            )}
          </div>
        </Panel>
      </div>

      {/* 6 — the record ------------------------------------------------ */}
      <Panel>
        <PanelHeader
          title={t("risk.evidence")}
          note="Changing a field recomputes the whole screen. Clearing it is a real answer, not a gap."
        />
        <div className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-3">
          {data.evidence.map((item) => {
            const factor = [...data.locked_factors].find((f) => f.id === item.variable);
            return (
              <div key={item.variable} className="rounded-card border border-rule p-3">
                <div className="flex items-start justify-between gap-2">
                  <Eyebrow>{pick(item.label, item.label_si)}</Eyebrow>
                  {item.concern ? (
                    <span className="size-1.5 shrink-0 rounded-full bg-attention" aria-label="concern" />
                  ) : null}
                </div>
                <select
                  className={cn(controlClass, "mt-1.5 py-1.5 text-[13px]")}
                  value={item.state ?? ""}
                  disabled={savingField === item.variable}
                  onChange={(event) => updateEvidence(item.variable, event.target.value || null)}
                  aria-label={item.label}
                >
                  <option value="">{t("risk.notRecorded")}</option>
                  {(factor?.states ?? []).map((state) => (
                    <option key={state.value} value={state.value}>
                      {state.label}
                    </option>
                  ))}
                  {!factor && item.state ? (
                    <option value={item.state}>{item.state_label}</option>
                  ) : null}
                </select>
                <p className="mt-1.5 flex items-center gap-1.5 text-[11px] text-ink-muted">
                  {savedField === item.variable ? (
                    <>
                      <Check className="size-3 text-indigo" aria-hidden /> {t("common.saved")}
                    </>
                  ) : (
                    <>
                      {item.source ?? "—"}
                      {item.recorded_at ? ` · ${relativeDate(item.recorded_at)}` : ""}
                    </>
                  )}
                </p>
              </div>
            );
          })}
        </div>
      </Panel>

      {/* 7 — not a lever ----------------------------------------------- */}
      <Panel>
        <PanelHeader
          title={
            <span className="flex items-center gap-2">
              <Lock className="size-4 text-ink-muted" aria-hidden />
              {t("risk.locked")}
            </span>
          }
          note={t("risk.lockedNote")}
        />
        <div className="grid gap-3 p-4 md:grid-cols-2">
          {data.locked_factors.map((factor) => (
            <div key={factor.id} className="rounded-card border border-dashed border-rule p-3">
              <p className="text-[13.5px] font-medium">{pick(factor.label, factor.label_si)}</p>
              {factor.why_not_actionable ? (
                <p className="mt-1 text-[12.5px] text-ink-secondary">{factor.why_not_actionable}</p>
              ) : null}
              <button
                type="button"
                onClick={() => askForbidden(factor.id)}
                className={cn(buttonClass, "mt-2.5 text-[12px]")}
              >
                <ShieldAlert className="size-3.5" aria-hidden />
                Ask what would change if this were different
              </button>
            </div>
          ))}
        </div>
        {refusal ? (
          <div className="border-t border-rule bg-attention-soft px-4 py-3">
            <p className="flex items-start gap-2 text-[12.5px] text-attention">
              <ShieldAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
              <span>{refusal}</span>
            </p>
          </div>
        ) : null}
      </Panel>

      {/* attendance ---------------------------------------------------- */}
      {data.attendance.length > 0 ? (
        <Panel>
          <PanelHeader title="Attendance" />
          <div className="grid gap-3 p-4 sm:grid-cols-2">
            {data.attendance.map((row) => (
              <div key={row.term_id} className="rounded-card border border-rule p-3">
                <Eyebrow>{row.term_label}</Eyebrow>
                <p className="num mt-1 text-[20px] font-semibold">{percent(row.rate)}</p>
                <p className="text-[12px] text-ink-secondary">
                  <span className="num">{row.days_present}</span> {t("common.of")}{" "}
                  <span className="num">{row.days_total}</span> days ·{" "}
                  <span className="num">{row.max_consecutive_absences}</span> consecutive absent
                </p>
                <div className="mt-2">
                  <Meter value={row.rate} tone={row.rate < 0.8 ? "attention" : "calm"} />
                </div>
              </div>
            ))}
          </div>
        </Panel>
      ) : null}
    </div>
  );
}

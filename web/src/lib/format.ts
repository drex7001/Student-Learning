import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import type { RiskBand, SupportStatus } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Percentages of the cohort, not probabilities about a person. */
export function percent(value: number | null | undefined, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

/** Signed change in percentage points — the unit an action is discussed in. */
export function points(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const scaled = value * 100;
  const sign = scaled > 0 ? "+" : scaled < 0 ? "−" : "";
  return `${sign}${Math.abs(scaled).toFixed(digits)} pp`;
}

export function score(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value * 100)}%`;
}

/**
 * Band styling. Only two states carry a hue; "not marked" is deliberately a
 * non-colour, because nothing here marks a student as good.
 */
export const bandStyle: Record<RiskBand, { chip: string; bar: string; rule: string }> = {
  needs_attention: {
    chip: "bg-attention-soft text-attention border-attention/30",
    bar: "bg-attention",
    rule: "border-l-attention",
  },
  watch: {
    chip: "bg-watch-soft text-watch border-watch/30",
    bar: "bg-watch",
    rule: "border-l-watch",
  },
  not_marked: {
    chip: "bg-transparent text-ink-muted border-rule",
    bar: "bg-calm",
    rule: "border-l-rule-strong",
  },
};

export const statusStyle: Record<SupportStatus, { chip: string; dot: string }> = {
  support_now: { chip: "bg-attention-soft text-attention border-attention/30", dot: "bg-attention" },
  watch: { chip: "bg-watch-soft text-watch border-watch/30", dot: "bg-watch" },
  ready: { chip: "bg-transparent text-ink-muted border-rule", dot: "bg-calm" },
  missing_evidence: { chip: "bg-transparent text-ink-muted border-dashed border-rule", dot: "bg-transparent border border-rule-strong" },
};

export function relativeDate(iso: string | null | undefined) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

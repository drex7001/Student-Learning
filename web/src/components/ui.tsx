"use client";

/**
 * The register's vocabulary: ruled panels, hairlines, tabular figures, restrained
 * marks. Every piece here is plain HTML with tokens — no component library, so the
 * design language stays legible in the markup.
 */

import { AlertTriangle, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/format";

export function Panel({
  children,
  className,
  as: Tag = "section",
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "aside" | "article";
}) {
  return (
    <Tag
      className={cn(
        "rounded-card border border-rule bg-surface",
        className,
      )}
    >
      {children}
    </Tag>
  );
}

export function PanelHeader({
  title,
  note,
  action,
  className,
}: {
  title: ReactNode;
  note?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <header
      className={cn(
        "flex flex-wrap items-start justify-between gap-3 border-b border-rule px-4 py-3",
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="text-[15px] font-semibold tracking-tight">{title}</h2>
        {note ? <p className="mt-1 max-w-prose text-[13px] text-ink-secondary">{note}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </header>
  );
}

/**
 * Small uppercase label above a figure or field. A `span` rather than a `p` so it
 * stays valid wherever it is used — including inline inside a paragraph.
 */
export function Eyebrow({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "block text-[10.5px] font-medium uppercase tracking-[0.14em] text-ink-muted",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Chip({
  children,
  className,
  icon,
}: {
  children: ReactNode;
  className?: string;
  icon?: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-chip border px-2 py-0.5 text-[12px] font-medium",
        className,
      )}
    >
      {icon}
      {children}
    </span>
  );
}

export function StatTile({
  label,
  value,
  hint,
  emphasis,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  emphasis?: "attention" | "watch" | "none";
}) {
  return (
    <div className="rounded-card border border-rule bg-surface px-4 py-3">
      <Eyebrow>{label}</Eyebrow>
      <p
        className={cn(
          "num mt-1 text-[26px] leading-none font-semibold",
          emphasis === "attention" && "text-attention",
          emphasis === "watch" && "text-watch",
        )}
      >
        {value}
      </p>
      {hint ? <p className="mt-1.5 text-[12px] text-ink-secondary">{hint}</p> : null}
    </div>
  );
}

/**
 * A horizontal magnitude bar. 4px rounded data-end anchored to the baseline; the
 * track is a sunken surface, not a second colour.
 */
export function Meter({
  value,
  tone = "attention",
  className,
  ariaLabel,
}: {
  value: number;
  tone?: "attention" | "watch" | "calm" | "indigo";
  className?: string;
  ariaLabel?: string;
}) {
  const width = Math.max(0, Math.min(1, Math.abs(value))) * 100;
  const toneClass =
    tone === "attention"
      ? "bg-attention"
      : tone === "watch"
        ? "bg-watch"
        : tone === "indigo"
          ? "bg-indigo"
          : "bg-calm";
  return (
    <div
      className={cn("h-1.5 w-full overflow-hidden rounded-full bg-sunken", className)}
      role="img"
      aria-label={ariaLabel}
    >
      <div className={cn("h-full rounded-full", toneClass)} style={{ width: `${width}%` }} />
    </div>
  );
}

/** Diverging bar for signed contributions, with a centre baseline. */
export function DivergingBar({
  value,
  max,
  ariaLabel,
}: {
  value: number;
  max: number;
  ariaLabel?: string;
}) {
  const scale = max > 0 ? Math.min(1, Math.abs(value) / max) : 0;
  const width = scale * 50;
  const positive = value >= 0;
  return (
    <div className="relative h-2 w-full rounded-full bg-sunken" role="img" aria-label={ariaLabel}>
      <span className="absolute inset-y-0 left-1/2 w-px -translate-x-1/2 bg-rule-strong" />
      <span
        className={cn(
          "absolute inset-y-0 rounded-full",
          positive ? "bg-attention" : "bg-indigo",
        )}
        style={
          positive
            ? { left: "50%", width: `${width}%` }
            : { right: "50%", width: `${width}%` }
        }
      />
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-card border border-dashed border-rule px-4 py-8 text-center text-[13px] text-ink-secondary">
      {children}
    </div>
  );
}

export function Loading({ label }: { label: string }) {
  return (
    <div
      className="flex items-center justify-center gap-2 px-4 py-10 text-[13px] text-ink-secondary"
      role="status"
      aria-live="polite"
    >
      <Loader2 className="size-4 animate-spin" aria-hidden />
      {label}
    </div>
  );
}

export function ErrorNote({ message, onRetry, retryLabel }: { message: string; onRetry?: () => void; retryLabel?: string }) {
  return (
    <div
      className="flex flex-wrap items-center gap-3 rounded-card border border-attention/30 bg-attention-soft px-4 py-3 text-[13px] text-attention"
      role="alert"
      aria-live="assertive"
    >
      <AlertTriangle className="size-4 shrink-0" aria-hidden />
      <span className="min-w-0 flex-1">{message}</span>
      {onRetry ? (
        <button type="button" onClick={onRetry} className="underline underline-offset-2">
          {retryLabel ?? "Try again"}
        </button>
      ) : null}
    </div>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="grid gap-1.5">
      <Eyebrow>{label}</Eyebrow>
      {children}
      {hint ? <span className="text-[12px] text-ink-secondary">{hint}</span> : null}
    </label>
  );
}

export const controlClass =
  "w-full rounded-chip border border-rule bg-raised px-3 py-2 text-[14px] transition-colors hover:border-rule-strong";

export const buttonClass =
  "inline-flex items-center justify-center gap-2 rounded-chip border border-rule bg-raised px-3 py-2 text-[13px] font-medium transition-colors hover:border-rule-strong disabled:opacity-50";

export const primaryButtonClass =
  "inline-flex items-center justify-center gap-2 rounded-chip border border-indigo bg-indigo px-4 py-2 text-[13px] font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50";

/** Data tables get real table semantics; the old div-grid "tables" did not. */
export function Table({ children, caption }: { children: ReactNode; caption?: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-[13px]">
        {caption ? <caption className="sr-only">{caption}</caption> : null}
        {children}
      </table>
    </div>
  );
}

export function Th({
  children,
  className,
  scope = "col",
  ...rest
}: React.ThHTMLAttributes<HTMLTableCellElement> & { scope?: "col" | "row" }) {
  return (
    <th
      scope={scope}
      className={cn(
        "border-b border-rule px-3 py-2 text-[10.5px] font-medium uppercase tracking-[0.12em] text-ink-muted",
        className,
      )}
      {...rest}
    >
      {children}
    </th>
  );
}

export function Td({ children, className, ...rest }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cn("border-b border-rule px-3 py-2 align-middle", className)} {...rest}>
      {children}
    </td>
  );
}

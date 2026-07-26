"use client";

import { Users } from "lucide-react";
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
  Table,
  Td,
  Th,
  controlClass,
} from "@/components/ui";
import { query } from "@/lib/api";
import { bandStyle, cn, percent } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/use-api";
import type { CurrentUser, PeerNetworkResponse, SharedFactorsResponse } from "@/lib/types";

type ClassRow = {
  id: string;
  school_id: string;
  grade: number;
  section: string;
  label: string;
  medium: string;
};

export default function ClassesPage() {
  const { t, pick } = useI18n();
  const { data: user } = useApi<CurrentUser>("/api/auth/me");
  const schoolId = user?.school_id ?? null;

  const classes = useApi<ClassRow[]>(
    schoolId ? `/api/school/classes${query({ school_id: schoolId })}` : null,
    [schoolId],
  );
  // Derived rather than stored: the first class is the default until one is picked.
  const [chosenClassId, setClassId] = useState<string | null>(null);
  const classId = chosenClassId ?? classes.data?.[0]?.id ?? null;

  const peers = useApi<PeerNetworkResponse>(
    classId ? `/api/graph/classes/${classId}/peers` : null,
    [classId],
  );
  const shared = useApi<SharedFactorsResponse>(
    classId ? `/api/graph/shared-factors${query({ class_id: classId })}` : null,
    [classId],
  );

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">{t("nav.classes")}</h1>
          <p className="mt-1 text-[13px] text-ink-secondary">{user?.school_name}</p>
        </div>
        <label className="grid gap-1">
          <Eyebrow>{t("common.class")}</Eyebrow>
          <select
            className={cn(controlClass, "min-w-[160px]")}
            value={classId ?? ""}
            onChange={(event) => setClassId(event.target.value)}
          >
            {(classes.data ?? []).map((row) => (
              <option key={row.id} value={row.id}>
                {row.label} · {row.medium}
              </option>
            ))}
          </select>
        </label>
      </div>

      {peers.error ? (
        <ErrorNote message={peers.error} onRetry={peers.refresh} retryLabel={t("common.retry")} />
      ) : null}

      {peers.data ? (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <StatTile label="Learners" value={peers.data.summary.students} />
            <StatTile label={`Average ${t("peers.ties")}`} value={peers.data.summary.average_ties} />
            <StatTile
              label={t("peers.fewTies")}
              value={peers.data.summary.few_ties}
              emphasis={peers.data.summary.few_ties > 0 ? "watch" : "none"}
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.85fr)]">
            <Panel>
              <PanelHeader
                title={
                  <span className="flex items-center gap-2">
                    <Users className="size-4 text-ink-muted" aria-hidden />
                    {t("peers.title")}
                  </span>
                }
                note={peers.data.note}
              />
              <Table caption="Peer connections within the class">
                <thead>
                  <tr>
                    <Th>{t("common.student")}</Th>
                    <Th className="w-40">{t("peers.ties")}</Th>
                    <Th className="w-36">Band</Th>
                  </tr>
                </thead>
                <tbody>
                  {peers.data.nodes.map((node) => {
                    const maxTies = Math.max(...peers.data!.nodes.map((n) => n.ties), 1);
                    return (
                      <tr key={node.id} className="transition-colors hover:bg-sunken/60">
                        <Td>
                          <Link
                            href={`/teacher/students/${node.id}`}
                            className="hover:underline underline-offset-2"
                          >
                            {node.name}
                          </Link>
                        </Td>
                        <Td>
                          <div className="flex items-center gap-2">
                            <span className="num w-5 shrink-0">{node.ties}</span>
                            <Meter
                              value={node.ties / maxTies}
                              tone={node.ties <= 1 ? "watch" : "calm"}
                              className="max-w-[90px]"
                            />
                          </div>
                        </Td>
                        <Td>
                          {node.risk_band ? (
                            <Chip className={bandStyle[node.risk_band].chip}>
                              {t(`band.${node.risk_band}`)}
                            </Chip>
                          ) : (
                            <span className="text-ink-muted">—</span>
                          )}
                        </Td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            </Panel>

            <Panel>
              <PanelHeader title={t("shared.title")} note={t("shared.note")} />
              <div className="p-4">
                {shared.data && shared.data.factors.length > 0 ? (
                  <ul className="grid gap-3">
                    {shared.data.factors.slice(0, 10).map((factor) => (
                      <li key={`${factor.variable}-${factor.state_label}`} className="grid gap-1.5">
                        <div className="flex flex-wrap items-baseline justify-between gap-2">
                          <span className="text-[13px]">
                            {pick(factor.label, factor.label_si)}
                            <span className="ml-1.5 text-ink-secondary">{factor.state_label}</span>
                          </span>
                          <span className="num shrink-0 text-[12.5px]">
                            {factor.affected} ({percent(factor.share)})
                          </span>
                        </div>
                        <Meter
                          value={factor.share}
                          tone={factor.school_level ? "attention" : "calm"}
                        />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <EmptyState>No shared conditions recorded for this class.</EmptyState>
                )}
              </div>
            </Panel>
          </div>
        </>
      ) : peers.loading ? (
        <Loading label={t("common.loading")} />
      ) : null}
    </div>
  );
}

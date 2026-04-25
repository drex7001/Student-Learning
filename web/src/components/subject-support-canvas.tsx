"use client";

import { useMemo, useState } from "react";

type SupportStatus = "support_now" | "watch" | "ready" | "missing_evidence";

export type ConceptSupportNode = {
  id: string;
  subject_id: string;
  name: string;
  name_si?: string | null;
  description?: string | null;
  description_si?: string | null;
  mastery_score?: number | null;
  confidence: number;
  status: SupportStatus;
  priority_score: number;
  depth: number;
  downstream_impact: number;
  evidence: string;
};

export type ConceptSupportEdge = {
  source_id: string;
  target_id: string;
};

type PositionedNode = ConceptSupportNode & {
  x: number;
  y: number;
};

type StatusFilter = "all" | SupportStatus;

type SubjectSupportCanvasProps = {
  nodes: ConceptSupportNode[];
  edges: ConceptSupportEdge[];
  selectedConceptId: string | null;
  recommendedConceptId: string | null;
  onSelectConcept: (conceptId: string) => void;
};

const WIDTH = 1180;
const HEIGHT = 680;

function displayName(item: { name: string; name_si?: string | null }) {
  return item.name_si ? `${item.name} / ${item.name_si}` : item.name;
}

function statusLabel(status: SupportStatus) {
  if (status === "support_now") {
    return "Support now";
  }
  if (status === "missing_evidence") {
    return "Missing evidence";
  }
  if (status === "ready") {
    return "Ready";
  }
  return "Watch";
}

function statusTone(status: SupportStatus) {
  if (status === "support_now") {
    return {
      fill: "#d9613d",
      fillSoft: "rgba(217,97,61,0.2)",
      stroke: "#ffb59f",
      text: "#fff4ef",
      line: "rgba(217,97,61,0.48)",
    };
  }
  if (status === "watch") {
    return {
      fill: "#e1b04b",
      fillSoft: "rgba(225,176,75,0.2)",
      stroke: "#ffe2a0",
      text: "#241b07",
      line: "rgba(225,176,75,0.45)",
    };
  }
  if (status === "ready") {
    return {
      fill: "#1b7f8a",
      fillSoft: "rgba(27,127,138,0.2)",
      stroke: "#99eee3",
      text: "#f2fffd",
      line: "rgba(82,208,197,0.38)",
    };
  }
  return {
    fill: "#667386",
    fillSoft: "rgba(102,115,134,0.18)",
    stroke: "#c7d0dc",
    text: "#f4f7fb",
    line: "rgba(148,163,184,0.32)",
  };
}

function filterTone(filter: StatusFilter, active: boolean) {
  if (active) {
    return "border-white/16 bg-white text-[#132034]";
  }
  if (filter === "support_now") {
    return "border-[rgba(217,97,61,0.36)] bg-[rgba(217,97,61,0.12)] text-[#ffd9ce]";
  }
  if (filter === "watch") {
    return "border-[rgba(225,176,75,0.36)] bg-[rgba(225,176,75,0.12)] text-[#ffe7aa]";
  }
  if (filter === "ready") {
    return "border-[rgba(82,208,197,0.32)] bg-[rgba(27,127,138,0.16)] text-[#c9fff7]";
  }
  if (filter === "missing_evidence") {
    return "border-white/12 bg-white/8 text-white/72";
  }
  return "border-white/12 bg-white/8 text-white/80";
}

function distribute(count: number, top: number, bottom: number) {
  if (count <= 1) {
    return [(top + bottom) / 2];
  }
  const span = bottom - top;
  return Array.from({ length: count }, (_, index) => top + (span / (count - 1)) * index);
}

function buildLayout(nodes: ConceptSupportNode[]): PositionedNode[] {
  const groups = new Map<number, ConceptSupportNode[]>();
  for (const node of nodes) {
    const group = groups.get(node.depth) ?? [];
    group.push(node);
    groups.set(node.depth, group);
  }

  const maxDepth = Math.max(1, ...nodes.map((node) => node.depth));
  const positioned: PositionedNode[] = [];

  Array.from(groups.entries())
    .sort(([left], [right]) => left - right)
    .forEach(([depth, group]) => {
      const sorted = [...group].sort((left, right) => {
        if (left.status !== right.status) {
          const order: Record<SupportStatus, number> = {
            support_now: 0,
            watch: 1,
            missing_evidence: 2,
            ready: 3,
          };
          return order[left.status] - order[right.status];
        }
        return right.priority_score - left.priority_score;
      });
      const ys = distribute(sorted.length, 110, HEIGHT - 90);
      const x = 100 + (depth / maxDepth) * (WIDTH - 220);
      sorted.forEach((node, index) => {
        positioned.push({ ...node, x, y: ys[index] });
      });
    });

  return positioned;
}

export function SubjectSupportCanvas({
  nodes,
  edges,
  selectedConceptId,
  recommendedConceptId,
  onSelectConcept,
}: SubjectSupportCanvasProps) {
  const [zoom, setZoom] = useState(1);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const positionedNodes = useMemo(() => buildLayout(nodes), [nodes]);
  const nodeById = useMemo(
    () => new Map(positionedNodes.map((node) => [node.id, node])),
    [positionedNodes],
  );
  const hoveredNode = hoveredId ? nodeById.get(hoveredId) : null;

  function isVisible(node: ConceptSupportNode) {
    return filter === "all" || node.status === filter;
  }

  function resetView() {
    setZoom(1);
    setFilter("all");
  }

  return (
    <section className="overflow-hidden rounded-[2rem] border border-[#203249] bg-[linear-gradient(180deg,#0c1724,#09111c)] shadow-[0_28px_120px_rgba(9,18,30,0.24)]">
      <div className="flex flex-col gap-4 border-b border-white/10 px-4 py-4 text-white xl:flex-row xl:items-center xl:justify-between">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-white/48">Subject support map</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">
            Every concept for this learner in one view
          </h2>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {[
            { id: "all", label: "All" },
            { id: "support_now", label: "Support now" },
            { id: "watch", label: "Watch" },
            { id: "ready", label: "Ready" },
            { id: "missing_evidence", label: "Missing" },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setFilter(item.id as StatusFilter)}
              className={`rounded-full border px-3 py-2 font-mono text-[11px] uppercase tracking-[0.12em] transition-colors ${filterTone(
                item.id as StatusFilter,
                filter === item.id,
              )}`}
            >
              {item.label}
            </button>
          ))}
          <span className="mx-1 h-7 w-px bg-white/12" />
          <button
            type="button"
            onClick={() => setZoom((value) => Math.max(0.72, value - 0.12))}
            className="rounded-full border border-white/12 bg-white/8 px-3 py-2 text-sm text-white/80"
          >
            -
          </button>
          <button
            type="button"
            onClick={() => setZoom((value) => Math.min(1.42, value + 0.12))}
            className="rounded-full border border-white/12 bg-white/8 px-3 py-2 text-sm text-white/80"
          >
            +
          </button>
          <button
            type="button"
            onClick={resetView}
            className="rounded-full border border-white/12 bg-white/8 px-3 py-2 text-sm text-white/80"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={() => setZoom(0.9)}
            className="rounded-full border border-white/12 bg-white/8 px-3 py-2 text-sm text-white/80"
          >
            Fit
          </button>
        </div>
      </div>

      <div className="relative min-h-[680px] overflow-hidden">
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Subject concept support graph"
        >
          <defs>
            <linearGradient id="subject-map-bg" x1="0" x2="1" y1="0" y2="1">
              <stop offset="0%" stopColor="#0c1724" />
              <stop offset="52%" stopColor="#0f1d2d" />
              <stop offset="100%" stopColor="#08111c" />
            </linearGradient>
            <marker id="arrow-support" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto">
              <path d="M0,0 L0,6 L8,3 z" fill="rgba(255,255,255,0.32)" />
            </marker>
          </defs>
          <rect width={WIDTH} height={HEIGHT} fill="url(#subject-map-bg)" />
          <g transform={`translate(${(1 - zoom) * WIDTH * 0.5} ${(1 - zoom) * HEIGHT * 0.5}) scale(${zoom})`}>
            {edges.map((edge) => {
              const source = nodeById.get(edge.source_id);
              const target = nodeById.get(edge.target_id);
              if (!source || !target) {
                return null;
              }
              const visible = isVisible(source) || isVisible(target);
              const stroke = source.status === "support_now" || target.status === "support_now"
                ? "rgba(217,97,61,0.5)"
                : "rgba(255,255,255,0.18)";
              return (
                <line
                  key={`${edge.source_id}-${edge.target_id}`}
                  x1={source.x + 58}
                  y1={source.y}
                  x2={target.x - 58}
                  y2={target.y}
                  stroke={stroke}
                  strokeWidth={visible ? 2.4 : 1.4}
                  opacity={visible ? 1 : 0.18}
                  markerEnd="url(#arrow-support)"
                />
              );
            })}

            {positionedNodes.map((node) => {
              const tone = statusTone(node.status);
              const selected = selectedConceptId === node.id;
              const recommended = recommendedConceptId === node.id;
              const visible = isVisible(node);
              const priorityRadius = 42 + Math.min(18, node.priority_score * 20);
              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x} ${node.y})`}
                  opacity={visible ? 1 : 0.18}
                  onMouseEnter={() => setHoveredId(node.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  {recommended ? (
                    <>
                      <circle r={priorityRadius + 12} fill="none" stroke="#e1b04b" strokeWidth="3" strokeDasharray="7 5" />
                      <text x="-42" y={-(priorityRadius + 22)} fill="#ffe09a" className="font-mono text-[11px] uppercase tracking-[0.16em]">
                        Start here
                      </text>
                    </>
                  ) : null}
                  <circle r={priorityRadius} fill={tone.fillSoft} stroke={tone.line} strokeWidth="8" />
                  <g
                    role="button"
                    tabIndex={0}
                    aria-label={`Open ${node.name}`}
                    onClick={() => onSelectConcept(node.id)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        onSelectConcept(node.id);
                      }
                    }}
                    className="cursor-pointer"
                  >
                    <circle
                      r="45"
                      fill={tone.fill}
                      stroke={selected ? "#ffffff" : tone.stroke}
                      strokeWidth={selected ? 5 : 2.4}
                      className="transition-opacity hover:opacity-90"
                    />
                  </g>
                  <text
                    x="0"
                    y="-7"
                    textAnchor="middle"
                    fill={tone.text}
                    className="pointer-events-none select-none font-mono text-[10px] uppercase tracking-[0.12em]"
                  >
                    {node.id}
                  </text>
                  <text
                    x="0"
                    y="12"
                    textAnchor="middle"
                    fill={tone.text}
                    className="pointer-events-none select-none text-[13px] font-semibold"
                  >
                    {node.name.length > 18 ? `${node.name.slice(0, 16)}...` : node.name}
                  </text>
                  <text
                    x="0"
                    y="30"
                    textAnchor="middle"
                    fill={tone.text}
                    className="pointer-events-none select-none text-[12px]"
                    opacity="0.88"
                  >
                    {node.mastery_score == null ? "No data" : `${Math.round(node.mastery_score * 100)}%`}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        {hoveredNode ? (
          <div className="absolute right-4 top-4 max-w-[360px] rounded-[1.4rem] border border-white/12 bg-[rgba(12,23,36,0.88)] p-4 text-white shadow-[0_20px_80px_rgba(0,0,0,0.25)] backdrop-blur">
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/48">
              {hoveredNode.id} · {statusLabel(hoveredNode.status)}
            </p>
            <strong className="mt-2 block text-xl">{displayName(hoveredNode)}</strong>
            <div className="mt-4 grid grid-cols-3 gap-2">
              <div className="rounded-2xl bg-white/8 p-3">
                <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-white/44">Mastery</p>
                <strong className="mt-1 block">{hoveredNode.mastery_score == null ? "N/A" : `${Math.round(hoveredNode.mastery_score * 100)}%`}</strong>
              </div>
              <div className="rounded-2xl bg-white/8 p-3">
                <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-white/44">Confidence</p>
                <strong className="mt-1 block">{Math.round(hoveredNode.confidence * 100)}%</strong>
              </div>
              <div className="rounded-2xl bg-white/8 p-3">
                <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-white/44">Priority</p>
                <strong className="mt-1 block">{hoveredNode.priority_score.toFixed(2)}</strong>
              </div>
            </div>
            <p className="mt-3 text-sm leading-6 text-white/70">{hoveredNode.evidence}</p>
          </div>
        ) : null}

        <div className="absolute bottom-4 left-4 flex flex-wrap gap-2 text-white">
          {(["support_now", "watch", "ready", "missing_evidence"] as SupportStatus[]).map((status) => {
            const tone = statusTone(status);
            return (
              <span key={status} className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-[rgba(12,23,36,0.72)] px-3 py-2 text-xs backdrop-blur">
                <span className="h-2.5 w-2.5 rounded-full" style={{ background: tone.fill }} />
                {statusLabel(status)}
              </span>
            );
          })}
        </div>
      </div>
    </section>
  );
}

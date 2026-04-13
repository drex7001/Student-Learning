"use client";

import { startTransition, useEffect, useEffectEvent, useState } from "react";

type ConceptNode = {
  id: string;
  name: string;
  description?: string;
};

type PathSegment = {
  path_index: number;
  nodes: ConceptNode[];
};

type PrerequisiteResponse = {
  concept: ConceptNode;
  prerequisite_paths: PathSegment[];
  downstream_concepts: ConceptNode[];
};

type SelectorOptionsResponse = {
  students: { id: string; full_name: string; cohort: string }[];
  concepts: ConceptNode[];
};

type PositionedNode = {
  id: string;
  name: string;
  x: number;
  y: number;
  tone: "upstream" | "focus" | "downstream";
};

type Edge = {
  key: string;
  from: string;
  to: string;
  dashed?: boolean;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function distributeYPositions(count: number): number[] {
  if (count <= 0) {
    return [];
  }
  if (count === 1) {
    return [50];
  }
  const start = 16;
  const span = 68;
  return Array.from({ length: count }, (_, index) => start + (span / (count - 1)) * index);
}

function buildDependencyMap(drilldown: PrerequisiteResponse | null): {
  nodes: PositionedNode[];
  edges: Edge[];
} {
  if (!drilldown) {
    return { nodes: [], edges: [] };
  }

  const focus = drilldown.concept;
  const upstreamById = new Map<string, { node: ConceptNode; distance: number }>();
  const edges = new Map<string, Edge>();

  for (const path of drilldown.prerequisite_paths) {
    path.nodes.forEach((node, index) => {
      const distance = path.nodes.length - index - 1;
      if (distance > 0) {
        const current = upstreamById.get(node.id);
        if (!current || distance < current.distance) {
          upstreamById.set(node.id, { node, distance });
        }
      }
      if (index < path.nodes.length - 1) {
        const from = path.nodes[index].id;
        const to = path.nodes[index + 1].id;
        edges.set(`${from}->${to}`, { key: `${from}->${to}`, from, to });
      }
    });
  }

  const upstreamEntries = Array.from(upstreamById.values()).sort((left, right) => {
    if (left.distance !== right.distance) {
      return right.distance - left.distance;
    }
    return left.node.name.localeCompare(right.node.name);
  });

  const maxDistance = Math.max(1, ...upstreamEntries.map((entry) => entry.distance));
  const positionedNodes = new Map<string, PositionedNode>();
  const groups = new Map<number, ConceptNode[]>();

  for (const entry of upstreamEntries) {
    const group = groups.get(entry.distance) ?? [];
    group.push(entry.node);
    groups.set(entry.distance, group);
  }

  for (const [distance, nodes] of groups.entries()) {
    const ys = distributeYPositions(nodes.length);
    nodes.forEach((node, index) => {
      const x = maxDistance === 1 ? 24 : 10 + ((maxDistance - distance) / (maxDistance - 1)) * 34;
      positionedNodes.set(node.id, {
        id: node.id,
        name: node.name,
        x,
        y: ys[index],
        tone: "upstream",
      });
    });
  }

  positionedNodes.set(focus.id, {
    id: focus.id,
    name: focus.name,
    x: 58,
    y: 50,
    tone: "focus",
  });

  const downstream = drilldown.downstream_concepts.filter((node) => node.id !== focus.id).slice(0, 6);
  const downstreamRows = distributeYPositions(Math.min(3, Math.max(downstream.length, 1)));
  downstream.forEach((node, index) => {
    const columnIndex = index >= 3 ? 1 : 0;
    const rowIndex = index % 3;
    positionedNodes.set(node.id, {
      id: node.id,
      name: node.name,
      x: columnIndex === 0 ? 81 : 93,
      y: downstreamRows[rowIndex] ?? 50,
      tone: "downstream",
    });
    edges.set(`${focus.id}->${node.id}`, {
      key: `${focus.id}->${node.id}`,
      from: focus.id,
      to: node.id,
      dashed: true,
    });
  });

  return {
    nodes: Array.from(positionedNodes.values()),
    edges: Array.from(edges.values()).filter(
      (edge) => positionedNodes.has(edge.from) && positionedNodes.has(edge.to),
    ),
  };
}

export function ConceptExplorer({
  initialConceptId = "ALG-024",
}: {
  initialConceptId?: string;
}) {
  const [conceptId, setConceptId] = useState(initialConceptId);
  const [concepts, setConcepts] = useState<ConceptNode[]>([]);
  const [graph, setGraph] = useState<PrerequisiteResponse | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [message, setMessage] = useState("Loading concept graph...");

  async function fetchOptions() {
    const response = await fetch(`${API_BASE_URL}/api/options`);
    if (!response.ok) {
      throw new Error("Unable to load concept options.");
    }
    return (await response.json()) as SelectorOptionsResponse;
  }

  async function fetchGraph(nextConceptId: string) {
    const response = await fetch(`${API_BASE_URL}/api/concepts/${nextConceptId}/prerequisites`);
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? "Unable to load concept graph.");
    }
    return (await response.json()) as PrerequisiteResponse;
  }

  async function loadExplorer(nextConceptId: string) {
    setStatus("loading");
    setMessage("Tracing prerequisite paths and downstream links...");
    try {
      const optionsPayload = await fetchOptions();
      setConcepts(optionsPayload.concepts);
      const resolvedConceptId =
        optionsPayload.concepts.find((concept) => concept.id === nextConceptId)?.id ??
        optionsPayload.concepts[0]?.id ??
        nextConceptId;
      setConceptId(resolvedConceptId);

      const graphPayload = await fetchGraph(resolvedConceptId);
      setGraph(graphPayload);
      setStatus("idle");
      setMessage("Concept graph updated.");
    } catch (error) {
      setGraph(null);
      setStatus("error");
      setMessage(error instanceof Error ? error.message : "Unable to load concept graph.");
    }
  }

  const loadInitialGraph = useEffectEvent(() => {
    void loadExplorer(conceptId);
  });

  useEffect(() => {
    startTransition(() => {
      loadInitialGraph();
    });
  }, []);

  const { nodes, edges } = buildDependencyMap(graph);
  const nodeById = new Map(nodes.map((node) => [node.id, node]));

  return (
    <div className="grid gap-6">
      <section className="rounded-[2.4rem] border border-line bg-[linear-gradient(135deg,#edf6f4,#ffffff)] p-6 shadow-[0_24px_80px_rgba(19,32,52,0.08)] md:p-8">
        <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-teal">Concept Explorer</p>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight text-foreground md:text-5xl">
              Read the graph without student noise.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-8 text-muted">
              This route is only for curriculum structure. Pick a concept and inspect its upstream
              path and downstream spread.
            </p>
          </div>

          <div className="rounded-[1.8rem] border border-line bg-white/90 p-5">
            <label className="grid gap-3">
              <span className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Concept</span>
              <select
                className="rounded-2xl border border-line bg-surface-strong px-4 py-3 outline-none"
                value={conceptId}
                onChange={(event) => {
                  const nextConceptId = event.target.value;
                  setConceptId(nextConceptId);
                  startTransition(() => {
                    void loadExplorer(nextConceptId);
                  });
                }}
              >
                {concepts.map((concept) => (
                  <option key={concept.id} value={concept.id}>
                    {concept.name}
                  </option>
                ))}
              </select>
            </label>
            <p className="mt-4 text-sm leading-7 text-muted">{message}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="rounded-[2rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Route map</p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight text-foreground">
                {graph?.concept.name ?? "Loading concept"}
              </h2>
            </div>
            {graph ? (
              <span className="rounded-full bg-accent-soft px-3 py-2 font-mono text-[11px] uppercase tracking-[0.16em] text-accent">
                {graph.downstream_concepts.length} downstream concepts
              </span>
            ) : null}
          </div>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-muted">
            {graph?.concept.description ?? "Waiting for concept details."}
          </p>

          <div className="relative mt-5 h-[520px] overflow-hidden rounded-[1.8rem] bg-[radial-gradient(circle_at_top_left,rgba(27,127,138,0.16),transparent_34%),radial-gradient(circle_at_right,rgba(217,97,61,0.12),transparent_34%),linear-gradient(180deg,#132034,#101825)]">
            <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
              {edges.map((edge) => {
                const from = nodeById.get(edge.from);
                const to = nodeById.get(edge.to);
                if (!from || !to) {
                  return null;
                }
                return (
                  <line
                    key={edge.key}
                    x1={from.x}
                    y1={from.y}
                    x2={to.x}
                    y2={to.y}
                    stroke={edge.dashed ? "rgba(225,176,75,0.52)" : "rgba(255,255,255,0.18)"}
                    strokeDasharray={edge.dashed ? "2.6 2" : undefined}
                    strokeWidth={edge.dashed ? 0.44 : 0.38}
                  />
                );
              })}
            </svg>

            {nodes.map((node) => {
              const toneClasses =
                node.tone === "focus"
                  ? "border-[rgba(225,176,75,0.42)] bg-[rgba(225,176,75,0.18)] text-white"
                  : node.tone === "downstream"
                    ? "border-[rgba(27,127,138,0.22)] bg-[rgba(27,127,138,0.18)] text-white/92"
                    : "border-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.07)] text-white/86";

              return (
                <div
                  key={node.id}
                  className={`absolute w-[146px] -translate-x-1/2 -translate-y-1/2 rounded-2xl border px-3 py-3 ${toneClasses}`}
                  style={{ left: `${node.x}%`, top: `${node.y}%` }}
                >
                  <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-white/52">
                    {node.id}
                  </p>
                  <strong className="mt-2 block text-sm leading-5">{node.name}</strong>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-[2rem] border border-line bg-surface p-5 shadow-[0_20px_80px_rgba(19,32,52,0.08)]">
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-muted">Graph facts</p>
          <div className="mt-4 grid gap-3">
            <div className="rounded-[1.5rem] bg-[#fff9ef] p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Prerequisite paths</p>
              <strong className="mt-2 block text-3xl text-foreground">
                {graph?.prerequisite_paths.length ?? 0}
              </strong>
            </div>
            <div className="rounded-[1.5rem] bg-[#f4faf8] p-4">
              <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">Downstream concepts</p>
              <strong className="mt-2 block text-3xl text-foreground">
                {graph?.downstream_concepts.length ?? 0}
              </strong>
            </div>
          </div>

          <div className="mt-5 rounded-[1.6rem] border border-line bg-white p-4">
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted">Downstream list</p>
            <div className="mt-4 grid gap-2">
              {graph?.downstream_concepts.length ? (
                graph.downstream_concepts.map((concept) => (
                  <div key={concept.id} className="rounded-2xl bg-[#f8f6f1] px-4 py-3">
                    <strong className="block text-foreground">{concept.name}</strong>
                    <p className="mt-1 text-sm text-muted">{concept.id}</p>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-line p-4 text-sm text-muted">
                  {status === "loading" ? "Loading downstream concepts..." : "No downstream concepts."}
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

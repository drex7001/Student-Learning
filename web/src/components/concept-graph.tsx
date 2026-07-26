"use client";

/**
 * The prerequisite concept map.
 *
 * Replaces the two incompatible hand-rolled SVG renderers the app used to carry (one
 * fixed-viewBox layered DAG, one percentage-positioned overlay). One renderer now
 * serves the concept map and, in a sibling component, the causal DAG — both get
 * pan, zoom and keyboard focus for free.
 */

import dagre from "@dagrejs/dagre";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/base.css";
import { useMemo } from "react";

import { cn, statusStyle } from "@/lib/format";
import type { ConceptSupportEdge, ConceptSupportNode, SupportStatus } from "@/lib/types";

const NODE_WIDTH = 156;
const NODE_HEIGHT = 62;

type ConceptData = {
  label: string;
  id: string;
  mastery: number | null;
  status: SupportStatus;
  recommended: boolean;
  onSelect?: (id: string) => void;
};

function ConceptNodeView({ data, selected }: NodeProps) {
  const { label, id, mastery, status, recommended } = data as ConceptData;
  return (
    <div
      className={cn(
        "grid h-[62px] w-[156px] content-center gap-0.5 rounded-chip border px-2 text-center",
        statusStyle[status].chip,
        recommended && "ring-2 ring-indigo ring-offset-2 ring-offset-[var(--surface-sunken)]",
        selected && "ring-2 ring-indigo",
      )}
    >
      <Handle type="target" position={Position.Left} />
      <span className="num text-[9.5px] uppercase tracking-[0.1em] opacity-70">{id}</span>
      <span className="line-clamp-2 text-[11px] font-medium leading-tight">{label}</span>
      <span className="num text-[11px]">{mastery === null ? "—" : `${Math.round(mastery * 100)}%`}</span>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { concept: ConceptNodeView };

export function ConceptGraph({
  concepts,
  edges,
  recommendedId,
  selectedId,
  onSelect,
  height = 460,
}: {
  concepts: ConceptSupportNode[];
  edges: ConceptSupportEdge[];
  recommendedId?: string | null;
  selectedId?: string | null;
  onSelect?: (conceptId: string) => void;
  height?: number;
}) {
  const { flowNodes, flowEdges } = useMemo(() => {
    const graph = new dagre.graphlib.Graph();
    graph.setDefaultEdgeLabel(() => ({}));
    graph.setGraph({ rankdir: "LR", nodesep: 16, ranksep: 72, marginx: 16, marginy: 16 });

    concepts.forEach((concept) =>
      graph.setNode(concept.id, { width: NODE_WIDTH, height: NODE_HEIGHT }),
    );
    edges.forEach((edge) => graph.setEdge(edge.source_id, edge.target_id));
    dagre.layout(graph);

    const nodes: Node[] = concepts.map((concept) => {
      const position = graph.node(concept.id);
      return {
        id: concept.id,
        type: "concept",
        selected: concept.id === selectedId,
        position: {
          x: (position?.x ?? 0) - NODE_WIDTH / 2,
          y: (position?.y ?? 0) - NODE_HEIGHT / 2,
        },
        data: {
          label: concept.name,
          id: concept.id,
          mastery: concept.mastery_score,
          status: concept.status,
          recommended: concept.id === recommendedId,
        } satisfies ConceptData,
        draggable: false,
        connectable: false,
      };
    });

    const flowEdges: Edge[] = edges.map((edge) => ({
      id: `${edge.source_id}->${edge.target_id}`,
      source: edge.source_id,
      target: edge.target_id,
      markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12 },
      style: { strokeWidth: 1.4 },
    }));

    return { flowNodes: nodes, flowEdges };
  }, [concepts, edges, recommendedId, selectedId]);

  return (
    <div style={{ height }} className="rounded-card border border-rule bg-sunken">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.1 }}
        nodesDraggable={false}
        nodesConnectable={false}
        onNodeClick={(_event, node) => onSelect?.(node.id)}
        proOptions={{ hideAttribution: true }}
        minZoom={0.25}
        maxZoom={1.8}
        aria-label="Prerequisite concept map"
      >
        <Background gap={18} size={1} color="var(--rule)" />
        <Controls showInteractive={false} className="!border !border-rule !bg-surface" />
      </ReactFlow>
    </div>
  );
}

export function ConceptLegend({ labels }: { labels: Record<SupportStatus, string> }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-[12px] text-ink-secondary">
      {(Object.keys(labels) as SupportStatus[]).map((status) => (
        <li key={status} className="flex items-center gap-1.5">
          <span aria-hidden className={cn("size-2.5 rounded-full", statusStyle[status].dot)} />
          {labels[status]}
        </li>
      ))}
    </ul>
  );
}

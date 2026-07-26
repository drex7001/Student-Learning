"use client";

/**
 * The "why this flag?" surface: every directed route a factor takes to the outcome,
 * laid out left to right, read from Neo4j.
 *
 * This is the piece that replaces a SHAP bar chart. A bar says a feature mattered;
 * this says *through what* it mattered — and makes visible that a protected
 * characteristic never reaches the outcome except through something a school can
 * change.
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

import { cn } from "@/lib/format";
import type { CausalPathsResponse } from "@/lib/types";

const NODE_WIDTH = 168;
const NODE_HEIGHT = 54;

type FactorData = {
  label: string;
  kind: "origin" | "mechanism" | "outcome";
  modifiable: boolean;
  protected: boolean;
};

function FactorNode({ data }: NodeProps) {
  const { label, kind, modifiable, protected: isProtected } = data as FactorData;
  return (
    <div
      className={cn(
        "grid h-[54px] w-[168px] place-items-center rounded-chip border px-2 text-center text-[11.5px] leading-tight",
        kind === "outcome" && "border-attention/40 bg-attention-soft font-medium text-attention",
        kind === "origin" && isProtected && "border-dashed border-rule-strong bg-sunken text-ink-secondary",
        kind === "origin" && !isProtected && "border-indigo/40 bg-indigo-soft font-medium text-indigo",
        kind === "mechanism" && modifiable && "border-watch/40 bg-watch-soft text-watch",
        kind === "mechanism" && !modifiable && "border-rule bg-raised text-ink-secondary",
      )}
    >
      <Handle type="target" position={Position.Left} />
      <span>{label}</span>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = { factor: FactorNode };

function layout(nodes: Node[], edges: Edge[]) {
  const graph = new dagre.graphlib.Graph();
  graph.setDefaultEdgeLabel(() => ({}));
  graph.setGraph({ rankdir: "LR", nodesep: 18, ranksep: 64, marginx: 12, marginy: 12 });

  nodes.forEach((node) => graph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  dagre.layout(graph);

  return nodes.map((node) => {
    const position = graph.node(node.id);
    return {
      ...node,
      position: { x: position.x - NODE_WIDTH / 2, y: position.y - NODE_HEIGHT / 2 },
    };
  });
}

export function CausalGraph({ data, height = 320 }: { data: CausalPathsResponse; height?: number }) {
  const { nodes, edges } = useMemo(() => {
    const nodeMap = new Map<string, Node>();
    const edgeMap = new Map<string, Edge>();

    for (const path of data.paths) {
      path.nodes.forEach((node, index) => {
        if (!nodeMap.has(node.id)) {
          nodeMap.set(node.id, {
            id: node.id,
            type: "factor",
            position: { x: 0, y: 0 },
            data: {
              label: node.label,
              kind:
                index === 0
                  ? "origin"
                  : node.id === data.target
                    ? "outcome"
                    : "mechanism",
              modifiable: node.modifiable,
              protected: node.protected,
            } satisfies FactorData,
            draggable: false,
            connectable: false,
          });
        }
        const next = path.nodes[index + 1];
        if (!next) return;
        const key = `${node.id}->${next.id}`;
        if (!edgeMap.has(key)) {
          const step = path.steps[index];
          edgeMap.set(key, {
            id: key,
            source: node.id,
            target: next.id,
            label: step?.mechanism ?? undefined,
            markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
            style: { strokeWidth: 1.5 },
          });
        }
      });
    }

    const rawNodes = [...nodeMap.values()];
    const rawEdges = [...edgeMap.values()];
    return { nodes: layout(rawNodes, rawEdges), edges: rawEdges };
  }, [data]);

  return (
    <div style={{ height }} className="rounded-card border border-rule bg-sunken">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
        minZoom={0.35}
        maxZoom={1.6}
        aria-label={`Routes from ${data.label} to the outcome`}
      >
        <Background gap={18} size={1} color="var(--rule)" />
        <Controls showInteractive={false} className="!border !border-rule !bg-surface" />
      </ReactFlow>
    </div>
  );
}

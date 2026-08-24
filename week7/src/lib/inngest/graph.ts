import type { WorkflowEdge, WorkflowNode } from "@/components/workflow/types";

export type ExecutionStep = {
  nodeId: string;
  label: string;
  prompt: string;
  answer: "YES" | "NO";
};

export type ExecutionResult = {
  trace: ExecutionStep[];
  outcome: { nodeId: string; label: string } | null;
  status:
    | "completed"
    | "dead-end"
    | "no-start"
    | "max-steps-exceeded"
    | "invalid-input"
    | "error";
  /** Set when status is "invalid-input" or "error". */
  error?: string;
};

export const MAX_STEPS = 25;

/**
 * Minimal structural check on graph data coming from outside the app (an
 * event payload, in this case) -- not a full schema validator, just enough
 * to turn "malformed request" into a clean error instead of a crash deep in
 * the traversal loop.
 */
export function validateGraph(nodes: unknown, edges: unknown): string | null {
  if (!Array.isArray(nodes) || nodes.length === 0) {
    return "Graph has no nodes";
  }
  if (!Array.isArray(edges)) {
    return "Graph edges must be an array";
  }
  for (const node of nodes) {
    if (
      !node ||
      typeof node !== "object" ||
      typeof (node as { id?: unknown }).id !== "string" ||
      typeof (node as { type?: unknown }).type !== "string"
    ) {
      return "Every node needs an id and a type";
    }
  }
  for (const edge of edges) {
    if (
      !edge ||
      typeof edge !== "object" ||
      typeof (edge as { source?: unknown }).source !== "string" ||
      typeof (edge as { target?: unknown }).target !== "string"
    ) {
      return "Every edge needs a source and a target";
    }
  }
  return null;
}

export function findStartNode(nodes: WorkflowNode[]) {
  return nodes.find((node) => node.type === "start");
}

export function findEdgeFrom(
  edges: WorkflowEdge[],
  sourceId: string,
  sourceHandle?: string,
) {
  return edges.find(
    (edge) =>
      edge.source === sourceId &&
      (sourceHandle === undefined || edge.sourceHandle === sourceHandle),
  );
}

export function nodeById(nodes: WorkflowNode[], id: string) {
  return nodes.find((node) => node.id === id);
}

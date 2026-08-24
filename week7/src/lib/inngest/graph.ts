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
  status: "completed" | "dead-end" | "no-start" | "max-steps-exceeded";
};

export const MAX_STEPS = 25;

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

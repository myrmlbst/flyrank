import type { Edge, Node } from "@xyflow/react";

export type StartNodeData = {
  label: string;
};

export type DecisionNodeData = {
  label: string;
  prompt: string;
};

export type OutcomeNodeData = {
  label: string;
};

export type StartNode = Node<StartNodeData, "start">;
export type DecisionNode = Node<DecisionNodeData, "decision">;
export type OutcomeNode = Node<OutcomeNodeData, "outcome">;

export type WorkflowNode = StartNode | DecisionNode | OutcomeNode;

export type Branch = "yes" | "no";

export type BranchEdge = Edge<{ branch: Branch }, Branch>;

export type WorkflowEdge = BranchEdge;

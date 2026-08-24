"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  Background,
  Controls,
  MiniMap,
  Panel,
  ReactFlow,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Button } from "@/components/ui/button";
import { DecisionNodeComponent } from "./nodes/decision-node";
import { OutcomeNodeComponent } from "./nodes/outcome-node";
import { StartNodeComponent } from "./nodes/start-node";
import { edgeTypes } from "./edges/branch-edge";
import type { WorkflowEdge, WorkflowNode } from "./types";

const nodeTypes: NodeTypes = {
  start: StartNodeComponent,
  decision: DecisionNodeComponent,
  outcome: OutcomeNodeComponent,
};

const STORAGE_KEY = "ai-workflow-graph-v1";

const initialNodes: WorkflowNode[] = [
  {
    id: "start",
    type: "start",
    position: { x: 260, y: 0 },
    data: { label: "Start" },
  },
  {
    id: "decision-urgent",
    type: "decision",
    position: { x: 160, y: 100 },
    data: { label: "Decision", prompt: "Is this request urgent?" },
  },
  {
    id: "decision-approval",
    type: "decision",
    position: { x: 40, y: 300 },
    data: {
      label: "Decision",
      prompt: "Does it need manager approval?",
    },
  },
  {
    id: "outcome-backlog",
    type: "outcome",
    position: { x: 420, y: 320 },
    data: { label: "Add to backlog" },
  },
  {
    id: "outcome-escalate",
    type: "outcome",
    position: { x: -140, y: 520 },
    data: { label: "Escalate to manager" },
  },
  {
    id: "outcome-auto",
    type: "outcome",
    position: { x: 120, y: 520 },
    data: { label: "Auto-approve" },
  },
];

const initialEdges: WorkflowEdge[] = [
  { id: "start->urgent", source: "start", target: "decision-urgent" },
  {
    id: "urgent-yes->approval",
    source: "decision-urgent",
    sourceHandle: "yes",
    target: "decision-approval",
    type: "yes",
  },
  {
    id: "urgent-no->backlog",
    source: "decision-urgent",
    sourceHandle: "no",
    target: "outcome-backlog",
    type: "no",
  },
  {
    id: "approval-yes->escalate",
    source: "decision-approval",
    sourceHandle: "yes",
    target: "outcome-escalate",
    type: "yes",
  },
  {
    id: "approval-no->auto",
    source: "decision-approval",
    sourceHandle: "no",
    target: "outcome-auto",
    type: "no",
  },
];

export function WorkflowCanvas() {
  const [nodes, setNodes, onNodesChange] =
    useNodesState<WorkflowNode>(initialNodes);
  const [edges, setEdges, onEdgesChange] =
    useEdgesState<WorkflowEdge>(initialEdges);
  const [hydrated, setHydrated] = useState(false);
  const nodeCounter = useRef(0);

  // Load any saved graph after mount so the server-rendered markup always
  // matches the deterministic demo graph above (avoids a hydration mismatch).
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved) as {
          nodes: WorkflowNode[];
          edges: WorkflowEdge[];
        };
        setNodes(parsed.nodes);
        setEdges(parsed.edges);
      }
    } catch {
      // Corrupt or unavailable storage -- fall back to the demo graph.
    }
    // One-time mount effect (empty deps): flips the gate that lets the
    // persistence effect below start writing, not a reactive sync.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHydrated(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist on every change, once past the initial load, debounced so a
  // node drag doesn't hit localStorage on every pointer-move frame.
  useEffect(() => {
    if (!hydrated) return;
    const timeout = setTimeout(() => {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ nodes, edges }));
    }, 300);
    return () => clearTimeout(timeout);
  }, [nodes, edges, hydrated]);

  const onConnect = useCallback(
    (connection: Connection) => {
      const branch = connection.sourceHandle === "no" ? "no" : "yes";
      setEdges((eds) =>
        addEdge({ ...connection, type: branch }, eds),
      );
    },
    [setEdges],
  );

  const addDecisionNode = useCallback(() => {
    nodeCounter.current += 1;
    const id = `decision-${Date.now()}-${nodeCounter.current}`;
    setNodes((nds) => [
      ...nds,
      {
        id,
        type: "decision",
        position: {
          x: 160 + ((nodeCounter.current * 40) % 240),
          y: 120 + nodes.length * 40,
        },
        data: { label: "Decision", prompt: "" },
      },
    ]);
  }, [nodes.length, setNodes]);

  const resetGraph = useCallback(() => {
    window.localStorage.removeItem(STORAGE_KEY);
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [setNodes, setEdges]);

  return (
    <div className="h-162.5 w-full rounded-lg border">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap pannable zoomable />
        <Panel position="top-left" className="flex gap-2">
          <Button size="sm" onClick={addDecisionNode}>
            + Add decision node
          </Button>
          <Button size="sm" variant="outline" onClick={resetGraph}>
            Reset
          </Button>
        </Panel>
      </ReactFlow>
    </div>
  );
}

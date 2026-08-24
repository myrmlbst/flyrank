"use client";

import { useCallback } from "react";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const initialNodes: Node[] = [
  {
    id: "start",
    position: { x: 0, y: 0 },
    data: { label: "Start" },
    type: "input",
  },
  {
    id: "decision-1",
    position: { x: 0, y: 120 },
    data: { label: "Decision: is X true?" },
  },
  {
    id: "yes",
    position: { x: -150, y: 260 },
    data: { label: "YES" },
    type: "output",
  },
  {
    id: "no",
    position: { x: 150, y: 260 },
    data: { label: "NO" },
    type: "output",
  },
];

const initialEdges: Edge[] = [
  { id: "start-decision-1", source: "start", target: "decision-1" },
  { id: "decision-1-yes", source: "decision-1", target: "yes", label: "YES" },
  { id: "decision-1-no", source: "decision-1", target: "no", label: "NO" },
];

export function WorkflowCanvas() {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (connection: Connection) => setEdges((eds) => addEdge(connection, eds)),
    [setEdges],
  );

  return (
    <div className="h-[600px] w-full rounded-lg border">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}

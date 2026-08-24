"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { findEdgeFrom } from "@/lib/inngest/graph";
import type { ExecutionResult } from "@/lib/inngest/graph";
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
const POLL_INTERVAL_MS = 1000;
const MAX_POLL_ATTEMPTS = 30;

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

type RunStatus = "idle" | "running" | "done" | "failed";

export function WorkflowCanvas() {
  const [nodes, setNodes, onNodesChange] =
    useNodesState<WorkflowNode>(initialNodes);
  const [edges, setEdges, onEdgesChange] =
    useEdgesState<WorkflowEdge>(initialEdges);
  const [hydrated, setHydrated] = useState(false);
  const nodeCounter = useRef(0);

  const [runStatus, setRunStatus] = useState<RunStatus>("idle");
  const [executionResult, setExecutionResult] =
    useState<ExecutionResult | null>(null);
  const pollGeneration = useRef(0);

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

  // Cancel any in-flight poll loop on unmount.
  useEffect(() => () => {
    pollGeneration.current += 1;
  }, []);

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
    setRunStatus("idle");
    setExecutionResult(null);
  }, [setNodes, setEdges]);

  const runWorkflow = useCallback(async () => {
    const generation = ++pollGeneration.current;
    setRunStatus("running");
    setExecutionResult(null);

    try {
      const startRes = await fetch("/api/workflow/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nodes, edges }),
      });
      const { requestId, eventId } = await startRes.json();

      for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt++) {
        if (pollGeneration.current !== generation) return; // superseded

        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
        if (pollGeneration.current !== generation) return;

        const pollRes = await fetch(
          `/api/workflow/run/${requestId}?eventId=${eventId}`,
        );
        const poll = await pollRes.json();

        if (poll.status === "done") {
          setExecutionResult(poll.result as ExecutionResult);
          setRunStatus("done");
          return;
        }
        if (poll.status === "failed") {
          setRunStatus("failed");
          return;
        }
      }
      setRunStatus("failed");
    } catch {
      if (pollGeneration.current === generation) setRunStatus("failed");
    }
  }, [nodes, edges]);

  // Recompute which nodes/edges were actually visited on the last run, so
  // the canvas can highlight the path the model traversed.
  const { highlightedNodeIds, highlightedEdgeIds } = useMemo(() => {
    const nodeIds = new Set<string>();
    const edgeIds = new Set<string>();
    if (!executionResult || executionResult.trace.length === 0) {
      return { highlightedNodeIds: nodeIds, highlightedEdgeIds: edgeIds };
    }

    const start = nodes.find((node) => node.type === "start");
    if (start) {
      const firstEdge = findEdgeFrom(edges, start.id);
      if (firstEdge) edgeIds.add(firstEdge.id);
    }

    for (const step of executionResult.trace) {
      nodeIds.add(step.nodeId);
      const branch = step.answer === "YES" ? "yes" : "no";
      const nextEdge = findEdgeFrom(edges, step.nodeId, branch);
      if (nextEdge) edgeIds.add(nextEdge.id);
    }
    if (executionResult.outcome) nodeIds.add(executionResult.outcome.nodeId);

    return { highlightedNodeIds: nodeIds, highlightedEdgeIds: edgeIds };
  }, [executionResult, nodes, edges]);

  const decoratedNodes = useMemo(
    () =>
      nodes.map((node) =>
        highlightedNodeIds.has(node.id)
          ? { ...node, className: "ring-2 ring-primary ring-offset-2 rounded-xl" }
          : node,
      ),
    [nodes, highlightedNodeIds],
  );

  const decoratedEdges = useMemo(
    () =>
      edges.map((edge) =>
        highlightedEdgeIds.has(edge.id)
          ? { ...edge, style: { strokeWidth: 5 }, animated: true }
          : edge,
      ),
    [edges, highlightedEdgeIds],
  );

  return (
    <div className="h-162.5 w-full rounded-lg border">
      <ReactFlow
        nodes={decoratedNodes}
        edges={decoratedEdges}
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
          <Button
            size="sm"
            variant="secondary"
            onClick={runWorkflow}
            disabled={runStatus === "running"}
          >
            {runStatus === "running" ? "Running..." : "▶ Run workflow"}
          </Button>
        </Panel>
        {runStatus !== "idle" && (
          <Panel position="top-right">
            <Card className="w-80 gap-2 py-3">
              <CardHeader className="flex items-center justify-between px-3">
                <span className="text-sm font-semibold">Execution</span>
                <Badge
                  variant={
                    runStatus === "failed"
                      ? "destructive"
                      : runStatus === "done"
                        ? "default"
                        : "secondary"
                  }
                >
                  {runStatus}
                </Badge>
              </CardHeader>
              <CardContent className="flex flex-col gap-2 px-3 text-sm">
                {runStatus === "failed" && (
                  <p className="text-destructive">
                    The run failed or timed out. Check the Inngest dev
                    dashboard (localhost:8288) for details.
                  </p>
                )}
                {executionResult?.trace.map((step, i) => (
                  <div key={step.nodeId} className="border-b pb-1 last:border-b-0">
                    <span className="text-muted-foreground">{i + 1}.</span>{" "}
                    &ldquo;{step.prompt}&rdquo; →{" "}
                    <span
                      className={
                        step.answer === "YES"
                          ? "font-semibold text-emerald-600"
                          : "font-semibold text-destructive"
                      }
                    >
                      {step.answer}
                    </span>
                  </div>
                ))}
                {executionResult?.outcome && (
                  <p className="font-medium">
                    Outcome: {executionResult.outcome.label}
                  </p>
                )}
                {executionResult && !executionResult.outcome && (
                  <p className="text-muted-foreground">
                    No outcome reached ({executionResult.status}).
                  </p>
                )}
              </CardContent>
            </Card>
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
}

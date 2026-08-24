import type { WorkflowEdge, WorkflowNode } from "@/components/workflow/types";
import { classifyYesNo } from "./classify";
import { inngest } from "./client";
import {
  findEdgeFrom,
  findStartNode,
  MAX_STEPS,
  nodeById,
  validateGraph,
  type ExecutionResult,
  type ExecutionStep,
} from "./graph";

// Smoke-test function: proves the Inngest dev server, event flow, and OpenAI
// SDK are wired together end to end.
export const decisionStep = inngest.createFunction(
  { id: "decision-step", triggers: { event: "workflow/decision.requested" } },
  async ({ event, step }) => {
    const answer = await step.run("ask-openai", () =>
      classifyYesNo(event.data.question),
    );

    return { question: event.data.question, answer };
  },
);

// Executes a full workflow graph: starting from the Start node, each
// decision node's prompt becomes its own Inngest step (so a crash/retry
// resumes from the last completed node instead of re-running the whole
// walk), and the model's YES/NO answer picks which edge to follow next.
// Stops at an Outcome node, a decision node with no edge for the branch
// it picked, or after MAX_STEPS hops (guards against a cyclic graph).
export const runWorkflow = inngest.createFunction(
  { id: "run-workflow", triggers: { event: "workflow/execute.requested" } },
  async ({ event, step }) => {
    const nodes = event.data.nodes as WorkflowNode[];
    const edges = event.data.edges as WorkflowEdge[];

    const publishResult = (result: ExecutionResult) =>
      step.sendEvent("publish-result", {
        name: "workflow/execute.completed",
        data: { requestId: event.data.requestId, result },
      });

    const inputError = validateGraph(nodes, edges);
    if (inputError) {
      const result = {
        trace: [],
        outcome: null,
        status: "invalid-input",
        error: inputError,
      } satisfies ExecutionResult;
      await publishResult(result);
      return result;
    }

    const start = findStartNode(nodes);
    if (!start) {
      const result = {
        trace: [],
        outcome: null,
        status: "no-start",
        error: "Graph has no Start node",
      } satisfies ExecutionResult;
      await publishResult(result);
      return result;
    }

    const trace: ExecutionStep[] = [];
    let edge = findEdgeFrom(edges, start.id);
    let hops = 0;

    while (edge && hops < MAX_STEPS) {
      hops += 1;
      const node = nodeById(nodes, edge.target);
      if (!node) break;

      if (node.type === "outcome") {
        const result = {
          trace,
          outcome: { nodeId: node.id, label: node.data.label },
          status: "completed",
        } satisfies ExecutionResult;
        await publishResult(result);
        return result;
      }

      if (node.type !== "decision") break;

      // step.run already retries transient failures on its own (with
      // backoff) before giving up -- this catch only fires once it has
      // truly exhausted those attempts, or hit a non-retriable error like
      // an empty prompt. Reported as a normal (non-"failed") result so the
      // frontend gets a specific reason instead of a generic timeout.
      let answer;
      try {
        answer = await step.run(`node-${node.id}`, () =>
          classifyYesNo(node.data.prompt),
        );
      } catch (cause) {
        const result = {
          trace,
          outcome: null,
          status: "error",
          error: `"${node.data.label}" (${node.id}) failed: ${
            cause instanceof Error ? cause.message : String(cause)
          }`,
        } satisfies ExecutionResult;
        await publishResult(result);
        return result;
      }

      trace.push({
        nodeId: node.id,
        label: node.data.label,
        prompt: node.data.prompt,
        answer,
      });

      const branch = answer === "YES" ? "yes" : "no";
      edge = findEdgeFrom(edges, node.id, branch);

      if (!edge) {
        const result = {
          trace,
          outcome: null,
          status: "dead-end",
          error: `"${node.data.label}" has no ${branch.toUpperCase()} edge`,
        } satisfies ExecutionResult;
        await publishResult(result);
        return result;
      }
    }

    const result = {
      trace,
      outcome: null,
      status: hops >= MAX_STEPS ? "max-steps-exceeded" : "dead-end",
      error:
        hops >= MAX_STEPS
          ? `Stopped after ${MAX_STEPS} hops -- check the graph for a cycle`
          : "Reached a node with no further edge",
    } satisfies ExecutionResult;
    await publishResult(result);
    return result;
  },
);

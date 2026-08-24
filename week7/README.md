# Week 7: Build an AI Decision Flow with React Flow + Inngest

A visual AI workflow system where each node represents an AI decision step that returns either YES or NO. The workflow execution should run through Inngest while the frontend visualizes the flow using React Flow.

## Tech Stack
TypeScript, Next.js, Inngest, Shadcn, React Flow, OpenAI SDK

## Deliverables
### (Phase 1: Setup)
- [x] Running frontend application (`npm run dev`, verified `GET /` → 200)
- [x] Working Inngest dev server (verified `GET /api/inngest` → `mode: dev`,
      1 function discovered; dev dashboard reachable on :8288)
- [x] Repository initialized with README
### (Phase 2: Foundations)
- [x] Render a React Flow canvas
- [x] Adding nodes (toolbar button)
- [x] Connecting nodes (drag between handles)
- [x] Editing node prompts (inline textarea on decision nodes)
- [x] Edge types: YES path (green) / NO path (red)
- [x] Store graph state locally (`localStorage`, debounced autosave)
### (Phase 3: Build/Core)
- [x] Each node maps to an Inngest step (`step.run` per decision node)
- [x] Node prompt sent to an LLM (`classifyYesNo`, OpenAI `gpt-4o-mini`)
- [x] Model constrained to exactly YES or NO (system prompt + code-side
      normalization of the reply)
- [x] Execution continues based on the selected edge (`sourceHandle`
      `yes`/`no` lookup after each answer)
- [x] Execution order tracked (`trace` array, in the order nodes were
      visited) and shown in the UI
- [x] End-to-end workflow execution, dynamic node traversal, AI-powered
      branching logic — verified via the demo graph and a custom two-hop
      graph (see "Try it" above)
### (Phase 3: Build/Polish)
- [] Better node styling
- [] Error handling
- [] Animated active edges

## What's Included
- `src/app/api/inngest/route.ts` registers the Inngest client with the
  Next.js route handler. Confirmed working: `GET /api/inngest` returns
  `{"mode":"dev","function_count":1,...}` once `INNGEST_DEV=1` is set.
- `src/lib/inngest/functions.ts` has one smoke-test function, `decision-step`,
  triggered by a `workflow/decision.requested` event. It calls OpenAI
  (`gpt-4o-mini`) with a system prompt constraining the reply to `YES`/`NO`,
  proving the Inngest -> OpenAI path works end to end. Real per-node decision
  functions and the event contract between the canvas and Inngest are future
  work.
- `src/components/workflow/workflow-canvas.tsx` renders a small demo graph
  (start -> decision -> YES/NO) with React Flow, confirming the canvas,
  pan/zoom, and edge rendering work. This is scaffolding for the real
  node-graph editor, not the final UI.
- shadcn/ui is initialized (`components.json`, `button`, `card`, `badge`
  installed) for the node/panel UI in later phases.
- `src/components/workflow/nodes/` — custom React Flow node types:
  `start-node.tsx`, `decision-node.tsx` (editable prompt textarea, YES/NO
  source handles), `outcome-node.tsx`.
- `src/components/workflow/edges/branch-edge.tsx` — custom `yes`/`no` edge
  types (green/red, labeled). Dragging a connection from a decision node's
  YES or NO handle automatically assigns the matching edge type.
- `src/components/workflow/types.ts` — shared node/edge data types.
- `src/components/workflow/workflow-canvas.tsx` — now a real editor:
  - "+ Add decision node" / "Reset" toolbar buttons (top-left panel)
  - connect nodes by dragging between handles
  - edit a decision node's prompt inline
  - graph state (nodes + edges) autosaves to `localStorage`
    (`ai-workflow-graph-v1`), debounced, and reloads on refresh
- `src/lib/inngest/classify.ts` — `classifyYesNo(prompt)`, the single place
  that calls OpenAI (`gpt-4o-mini`) and normalizes the reply to exactly
  `YES`/`NO`. Shared by the Phase 1 smoke-test function and the real
  workflow runner. `OPENAI_STUB=1` skips the real call and returns a
  deterministic answer (hash of the prompt) so the whole pipeline can be
  exercised with no API key and no spend.
- `src/lib/inngest/graph.ts` — pure graph-traversal helpers
  (`findStartNode`, `findEdgeFrom`, `nodeById`) and the `ExecutionResult`/
  `ExecutionStep` types, kept separate from Inngest so the traversal logic
  is plain, readable code.
- `src/lib/inngest/functions.ts` — `runWorkflow`, triggered by
  `workflow/execute.requested`. Starting from the Start node, it walks the
  graph: **each decision node's prompt becomes its own `step.run`** (so a
  crash/retry resumes from the last completed node instead of redoing the
  whole walk), sends it to the model via `classifyYesNo`, and uses the
  YES/NO answer to pick which edge to follow next. Stops at an Outcome
  node, a decision node with no edge for the branch it picked, or after 25
  hops (guards against a cyclic graph). Publishes its own
  `workflow/execute.completed` event with the full result at the end.
- `src/app/api/workflow/run/route.ts` (`POST`) — takes the current
  `{ nodes, edges }` from the canvas, sends the `workflow/execute.requested`
  event, returns `{ requestId, eventId }`.
- `src/app/api/workflow/run/[requestId]/route.ts` (`GET`) — polled by the
  frontend. Looks for the matching `workflow/execute.completed` event and
  returns `{ status: "done", result }` once found; returns
  `{ status: "failed" }` if the underlying Inngest run failed; otherwise
  `{ status: "pending" }`.

  Note: the Inngest dev server's REST API (`/v1/runs/:id`) doesn't reliably
  populate a completed run's `output` field in this version, so status
  polling deliberately doesn't depend on it — the workflow's own
  `workflow/execute.completed` event is the source of truth for the result.
- `src/components/workflow/workflow-canvas.tsx` — "▶ Run workflow" button:
  posts the graph, polls every second (up to 30s) for a result, then
  highlights the exact path taken (nodes get a ring, traversed edges get
  thicker + animated) and shows an execution panel with the ordered
  decision trace and final outcome.

### Try it
With both dev servers running (see "Run it" above), click **Run workflow**
on the canvas. Example matching the assignment's sample graph:

```bash
curl -s -X POST http://localhost:3000/api/workflow/run -H "Content-Type: application/json" -d '{
  "nodes": [
    {"id":"start","type":"start","position":{"x":0,"y":0},"data":{"label":"Start"}},
    {"id":"d1","type":"decision","position":{"x":0,"y":0},"data":{"label":"Decision","prompt":"Is this a support request?"}},
    {"id":"o-support","type":"outcome","position":{"x":0,"y":0},"data":{"label":"Support Node"}},
    {"id":"o-sales","type":"outcome","position":{"x":0,"y":0},"data":{"label":"Sales Node"}}
  ],
  "edges": [
    {"id":"e1","source":"start","target":"d1"},
    {"id":"e2","source":"d1","sourceHandle":"yes","target":"o-support","type":"yes"},
    {"id":"e3","source":"d1","sourceHandle":"no","target":"o-sales","type":"no"}
  ]
}'
# {"requestId":"...","eventId":"..."}

curl -s "http://localhost:3000/api/workflow/run/<requestId>?eventId=<eventId>"
# {"status":"done","result":{"outcome":{"nodeId":"o-support","label":"Support Node"},
#   "status":"completed","trace":[{"nodeId":"d1","label":"Decision",
#   "prompt":"Is this a support request?","answer":"YES"}]}}
```

Verified working with both a single decision node and a two-decision-node
chain (each hop got its own Inngest step, in the correct order).

---

## Phase 1: Setup

Goal: initialize the project and prepare the development environment.

## Project structure
```
src/
  app/
    page.tsx               # Home page, renders the workflow canvas
    layout.tsx
    api/inngest/route.ts   # Inngest serve handler (GET/POST/PUT)
  components/
    ui/                    # shadcn/ui primitives (button, card, badge)
    workflow/
      workflow-canvas.tsx  # React Flow canvas (client component)
  lib/
    inngest/
      client.ts            # Inngest client
      functions.ts         # Workflow functions (decision-step smoke test)
```

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```
2. Copy the env template and fill in your OpenAI key:
   ```bash
   cp .env.example .env.local
   ```
   See [`.env.example`](.env.example) for what each variable does.

## Run it

Two processes run side by side in local dev: the Next.js app, and the Inngest
dev server (which discovers functions from the app and gives you a local
run dashboard).

```bash
# Terminal 1
npm run dev

# Terminal 2
npm run inngest:dev
```

- App: http://localhost:3000
- Inngest dev dashboard: http://localhost:8288

`npm run inngest:dev` runs `npx inngest-cli@latest dev` under the hood. On
first run it downloads a small platform binary, so the first startup is
slower than later ones.

`INNGEST_DEV=1` (set in `.env.local`) tells the SDK it's talking to the local
dev server instead of Inngest Cloud, so it skips signing-key verification.
Don't set it in production.

---


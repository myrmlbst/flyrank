# Week 7: Build an AI Decision Flow with React Flow + Inngest

A visual AI workflow system where each node represents an AI decision step that returns either YES or NO. The workflow execution should run through Inngest while the frontend visualizes the flow using React Flow.

## Tech Stack
TypeScript, Next.js, Inngest, Shadcn, React Flow, OpenAI SDK

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

## Deliverables
### (Phase 1)
- [x] Running frontend application (`npm run dev`, verified `GET /` → 200)
- [x] Working Inngest dev server (verified `GET /api/inngest` → `mode: dev`,
      1 function discovered; dev dashboard reachable on :8288)
- [x] Repository initialized with README
### (Phase 2)
- [x] Render a React Flow canvas
- [x] Adding nodes (toolbar button)
- [x] Connecting nodes (drag between handles)
- [x] Editing node prompts (inline textarea on decision nodes)
- [x] Edge types: YES path (green) / NO path (red)
- [x] Store graph state locally (`localStorage`, debounced autosave)


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

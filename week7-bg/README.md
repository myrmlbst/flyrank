# Week 7 (bg): Job System

A background job system, built up in stages starting from a plain API.

## Stack
- Python
- FastAPI
- Inngest

## Stage 0: Hello, server
- `GET /health` -> `{"status": "ok"}`

## Stage 1: Hire the worker (connect Inngest)
- Inngest client (`app_id="report-api"`), served at `/api/inngest`.
- One function, `say-hello`, triggered by the `test/hello` event: sleeps 5s
  (`ctx.step.sleep`), then returns `"Hello from the background!"`.
- Note: the Python SDK passes `step` as `ctx.step`, not as a second handler
  argument — the quick start's `(ctx, step)` signature is for other lanes.
- Note: the SDK talks to the dev server at `INNGEST_DEV` (default
  `127.0.0.1:8288`). If that port's taken, start the dev server on another
  port and export `INNGEST_DEV=http://127.0.0.1:<port>` before `uvicorn`.

### Run it
```bash
source venv/bin/activate
uvicorn main:app --port 8000
# second terminal
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest
```
Dashboard: http://localhost:8288 (or whatever port it lands on).

### Checkpoint
Invoked `say-hello` from the dashboard: run completed in ~5.1s (the sleep
step), output `"Hello from the background!"`. Confirmed 2026-08-26.

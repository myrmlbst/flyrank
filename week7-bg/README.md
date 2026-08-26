# Week 7 (bg): Job System

A background job system, built up in stages starting from a plain API.

## Tech Stack
- Python
- FastAPI
- Inngest

## Stage 0: Hello, server
- `GET /health` -> `{"status": "ok"}`

## Stage 1: Connect Inngest
- Inngest client (`app_id="report-api"`), served at `/api/inngest`
- One function, `say-hello`, triggered by the `test/hello` event: sleeps 5s
  (`ctx.step.sleep`), then returns `"Hello from the background!"`

## Running Locally
```bash
source venv/bin/activate
uvicorn main:app --port 8000
# second terminal
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest
```
Dashboard: http://localhost:8288

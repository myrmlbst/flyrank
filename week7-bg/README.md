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

## Stage 2: Accept now, work later
- `POST /reports` (`{"topic": "cats"}`) makes an id, saves it `pending` in
  an in-memory dict, sends `report/requested`, and returns `202` immediately
  (`{"id", "status": "pending"}`) — no slow work on the request path.
- `make-report` function, triggered by `report/requested`: `step.sleep` 8s,
  then `step.run` builds the result and marks the report `done`.
- `GET /reports/{id}` returns the saved object (`pending` -> `done` +
  `result`); unknown id -> `404`.

## Stage 3: Jobs fail. Watch the retry.
- `make-report` now has `retries=2`; the `build-report` step raises if
  `topic == "fail"`, so a `{"topic": "fail"}` request runs the full
  attempt-1 → backoff → attempt-2 → backoff → attempt-3 → `Failed` cycle,
  visible in the dashboard.
- `POST /reports` with no `topic` now returns `400` before anything is
  saved or sent — no report, no event, no Inngest run.
- The difference: a missing `topic` is wrong no matter when you send it, so
  it's rejected at the door (`400`); a broken oven might work if you just
  try again a moment later, so it's worth a retry.

## Running Locally
```bash
source venv/bin/activate
uvicorn main:app --port 8000
# second terminal
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest
```
Dashboard: http://localhost:8288

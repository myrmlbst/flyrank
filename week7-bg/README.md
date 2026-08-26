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
  (`{"id", "status": "pending"}`), no slow work on the request path.
- `make-report` function, triggered by `report/requested`: `step.sleep` 8s,
  then `step.run` builds the result and marks the report `done`.
- `GET /reports/{id}` returns the saved object (`pending` -> `done` +
  `result`); unknown id -> `404`.

## Stage 3: Watch the retry 
- `make-report` now has `retries=2`; the `build-report` step raises if
  `topic == "fail"`, so a `{"topic": "fail"}` request runs the full
  attempt-1 → backoff → attempt-2 → backoff → attempt-3 → `Failed` cycle,
  visible in the dashboard.
- `POST /reports` with no `topic` now returns `400` before anything is
  saved or sent. No report, no event, no Inngest run.
- The difference: a missing `topic` is wrong no matter when you send it, so
  it's rejected at the door (`400`); a broken oven might work if you just
  try again a moment later, so it's worth a retry.

## Stage 4: The clock knocks (cron)
- `heartbeat` is triggered by a cron schedule, not an event:
  `inngest.TriggerCron(cron="* * * * *")` (every minute, for testing purposes).
- Each run counts `reports` by status and prints/returns one line:
  `heartbeat: N pending, N done, N failed`.
- Every day at 08:00: `0 8 * * *`. Every Sunday at 22:00: `0 22 * * 0`
  (built on crontab.guru; servers run cron in UTC, so check the timezone
  before trusting either).
- Caveat: `failed` always reads `0` for now. `make-report` never sets
  `status: "failed"` after exhausting retries, it just stays `pending`
  forever (see Stage 3).

## Running Locally
```bash
source venv/bin/activate
uvicorn main:app --port 8000
# second terminal
npx inngest-cli@latest dev -u http://localhost:8000/api/inngest
```
Dashboard: http://localhost:8288


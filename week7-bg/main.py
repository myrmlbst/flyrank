import datetime
import uuid

import inngest
import inngest.fast_api
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Job System API", version="1.0")

inngest_client = inngest.Inngest(app_id="report-api", is_production=False)

reports: dict[str, dict] = {}


@inngest_client.create_function(
    fn_id="say-hello",
    trigger=inngest.TriggerEvent(event="test/hello"),
)
async def say_hello(ctx: inngest.Context) -> str:
    await ctx.step.sleep("wait-a-moment", datetime.timedelta(seconds=5))
    return "Hello from the background!"


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,
)
async def make_report(ctx: inngest.Context) -> str:
    await ctx.step.sleep("do-the-slow-work", datetime.timedelta(seconds=8))

    async def build_report() -> str:
        report_id = ctx.event.data["id"]
        topic = ctx.event.data["topic"]
        if topic == "fail":
            raise Exception("The report oven is broken!")
        result = f"Report on {topic!r}: this is a stand-in for a real result."
        reports[report_id]["status"] = "done"
        reports[report_id]["result"] = result
        return result

    return await ctx.step.run("build-report", build_report)


@inngest_client.create_function(
    fn_id="heartbeat",
    trigger=inngest.TriggerCron(cron="* * * * *"),
)
async def heartbeat(ctx: inngest.Context) -> str:
    pending = sum(1 for r in reports.values() if r["status"] == "pending")
    done = sum(1 for r in reports.values() if r["status"] == "done")
    failed = sum(1 for r in reports.values() if r["status"] == "failed")
    summary = f"heartbeat: {pending} pending, {done} done, {failed} failed"
    print(summary, flush=True)
    return summary


inngest.fast_api.serve(app, inngest_client, [say_hello, make_report, heartbeat])


class ReportRequest(BaseModel):
    topic: str | None = None


@app.post("/reports", status_code=202, summary="Request a report")
async def create_report(body: ReportRequest):
    if not body.topic:
        raise HTTPException(status_code=400, detail="topic is required")

    report_id = str(uuid.uuid4())
    reports[report_id] = {"id": report_id, "topic": body.topic, "status": "pending"}
    await inngest_client.send(
        inngest.Event(
            name="report/requested",
            data={"id": report_id, "topic": body.topic},
        )
    )
    return {"id": report_id, "status": "pending"}


@app.get("/reports/{report_id}", summary="Check a report's status")
def get_report(report_id: str):
    report = reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/health", summary="Health check")
def health():
    return {"status": "ok"}


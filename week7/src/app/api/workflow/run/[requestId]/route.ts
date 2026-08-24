import { NextResponse } from "next/server";
import type { ExecutionResult } from "@/lib/inngest/graph";

const INNGEST_BASE_URL = process.env.INNGEST_BASE_URL ?? "http://localhost:8288";

type InngestEvent = {
  id: string;
  name: string;
  data: { requestId: string; result: ExecutionResult };
};

type RunSummary = { status: string };

export async function GET(
  request: Request,
  { params }: { params: Promise<{ requestId: string }> },
) {
  const { requestId } = await params;
  const eventId = new URL(request.url).searchParams.get("eventId");

  // Fast path: the function's own completion event carries the full result.
  // (The dev server's /v1/runs "output" field is unreliable for this, so we
  // don't rely on it -- see README.)
  const eventsRes = await fetch(`${INNGEST_BASE_URL}/v1/events?limit=25`, {
    cache: "no-store",
  });
  if (eventsRes.ok) {
    const { data } = (await eventsRes.json()) as { data: InngestEvent[] };
    const match = data.find(
      (e) =>
        e.name === "workflow/execute.completed" &&
        e.data.requestId === requestId,
    );
    if (match) {
      return NextResponse.json({ status: "done", result: match.data.result });
    }
  }

  // No completion event yet -- check whether the underlying run already
  // failed (e.g. exhausted OpenAI retries) so the frontend isn't stuck
  // polling for an event that will never arrive.
  if (eventId) {
    const runsRes = await fetch(
      `${INNGEST_BASE_URL}/v1/events/${eventId}/runs`,
      { cache: "no-store" },
    );
    if (runsRes.ok) {
      const { data } = (await runsRes.json()) as { data: RunSummary[] };
      if (data.some((run) => run.status === "Failed")) {
        return NextResponse.json({ status: "failed" });
      }
    }
  }

  return NextResponse.json({ status: "pending" });
}

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
  try {
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
  } catch {
    // Inngest dev server unreachable -- fall through to the same signal the
    // frontend uses for any other failure, with a message pointing at why.
    return NextResponse.json({
      status: "failed",
      error: `Can't reach the Inngest dev server at ${INNGEST_BASE_URL}. Is "npm run inngest:dev" running?`,
    });
  }

  // No completion event yet -- check whether the underlying run already
  // failed (e.g. exhausted OpenAI retries) so the frontend isn't stuck
  // polling for an event that will never arrive.
  if (eventId) {
    try {
      const runsRes = await fetch(
        `${INNGEST_BASE_URL}/v1/events/${eventId}/runs`,
        { cache: "no-store" },
      );
      if (runsRes.ok) {
        const { data } = (await runsRes.json()) as { data: RunSummary[] };
        if (data.some((run) => run.status === "Failed")) {
          return NextResponse.json({
            status: "failed",
            error: "The Inngest run failed. Check the dev dashboard (localhost:8288) for details.",
          });
        }
      }
    } catch {
      // Already succeeded once above in this same request, so treat a
      // transient failure here as "still pending" rather than erroring out.
    }
  }

  return NextResponse.json({ status: "pending" });
}

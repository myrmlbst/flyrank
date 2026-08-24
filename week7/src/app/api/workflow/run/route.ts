import { randomUUID } from "crypto";
import { NextResponse } from "next/server";
import { inngest } from "@/lib/inngest/client";
import { validateGraph } from "@/lib/inngest/graph";

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Request body must be valid JSON" },
      { status: 400 },
    );
  }

  const { nodes, edges } = (body ?? {}) as { nodes?: unknown; edges?: unknown };
  const inputError = validateGraph(nodes, edges);
  if (inputError) {
    return NextResponse.json({ error: inputError }, { status: 400 });
  }

  const requestId = randomUUID();

  try {
    const { ids } = await inngest.send({
      name: "workflow/execute.requested",
      data: { requestId, nodes, edges },
    });
    return NextResponse.json({ requestId, eventId: ids[0] });
  } catch (cause) {
    // Most commonly: the local Inngest dev server isn't running.
    return NextResponse.json(
      {
        error: `Couldn't reach Inngest -- is the dev server running (npm run inngest:dev)? ${
          cause instanceof Error ? cause.message : String(cause)
        }`,
      },
      { status: 502 },
    );
  }
}

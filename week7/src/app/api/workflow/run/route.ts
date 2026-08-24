import { randomUUID } from "crypto";
import { NextResponse } from "next/server";
import { inngest } from "@/lib/inngest/client";

export async function POST(request: Request) {
  const { nodes, edges } = await request.json();
  const requestId = randomUUID();

  const { ids } = await inngest.send({
    name: "workflow/execute.requested",
    data: { requestId, nodes, edges },
  });

  return NextResponse.json({ requestId, eventId: ids[0] });
}

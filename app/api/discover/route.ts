import { NextRequest, NextResponse } from "next/server";
import { startDiscovery } from "@/lib/discovery";
import { SearchQuery } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Start a live discovery session. Returns immediately with the session id and
// the H Agent View URL so the UI can show the agent browsing live.
export async function POST(req: NextRequest) {
  let q: SearchQuery;
  try {
    q = (await req.json()) as SearchQuery;
  } catch {
    return NextResponse.json({ error: "invalid body" }, { status: 400 });
  }
  try {
    const rec = await startDiscovery(q);
    return NextResponse.json({
      sessionId: rec.sessionId,
      agentViewUrl: rec.agentViewUrl,
      status: rec.status,
    });
  } catch (err) {
    return NextResponse.json({ error: (err as Error).message }, { status: 502 });
  }
}

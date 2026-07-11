import { NextRequest, NextResponse } from "next/server";
import { getDiscovery } from "@/lib/discovery";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Poll a discovery session: live status + streamed steps + listings (once ready).
export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  const rec = getDiscovery(params.id);
  if (!rec) return NextResponse.json({ error: "unknown session" }, { status: 404 });
  return NextResponse.json({
    status: rec.status,
    events: rec.events,
    listings: rec.listings, // null until ready
    source: rec.source,
    agentViewUrl: rec.agentViewUrl,
    error: rec.error ?? null,
  });
}

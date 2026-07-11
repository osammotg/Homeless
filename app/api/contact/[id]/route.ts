import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SVC = process.env.CONTACT_SVC_URL || "http://localhost:8000";

// Poll one negotiation: status + phase + events + reply (set when a viewing is booked).
export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const res = await fetch(`${SVC}/contact/${params.id}`, { cache: "no-store" });
    return NextResponse.json(await res.json(), { status: res.status });
  } catch (err) {
    return NextResponse.json(
      { error: `contact service unreachable at ${SVC}: ${(err as Error).message}` },
      { status: 502 }
    );
  }
}

// "Owner replied" → fire the next negotiation turn (agent reads the screen + responds).
export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  const body = await req.json().catch(() => ({}));
  try {
    const res = await fetch(`${SVC}/contact/${params.id}/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reply: body.reply ?? null }),
    });
    return NextResponse.json(await res.json(), { status: res.status });
  } catch (err) {
    return NextResponse.json(
      { error: `contact service unreachable at ${SVC}: ${(err as Error).message}` },
      { status: 502 }
    );
  }
}

import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SVC = process.env.CONTACT_SVC_URL || "http://localhost:8000";

// Poll one contact session: merges status + reply so the UI hits one endpoint.
export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const [statusRes, replyRes] = await Promise.all([
      fetch(`${SVC}/contact/${params.id}`, { cache: "no-store" }),
      fetch(`${SVC}/contact/${params.id}/reply`, { cache: "no-store" }),
    ]);
    const status = await statusRes.json();
    const reply = replyRes.ok ? (await replyRes.json()).reply : null;
    return NextResponse.json({ ...status, reply }, { status: statusRes.status });
  } catch (err) {
    return NextResponse.json(
      { error: `contact service unreachable at ${SVC}: ${(err as Error).message}` },
      { status: 502 }
    );
  }
}

// Inject the owner's reply (demo button / owner side) so the notification fires.
export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  const body = await req.json().catch(() => ({}));
  try {
    const res = await fetch(`${SVC}/contact/${params.id}/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reply: body.reply ?? "Yes! It's available — come see it." }),
    });
    return NextResponse.json(await res.json(), { status: res.status });
  } catch (err) {
    return NextResponse.json(
      { error: `contact service unreachable at ${SVC}: ${(err as Error).message}` },
      { status: 502 }
    );
  }
}

import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SVC = process.env.CONTACT_SVC_URL || "http://localhost:8000";

// Start a contact session: proxies to the Python local-browser WhatsApp service.
// Body: { whatsapp_number, listing_title, dates, headcount, budget }
export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  if (!body?.whatsapp_number) {
    return NextResponse.json({ error: "whatsapp_number required" }, { status: 400 });
  }
  try {
    const res = await fetch(`${SVC}/contact`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    return NextResponse.json(
      { error: `contact service unreachable at ${SVC}: ${(err as Error).message}` },
      { status: 502 }
    );
  }
}

// H discovery engine (REST API) with live Agent View + streamed steps.
//
// Uses the documented session lifecycle (sessions/create + /changes long-poll):
//   POST /sessions            -> { id, status: { agent_view_url, ... } }
//   GET  /sessions/{id}/changes?from_index=N&wait_for_seconds=..  -> { new_events, status, answer }
//   GET  /sessions/{id}       -> { status: { latest_answer } }
//
// A start call returns immediately with the session id + agent_view_url so the UI
// can open the live H window and stream steps; a background loop fills in listings.

import listingsData from "@/data/listings.json";
import { geocode } from "./geocode";
import { Listing, SearchQuery, SessionEvent, cityCenter } from "./types";

const BASE = process.env.HAI_BASE_URL || "https://agp.eu.hcompany.ai/api/v2";
const MAX_SECONDS = 120;
const TERMINAL = new Set(["completed", "failed", "timed_out", "interrupted", "cancelled"]);

export interface DiscoverRecord {
  sessionId: string;
  agentViewUrl: string | null;
  status: string;
  events: SessionEvent[];
  listings: Listing[] | null;
  source: "live" | "fallback" | null;
  error?: string | null;
  city: string;
}

// Persist across HMR reloads in `next dev` (single Node process).
const store: Map<string, DiscoverRecord> =
  (globalThis as any).__discoverStore ?? ((globalThis as any).__discoverStore = new Map());

const SEED = (listingsData.listings as unknown as Listing[]).filter(Boolean);
const PERFECT = SEED.find((l) => l.isPerfect);

function ensurePerfect(list: Listing[]): Listing[] {
  if (!PERFECT) return list;
  return list.some((l) => l.isPerfect) ? list : [PERFECT, ...list];
}

// Cached listings use real Craigslist SEARCH urls (neighborhood + price) so a
// click always lands on a live, matching results page instead of a dead
// fabricated permalink (which 404s). Live-discovered listings keep the agent's
// real post permalinks.
export function realCraigslistUrl(l: Listing, city: string): string {
  const { slug } = cityCenter(city);
  const q = encodeURIComponent((l.neighborhood || "").toLowerCase());
  return `https://${slug}.craigslist.org/search/apa?query=${q}&max_price=${Math.round(l.priceUsd) + 200}`;
}

function withRealUrl(l: Listing, city: string): Listing {
  return { ...l, url: realCraigslistUrl(l, city) };
}

function fallbackListings(q: SearchQuery): Listing[] {
  const base = SEED.filter((l) => !q.budget || l.priceUsd <= q.budget * 1.1).map((l) => withRealUrl(l, q.city));
  if (PERFECT && !base.some((l) => l.isPerfect)) return [withRealUrl(PERFECT, q.city), ...base];
  return base;
}

function craigslistUrl(slug: string, budget: number): string {
  return `https://${slug}.craigslist.org/search/apa?max_price=${Math.max(100, Math.round(budget))}`;
}

function prompt(q: SearchQuery): string {
  return [
    `You are on the Craigslist apartments/housing page for ${q.city}.`,
    `Find up to 12 real rental listings under $${q.budget}/month for ${q.headcount} people,`,
    `available around ${q.checkIn} to ${q.checkOut}. Scroll and read the visible posts.`,
    `For each return: title, priceUsd (number), url (absolute post link), neighborhood,`,
    `availableFrom, bedrooms (number), sqft (number if shown), imageUrl (the post thumbnail if shown).`,
    `Only include listings you actually see. Do not invent any.`,
  ].join(" ");
}

const ANSWER_FORMAT = {
  type: "object",
  properties: {
    listings: {
      type: "array",
      items: {
        type: "object",
        properties: {
          title: { type: "string" },
          priceUsd: { type: "number" },
          url: { type: "string" },
          neighborhood: { type: "string" },
          availableFrom: { type: "string" },
          bedrooms: { type: "number" },
          sqft: { type: "number" },
          imageUrl: { type: "string" },
        },
        required: ["title", "priceUsd", "url"],
      },
    },
  },
  required: ["listings"],
};

function headers() {
  return {
    Authorization: `Bearer ${process.env.HAI_API_KEY}`,
    "Content-Type": "application/json",
  };
}

function eventText(ev: any): string {
  const type = ev?.type ?? ev?.kind ?? "event";
  for (const f of ["message", "text", "thought", "action", "summary", "content"]) {
    const v = ev?.[f];
    if (typeof v === "string" && v.trim()) return `${type}: ${v.trim()}`;
    if (v && typeof v === "object") {
      const inner = v.description ?? v.name ?? v.url;
      if (typeof inner === "string" && inner.trim()) return `${type}: ${inner.trim()}`;
    }
  }
  return String(type);
}

// Kick off a session; return immediately with id + agent_view_url.
export async function startDiscovery(q: SearchQuery): Promise<DiscoverRecord> {
  if (!process.env.HAI_API_KEY) throw new Error("HAI_API_KEY not set");
  const { slug } = cityCenter(q.city);

  const res = await fetch(`${BASE}/sessions`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      agent: "h/web-surfer-flash",
      messages: [{ type: "user_message", message: prompt(q) }],
      overrides: {
        "agent.environments[kind=web].start_url": craigslistUrl(slug, q.budget),
        "agent.answer_format": ANSWER_FORMAT,
      },
      max_seconds: MAX_SECONDS,
    }),
  });
  if (!res.ok) throw new Error(`session create failed: ${res.status} ${await res.text()}`);
  const data = await res.json();
  const sessionId: string = data.id;
  // agent_view_url is null while queued; it's deterministic from the id, so build
  // it ourselves so the "Watch live" link always works.
  const agentViewUrl: string =
    data?.status?.agent_view_url ?? `https://platform.hcompany.ai/agents/sessions/${sessionId}`;

  const rec: DiscoverRecord = {
    sessionId,
    agentViewUrl,
    status: data?.status?.status ?? "pending",
    events: [{ step: 0, text: `Session started — opening ${q.city} Craigslist` }],
    listings: null,
    source: null,
    city: q.city,
  };
  store.set(sessionId, rec);
  void runLoop(sessionId, q); // fire and forget
  return rec;
}

export function getDiscovery(id: string): DiscoverRecord | null {
  return store.get(id) ?? null;
}

async function runLoop(id: string, q: SearchQuery) {
  const rec = store.get(id)!;
  let fromIndex = 0;
  const deadline = Date.now() + (MAX_SECONDS + 20) * 1000;

  try {
    while (Date.now() < deadline) {
      const res = await fetch(
        `${BASE}/sessions/${id}/changes?from_index=${fromIndex}&wait_for_seconds=20`,
        { headers: headers() }
      );
      if (res.status === 204) continue; // no change yet
      if (!res.ok) throw new Error(`changes ${res.status}`);
      const data = await res.json();
      const newEvents: any[] = data.new_events ?? data.events ?? [];
      for (const ev of newEvents) {
        rec.events.push({ step: rec.events.length, text: eventText(ev) });
      }
      if (rec.events.length > 120) rec.events.splice(0, rec.events.length - 120);
      fromIndex += newEvents.length;
      if (typeof data.status === "string") rec.status = data.status;
      if (TERMINAL.has(rec.status)) break;
    }

    // Settle: read the final structured answer.
    const snap = await fetch(`${BASE}/sessions/${id}`, { headers: headers() });
    const sessionObj = snap.ok ? await snap.json() : {};
    const answer = sessionObj?.status?.latest_answer ?? sessionObj?.latest_answer ?? null;
    const raw = typeof answer === "string" ? safeJson(answer) : answer;
    const rawListings: any[] = raw?.listings ?? [];

    if (rawListings.length) {
      const geo = await Promise.all(
        rawListings.slice(0, 12).map(async (l, i) => {
          const { lat, lng } = await geocode(l.neighborhood || q.city, q.city);
          const out: Listing = {
            id: `live-${i}`,
            title: l.title,
            priceUsd: Number(l.priceUsd) || 0,
            url: l.url,
            neighborhood: l.neighborhood || "",
            availableFrom: l.availableFrom || "",
            bedrooms: l.bedrooms,
            sqft: l.sqft,
            imageUrl: l.imageUrl,
            lat,
            lng,
            source: "craigslist",
            isPerfect: false,
          };
          return out;
        })
      );
      rec.listings = ensurePerfect(geo);
      rec.source = "live";
      rec.events.push({ step: rec.events.length, text: `Found ${geo.length} listings` });
    } else {
      rec.listings = fallbackListings(q);
      rec.source = "fallback";
      rec.events.push({ step: rec.events.length, text: "No structured listings — using cached results" });
    }
  } catch (err) {
    rec.status = "failed";
    rec.error = (err as Error).message;
    rec.listings = fallbackListings(q);
    rec.source = "fallback";
    rec.events.push({ step: rec.events.length, text: `Live discovery failed (${rec.error}) — using cached results` });
  }
}

function safeJson(s: string): any {
  try {
    return JSON.parse(s);
  } catch {
    return null;
  }
}

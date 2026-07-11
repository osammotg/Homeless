// H Company discovery client (cloud browser, text-mode) for the Next.js side.
//
// Written against the H docs (quickstart + structured-output):
//   - `new HaiAgentsClient()` reads HAI_API_KEY from the env, EU region by default.
//   - `runSession({ agent, messages, overrides, answerSchema })` runs a browser
//     session and returns a typed answer parsed against the Zod schema.
//   - We use the prebuilt `h/web-surfer-flash` agent and override its web
//     environment's start_url to the city's Craigslist housing page.
//
// The SDK is imported dynamically and typed as `any` so a missing/renamed export
// never hard-fails the build — the discover route catches errors and falls back
// to the cached listings, which is the demo-safety contract from the spec.

import { ListingsSchema, SearchQuery, cityCenter } from "./types";

const DISCOVERY_TIMEOUT_MS = 90_000;

function craigslistUrl(citySlug: string, budget: number): string {
  // Craigslist apartments/housing search, price-capped.
  return `https://${citySlug}.craigslist.org/search/apa?max_price=${Math.max(
    100,
    Math.round(budget)
  )}`;
}

function discoveryPrompt(q: SearchQuery): string {
  return [
    `You are on the Craigslist apartments/housing page for ${q.city}.`,
    `Find up to 12 real rental listings that fit this search:`,
    `- budget: total under $${q.budget}/month`,
    `- for ${q.headcount} people`,
    `- available around ${q.checkIn} to ${q.checkOut}`,
    `Scroll the results and read the visible listings. For each, return:`,
    `title, priceUsd (a number, no $ or commas), url (absolute link to the post),`,
    `neighborhood (the area/hood shown), availableFrom (date if shown), bedrooms (number if shown).`,
    `Only include listings you actually see on the page. Do not invent any.`,
  ].join(" ");
}

export interface DiscoverResult {
  listings: {
    title: string;
    priceUsd: number;
    url: string;
    neighborhood: string;
    availableFrom: string;
    bedrooms?: number;
  }[];
  source: "live" | "fallback";
}

// Runs the live H discovery session. Throws on any failure or timeout so the
// caller can fall back to cached data.
export async function discoverLive(q: SearchQuery): Promise<DiscoverResult> {
  const apiKey = process.env.HAI_API_KEY;
  if (!apiKey) throw new Error("HAI_API_KEY not set");

  const mod: any = await import("hai-agents");
  const HaiAgentsClient = mod.HaiAgentsClient ?? mod.default?.HaiAgentsClient;
  if (!HaiAgentsClient) throw new Error("hai-agents client export not found");

  const client = new HaiAgentsClient(); // reads HAI_API_KEY, EU region default
  const { slug } = cityCenter(q.city);
  const startUrl = craigslistUrl(slug, q.budget);

  const run = client.runSession({
    agent: "h/web-surfer-flash",
    messages: discoveryPrompt(q),
    overrides: { "agent.environments[kind=web].start_url": startUrl },
    answerSchema: ListingsSchema,
  });

  const timeout = new Promise<never>((_, reject) =>
    setTimeout(() => reject(new Error("discovery timeout")), DISCOVERY_TIMEOUT_MS)
  );

  const result: any = await Promise.race([run, timeout]);
  const answer = result?.answer ?? result?.finalAnswer;
  const parsed = ListingsSchema.parse(answer);

  return {
    listings: parsed.listings.map((l) => ({
      title: l.title,
      priceUsd: l.priceUsd,
      url: l.url,
      neighborhood: l.neighborhood ?? "",
      availableFrom: l.availableFrom ?? "",
      bedrooms: l.bedrooms,
    })),
    source: "live",
  };
}

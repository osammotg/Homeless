import { NextRequest, NextResponse } from "next/server";
import listingsData from "@/data/listings.json";
import { discoverLive } from "@/lib/hai";
import { geocode } from "@/lib/geocode";
import { Listing, SearchQuery } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SEED = (listingsData.listings as unknown as Listing[]).filter(Boolean);
const PERFECT = SEED.find((l) => l.isPerfect);

function withinBudget(l: Listing, budget: number) {
  return !budget || l.priceUsd <= budget * 1.1; // small headroom
}

// Guarantee the controlled "perfect listing" is always present so the contact
// money-shot has a real target, regardless of live vs fallback discovery.
function ensurePerfect(list: Listing[]): Listing[] {
  if (!PERFECT) return list;
  if (list.some((l) => l.isPerfect)) return list;
  return [PERFECT, ...list];
}

export async function POST(req: NextRequest) {
  let q: SearchQuery;
  try {
    q = (await req.json()) as SearchQuery;
  } catch {
    return NextResponse.json({ error: "invalid body" }, { status: 400 });
  }

  // 1) Try live H discovery on real Craigslist.
  try {
    const live = await discoverLive(q);
    if (live.listings.length) {
      const geo = await Promise.all(
        live.listings.slice(0, 12).map(async (l, i) => {
          const { lat, lng } = await geocode(l.neighborhood || q.city, q.city);
          const out: Listing = {
            id: `live-${i}`,
            title: l.title,
            priceUsd: l.priceUsd,
            url: l.url,
            neighborhood: l.neighborhood || "",
            availableFrom: l.availableFrom || "",
            bedrooms: l.bedrooms,
            lat,
            lng,
            source: "craigslist",
            isPerfect: false,
          };
          return out;
        })
      );
      return NextResponse.json({ listings: ensurePerfect(geo), source: "live" });
    }
  } catch (err) {
    // fall through to cached data — demo-safety contract
    console.warn("[discover] live failed, using fallback:", (err as Error).message);
  }

  // 2) Fallback: cached listings (filtered to the requested budget).
  const fallback = ensurePerfect(SEED.filter((l) => withinBudget(l, q.budget)));
  return NextResponse.json({ listings: fallback, source: "fallback" });
}

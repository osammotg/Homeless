import { NextResponse } from "next/server";
import listingsData from "@/data/listings.json";
import { realCraigslistUrl } from "@/lib/discovery";
import { Listing } from "@/lib/types";

export const runtime = "nodejs";

// Emergency fallback: cached listings, used by the UI only if a live discovery
// session can't even be created. URLs are rewritten to real Craigslist searches
// so links resolve instead of 404-ing on fabricated permalinks.
export async function GET() {
  const city = (listingsData as any).city || "san francisco";
  const listings = (listingsData.listings as unknown as Listing[])
    .filter(Boolean)
    .map((l) => ({ ...l, url: realCraigslistUrl(l, city) }));
  return NextResponse.json({ listings, source: "fallback" });
}

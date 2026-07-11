import { NextResponse } from "next/server";
import listingsData from "@/data/listings.json";
import { Listing } from "@/lib/types";

export const runtime = "nodejs";

// Emergency fallback: cached listings, used by the UI only if a live discovery
// session can't even be created (network/key failure).
export async function GET() {
  const listings = (listingsData.listings as unknown as Listing[]).filter(Boolean);
  return NextResponse.json({ listings, source: "fallback" });
}

import { z } from "zod";

// A single apartment listing shown on the map.
export const ListingSchema = z.object({
  id: z.string(),
  title: z.string(),
  priceUsd: z.number(),
  url: z.string(),
  neighborhood: z.string().optional().default(""),
  lat: z.number(),
  lng: z.number(),
  availableFrom: z.string().optional().default(""), // ISO date or free text
  bedrooms: z.number().optional(),
  sqft: z.number().optional(),
  imageUrl: z.string().optional(),
  source: z.string().optional().default("craigslist"),
  // The controlled "perfect listing" the agent contacts. Carries the owner's WhatsApp number.
  isPerfect: z.boolean().optional().default(false),
  whatsapp: z.string().optional(),
});
export type Listing = z.infer<typeof ListingSchema>;

// What the H discovery agent returns (typed answer).
export const ListingsSchema = z.object({
  listings: z.array(
    z.object({
      title: z.string(),
      priceUsd: z.number(),
      url: z.string(),
      neighborhood: z.string().optional().default(""),
      availableFrom: z.string().optional().default(""),
      bedrooms: z.number().optional(),
    })
  ),
});
export type Listings = z.infer<typeof ListingsSchema>;

export interface SearchQuery {
  city: string;
  checkIn: string;
  checkOut: string;
  budget: number;
  headcount: number;
}

// One step of a running H session, surfaced in the Agent View panel.
export interface SessionEvent {
  step: number;
  text: string;
  ts?: string;
}

export interface ContactStatus {
  status: string; // pending | running | completed | failed | ...
  events: SessionEvent[];
  answer?: string | null;
  reply?: string | null;
  outcome?: string | null;
  error?: string | null;
  agent_view_url?: string | null;
  hai_session_id?: string | null;
}

// City centers for proximity filtering + initial map view.
export const CITY_CENTERS: Record<string, { lat: number; lng: number; slug: string }> = {
  "san francisco": { lat: 37.7749, lng: -122.4194, slug: "sfbay" },
  "new york": { lat: 40.7128, lng: -74.006, slug: "newyork" },
  "los angeles": { lat: 34.0522, lng: -118.2437, slug: "losangeles" },
  chicago: { lat: 41.8781, lng: -87.6298, slug: "chicago" },
  austin: { lat: 30.2672, lng: -97.7431, slug: "austin" },
};

export function cityCenter(city: string) {
  return CITY_CENTERS[city.trim().toLowerCase()] ?? CITY_CENTERS["san francisco"];
}

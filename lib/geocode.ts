import { cityCenter } from "./types";

const cache = new Map<string, { lat: number; lng: number }>();

// Free geocoder (OpenStreetMap Nominatim). Best-effort: on any failure we fall
// back to a small deterministic jitter around the city center so pins never pile
// up on one point. Nominatim asks for a descriptive User-Agent.
export async function geocode(
  place: string,
  city: string
): Promise<{ lat: number; lng: number }> {
  const key = `${place}|${city}`.toLowerCase();
  const hit = cache.get(key);
  if (hit) return hit;

  const center = cityCenter(city);
  try {
    const q = encodeURIComponent(`${place}, ${city}`);
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${q}`,
      { headers: { "User-Agent": "Homeless-ApartmentAgent/0.1 (hackathon demo)" } }
    );
    if (res.ok) {
      const data: any[] = await res.json();
      if (data.length) {
        const out = { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) };
        cache.set(key, out);
        return out;
      }
    }
  } catch {
    // fall through to jitter
  }

  // Deterministic jitter around city center based on the place string.
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  const jitter = (n: number) => ((n % 1000) / 1000 - 0.5) * 0.06; // ~±3km
  const out = { lat: center.lat + jitter(h), lng: center.lng + jitter(h >> 3) };
  cache.set(key, out);
  return out;
}

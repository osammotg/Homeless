"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Listing } from "@/lib/types";

function pin(l: Listing) {
  return L.divIcon({
    className: "",
    html: `<div class="price-pin ${l.isPerfect ? "perfect" : ""}">$${l.priceUsd}</div>`,
    iconSize: [0, 0],
    iconAnchor: [24, 12],
  });
}

function FitBounds({ listings }: { listings: Listing[] }) {
  const map = useMap();
  useEffect(() => {
    if (!listings.length) return;
    const bounds = L.latLngBounds(listings.map((l) => [l.lat, l.lng] as [number, number]));
    map.fitBounds(bounds, { padding: [60, 60], maxZoom: 14 });
  }, [listings, map]);
  return null;
}

export default function ListingMap({
  listings,
  center,
  onReach,
}: {
  listings: Listing[];
  center: { lat: number; lng: number };
  onReach: (l: Listing) => void;
}) {
  return (
    <MapContainer center={[center.lat, center.lng]} zoom={12} scrollWheelZoom>
      <TileLayer
        attribution='&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap'
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      <FitBounds listings={listings} />
      {listings.map((l) => (
        <Marker key={l.id} position={[l.lat, l.lng]} icon={pin(l)}>
          <Popup>
            <div style={{ minWidth: 200, maxWidth: 240 }}>
              {l.imageUrl && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={l.imageUrl}
                  alt={l.title}
                  style={{ width: "100%", height: 120, objectFit: "cover", borderRadius: 6, marginBottom: 6 }}
                />
              )}
              <a href={l.url} target="_blank" rel="noreferrer" style={{ fontWeight: 700, color: "#111", textDecoration: "none" }}>
                {l.title}
              </a>
              <div style={{ color: "#0a7", fontWeight: 700, marginTop: 2 }}>
                ${l.priceUsd}/mo
                <span style={{ color: "#666", fontWeight: 500, fontSize: 12 }}>
                  {l.bedrooms === 0 ? " · Studio" : l.bedrooms ? ` · ${l.bedrooms} BR` : ""}
                  {l.sqft ? ` · ${l.sqft} ft²` : ""}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "#555" }}>
                {l.neighborhood} {l.availableFrom ? `· from ${l.availableFrom}` : ""}
              </div>
              {l.isPerfect && (
                <button
                  onClick={() => onReach(l)}
                  style={{
                    marginTop: 8,
                    background: "#34d399",
                    border: "none",
                    borderRadius: 6,
                    padding: "6px 10px",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Reach out on WhatsApp
                </button>
              )}
            </div>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}

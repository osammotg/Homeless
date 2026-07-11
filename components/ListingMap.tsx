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
            <div style={{ minWidth: 180 }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>{l.title}</div>
              <div style={{ color: "#0a7", fontWeight: 700 }}>${l.priceUsd}/mo</div>
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

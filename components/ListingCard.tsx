"use client";

import { Listing } from "@/lib/types";

function beds(l: Listing) {
  if (l.bedrooms === 0) return "Studio";
  if (l.bedrooms) return `${l.bedrooms} BR`;
  return null;
}

// Rich card: thumbnail, linked title, price, beds/size, distance, contact CTA.
export default function ListingCard({
  l,
  distanceKm,
  onReach,
  contacting,
}: {
  l: Listing;
  distanceKm: number;
  onReach?: (l: Listing) => void;
  contacting?: boolean;
}) {
  return (
    <div className={`card ${l.isPerfect ? "perfect" : ""}`}>
      {l.isPerfect && <span className="perfect-tag">◆ best match · contactable</span>}
      <div className="card-body">
        {l.imageUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img className="thumb" src={l.imageUrl} alt={l.title} loading="lazy" />
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <a className="title link" href={l.url} target="_blank" rel="noreferrer" title={l.title}>
            {l.title}
          </a>
          <div className="meta">
            <span className="price">${l.priceUsd}/mo</span>
            {beds(l) && <span>{beds(l)}</span>}
            {l.sqft ? <span>{l.sqft} ft²</span> : null}
          </div>
          <div className="meta">
            <span>{l.neighborhood}</span>
            <span>· {Math.round(distanceKm * 10) / 10} km</span>
            {l.availableFrom && <span>· from {l.availableFrom}</span>}
          </div>
        </div>
      </div>
      {l.isPerfect && onReach && (
        <button className="primary" style={{ marginTop: 8 }} onClick={() => onReach(l)} disabled={contacting}>
          {contacting ? "Contacting…" : "Reach out on WhatsApp"}
        </button>
      )}
    </div>
  );
}

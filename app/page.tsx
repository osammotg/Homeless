"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import SearchForm from "@/components/SearchForm";
import FilterPanel, { Filters } from "@/components/FilterPanel";
import AgentViewPanel from "@/components/AgentViewPanel";
import Toast from "@/components/Toast";
import { ContactStatus, Listing, SearchQuery, cityCenter } from "@/lib/types";

// Leaflet must not render on the server.
const ListingMap = dynamic(() => import("@/components/ListingMap"), { ssr: false });

type Phase = "idle" | "discovering" | "results" | "contacting" | "replied";

function haversineKm(a: { lat: number; lng: number }, b: { lat: number; lng: number }) {
  const R = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((a.lat * Math.PI) / 180) *
      Math.cos((b.lat * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

export default function Home() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [query, setQuery] = useState<SearchQuery | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [source, setSource] = useState<"live" | "fallback" | null>(null);
  const [filters, setFilters] = useState<Filters>({ maxPrice: 4000, maxKm: 20 });

  const [contactId, setContactId] = useState<string | null>(null);
  const [contactStatus, setContactStatus] = useState<ContactStatus | null>(null);
  const [contactListing, setContactListing] = useState<Listing | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const center = useMemo(() => cityCenter(query?.city ?? "san francisco"), [query]);

  const priceBounds = useMemo(() => {
    if (!listings.length) return { min: 1000, max: 4000 };
    const prices = listings.map((l) => l.priceUsd);
    return { min: Math.floor(Math.min(...prices) / 100) * 100, max: Math.ceil(Math.max(...prices) / 100) * 100 };
  }, [listings]);

  const filtered = useMemo(() => {
    return listings.filter((l) => {
      const km = haversineKm(center, l);
      return l.priceUsd <= filters.maxPrice && km <= filters.maxKm;
    });
  }, [listings, filters, center]);

  // Shortlist: keep the perfect listing, then the 3 best by (price + distance).
  const shortlist = useMemo(() => {
    const scored = [...filtered].sort((a, b) => {
      const sa = a.priceUsd / 1000 + haversineKm(center, a);
      const sb = b.priceUsd / 1000 + haversineKm(center, b);
      return sa - sb;
    });
    const perfect = scored.filter((l) => l.isPerfect);
    const rest = scored.filter((l) => !l.isPerfect).slice(0, 4 - perfect.length);
    return [...perfect, ...rest];
  }, [filtered, center]);

  const handleSearch = useCallback(async (q: SearchQuery) => {
    setQuery(q);
    setPhase("discovering");
    setListings([]);
    setSource(null);
    try {
      const res = await fetch("/api/discover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(q),
      });
      const data = await res.json();
      setListings(data.listings ?? []);
      setSource(data.source ?? null);
      setFilters({ maxPrice: Math.max(q.budget, 1000) + 400, maxKm: 20 });
      setPhase("results");
    } catch {
      setPhase("idle");
    }
  }, []);

  const stopPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = null;
  };

  const handleReach = useCallback(
    async (l: Listing) => {
      if (!query) return;
      if (!l.whatsapp) {
        alert("This listing has no WhatsApp number. Only the controlled 'perfect' listing can be contacted.");
        return;
      }
      setContactListing(l);
      setContactStatus(null);
      setPhase("contacting");
      try {
        const res = await fetch("/api/contact", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            whatsapp_number: l.whatsapp,
            listing_title: l.title,
            dates: `${query.checkIn} to ${query.checkOut}`,
            headcount: query.headcount,
            budget: query.budget,
          }),
        });
        const data = await res.json();
        if (!data.session_id) {
          setContactStatus({ status: "failed", events: [{ step: 0, text: data.error ?? "Contact service error" }] });
          return;
        }
        setContactId(data.session_id);
      } catch (e) {
        setContactStatus({ status: "failed", events: [{ step: 0, text: String(e) }] });
      }
    },
    [query]
  );

  // Poll the contact session while contacting.
  useEffect(() => {
    if (!contactId) return;
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/contact/${contactId}`, { cache: "no-store" });
        const data: ContactStatus = await res.json();
        setContactStatus(data);
        if (data.reply) {
          setPhase("replied");
          stopPolling();
        }
      } catch {
        /* keep polling */
      }
    }, 1500);
    return stopPolling;
  }, [contactId]);

  const simulateReply = useCallback(async () => {
    if (!contactId) return;
    await fetch(`/api/contact/${contactId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reply: "Yes! It's available for your dates — want to come see it tomorrow?" }),
    });
  }, [contactId]);

  const closeContact = () => {
    stopPolling();
    setContactId(null);
    setContactStatus(null);
    setContactListing(null);
    setPhase("results");
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="dot" />
          <h1>Homeless</h1>
          <small>ApartmentAgent</small>
        </div>

        <SearchForm onSearch={handleSearch} loading={phase === "discovering"} />

        {source && (
          <div>
            <span className={`badge ${source}`}>
              {source === "live" ? "● live from Craigslist (H agent)" : "● cached listings (fallback)"}
            </span>
          </div>
        )}

        {listings.length > 0 && (
          <>
            <FilterPanel filters={filters} onChange={setFilters} priceBounds={priceBounds} />
            <div>
              <div className="section-title">Shortlist · {shortlist.length} of {filtered.length} fits</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {shortlist.map((l) => (
                  <div className={`card ${l.isPerfect ? "perfect" : ""}`} key={l.id}>
                    {l.isPerfect && <span className="perfect-tag">◆ best match · contactable</span>}
                    <div className="title">{l.title}</div>
                    <div className="meta">
                      <span className="price">${l.priceUsd}/mo</span>
                      <span>{l.neighborhood}</span>
                      <span>{Math.round(haversineKm(center, l) * 10) / 10} km</span>
                    </div>
                    {l.isPerfect && (
                      <button
                        className="primary"
                        style={{ marginTop: 6 }}
                        onClick={() => handleReach(l)}
                        disabled={phase === "contacting"}
                      >
                        {phase === "contacting" ? "Contacting…" : "Reach out on WhatsApp"}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {phase === "idle" && <div className="empty">Enter your search and the agent will scout Craigslist live.</div>}
      </aside>

      <main className="map-wrap">
        <ListingMap listings={filtered} center={center} onReach={handleReach} />
        {(phase === "contacting" || phase === "replied") && contactListing && (
          <AgentViewPanel
            listingTitle={contactListing.title}
            status={contactStatus}
            agentViewUrl={contactStatus?.agent_view_url}
            onSimulateReply={simulateReply}
            onClose={closeContact}
          />
        )}
        {phase === "replied" && contactStatus?.reply && (
          <Toast message={`Found you a place! Owner: "${contactStatus.reply}"`} />
        )}
      </main>
    </div>
  );
}

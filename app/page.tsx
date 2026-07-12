"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import SearchForm from "@/components/SearchForm";
import FilterPanel, { Filters } from "@/components/FilterPanel";
import AgentViewPanel from "@/components/AgentViewPanel";
import ListingCard from "@/components/ListingCard";
import Toast from "@/components/Toast";
import { ContactStatus, Listing, SearchQuery, SessionEvent, cityCenter } from "@/lib/types";

const ListingMap = dynamic(() => import("@/components/ListingMap"), { ssr: false });

type Phase = "idle" | "discovering" | "results" | "contacting" | "replied";

function haversineKm(a: { lat: number; lng: number }, b: { lat: number; lng: number }) {
  const R = 6371;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLng = ((b.lng - a.lng) * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((a.lat * Math.PI) / 180) * Math.cos((b.lat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

interface Discovery {
  sessionId: string;
  agentViewUrl: string | null;
  events: SessionEvent[];
  status: string;
}

export default function Home() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [query, setQuery] = useState<SearchQuery | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [source, setSource] = useState<"live" | "fallback" | null>(null);
  const [filters, setFilters] = useState<Filters>({ maxPrice: 4000, maxKm: 20 });

  const [discovery, setDiscovery] = useState<Discovery | null>(null);
  const discPoll = useRef<ReturnType<typeof setInterval> | null>(null);

  const [contactId, setContactId] = useState<string | null>(null);
  const [contactStatus, setContactStatus] = useState<ContactStatus | null>(null);
  const [contactListing, setContactListing] = useState<Listing | null>(null);
  const contactPoll = useRef<ReturnType<typeof setInterval> | null>(null);

  const center = useMemo(() => cityCenter(query?.city ?? "san francisco"), [query]);

  const priceBounds = useMemo(() => {
    if (!listings.length) return { min: 1000, max: 4000 };
    const p = listings.map((l) => l.priceUsd);
    return { min: Math.floor(Math.min(...p) / 100) * 100, max: Math.ceil(Math.max(...p) / 100) * 100 };
  }, [listings]);

  const filtered = useMemo(
    () => listings.filter((l) => l.priceUsd <= filters.maxPrice && haversineKm(center, l) <= filters.maxKm),
    [listings, filters, center]
  );

  const shortlist = useMemo(() => {
    const scored = [...filtered].sort(
      (a, b) => a.priceUsd / 1000 + haversineKm(center, a) - (b.priceUsd / 1000 + haversineKm(center, b))
    );
    const perfect = scored.filter((l) => l.isPerfect);
    const rest = scored.filter((l) => !l.isPerfect).slice(0, 4 - perfect.length);
    return [...perfect, ...rest];
  }, [filtered, center]);

  const stopDisc = () => {
    if (discPoll.current) clearInterval(discPoll.current);
    discPoll.current = null;
  };
  const stopContact = () => {
    if (contactPoll.current) clearInterval(contactPoll.current);
    contactPoll.current = null;
  };

  const finishDiscovery = useCallback((data: any, q: SearchQuery) => {
    setListings(data.listings ?? []);
    setSource(data.source ?? "fallback");
    setFilters({ maxPrice: Math.max(q.budget, 1000) + 400, maxKm: 20 });
    setPhase("results");
  }, []);

  const handleSearch = useCallback(
    async (q: SearchQuery) => {
      stopDisc();
      setQuery(q);
      setPhase("discovering");
      setListings([]);
      setSource(null);
      setDiscovery({ sessionId: "", agentViewUrl: null, events: [], status: "pending" });

      let sessionId = "";
      try {
        const res = await fetch("/api/discover", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(q),
        });
        const data = await res.json();
        if (!res.ok || !data.sessionId) throw new Error(data.error ?? "discover start failed");
        sessionId = data.sessionId;
        setDiscovery({ sessionId, agentViewUrl: data.agentViewUrl ?? null, events: [], status: data.status ?? "pending" });
      } catch {
        // Can't even start a live session — fall back to cached listings.
        const fb = await fetch("/api/listings").then((r) => r.json()).catch(() => ({ listings: [], source: "fallback" }));
        finishDiscovery(fb, q);
        return;
      }

      discPoll.current = setInterval(async () => {
        try {
          const res = await fetch(`/api/discover/${sessionId}`, { cache: "no-store" });
          const data = await res.json();
          setDiscovery((prev) =>
            prev ? { ...prev, events: data.events ?? prev.events, status: data.status ?? prev.status, agentViewUrl: data.agentViewUrl ?? prev.agentViewUrl } : prev
          );
          if (data.listings) {
            stopDisc();
            finishDiscovery(data, q);
          }
        } catch {
          /* keep polling */
        }
      }, 1200);
    },
    [finishDiscovery]
  );

  const handleReach = useCallback(
    async (l: Listing) => {
      if (!query) return;
      if (!l.whatsapp) {
        alert("Only the controlled 'perfect' listing has a WhatsApp number to contact.");
        return;
      }
      stopContact();
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

  useEffect(() => {
    if (!contactId) return;
    stopContact();
    contactPoll.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/contact/${contactId}`, { cache: "no-store" });
        const data: ContactStatus = await res.json();
        setContactStatus(data);
        if (data.reply) {
          setPhase("replied");
          stopContact();
        }
      } catch {
        /* keep polling */
      }
    }, 1500);
    return stopContact;
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
    stopContact();
    setContactId(null);
    setContactStatus(null);
    setContactListing(null);
    setPhase("results");
  };

  const contactStatusLabel = contactStatus?.status ?? "pending";

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
              {source === "live" ? "live · Craigslist (H agent)" : "cached listings"}
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
                  <ListingCard
                    key={l.id}
                    l={l}
                    distanceKm={haversineKm(center, l)}
                    onReach={handleReach}
                    contacting={phase === "contacting"}
                  />
                ))}
              </div>
            </div>

            {filtered.length > shortlist.length && (
              <div>
                <div className="section-title">All results · {filtered.length}</div>
                <div className="rows">
                  {filtered.map((l) => (
                    <div className="rowitem" key={`row-${l.id}`}>
                      {l.imageUrl && /* eslint-disable-next-line @next/next/no-img-element */ <img src={l.imageUrl} alt="" />}
                      <a className="rtitle" href={l.url} target="_blank" rel="noreferrer">
                        {l.title}
                      </a>
                      <span className="rprice">${l.priceUsd}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {phase === "idle" && <div className="empty">Enter your search and the agent will scout Craigslist live.</div>}
      </aside>

      <main className="map-wrap">
        <ListingMap listings={filtered} center={center} onReach={handleReach} />

        {phase === "discovering" && discovery && (
          <AgentViewPanel
            title="Agent View — searching Craigslist"
            subtitle={`Scouting ${query?.city} for a place under $${query?.budget}`}
            statusLabel={discovery.status}
            events={discovery.events}
            agentViewUrl={discovery.agentViewUrl}
            onClose={() => {
              stopDisc();
              setPhase(listings.length ? "results" : "idle");
            }}
          />
        )}

        {(phase === "contacting" || phase === "replied") && contactListing && (
          <AgentViewPanel
            title="Agent View — contacting owner"
            subtitle={`WhatsApp inquiry · ${contactListing.title}`}
            statusLabel={contactStatusLabel}
            events={contactStatus?.events ?? []}
            agentViewUrl={contactStatus?.agent_view_url}
            onClose={closeContact}
            action={{ label: "Owner replied", onClick: simulateReply }}
          />
        )}

        {phase === "replied" && contactStatus?.reply && (
          <Toast message={contactStatus.reply} />
        )}
      </main>
    </div>
  );
}

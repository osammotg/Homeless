"use client";

import { useState } from "react";
import { SearchQuery } from "@/lib/types";

export default function SearchForm({
  onSearch,
  loading,
}: {
  onSearch: (q: SearchQuery) => void;
  loading: boolean;
}) {
  const [q, setQ] = useState<SearchQuery>({
    city: "San Francisco",
    checkIn: "2026-07-12",
    checkOut: "2026-08-12",
    budget: 2800,
    headcount: 2,
  });

  const set = (k: keyof SearchQuery, v: string | number) => setQ((p) => ({ ...p, [k]: v }));

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSearch(q);
      }}
    >
      <div className="field">
        <label>City</label>
        <input value={q.city} onChange={(e) => set("city", e.target.value)} placeholder="San Francisco" />
      </div>
      <div className="row">
        <div className="field">
          <label>Check-in</label>
          <input type="date" value={q.checkIn} onChange={(e) => set("checkIn", e.target.value)} />
        </div>
        <div className="field">
          <label>Check-out</label>
          <input type="date" value={q.checkOut} onChange={(e) => set("checkOut", e.target.value)} />
        </div>
      </div>
      <div className="row">
        <div className="field">
          <label>Budget ($/mo)</label>
          <input
            type="number"
            value={q.budget}
            onChange={(e) => set("budget", Number(e.target.value))}
          />
        </div>
        <div className="field">
          <label>People</label>
          <input
            type="number"
            min={1}
            value={q.headcount}
            onChange={(e) => set("headcount", Number(e.target.value))}
          />
        </div>
      </div>
      <button className="primary" type="submit" disabled={loading} style={{ width: "100%" }}>
        {loading ? (
          <span style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
            <span className="spinner" /> Agent is searching Craigslist…
          </span>
        ) : (
          "Find me a place"
        )}
      </button>
    </form>
  );
}

# Deslop brief — Homeless / ApartmentAgent UI

## User brief (verbatim intent)
Make the dark, map-first apartment concierge look **premium and demo-worthy** for a hackathon (H Company computer-use + NVIDIA). Not templated AI-slop. Strong typography/hierarchy, refined dark palette, tasteful accent, elegant cards, and a **striking Agent View panel** (the wow — the live AI agent browsing Craigslist / negotiating on WhatsApp, streaming its steps). Delightful but fast micro-interactions. **Keep the dark, map-first concept.**

## Register
**App / tool UI** (design SERVES the product). It's a live product, not a marketing page. Clarity + the live-agent "wow" beat decoration.

## What it is
A concierge that finds + contacts apartments autonomously. Screen = a fixed full-height two-pane app:
- **Left sidebar (~400px):** brand "Homeless · ApartmentAgent"; search form (City, Check-in, Check-out, Budget $/mo, People); a source badge ("● live from Craigslist (H agent)" green / "● cached listings" amber); Filters (max price slider, max distance slider); a **Shortlist** of rich listing cards; an "All results" compact list.
- **Right/main:** a big **dark Leaflet map** (CARTO dark tiles) with **price-bubble pins** ($2450 etc.); the best-match pin glows.
- **Floating "Agent View" panel** (bottom-right, ~420px): streams the live H agent's steps as it works (a pulsing "live" dot, a scrolling event log, a "Watch live in H Agent View ↗" link, a status badge); used for BOTH discovery and the WhatsApp negotiation.
- **Toast** (top-center): "🏠 Found you a place! Owner: …" when a viewing is booked.

## Listing card (rich) currently shows
thumbnail image · linked title · price ($/mo) · beds (Studio/NBR) · sqft · neighborhood · distance (km) · "from <date>"; the best match has a "◆ best match · contactable" tag + a green "Reach out on WhatsApp" button.

## Functional inventory (PARITY — the redesign must preserve every item; these are wired to real APIs, do not break them)
1. Search form with controlled inputs: city, checkIn, checkOut (date), budget (number), headcount (number); submit → POST /api/discover.
2. Loading state on the submit button ("Agent is searching Craigslist…" with spinner).
3. Source badge reflecting live vs fallback.
4. Filters: max price slider (bounds derived from results), max distance slider (km from city center); filtering is live/reactive.
5. Shortlist = top ~4 by price+proximity, best match ("perfect") pinned first with the contact CTA.
6. "All results" scrollable list (thumb + title link + price).
7. Leaflet map: dark tiles, price-bubble divIcon pins, best-match pin highlighted, popups with image + linked title + price + beds/sqft + "Reach out on WhatsApp" on the best match, auto fit-bounds to results.
8. Agent View panel: title, subtitle, pulsing live indicator while running, streamed step events (auto-scroll), status badge, "Watch live in H Agent View ↗" external link, optional action button ("Owner replied"), close button. Used for discovery AND negotiation phases.
9. Notification toast on "booked/found".
10. Phase state machine: idle → discovering → results → contacting → replied.
11. "Reach out on WhatsApp" triggers the contact/negotiation flow.

## Tech / constraints
- Next.js 14 (app router, TS), React 18. Leaflet + react-leaflet v4 (dark CARTO tiles; custom divIcon pins). Plain CSS in app/globals.css (CSS variables). Components in components/*.tsx.
- KEEP the component APIs + the page.tsx state logic + API route wiring intact — this is a visual rebuild (restyle markup/classes + globals.css), transplant the React logic unchanged.
- Dark, map-first is non-negotiable. Accent currently emerald/teal — open to a more distinctive premium palette but stay legible on the dark map.
- Fast: no heavy libraries, no blocking animations. Micro-interactions must feel instant.

## Text-diet license
Yes — copy may be trimmed/rewritten; layout may change freely. Keep labels clear.

## Screenshots
`00-current/idle.png`, `00-current/idle-wide.png` — the current idle state (search form + dark SF map). (Results/agent-view states are described above; design for them too.)

## Slop to avoid
Uniform rounded cards in a 3-grid; gradient blobs; glassmorphism-by-default; emoji-as-icons; purple-on-dark "AI default"; identical section rhythms; generic SaaS dashboard look. This should feel like a crafted, slightly cinematic operator console for a live AI agent.

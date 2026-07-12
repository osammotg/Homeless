# ApartmentAgent — PARITY-QA (end-user + QA) findings

Branch `feat/apartmentagent-spine` · UI http://localhost:3000 · contact-svc http://localhost:8000 (health 200).
Exercised the full live flow in a real headless browser: initial load → live H discovery → results/filters/map → WhatsApp contact → owner-reply → empty-filter edge case. HAI_API_KEY is set in the dev-server env, so the **live** path (not the cached fallback) was tested end-to-end.

## What works (the safety floor holds)

- **Clean initial load.** Dark, map-first layout renders; search form has sensible defaults (SF, 2 people, $2800). No console errors. `evidence/parity-qa/01-initial-load.png`
- **Live discovery is real and it works.** "Find me a place" → `POST /api/discover` 200, an Agent View panel opens over the map with a live pulse, running timer, session id, PENDING→RUNNING status, and a working "Watch live in H Agent View" link. `02`, `03`, `04`
- **Discovery completes with real data.** Two full runs returned real Craigslist listings (`source:"live"`, 13 listings incl. the seeded contactable one) in ~90s and ~130s. `05`
- **Results UI is solid.** LIVE badge, price + distance sliders, "Shortlist · 4 of 9 fits", a best-match "contactable" card with thumbnail, an "All results · 9" list, and map price-pins. `05`, `07`
- **WhatsApp contact flow works end-to-end.** `POST /api/contact` 200 → contact-svc drives real computer-use. The contact Agent View shows *readable* steps: "Contacting +1415…", "Opened WhatsApp to +1415… (deep link, prefilled)", "Turn 1 started", and later a realistic negotiation incl. "Blocked — login wall / missing permissions", "Turn settled (phase=awaiting_owner)". `08`, `09`
- **No console errors** during any normal flow (only the 409 noted below).
- Graceful fallback design exists (cached listings if a live session can't start).

## What's broken / slow / confusing

### 1. Geocoding bug → impossible distances + pin pile-up (highest impact)
`lib/geocode.ts` builds the Nominatim query as `"{neighborhood}, {city}"`. Live listings already carry a full locality in `neighborhood` (e.g. "Fremont, CA"), so the query becomes the nonsensical **"Fremont, CA, San Francisco"**, Nominatim returns nothing, and the code falls back to a ±3km deterministic *jitter around SF center*. Consequences observed in `05`/`07`:
- Fremont, Vallejo, Pleasant Hill listings show distances of **2.6 / 2.7 / 3.0 km** from SF — they are 40–60 km away.
- Those suburb listings therefore **wrongly pass the 20km distance filter** and land in the shortlist.
- Their pins **pile up on downtown SF** ($1200/$2295/$2074 stacked and unreadable), while a few that did resolve ($901 El Cerrito, $2050 San Leandro) sit correctly. The map is internally inconsistent and misleading.

### 2. Search "San Francisco" returns mostly non-SF suburbs
The H prompt starts on the regional `sfbay` Craigslist, so results span the whole Bay Area (Fremont, Vallejo, Concord, Martinez, Pleasant Hill, San Mateo) rather than SF proper. Combined with #1 this makes the "places near you in San Francisco" promise ring false. `05`, `07` — `lib/discovery.ts` (`prompt`, `craigslistUrl`).

### 3. Map pins collide with no clustering
Even with correct coordinates, `components/ListingMap.tsx` renders raw price divIcons with no collision/spiderfy/cluster handling; overlapping pins render on top of each other and become unreadable. `05`, `07`.

### 4. Missing empty state when filters exclude everything
Dragging Max price to its floor ($800) leaves the sidebar showing a bare "SHORTLIST · 0 OF 0 FITS" over an empty void — no "no listings match, widen your filters" message, no cards, no pins, no guidance. `11` — `app/page.tsx`.

### 5. "Owner replied" silently fails (409) during an active agent turn
Clicking "Owner replied" while the H contact turn is running returns `409 {"detail":"A turn is already running; try again shortly."}`. `simulateReply` in `app/page.tsx` does `await fetch(...)` and ignores the response, so the user gets **zero feedback** — the button appears to do nothing and only a 409 shows in the console. Verified via UI click (console 409) and a direct `curl` (`HTTP 409`). Retrying after the turn settled succeeded (200). `09` + console.

### 6. Discovery Agent View events are opaque
The discovery feed is a wall of internal event-type names — "AgentEvent", "MetricsUpdateEvent", "RequestStartEvent", "RequestStartDispatchedEvent" — because `eventText` in `lib/discovery.ts` falls back to the raw event `type` when no human-readable message field is present. This undermines the "watch the agent think" wow-factor, and the contrast with the nicely-narrated *contact* panel makes it obvious. `04`, `10`.

### 7. Contact flow is slow and never surfaced completion in-window
After injecting the owner reply, the session stayed RUNNING for 2+ minutes cycling raw events; the phase never transitioned to "replied" / the success Toast never appeared, and the card stayed on "Contacting…". For a live demo this is a risk (medium confidence — could be H latency). `08`→`10` — `contact-svc/main.py`, `app/page.tsx`.

### 8. Minor: no map loading state
On first paint the map area is solid black until CARTO tiles arrive; a skeleton/loading shade would read better. `01`.

## Console
No JS console errors across load, discovery, results, and contact. The only network error observed was the expected/ungraceful **409** on the premature "Owner replied" click (finding #5).

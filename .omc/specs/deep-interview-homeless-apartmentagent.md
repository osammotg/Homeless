# Deep Interview Spec: Homeless — ApartmentAgent

## Metadata
- Interview ID: homeless-apartmentagent-2026-07-11
- Rounds: 6 (+ Round 0 topology gate)
- Final Ambiguity Score: ~10%
- Type: greenfield (repo had only README spec + postmortem)
- Generated: 2026-07-11
- Threshold: 0.20 (20%)
- Threshold Source: default
- Status: PASSED

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.92 | 0.40 | 0.37 |
| Constraint Clarity | 0.88 | 0.30 | 0.26 |
| Success Criteria | 0.90 | 0.30 | 0.27 |
| **Total Clarity** | | | **0.90** |
| **Ambiguity** | | | **0.10** |

## The One-Liner
An H Company computer-use agent finds the perfect apartment on real Craigslist live, then messages the owner on WhatsApp — watched step by step — and the reply closes the loop on stage. Goal: **excel at H Company browser/computer-use.**

## Topology
| Component | Status | Description | Coverage / Deferral Note |
|-----------|--------|-------------|--------------------------|
| Input | active | City / dates / budget / #people (typed; voice later) | Form in the Next.js UI |
| Discover + Map | active | H agent scrapes REAL Craigslist live; geocode; plot pins | Cloud browser, text mode + cached `data/listings.json` fallback so the map can't fail |
| Filter + Shortlist | active | Budget / proximity-to-center / availability → ~4 fits | Filter logic over the listing set; the planted "perfect listing" is among them |
| Contact | active | H agent drives **WhatsApp Web on the user's own laptop** (local browser control), messages the owner, watched in Agent View | **The differentiator.** Uses the teammate's real WhatsApp number carried on the controlled "perfect listing" |
| Notification | active | Teammate replies on their phone → agent/poller reads WhatsApp reply → "found you a place" fires live | Closed loop on stage |
| Voice (Gradium) | deferred | Speak search in + TTS narration | User-confirmed stretch; after core loop works |

## Goal
Build an app where an H computer-use agent (1) browses **real Craigslist** live to fill a map of listings (cached fallback so it can't hard-fail), (2) narrows to ~4 fits including a planted "perfect listing," and (3) as the money shot, **drives WhatsApp Web on the user's own machine via H local browser control** to message the owner (a teammate) — all visible in an Agent View panel — after which the teammate's reply is detected and a "found you a place" notification fires live.

## Constraints
- **Stack: hybrid.** Next.js (TypeScript) UI + a **thin Python contact service** (`hai-agents[browser]`) because H **local browser control is Python-SDK-only today**. The Next.js UI calls the Python service for the contact flow. Discovery/map/filter live in the Next.js app.
- **Contact = local browser control** (`host: "user_device"`): the H agent attaches to a Chrome on the user's machine with remote-debugging on port 9222 (or the SDK's `~/.hai/chrome-profile`), where **WhatsApp Web is already logged in**. No cloud login, no vault, no profile upload. Docs: `computer-use-agents/browser/local-control`.
- **Discovery = cloud browser, text mode** H agent (conserves tokens) + cached `data/listings.json` fallback.
- All H integration written against the official docs (`hai-agents` client, session-create + `/changes` long-poll, `answerSchema`/typed output, Agent View observe/steer, local-control). See [[feedback-use-hcompany-docs]] / [[hcompany-computer-use-docs]].
- H plan ~Developer tier: 60M tokens/mo (~59.5M remaining), 3–10 concurrent sessions. API key `HAI_API_KEY` from `~/.hcompany/credentials`; EU region `https://agp.eu.hcompany.ai`.
- Ethics/consent-clean: the owner is a teammate who consents; the "perfect listing" is controlled. Discovery only reads public Craigslist. No messaging real strangers.
- Runtime: local dev on the demo laptop (the laptop must be signed in to WhatsApp Web). 48h build, solo (user) + this agent.

## Non-Goals
- No Facebook Marketplace.
- No messaging real apartment owners.
- No dependency on Craigslist's async email relay (contact is WhatsApp).
- Voice not in the core build.

## Acceptance Criteria
- [ ] User enters city/dates/budget/#people in the Next.js form.
- [ ] An H agent (cloud, text mode) scrapes real Craigslist housing live; the map fills with geocoded pins (price/availability). If it stalls/CAPTCHAs, the map falls back to `data/listings.json` with no visible failure.
- [ ] Filters narrow to ~4 fits by budget + proximity-to-center + availability; the planted "perfect listing" (with the teammate's WhatsApp number) is present.
- [ ] Clicking "reach out" calls the Python contact service, which runs an H **local-browser** session that opens **WhatsApp Web on the user's laptop**, finds the owner's number, composes and sends a polite inquiry — visible step-by-step in an Agent View panel in the UI.
- [ ] The teammate replies on their phone; the app detects the reply (agent reads WhatsApp Web or a poller) and fires a "found you a place" notification live.
- [ ] The whole flow runs in ~90s and cannot hard-fail during the demo.

## Assumptions Exposed & Resolved
| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| Team splits the work | Round 1 | Solo (user) + this agent build everything |
| Backend language unstated | Round 2 | Next.js (TS) — later refined to hybrid for local control |
| "Hybrid = cache" but source unclear | Round 3 | Live scrape chosen |
| Live scrape fragile + who scrapes | Round 4 (contrarian) | H agent scrapes live + cached fallback |
| Contact win-moment + async reply | Round 5 | Full closed loop via a controlled instant channel |
| Controlled channel mechanism + stack | Round 6 (simplifier) | WhatsApp Web via H **local browser control** (Python-only) → hybrid Next.js + Python contact service; owner = teammate on the planted perfect listing |

## Technical Context
- **Discovery (cloud, TS):** `hai-agents` TS client → text-mode web env → `answerSchema` (Zod `Listings`) → typed array → geocode (Nominatim, free) → Leaflet pins. Fallback: read `data/listings.json`.
- **Contact (local, Python):** `pip install "hai-agents[browser]"`; agent env `{kind:"web", host:"user_device"}`; `client.run_session(agent, "Open WhatsApp Web, message <number> ...")`. Stream session events / `changes` into the Next.js Agent View panel. Cancel with `hai sessions cancel <id>`.
- **Controlled "perfect listing":** a listing (hosted by us or seeded into results) that carries the teammate's WhatsApp number, so the agent extracts a real number to message.
- **Agent View:** surface live session steps in the UI (observe-and-steer / `changes`).

## Suggested layout (hybrid)
```
Homeless/
  app/                     # Next.js (TS)
    page.tsx               # input form + Leaflet map + filter panel + Agent View + notification
    api/discover/          # H text-mode agent (TS) → listings (answerSchema) + fallback
    api/contact/route.ts   # proxies to the Python contact service
  contact-svc/             # Python (FastAPI) — H local browser control
    main.py                # run_session(host=user_device) → WhatsApp Web → events
  lib/hai.ts               # hai-agents TS client (discovery) per docs
  data/listings.json       # cached fallback
  .env.example             # HAI_API_KEY=...
```

## Ontology (Key Entities)
| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| SearchQuery | core domain | city, checkIn, checkOut, budget, headcount | produces many Listing |
| Listing | core domain | title, priceUsd, url, lat, lng, availableFrom, source, whatsapp? | belongs to SearchQuery; one is the controlled "perfect listing" |
| Session (H) | external system | id, agent, host(cloud/user_device), status, events, answer | drives Discover (cloud) and Contact (local) |
| Inquiry | core domain | listingId, whatsappNumber, message, sentAt, status | created by the Contact session |
| Reply | core domain | inquiryId, body, receivedAt | triggers Notification |

## Ontology Convergence
| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 0 (topology) | 5 components | 5 | - | - | - |
| 6 (final) | 5 entities | stable | 1 (Listing +whatsapp) | 4 | 100% |

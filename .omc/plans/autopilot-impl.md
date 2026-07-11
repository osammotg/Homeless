# Autopilot Implementation Plan — Homeless / ApartmentAgent

Source spec: `.omc/specs/deep-interview-homeless-apartmentagent.md` (ambiguity ~10%, PASSED).
Build dir: `/Users/admin/Documents/AI 2026/hackathonIterate/Homeless`.

## Architecture
```
Next.js (TS) app  ──HTTP──▶  Python contact-svc (FastAPI)
   │  discovery (cloud, TS hai-agents)          │  contact (local browser control, Python hai-agents[browser])
   ▼                                            ▼
 Leaflet map + filter + Agent View + notify   WhatsApp Web on the demo laptop (logged in)
```

## Task list (parallelizable where independent)

### A. Next.js app shell (me)
- [ ] `package.json`, `tsconfig.json`, `next.config.mjs`, `.gitignore`, `.env.example`
- [ ] `app/layout.tsx`, `app/globals.css` (dark, clean, map-first)
- [ ] `app/page.tsx` — SearchForm + Map + FilterPanel + AgentView + Notification (client component, state machine: idle→discovering→results→contacting→replied)
- [ ] `components/` — SearchForm, ListingMap (Leaflet, dynamic import, no SSR), FilterPanel, AgentViewPanel, Toast
- [ ] `lib/types.ts` — Listing, SearchQuery, SessionEvent (shared shapes)

### B. Discovery (me)
- [ ] `lib/hai.ts` — TS `hai-agents` client wrapper: create cloud text-mode web env + agent, `runSession` with Zod `answerSchema` (Listings), EU region, HAI_API_KEY
- [ ] `app/api/discover/route.ts` — POST {city,checkIn,checkOut,budget,headcount} → run discovery agent on real Craigslist (`<city>.craigslist.org`), geocode via Nominatim, return Listing[]; on any error/timeout → fall back to `data/listings.json`
- [ ] `data/listings.json` — ~10 seeded SF listings incl. the controlled "perfect listing" (carries teammate WhatsApp number placeholder) so the map/filter always has data

### C. Contact service (delegated subagent, Python — independent dir)
- [ ] `contact-svc/main.py` — FastAPI: `POST /contact` starts an H local-browser session (host=user_device) that opens WhatsApp Web and messages the number; `GET /contact/{id}` polls `/changes` and returns status+events+answer; `GET /contact/{id}/reply` checks for the owner reply
- [ ] `contact-svc/requirements.txt` — hai-agents[browser], fastapi, uvicorn
- [ ] `contact-svc/README.md` — how to run (`hai local browser` note, port 9222, WhatsApp Web pre-login)

### D. Integration (me)
- [ ] `app/api/contact/route.ts` — proxy POST → Python `/contact`; `app/api/contact/[id]/route.ts` — proxy GET status/events + reply
- [ ] Wire AgentViewPanel to poll contact status → render live steps → fire Notification on reply
- [ ] Root `README.md` run instructions (both servers) + `.env.example`

## Acceptance (from spec)
input → live Craigslist map (fallback-safe) → filter to ~4 → WhatsApp contact watched in Agent View → reply notification, ~90s, cannot hard-fail.

## Phases
1. Planning (this file) ✓
2. Execution: A+B+D (me) ‖ C (subagent)
3. QA: `npm run build` + typecheck; `python -c import` on contact-svc
4. Validation: review correctness/security/quality
5. Cleanup state

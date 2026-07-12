# ApartmentAgent — Handoff

_H Company Computer-Use Hackathon · Track 2 (Browser Use) · branch `feat/apartmentagent-spine`_

## What it is
A conversational apartment concierge. You **DM a Telegram bot** → it runs a **live Craigslist search** via an H **cloud** computer-use agent (shown on a dark map + streaming "Agent View") → posts a **shortlist with photos, prices, and a map screenshot** in Telegram → you **pick one** → an H **desktop** computer-use agent drives the **WhatsApp desktop app** to **negotiate** with the owner and **book a viewing** → confirmation back in Telegram. **Two H computer-use surfaces: browser + desktop.**

## Architecture / components
| Piece | Path | Role |
|---|---|---|
| Next.js UI (:3000) | `app/`, `components/`, `lib/` | Dark map ("Signal Dispatch"), live discovery + Agent View. `lib/discovery.ts` runs the H cloud session. |
| Contact service (:8000) | `contact-svc/main.py` | FastAPI; H **desktop** computer-use drives WhatsApp; fresh-session-per-turn negotiation. |
| Concierge bot | `concierge/main.py` | Telegram long-poll orchestrator; parses request → discovery → shortlist → pick → negotiation → confirmation. |
| Session sweep | `scripts/sweep-h-sessions.sh` | Kill zombie H sessions before demo (frees the 3-session cap). |

## How to run (all on the demo Mac)
```bash
# 0. keys already set: HAI_API_KEY in ~/.hcompany/credentials; concierge/.env has TELEGRAM_BOT_TOKEN + OWNER_WHATSAPP
# 1. UI
npm install && npm run dev            # http://localhost:3000
# 2. Contact service (H desktop → WhatsApp)
cd contact-svc && CONTACT_MODE=desktop .venv/bin/uvicorn main:app --port 8000
# 3. Concierge (Telegram bot)
contact-svc/.venv/bin/python concierge/main.py
# before demo: free H session slots
bash scripts/sweep-h-sessions.sh
```
Bot: **@apartmentagent_demo_7431bot** · Owner (friend): **+4915737431637**.

## ✅ Done & verified
- Telegram bot live; DM → live Craigslist discovery → shortlist (photos + prices + **map screenshot**) in chat.
- H **cloud** discovery works (live, with a cached `data/listings.json` fallback so the map can't fail); geocoder + city-scoping fixed.
- H **desktop** WhatsApp send **works** (deterministic Return safety-net, gated so the agent's own send is the visible action). Verified live — the inquiry landed in the owner chat.
- Multi-turn **negotiation** is fresh-session-per-turn (each owner reply fires a new H session that reads the WhatsApp screen and responds per a guided script); **"💰 Saved you $X"** callout on booking.
- **Agent View humanized** (readable steps, not raw `AgentEvent` class names).
- UI redesign ("Signal Dispatch": amber console, mono numerics, cyan agent timeline) + idle hero + empty state + "2 H agents" HUD + map scan overlay.
- Reliability: session-sweep script, Telegram `deleteWebhook` + Markdown formatting, macOS Accessibility + Screen Recording granted (python3.13 + terminal), `max_time_s` zombie fix + session teardown.
- Everything committed + pushed (`3a18c96`).

## ⛔ Still missing / to do before the stage
1. **One full live rehearsal end-to-end** — DM bot → shortlist → pick → the friend replies as owner on WhatsApp (3-line script: *available → accept small discount → agree a viewing time*) → "✅ Booked!" in Telegram. Not yet run as one clean take.
2. **Record the sped-up backup video** during that clean run (the only net if venue wifi/H quota fails live).
3. **Presenter setup:** press **Start** on the bot from your own Telegram once (bots can't message you first).
4. **Staging (presentation, not code):** lead with the WhatsApp negotiation on a **split-screen**; put the **real WhatsApp window on the projector** during negotiation; a persistent "2 computer-use surfaces" framing in the pitch.
5. **NemoClaw / NVIDIA prize (optional):** needs an `nvapi-…` key from build.nvidia.com → then the Brev NemoClaw box comes up and the concierge's request-parsing runs on Nemotron. Skipped for now; the bot uses a regex parser and works without it.

## Known gotchas
- **Don't run `npm run build` while `next dev` is running** — it corrupts `.next` (500s). Restart dev + `rm -rf .next` if it happens.
- **The friend is on the critical path** — the negotiation needs a *real inbound* WhatsApp message from +4915737431637; the "Owner replied" button/`/reply` only fires the next agent turn, it doesn't fake an incoming message.
- **H = 3 concurrent sessions.** Run the sweep script before the demo; discovery + negotiation each take a slot.
- **Free the screen during agent runs** — the desktop agent drives the real mouse/keyboard.
- If the owner is a **different number/teammate**, edit `OWNER_WHATSAPP` in `concierge/.env` and restart the concierge.

## Judge-lens notes (from the autoanalysis pass)
- **The 90s money-shot:** the desktop agent physically haggling on the native WhatsApp app (a no-API surface) — almost no other Track-2 team will have computer-use driving a native app in a real negotiation.
- **One-line pitch:** _"Two H agents, two surfaces, zero APIs: one scouts Craigslist in the browser, the other haggles with the landlord in the WhatsApp desktop app — computer-use the whole way down."_
- Full analysis + the review board: `autoanalysis-run/apartmentagent-20260711/`.

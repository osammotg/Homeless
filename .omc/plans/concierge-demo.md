# Plan: ApartmentAgent Concierge (chat → live search → pick → autonomous WhatsApp negotiation)

Status: **PENDING APPROVAL** (consensus: Planner → Architect → Critic; verdict REVISE → all fixes applied)
Target: /Users/admin/Documents/AI 2026/hackathonIterate/Homeless
Event: H Company Computer-Use Hackathon (SF, Track 2) + NVIDIA NemoClaw side-prize.

## Requirements Summary
A conversational concierge: user DMs an agent → it replies + sends a live-UI link → searches Craigslist live (H **cloud** computer-use) shown on our map → posts a shortlist in chat → user picks → the agent autonomously drives the WhatsApp **desktop** app (H **desktop** computer-use) to **negotiate a discount and book a viewing** with the "owner" (our own number; teammate replies live within a script). Everything live; a sped-up video is the backup.

## Target Architecture
```
 User (Telegram)                 Orchestrator (thin: Nemotron llm() + state)          Hands (H Company computer-use)
 "find SF, 2ppl, $2500" ─▶ bot ─▶ parse intent ─▶ tool: search() ──HTTP──▶ Next.js /api/discover (H CLOUD → Leaflet map)
        ▲  "watch live: <url>" ◀────┤
        │  "top 3: 1)…2)…3)…" ◀─────┤  tool: get_results(id) ◀──HTTP── /api/discover/{id} (poll until listings!=null)
 "go with 2" ──────────────▶ bot ─▶ tool: negotiate(owner#) ──HTTP──▶ contact-svc /contact (mode=desktop, per-turn)
        │  "negotiating: <av>" ◀────┤
        │  "✅ $2350, Sat 5pm" ◀─────┤  turn loop: owner replies → next /contact turn → … → booked
```
Two H computer-use surfaces: **browser** (discovery) + **desktop** (WhatsApp negotiation). Orchestrator brain = NVIDIA Nemotron. Owner = our own phone; teammate replies live within the script.

## Decision (ADR)
- **Decision:** Option A — **Telegram front-door + thin orchestrator (Nemotron via hosted API by default) calling our existing HTTP services as tools**, with **fresh-session-per-turn** WhatsApp negotiation. Build the H computer-use **core first**, orchestrator/Telegram/NemoClaw last.
- **Drivers:** dual-sponsor wow (H + NVIDIA) · 48h reliability · reuse ~80% already built.
- **Alternatives:** B (WhatsApp for user side too — rejected: Business API approval/2nd driven WhatsApp, too heavy); C (Next.js chat box drives it, no bot — kept as the clean CUT-DOWN fallback).
- **Why chosen (Architect+Critic synthesis):** the `llm()` seam makes NemoClaw additive not load-bearing; 4 HTTP calls as tools reuse what works; the cut list degrades A→C without losing the core. Architect's "glue-on-critical-path" risk is answered by **core-first sequencing** + the recorded backup.
- **Consequences:** new (small) orchestrator + Telegram glue; the negotiation service is reshaped from single-shot to **per-turn** (the one real code lift).
- **Follow-ups:** if idle-loop is ever wanted for elegance, revisit; not for this demo.

## RALPLAN-DR
**Principles:** (1) reuse discovery+contact HTTP APIs as tools; (2) H computer-use core must shine even if the orchestrator/NemoClaw slip (decouple via `llm()`); (3) demo can't hard-fail (fallbacks + recorded backup); (4) guided negotiation, teammate stays in-branch; (5) respect H's **3-session** cap.
**Drivers:** dual-sponsor wow · 48h reliability · reuse. **Options:** A [chosen] · B [rejected] · C [cut-down fallback].

## Front-door: **Telegram (recommended)** — long-poll `getUpdates`
BotFather token in 2 min; long-poll (no public webhook, venue-wifi friendly); **one** getUpdates consumer per token → single orchestrator process. Pre-create + test on venue wifi in first 2h. WhatsApp for the *user* side is rejected (Business API/2nd instance). WhatsApp stays only for the **owner** negotiation (built).

## Orchestrator (thin, built LAST)
Single process `concierge/`: receive Telegram updates → `llm()` parses free text → `{city,checkIn,checkOut,budget,headcount}`; calls 4 HTTP tools; per-chat state machine `idle→searching→shortlist→negotiating→done`.
- **State map:** `chat_id → {discoverSessionId, contactSessionId, ownerNumber, pickedListing, phase}`. **Normalize casing** (`sessionId` camel from discover, `session_id` snake from contact) into one internal field.
- **Owner number = orchestrator CONFIG** (fixed teammate phone), NOT from a listing (Craigslist carries no phone; `Listing` has no phone field — discovery.ts:66-99). `negotiate(pick)` injects the configured number + maps `pick → {listing_title, price, dates}` into the contact task.
- **Polling = poll OUR services** (H's own `changes` loop already runs inside discovery.ts/main.py): `GET /api/discover/{id}` until `listings!=null` (bound ~140s), `GET /contact/{id}` until terminal; debounce Telegram message edits.

## NemoClaw → **GO (instance live), but hosted Nemotron is the DEFAULT live path**
- Live instance on Brev: `nemoclaw-3f867d`, Running, org `atopaloglu-0-wfrb`, IP `34.11.158.114`, SSH :22, HTTPS :80 → `https://nemoclaw-p977lz6m9.brevlab.com` (Cloudflare-Access login-walled → reach via `brev shell` / `brev port-forward`, not the raw URL). See [[nemoclaw-brev-instance]], [[brev-project]].
- **Reality check:** the box is **4 CPU / 16 GiB, no GPU** → won't serve Nemotron at demo latency. So:
  - **Default live `llm()` = hosted Nemotron API** (build.nvidia.com, OpenAI-compatible) — still "NVIDIA Nemotron", low variance.
  - **Brev NemoClaw box = the "runs on NVIDIA / OpenClaw sandbox" B-roll + story** (SSH in, `curl localhost` to confirm what it serves; if it exposes an OpenClaw agent or OpenAI-compatible route, screenshot it running; rehearse one call through the port-forward).
  - One-line `llm()` config flip between them; the live loop never gambles on the tunnel/CPU.
- **First-2h task:** `brev shell nemoclaw-3f867d`; `curl localhost:80/v1/models` (+ `/health`, look for OpenClaw docs on the box); confirm Nemotron model id, route, auth; decide model-vs-agent role for the *story*, keep hosted API for the *run*.

## Guided negotiation — **fresh-session-per-turn** (the must-fix; single-shot code is reshaped)
Why per-turn over `idle_timeout_s`: current code already does create→send→report once (main.py:198-259), so per-turn is the minimal delta; it **frees the H slot between turns** (an `idle` session holds 1 of 3 slots the whole convo — plans-and-limits.md:53); it has **no idle clock** to expire on a hand-typed teammate reply; and the WhatsApp desktop app **keeps the whole conversation on screen**, so a fresh session reads prior turns for free.
Mechanism: each owner reply triggers a NEW `/contact` turn whose task = "read the newest incoming owner message in the open WhatsApp chat, pick the scripted branch, compose + send the reply, report." `/contact/{id}/reply` is rewired from *store-only* to **fire the next turn**. Turn 1 uses the `whatsapp://send` deep-link prefill (built); turns ≥2 read the latest on-screen message instead (no prefill).

Script (owner-reply → agent-reply), stay ≤ budget + within dates:
| Owner reply | Agent |
|---|---|
| available | "Great! Listed at $2450 — for the full 2 months could you do $2350? When can we view it?" |
| counter (e.g. $2400) | ≤budget: "Deal at $2400. View this weekend?" · >budget: "Our max is $2500 total incl. fees — can we make it work?" |
| question (move-in/#people/pets) | answer from criteria (dates, 2 people, no pets), then re-ask to book a viewing |
| unavailable | "Understood, thanks! Anything similar coming up?" → end; report unavailable |
| stalls | one polite nudge; else report "awaiting owner" (video shows a completed run) |
| agrees to a time | "Perfect, booked for <time>. Thank you!" → finish; report success + price + time |
Teammate crib sheet: reply as owner, one branch/turn — start "available" → accept a small discount → agree a viewing time, so the live run reliably reaches "booked."

## Record-backup + live reply
Owner number = our own 2nd phone (teammate's), pre-saved as WhatsApp contact "ApartmentAgent Owner" (consent-clean, we own both ends). Teammate replies per crib sheet as agent messages arrive. Backup: screen-record a full clean run (Telegram + our UI + WhatsApp Agent View), speed 2–4×, recorded the night before.

## Prioritized 48h build sequence — **CORE FIRST** (re-sequenced per review)
**P0 — irreducible core (must survive every cut):**
1. **Fix discovery zombies:** discovery.ts create uses `max_seconds` (wrong) → change to documented **`max_time_s`**; add `DELETE /sessions/{id}` when `runLoop` settles; add a pre-demo sweep (`GET /sessions?status=running` → DELETE). [~1h]
2. **Reshape negotiation to per-turn** (rewrite `_desktop_task` for read-latest+branch; rewire `/contact/{id}/reply` to fire the next turn; free each turn's session before the next). [~4-5h]
3. **Manual end-to-end negotiation test:** fire `POST /contact` by hand, teammate replies live, reach "viewing booked" in ≥3 turns — **no orchestrator/Telegram in the loop yet.** [~1h]
4. Discovery smoke (already works): instant cached map + live H Agent View. [~0.5h]
**P1 — the concierge shell (thin, last):**
5. Telegram bot skeleton (BotFather, getUpdates, reply). [~1h]
6. Orchestrator state machine + `llm()` intent-parse + 4 HTTP tool calls + owner-number config + casing normalize. [~3h]
7. Wire search→shortlist→pick→negotiate through the bot. [~2h]
8. Nemotron hosted-API `llm()`; NemoClaw Brev B-roll via SSH/port-forward. [~2h]
**P2 — polish/safety:** pre-flight (perms, quota sweep, WhatsApp login, cached discovery); record the sped-up backup. [~2h]
**CUT LIST (drop in order):** NemoClaw box→hosted Nemotron→any LLM · multi-turn→single inquiry+one scripted reply · Telegram→UI chat box · negotiation→confirm+book only. **Irreducible core that survives all cuts:** live H browser discovery on the map + live H desktop WhatsApp message, watched in Agent View.

## Acceptance Criteria (testable)
- [ ] **AC1 (core, by ~hour 8):** a hand-fired `POST /contact` runs a ≥3-turn negotiation to "viewing booked" with a human replying, zero orchestrator/Telegram in the loop; **each turn's H session reaches terminal (slot freed) before the next starts.**
- [ ] **AC2 (turn driver):** teammate sends an owner reply → within N s a new, context-appropriate agent message referencing it appears in WhatsApp; `/contact/{id}/reply` triggers the next turn (not store-only).
- [ ] **AC3 (owner config):** `negotiate(anyPick)` produces a `POST /contact` whose `whatsapp_number` = the configured owner number regardless of listing.
- [ ] **AC4 (concurrency):** after one discovery + one negotiation-to-booked, `GET /api/v2/sessions/quota` shows `active` back to 0; the sweep reduces a seeded 3-running state to 0; discovery create uses `max_time_s`.
- [ ] **AC5 (casing):** a canned Telegram dry-run threads a discover id + a contact id through the state machine with no undefined/None key.
- [ ] **AC6 (bot):** free-text to the bot returns a UI link ≤5s and the map fills; bot posts a 3-item shortlist (title+price) from `/api/discover/{id}`.
- [ ] **AC7 (llm default):** the live loop defaults `llm()` to the hosted Nemotron endpoint; flipping to the Brev box is a one-line change, rehearsed once, not on the demo default path.
- [ ] **AC8:** a sped-up backup video of a full clean run exists.

## Risks & Mitigations
| Risk | Mitigation |
|---|---|
| Negotiation is the hardest + underscoped, was scheduled last | Re-sequenced to P0 #2, ~4-5h, before any glue (AC1). |
| Turn-2 never fires (reply is store-only today) | Rewire `/contact/{id}/reply` → next turn (AC2); named build item. |
| H 3-session cap / zombies (already bit us) | Fix `max_time_s`, DELETE discovery session on settle, per-turn frees slots, pre-demo sweep (AC4). |
| NemoClaw box CPU-only/slow | Hosted Nemotron = default live path; Brev = B-roll only (AC7). |
| WhatsApp unsaved number / turn-2 prefill | Deep-link for turn 1; turns ≥2 read latest on-screen message; owner pre-saved. |
| macOS perms lost on demo Mac | `/health` accessibility+screen_recording preflight; re-grant python3.13 + cmux/terminal if needed. |
| Telegram getUpdates on venue wifi | long-poll, single consumer, token pre-created, tested first 2h. |
| Negotiation drifts | guided script + teammate crib sheet keep in-branch; bounded turns; video backup. |

## Changelog (consensus fixes applied)
Reshaped negotiation single-shot→**fresh-session-per-turn** with a real turn driver (Architect+Critic must-fix); re-sequenced P0 to **core-first**; owner number = orchestrator config (Craigslist has no phone); normalized `sessionId`/`session_id`; fixed discovery `max_seconds`→`max_time_s` + added session teardown/sweep (root-causes the earlier zombies); made hosted Nemotron the **default** `llm()` and NemoClaw Brev the B-roll; upgraded ACs to be testable against the reshaped primitive.

# Demo Reliability — ApartmentAgent (live on stage, 2026-07-12)

Angle: **DEMO-RELIABILITY**. Goal: enumerate everything that can break LIVE, bulletproof each,
and give a preflight checklist + an "if X breaks, do Y" runbook.

Stack under test:
- **Next.js UI** on `:3000` (`app/`, `lib/discovery.ts`, `lib/geocode.ts`) — live H CLOUD Craigslist discovery + Leaflet map.
- **Telegram concierge** (`concierge/main.py`) — long-poll `getUpdates`, single consumer.
- **contact-svc** (`contact-svc/main.py`) on `:8000` — H DESKTOP computer-use drives the **WhatsApp macOS app**, per-turn negotiation.
- **The "owner"** = a friend's WhatsApp `+4915737431637` replying live.

---

## 0. The three things that will actually sink this demo (read first)

1. **The negotiation money-shot depends on a REAL inbound WhatsApp message.**
   `_respond_task` (contact-svc/main.py:203) instructs the H agent to *read the screen* and only reply
   if "the owner's LATEST message is unanswered." The UI **"Owner replied"** button and the `reply` hint
   in `POST /contact/{id}/reply` are **only hints** — they do **not** put a message on the WhatsApp screen.
   If the friend does not physically type a reply in WhatsApp, the agent correctly reports `awaiting_owner`
   and nothing happens. **The friend replying is on the critical path, not optional.**
   → Mitigation: friend on standby with the crib sheet; a co-presenter holds the owner phone as backup;
     pre-stage the first owner reply in the chat before you go on stage.

2. **H concurrency = 3 sessions. A single zombie kills discovery OR negotiation.**
   Discovery holds 1 slot, desktop negotiation holds 1 slot. The plan's "pre-demo sweep" (delete all
   `status=running` sessions) is **documented but NOT coded** anywhere. Run it manually before you walk on.
   → Mitigation: the sweep script in §Preflight step 6.

3. **Everything needs the venue wifi.** H API, Telegram, Nominatim geocoding, unpkg + cartocdn map tiles.
   Discovery degrades to cached listings gracefully; **negotiation and Telegram do not degrade** — they just fail.
   → Mitigation: phone hotspot as a hot spare + the recorded backup video.

---

## 1. Failure modes → mitigation → demo-safe fallback

### A. H (Runner-H / computer-use) failures

| # | Failure | What happens in code | Mitigation (pre-demo) | On-stage fallback |
|---|---------|----------------------|-----------------------|-------------------|
| A1 | **H quota / 429 on discovery** | `startDiscovery` `res.ok` false → throws → UI `catch` calls `/api/listings` → **cached map** (discovery.ts:139, page.tsx:106). Graceful. | Sweep sessions to 0 active first; verify quota. | Map still fills from cache; badge shows "cached listings". Narrate "the agent already indexed these." |
| A2 | **H quota / 429 on negotiation** | `create_agent`/`start_session` throws → `phase="failed"`, error event shown (main.py:340). **No cached fallback — this is the live shot.** | Sweep to 0 active; only 1 negotiation at a time (`_DESKTOP_BUSY`). Keep discovery + negotiation from overlapping. | Cut to recorded backup video of a clean negotiation run. |
| A3 | **Session zombie holds a slot** | Discovery `deleteSession` on settle (discovery.ts:235); desktop `_http_delete_session` after each turn (main.py:331). Good, but a crash between start and delete leaks a slot. | **Run the sweep script (§Preflight 6) < 2 min before demo.** Re-run after any aborted rehearsal. | If create fails with "concurrent sessions" → run sweep live, retry once, else backup video. |
| A4 | **`h/web-surfer-flash` agent id deprecated/renamed** | Hardcoded (discovery.ts:130) → create 4xx → cached fallback. | Smoke-test one real discovery in the last hour. | Cached map; don't dwell on "live" claim. |
| A5 | **Discovery takes 60–90s / stalls** | UI polls every 1.2s indefinitely; runLoop deadline = 140s then cached fallback (discovery.ts:168). Concierge deadline 150s (main.py:230). | Warm a discovery run once right before; cache is always seeded from `data/listings.json`. | After ~20s of "watching live," the map fills from cache automatically. Keep talking. |
| A6 | **max_time_s not honored / agent runs long** | Desktop watchdog `Timer(MAX_TIME_S+40=220s)` cancels handle (main.py:326). | Keep `MAX_TIME_S=180`. | Watchdog frees the slot; narrate and move on / backup video. |

### B. WhatsApp desktop control failures

| # | Failure | Code reality | Mitigation | Fallback |
|---|---------|--------------|------------|----------|
| B1 | **Agent typed but didn't press Send** | `_force_send()` deterministically activates WhatsApp + presses Return after every desktop turn (main.py:161,330). | Keep the WhatsApp input box focused, nothing else typed. Rehearse that Return sends (not newline). | If still unsent, presenter presses Return on the Mac manually. |
| B2 | **Wrong chat / messages a stranger** | Task aborts with "contact not found" if wrong/no chat (main.py:190,205). Deep-link `whatsapp://send?phone=` opens the specific number (main.py:156). | **Pre-save `+4915737431637` as a WhatsApp contact** ("ApartmentAgent Owner"); optionally set `OWNER_CONTACT_NAME`. Close all other chats. | If it opens the wrong chat, hit ✕ (cancel endpoint), reselect the chat, restart the turn. |
| B3 | **WhatsApp login / QR wall** | Task reports **BLOCKED on WhatsApp login** and stops (main.py:183). | **Confirm WhatsApp desktop is logged in and stays logged in** the morning of. Don't log out other linked devices. | Re-link WhatsApp on the Mac (phone → Linked Devices) or backup video. |
| B4 | **`_force_send` fires on empty/wrong focus** | Return on empty box is safe; but if H left focus in the search field, Return could open a chat. | Task step 5 verifies the message is sent before finishing; force_send is belt-and-suspenders. | Low risk; presenter watches the Agent View and intervenes. |
| B5 | **Deep link doesn't open (unsaved number)** | `open whatsapp://send` needs WhatsApp registered as the URL handler. | Test the deep link once; pre-save the contact so it always resolves. | Presenter manually opens the chat; the agent still reads it. |
| B6 | **README says Chrome/WhatsApp-Web, code default is desktop app** | README:31 describes WhatsApp **Web in Chrome** (`~/.hai/chrome-profile`); code default `CONTACT_MODE=desktop` drives the **native app** (main.py:49). **Doc drift.** | Trust the CODE: prep the **WhatsApp desktop app**. Don't waste time logging into Chrome WhatsApp Web unless you deliberately run `CONTACT_MODE=browser`. | Know both paths exist; `CONTACT_MODE=browser` only works if `~/.hai/chrome-profile` is pre-logged into WhatsApp Web. |

### C. macOS permission failures

| # | Failure | Code reality | Mitigation | Fallback |
|---|---------|--------------|------------|----------|
| C1 | **Accessibility revoked** | `/health` returns `accessibility` via `AXIsProcessTrusted` (main.py:401). Without it, keystrokes/clicks fail silently. | Grant **Accessibility** to BOTH the terminal running uvicorn AND `python3.13`. `curl :8000/health` → `desktop_ready:true`. | Re-grant in System Settings → Privacy → Accessibility, **restart uvicorn**, re-check /health. |
| C2 | **Screen Recording revoked** | `/health.screen_recording` via `CGPreflightScreenCaptureAccess` (main.py:407). Agent can't "see" the screen. | Grant **Screen Recording** to the same two apps; a macOS/python update resets these. | Re-grant, **fully quit + reopen the terminal app** (Screen Recording needs a relaunch), restart uvicorn. |
| C3 | **python3.13 upgraded → perms reset** | TCC keys perms to the exact binary path. | Freeze the Python version; don't `brew upgrade` the morning of. Re-verify /health. | Re-grant to the new binary path. |

### D. Telegram failures

| # | Failure | Code reality | Mitigation | Fallback |
|---|---------|--------------|------------|----------|
| D1 | **Two getUpdates consumers → 409 conflict** | Long-poll single-consumer (main.py:354). A leftover `python main.py` or a set webhook steals updates. | **Exactly one** concierge process. `curl "$TG_API/deleteWebhook"` before start; `pkill -f concierge/main.py` to clear strays. | Kill the stray process; the running one recovers on the next poll. |
| D2 | **Telegram rate limit on the shortlist burst** | `run_search` fires text + 3 photos + map back-to-back (main.py:253-261). No retry in `send`. | Space the sends slightly; or accept a dropped photo (non-fatal). | If a photo 429s, keep going — text shortlist already delivered. |
| D3 | **Telegram / api.telegram.org unreachable** | Poll loop `catch` sleeps 3s and retries forever (main.py:361). Bot appears dead. | Test on venue wifi in the first 2h. Hotspot spare. | **Drive the demo from the Next.js UI directly** (search box → Reach out), skipping the bot. |
| D4 | **Audience DMs the bot mid-demo** | Any chat_id gets independent state but shares the single desktop lock + 3 H slots. | Keep the bot handle private; don't show it on the projector. | Ignore stray chats; they can't corrupt your chat_id's state. |

### E. Discovery / map / geocode failures (venue-wifi sensitive)

| # | Failure | Code reality | Mitigation | Fallback |
|---|---------|--------------|------------|----------|
| E1 | **Nominatim geocode fails/rate-limits** | 12 listings geocoded via OSM Nominatim (geocode.ts); on failure → deterministic jitter around city center (geocode.ts:36). Pins never pile up. | Cache is warmed on first run (in-memory Map). Don't hammer >1/s. | Pins land near the city center via jitter — map still looks right. |
| E2 | **unpkg/cartocdn tiles blocked** | UI `ListingMap` (react-leaflet) and `make_map_image` both load Leaflet + tiles from CDNs. Blocked = blank/greyed map. | Pre-load the UI once on venue wifi so the browser caches tiles. | The concierge map image simply won't send (`make_map_image` returns None, main.py:129) — text shortlist still lands. UI map may show grey tiles; listings/markers still render. |
| E3 | **Shared `browse` binary contention** | `make_map_image` shells out to `~/.claude/skills/gstack/browse/dist/browse` (main.py:89,125). If the /browse skill is used elsewhere, they contend on one daemon. | Don't run any gstack /browse or /qa skill during the live demo. | Map image drops; text shortlist unaffected. |
| E4 | **Next.js store lost (multi-worker / restart)** | Discovery records live in `globalThis.__discoverStore` (discovery.ts:31) — single `next dev` process only. `next start` with workers wouldn't share it. | **Run `npm run dev` (single process).** Don't restart Next mid-demo. | Restarting Next drops in-flight discovery ids; just start a fresh search. |

### F. Network / human failures

| # | Failure | Code reality | Mitigation | Fallback |
|---|---------|--------------|------------|----------|
| F1 | **Total venue network loss** | H, Telegram, tiles all fail; discovery → cached (ok); negotiation dead. | Phone hotspot pre-paired to the demo Mac; recorded backup video ready to play. | Switch to hotspot; if still dead, play the backup video. |
| F2 | **The friend doesn't reply in time** | Negotiation waits; concierge auto-advances every 25s while `awaiting_owner` (main.py:311) but there's nothing new to read until a real message lands. Concierge times out at 480s. | Friend on standby watching the phone with the crib sheet; a co-presenter holds a second copy of the owner phone. | Presenter (or co-presenter) types the scripted owner reply on the owner phone; agent then responds. Worst case: backup video. |
| F3 | **Ports 3000/8000 already in use** | uvicorn/next fail to bind. | `lsof -i :3000 -i :8000` in preflight; kill strays. | Kill the occupant, restart. |
| F4 | **Missing env (HAI_API_KEY / TG token / OWNER_WHATSAPP)** | Discovery throws "HAI_API_KEY not set" (discovery.ts:123); contact 400 (main.py:424); concierge `SystemExit` if no token (main.py:348); empty OWNER_WHATSAPP → "No OWNER_WHATSAPP configured" (main.py:270). | Verify all three .env files (root, concierge, contact-svc) in preflight. HAI_API_KEY needed in BOTH root and contact-svc. | Set the missing var, restart the affected service. |

---

## 2. Pre-demo preflight checklist (run in order, ~10 min before)

1. **Network**: connect the demo Mac to venue wifi; confirm `curl -s https://api.telegram.org` and `curl -s https://agp.eu.hcompany.ai` both respond. Pair the phone hotspot as a spare and confirm it works too.
2. **Env vars** (all three files present + filled):
   - root `.env`: `HAI_API_KEY`, `CONTACT_SVC_URL=http://localhost:8000`
   - `contact-svc/.env`: `HAI_API_KEY`
   - `concierge/.env`: `TELEGRAM_BOT_TOKEN`, `OWNER_WHATSAPP=+4915737431637`, `NEXT_URL`, `CONTACT_URL`
3. **Ports free**: `lsof -i :3000 -i :8000` → kill anything stale.
4. **Start services (single instances each):**
   - `npm run dev` (NOT `next start` — the discovery store is in-process, discovery.ts:31)
   - `cd contact-svc && CONTACT_MODE=desktop uvicorn main:app --port 8000`
   - `curl "$TG_API/deleteWebhook"` then `python concierge/main.py` (verify it prints `Owner: +4915737431637`)
5. **macOS perms**: `curl -s localhost:8000/health | jq` → require `desktop_ready:true`, `accessibility:true`, `screen_recording:true`, `whatsapp_installed:true`, `hai_key_present:true`, `hai_sdk_installed:true`, `desktop_busy:false`.
6. **H session sweep (kill zombies — NOT automated, do it by hand):**
   ```bash
   curl -s -H "Authorization: Bearer $HAI_API_KEY" \
     "https://agp.eu.hcompany.ai/api/v2/sessions?status=running" \
   | jq -r '.[].id // .sessions[].id' \
   | while read id; do
       curl -s -X DELETE -H "Authorization: Bearer $HAI_API_KEY" \
         "https://agp.eu.hcompany.ai/api/v2/sessions/$id" ; done
   ```
   Then confirm quota active == 0 (`GET /api/v2/sessions/quota`). Re-run after any aborted rehearsal.
7. **WhatsApp desktop**: open it, confirm it's **logged in** (not showing QR), confirm `+4915737431637` is saved as a contact, and **close every other chat** so only that one is reachable. Quiet Slack/Mail/notifications (Do Not Disturb).
8. **Warm the paths once**: run one real discovery from the UI (cache tiles + geocode); run one full 3-turn negotiation with the friend to "booked"; then **re-run the sweep (step 6)** to free the slots you just used.
9. **Friend check-in**: text the friend NOW, confirm they're watching the phone, resend the crib sheet (available → accept small discount → agree a viewing time, one branch per turn).
10. **Backup video**: open the recorded clean-run video in a player, cued to 0:00, on a second display/space so you can cut to it in 2 seconds.
11. **Kill distractions**: no gstack /browse, /qa, or other browse-daemon skills running during the demo (they contend with `make_map_image`, main.py:89).

---

## 3. On-stage runbook — "if X breaks, do Y"

- **Map doesn't fill / spins >20s** → it auto-falls to cached listings; if not, say "the agent already indexed these" and the cached map is already there. Do NOT restart Next (drops the store). Keep narrating.
- **Badge shows "cached listings" instead of "live"** → fine, don't call attention to it; the flow is identical downstream.
- **"Reach out" in the UI shows an alert** → only the perfect listing has a `whatsapp` number (page.tsx:135). Reach out on the **perfect** listing, or drive negotiation via the Telegram bot (which always uses `OWNER_WHATSAPP`).
- **Agent opens WhatsApp but message doesn't send** → wait 2s for `_force_send`; if still stuck, press **Return** on the Mac yourself.
- **Agent in the wrong chat** → hit ✕ (cancel), click the correct chat, restart the turn.
- **"BLOCKED on WhatsApp login"** in the event stream → WhatsApp got logged out. Re-link via phone, or cut to backup video.
- **Negotiation stuck on `awaiting_owner`** → the friend hasn't sent a real WhatsApp message. Signal the friend; if no response in ~10s, have your co-presenter type the scripted reply on the owner phone. The concierge auto-advances every 25s once a message appears.
- **/health shows `desktop_ready:false` mid-demo** → a permission dropped. You cannot fix TCC live gracefully → cut to backup video; fix in the break.
- **Telegram bot silent** → drive the whole demo from the Next.js UI directly (search box → Reach out on the perfect listing). The bot is a front-door, not load-bearing.
- **Telegram 409 conflict in logs** → a stray consumer/webhook. `curl "$TG_API/deleteWebhook"`, `pkill -f concierge/main.py`, restart one instance.
- **"concurrent sessions" / quota error** → run the sweep (Preflight 6) live, retry once, else backup video.
- **Network fully dead** → switch the Mac to the phone hotspot; if H is still unreachable, play the backup video and narrate over it.
- **Anything unrecoverable within ~15s** → play the backup video. A smooth recorded run beats a frozen stage.

---

## 4. Rehearsal checklist (night before + morning of)

- [ ] Full end-to-end on venue-like network: Telegram DM → live discovery map → pick → WhatsApp negotiation → "booked", with the friend replying live, in ≥3 turns.
- [ ] Confirm each desktop turn's H session is **deleted** (slot freed) before the next — `GET /sessions/quota` returns to 0 after a run.
- [ ] Verify the sweep script actually deletes running sessions (seed one, sweep, confirm 0).
- [ ] Force a WhatsApp login wall → confirm you see "BLOCKED on WhatsApp login" (no silent hang).
- [ ] Force a 429 / kill wifi mid-discovery → confirm the map falls back to cached and the badge flips.
- [ ] Confirm the friend's number is saved; run the `whatsapp://send` deep link once and watch it open the right chat.
- [ ] Time the full run; confirm it fits the 1:30 demo slot with buffer.
- [ ] Record the clean backup video (Telegram + UI + WhatsApp Agent View), 2–4× speed, cued and ready.
- [ ] Re-grant + re-verify Accessibility + Screen Recording for the terminal app AND python3.13; confirm `/health desktop_ready:true`.
- [ ] Confirm README vs code: you are demoing **WhatsApp desktop app** (`CONTACT_MODE=desktop`), not Chrome WhatsApp Web (README:31 is stale).
- [ ] Assign roles: driver (Mac), narrator, friend-on-phone, backup-video operator.

---

## 5. Known code-level gaps worth a 10-minute fix (optional, pre-demo)

- **The session sweep is a manual curl, not code.** Add a `/admin/sweep` route or a `sweep.sh` so it's one command, not a copy-pasted pipe under pressure. (Prevents the #1 zombie failure.)
- **README drift (README:31).** One-line edit to say "WhatsApp **desktop app** (`CONTACT_MODE=desktop`)" so no one preps the wrong surface.
- **`send()` has no retry on Telegram 429** (main.py:57). A tiny sleep/space between the shortlist photo sends avoids a dropped image on the burst.
- **No visible "friend must actually reply on WhatsApp" cue.** The UI "Owner replied" button implies it injects a message; it only hints. Rename it or add a note so the operator doesn't wait on a button that can't advance a desktop turn.
</content>
</invoke>

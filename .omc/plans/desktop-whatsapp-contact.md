# Plan: WhatsApp Desktop contact via H desktop computer-use

Status: **PENDING APPROVAL** (consensus: Planner → Architect → Critic complete; Critic verdict REVISE → all fixes applied)
Target: /Users/admin/Documents/AI 2026/hackathonIterate/Homeless
Scope: the "Reach out" money-shot messages the apartment owner through the **WhatsApp macOS app** (already logged in), driven by H **local desktop control**, replacing WhatsApp-Web browser control as the default. No Next.js UI changes.

## Requirements Summary
- H **desktop** agent (`kind:"desktop"`, `host:"user_device"`, `hai-agents[desktop]`, Python-only) opens the WhatsApp desktop app, opens the owner's chat, types a polite inquiry, sends it — watched live in the existing Agent View panel.
- Reuse the current contact-svc contract unchanged: `POST /contact`→`{session_id}`, `GET /contact/{id}`→`{status,events[],answer,agent_view_url}`, `GET/POST /contact/{id}/reply`. Add `POST /contact/{id}/cancel`.
- Grounded strictly in H docs (`desktop/local-control`, `observe-and-steer`, `sessions/create`). Every API name below is doc-verified.

## Decision (ADR)
- **Decision:** Option A — keep `CONTACT_MODE=desktop|browser` (default **desktop**), browser path reachable via env flag as insurance. Ship desktop as the money shot.
- **Drivers:** (1) WhatsApp desktop is already logged in → most reliable auth; (2) no UI churn; (3) macOS permission friction is the top live-run risk.
- **Alternatives considered:** Option B (delete browser path) — architect-recommended for less surface area; Option C (separate microservice) — rejected (needless process/wiring).
- **Why chosen (synthesis of Architect vs Critic):** Architect correctly noted the mode flag buys **no concurrency** (one local desktop session per process) and that the browser fallback is **illusory unless** `~/.hai/chrome-profile` is pre-logged into WhatsApp Web. Critic correctly noted the browser path is the **only currently-working, tested code**, so deleting it the night before a demo is the riskier move. **Resolution:** keep it as one small env-gated branch, default desktop. **Honest caveat baked into the docs/README:** the browser fallback is real insurance ONLY if you keep a WhatsApp-Web login in `~/.hai/chrome-profile`; if you won't maintain that, set the code to collapse to desktop-only (delete the branch) to reduce surface area.
- **Consequences:** two task builders + one env branch to maintain; a genuine fallback path only when the chrome profile is pre-logged-in; the real demo-safety net is `max_time_s` + a hard watchdog + explicit `blocked`/`infeasible` UI states, not the browser path.
- **Follow-ups:** if the second WhatsApp-Web login won't be maintained, collapse to Option B.

## RALPLAN-DR Summary
**Principles:** (1) reuse contact-svc scaffolding, no UI change; (2) doc-grounded API names only; (3) cannot silently hang — every failure is an explicit visible state; (4) minimal agent blast radius (one task, nothing else); (5) respect the 3-session cap (serialize + cap + watchdog + cancel).
**Decision drivers:** already-logged-in auth · no UI churn · macOS permission friction.
**Options:** A (mode flag, default desktop) [chosen] · B (replace browser) · C (microservice) [rejected].

## Implementation Steps (all R1–R7 fixes folded in)
1. **`contact-svc/requirements.txt`:** `hai-agents[browser]` → `hai-agents[browser,desktop]`.
2. **`contact-svc/main.py` — request + mode:**
   - `CONTACT_MODE = os.getenv("CONTACT_MODE", "desktop")`.
   - `ContactRequest`: add `mode: str | None = None` and **`contact_name: str | None = None`** (R4). Effective mode = `req.mode or CONTACT_MODE`.
3. **Agent creation branch** (in `_run_contact_session`, ~main.py:154):
   - desktop: `environments=[{"id":"my-mac","kind":"desktop","host":"user_device"}]`, description "Drives the WhatsApp desktop app on my Mac."
   - browser: unchanged existing web env.
4. **`max_time_s` + watchdog (R2):** pass **`max_time_s=180`** (NOT `max_seconds`) into the `start_session`/`run_session`/`create_session` create call. Add a watchdog `threading.Timer(210, lambda: handle.cancel())` (soft-cap + ~30s grace) because `max_time_s` only *asks* for a final answer, it does not hard-kill (`sessions_create.md:52-56`).
5. **Persist the handle + real cancel (R1):** store the `start_session` handle on the session record (not just `hai_session_id`). Add `POST /contact/{id}/cancel` → `handle.cancel()` (`observe-and-steer.md:98`); fallback `DELETE https://agp.eu.hcompany.ai/api/v2/sessions/{hai_session_id}` with the bearer key. **Delete the invented `client.sessions.cancel(id)`.** Also cancel on FastAPI `shutdown`.
6. **Serialize desktop sessions (R3):** a module-level lock / `active_desktop_session` flag. A 2nd `POST /contact` while a desktop session is active returns **HTTP 409** and does NOT touch the running one (`local-control.md:13` — a 2nd local desktop session silently cancels the 1st).
7. **Surface `outcome`/`error_code` mid-run (R5):** read `outcome` from `changes`/`status` during the run (not only at settle), emit a human-readable event for `blocked` (login wall / missing perms) and `infeasible` (contact not found) (`observe-and-steer.md:181-217`).
8. **`/health` preflight (R7):** return `mode` and a `desktop_ready` hint (Accessibility + Screen Recording granted per `local-control.md:62-66`; WhatsApp installed). Keep `hai_key_present`, `hai_sdk_installed`.
9. **agent_view_url:** already read at `main.py:180`; keep the `https://platform.hcompany.ai/agents/sessions/{id}` construction as fallback when null (queued).
10. **No Next.js changes.** Confirm the ✕ can call the new cancel endpoint (optional).
11. **Docs:** `contact-svc/README.md` + root `README.md`: `CONTACT_MODE=desktop`, `hai-agents[desktop]`, macOS permissions, the browser-fallback caveat, and `HAI_AUTO_BRIDGE` note.

## §2 — Desktop agent task (natural language; contact_name primary per R4)
> You are operating the macOS desktop of this machine. Do exactly the following, one step at a time; stop after the message is sent. Do not open any other app or take any unrelated action.
> 1. Open the **WhatsApp** desktop app (Cmd+Space → type "WhatsApp" → Return, or click it in the Dock). Wait until the chat list is visible.
> 2. If a login/QR screen is shown instead of chats, report you are **blocked on WhatsApp login** and stop.
> 3. Click the search field at the top of the chat list. Search for the contact by name `{contact_name}` first; if no name is given, type the number `{whatsapp_number}`. Open the matching chat. (WhatsApp desktop search matches **saved contacts / existing chats**; an unsaved raw number may not open a new chat.)
> 4. If nothing matches, report **"contact not found"** and stop — do NOT message a wrong person.
> 5. Click the message box and type EXACTLY: `{message}`
> 6. Send (Return). Confirm the sent check mark appears, then finish and report the inquiry was sent.

## §3 — macOS setup / run
```bash
cd contact-svc
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # hai-agents[browser,desktop]
CONTACT_MODE=desktop uvicorn main:app --port 8000   # first run errors until perms granted
```
Grant to the terminal running uvicorn (Terminal/iTerm) in **System Settings → Privacy & Security**: **Accessibility** + **Screen Recording**; restart uvicorn. WhatsApp desktop installed + logged in. Ensure `HAI_AUTO_BRIDGE` is unset/≠0. Pre-save the teammate's number as a WhatsApp contact (or pass `contact_name`).

## §4 — Live view + reply path
- **Live steps + Agent View:** unchanged — contact-svc streams `/changes` events + `agent_view_url`; the UI panel already renders them and shows "Watch live in H Agent View ↗". `start_session` auto-connect drives the desktop actions (`local-control.md:12,60`); the existing start→stream→wait ordering is fine (the read-only `stream()` caveat applies only to custom tools, which this task has none — `observe-and-steer.md:48`).
- **Reply / notification (RECOMMENDATION):** keep **`POST /contact/{id}/reply` inject** as the demo path (owner replies in WhatsApp on the same Mac; inject the text → notification fires). A second desktop session to *read* the reply would contend for the single-desktop slot and is fragile → stretch only.

## Acceptance Criteria (testable)
- [ ] `pip install -r requirements.txt` installs `hai-agents[browser,desktop]`.
- [ ] `GET /health` returns `mode:"desktop"` + a `desktop_ready` boolean.
- [ ] R1: after `POST /contact/{id}/cancel`, `GET /contact/{id}` shows `status:"interrupted"`.
- [ ] R2: a deliberately hung task is force-cancelled within ~30s grace; org quota slot frees.
- [ ] R3: two back-to-back POSTs → first completes, second returns 409, first never interrupted.
- [ ] R4: unsaved number + no `contact_name` → "contact not found", visible state, no wrong chat messaged; a saved teammate opens the correct chat.
- [ ] R5: forcing the WhatsApp login wall yields a visible `blocked` reason (no silent hang).
- [ ] R6: on a real `start_session` run the cursor/keystrokes visibly move the Mac; else fall back to the blocking `run_session` branch.
- [ ] End-to-end: with perms granted + WhatsApp open, `POST /contact` to a consenting teammate → app opens, message typed+sent (watch Agent View), status `completed`; `POST /contact/{id}/reply` → "Found you a place!".

## Risks & Mitigations
| Risk | Mitigation |
|---|---|
| macOS Accessibility/Screen-Recording not granted | Pre-grant; `/health.desktop_ready`; documented toggles; `CONTACT_MODE=browser` insurance (if chrome-profile pre-logged-in). |
| Agent drives the whole screen live on stage | Tightly-scoped task; close other apps; `max_time_s`+watchdog; ✕/cancel endpoint. |
| WhatsApp desktop won't open an unsaved raw number | `contact_name` primary; pre-save the teammate; abort-if-not-found. |
| Local desktop session counts against 3-session cap; zombies block runs | `max_time_s`=180 + watchdog cancel + serialize; startup cleanup cancels stale running sessions; `hai sessions cancel` escape hatch. |
| One local desktop session per process | Serialize (R3): 2nd POST → 409. |
| Browser fallback illusory | Only claim it if `~/.hai/chrome-profile` is pre-logged into WhatsApp Web; else collapse to desktop-only. |

## Changelog (consensus improvements applied)
- Switched cancel to handle.cancel()/DELETE + persist the handle (R1); renamed `max_seconds`→`max_time_s` + added watchdog (R2); coded serialization/409 (R3); added `contact_name` primary (R4); mid-run `outcome`/`blocked` surfacing (R5); auto-bridge verification step (R6); `/health` preflight (R7). Reframed Option A with the honest browser-fallback caveat (Architect vs Critic synthesis).

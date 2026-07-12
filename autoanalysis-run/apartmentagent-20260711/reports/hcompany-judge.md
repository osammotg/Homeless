# H Company Judge — ApartmentAgent

*Angle: put yourself in the head of an H engineer who BUILT the computer-use agents. Would this demo impress them? Is the computer-use central and un-fakeable? What holes get poked in Q&A?*

---

## Verdict in one line

**This is a top-3 finalist candidate IF they lead with the desktop WhatsApp negotiation and prove discovery is live.** The team clearly read the H docs and ran the real API hard — that shows in the code and it will show to us. The single risk that turns a winner into a "nice toy" is the demo defaulting to the safe, fakeable paths (cached listings + the web UI's canned reply). The un-fakeable wow is real; it's just buried behind two escape hatches.

---

## The ONE 90-second moment to lead with

**Split-screen: Telegram on the left, a REAL Mac running the WhatsApp desktop app on the right.**

1. In Telegram you type "find me a place in SF, 2 people, ~$2500, mid-July." The bot replies "On it — watch me live" with a `platform.hcompany.ai` Agent View link.
2. Shortlist lands in Telegram: 3 photos + prices + a dark map pin image. You reply "1".
3. **Cut the room's eyes to the right screen.** The H **desktop** agent physically brings WhatsApp to the front, types a haggling inquiry into the real input box, and sends it. A teammate playing the owner replies with a counter-price on their phone. The agent — a *fresh session* — reads the new chat bubble on screen, counters back under budget, and books a viewing.
4. Confirmation lands back in Telegram: "Booked a viewing at 6pm tomorrow — $2,327/mo."

Why this is the moment, and not the browser search: **every other Track-2 team will demo `web-surfer-flash` clicking around a website.** That's table stakes for this crowd — we built it, we've seen it a hundred times. What almost nobody will bring is **computer-use driving a native app that has no API and no web-automation surface at all** (WhatsApp desktop), doing a **multi-turn negotiation with visible price movement**. Those are the two things an H judge literally cannot dismiss as a scripted browser macro. The cursor moving on a real Mac, in a real native app, is the un-fakeable frame.

---

## The pitch (memorable, one line)

> **"Two H agents, two surfaces, zero APIs: one scouts Craigslist in the browser, the other haggles with the landlord in the WhatsApp desktop app — computer-use the whole way down."**

Backup framing if they want the "why it matters": *"The last mile of renting isn't search — it's the DMs. We automated the DMs, on an app that has no API, by driving it like a human."*

---

## What genuinely impresses an H judge (the un-fakeable substance)

These are the things that tell me the team *used our platform for real*, not mocked it:

- **Two distinct H surfaces, correctly chosen.** Browser (`h/web-surfer-flash` via `POST /api/v2/sessions`) for discovery; **desktop local control** (`{kind: "desktop", host: "user_device"}`) for the WhatsApp negotiation. They matched each surface to the job — browser for a website, desktop for a native app. That's the right instinct. (`lib/discovery.ts:126`, `contact-svc/main.py:297`)
- **The fresh-session-per-turn insight.** They understood that an H session *terminates after it answers* and cannot "wait" for a human reply, so each owner reply fires a brand-new desktop session that re-reads the whole on-screen conversation. That's a non-obvious, correct reading of our session lifecycle — not something you get from skimming the quickstart. (`contact-svc/main.py:11-21`, `_respond_task`)
- **Structured output used on both surfaces.** `answer_format` JSON schema for listings and for the per-turn negotiation result (`replied / awaiting_owner / booked / agreed_price / viewing_time`). This is exactly how we'd want it consumed. (`lib/discovery.ts:77`, `contact-svc/main.py:79`)
- **Operational scars that only come from real usage.** They fixed `max_seconds → max_time_s` (with a comment: "sessions never time-bounded → zombies"), they `DELETE` sessions to free the **3-slot concurrency limit**, they serialize desktop turns with a lock, and they run a watchdog cancel. Nobody writes these unless they hit our rate limits and zombie sessions live. That earns trust. (`lib/discovery.ts:136,235,240`, `contact-svc/main.py:76,326,331`)
- **They surface our Agent View as the "watch live" link** and build the URL deterministically from the session id so it works even while queued. Good product use of our observe-and-steer surface. (`lib/discovery.ts:144`)

This is not a team that bolted our logo onto an OpenAI app. Computer-use *is* the thesis: both no-API platforms are un-scriptable-by-design, which is the exact wedge our agents exist for.

---

## Where it looks like a toy vs a real agent (holes I'd poke in Q&A)

**1. Discovery probably falls back to cached JSON on stage — and that guts the "live" claim.**
Their own README admits Craigslist "hits CAPTCHA/IP blocks within minutes," and the code has a full `fallbackListings()` path that loads `data/listings.json` and even rewrites dead permalinks to live *search* URLs so a click "always lands." The UI badge flips to "cached listings." A skeptical judge's first question is: *"Was that map filled by the agent, or from a file?"* If the honest answer is "a file," then one of your two computer-use surfaces evaporated and Track-2 alignment drops. (`lib/discovery.ts:56,221,229`)
→ **Close it:** pre-warm one genuinely-live discovery session seconds before the demo (or scope it to 3–4 listings that reliably complete inside `max_time_s`), and *click the Agent View link on stage* so the room watches `web-surfer` actually reading Craigslist. Show the "live · Craigslist (H agent)" badge deliberately. If you can't guarantee live, be honest ("listings are pre-indexed") and put 100% of the computer-use weight on the WhatsApp negotiation — don't let a judge *catch* the fallback.

**2. `_force_send()` — the AppleScript that presses Return — is a loaded gun aimed at your own credibility.**
After each desktop turn you run `osascript ... key code 36` to send whatever is in the box "belt-and-suspenders." In Q&A this is fatal if surfaced: *"So did the H agent send the message, or did your AppleScript?"* If the agent ever fails to click send and the osascript saves it, then the un-fakeable action wasn't done by computer-use. This single helper can turn your strongest moment into "they scripted it." (`contact-svc/main.py:161,330`)
→ **Close it:** for the demo, let the agent's own send stand and *show the agent clicking the send button*. Keep the safety net silent (don't mention it), or gate it behind a "only if the agent reported replied=false" check so it never front-runs a successful agent send. The story must be "the agent did it," and the screen must back that up.

**3. The web UI has a hardcoded "owner reply."**
`simulateReply()` in `app/page.tsx:187` injects the canned string *"Yes! It's available for your dates — want to come see it tomorrow?"* If they demo the Next.js app's "Owner replied" button, an H judge sees a scripted string and mentally files the whole negotiation as fake — even though the *Telegram* path uses a real teammate and a real screen-read. Two entry points, and the more fakeable one is the flashier UI.
→ **Close it:** judge on the **Telegram path with a real teammate owner**. Hide/retire the web `simulateReply` button for the live demo. Don't give the room a canned string to notice.

**4. The "booking" is staged (consenting teammate).**
That's the correct, ethics-clean choice — but a judge knows the owner is a plant. The negotiation therefore has to *feel* real to survive: it must be genuinely multi-turn with **visible price movement** (asking $2,450 → agent counters ~$2,327 → owner agrees), not one message and a thumbs-up. The negotiation policy code supports this (counters, budget cap, discount ask), so *use it* — script the teammate to push back once so the agent visibly haggles. (`contact-svc/main.py:137`)

**5. Two products in one repo (web app + Telegram bot) dilutes the narrative.**
A judge wonders "which is the thing?" Pick Telegram as the front door for the demo (it's the better story: chat → live agents → chat), and treat the web app as the "operator's live view" you flash for 5 seconds to prove the browser session is real.

**6. The Telegram map is a cosmetic Leaflet screenshot, not H.**
`make_map_image()` renders pins via the `browse` binary. Harmless and nice, but don't imply it's agent output — a judge who inspects will see it's unrelated to computer-use. Just present it as UI. (`concierge/main.py:92`)

---

## Track-2 alignment (is computer-use central + un-fakeable?)

**Strong — arguably the strongest possible framing** *if the demo doesn't leak its escape hatches.* The entire premise is "platforms with no API," which is precisely where computer-use is the only tool that works — there's no API shortcut anyone could accuse them of taking. The desktop WhatsApp surface is the differentiator that most teams won't have and that we, the builders, would find genuinely hard. The only thing that can lower this score is self-inflicted: (a) discovery visibly falling back to cache, or (b) the AppleScript send being surfaced. Both are fixable before Saturday.

**Scorecard read (5×20):** Technicality high (fresh-session lifecycle, dual surface, real ops hardening). Track-alignment high (no-API thesis, desktop surface). Usefulness obvious (everyone has rented and hated the DMs). Creativity solid (desktop app negotiation is a fresh use of our platform). Demo is the swing variable — currently gated on live-discovery reliability and on not exposing the fakeable paths. Nail the demo framing and this competes for #1.

---

## The three things to change before demoing

1. **Reframe the demo around the Telegram → real-WhatsApp-desktop negotiation** with a real teammate owner and a split-screen showing the Mac. That's the un-fakeable wow; make the room watch it happen on a real screen.
2. **Prove discovery is live at least once** (click the `platform.hcompany.ai` Agent View link; show the "live" badge) — or be honest it's pre-indexed and lean entirely on the desktop surface. Never let a judge *catch* the cache fallback.
3. **Neutralize the two "gotcha" artifacts:** silence/gate `_force_send()` so the agent's own send is the visible action, and retire the web `simulateReply` canned string for judging.

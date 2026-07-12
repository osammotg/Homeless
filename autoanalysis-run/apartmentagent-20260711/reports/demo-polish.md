# Demo-Polish Angle — Homeless / ApartmentAgent

Targeted, high-impact visual/UX wins that make the on-screen demo read as a premium product to judges. This is **not** a redesign (the "Signal Dispatch" pass already landed the amber/mono/cyan direction well) — every item below is surgical polish on top of it. Effort is S (minutes) or M (an hour-ish).

Evidence captured live at http://localhost:3000 plus the Telegram map image. Screenshots in `evidence/demo-polish/`.

---

## The one thing to fix before anything else

### 1. The Agent View is streaming raw class names — "AgentEvent" x20 (impact 5, M)
The Agent View panel is the entire "wow" of this project — a live terminal that's supposed to feel like a machine thinking. In the live run it is instead a solid column of repeated internal event type names:

> `15 AgentEvent` · `16 AgentEvent` · `17 MetricsUpdateEvent` · `18 AgentEvent` · `19 AgentEvent` …

Root cause is in `lib/discovery.ts` `eventText()` (lines 108-119): it looks for `message/text/thought/action/summary/content` string fields, and when an H event has none (which is most of them), it falls through to `return String(type)` — the bare class name. The twin logic lives in `contact-svc/main.py`.

**Fix (S/M):**
- Add a lookup map from known H event types to human milestones ("Agent online — browser booted", "Dispatching to H web-surfer", "Reading Craigslist results", "Extracting listing details…").
- **Drop** any event that resolves to a bare type name, so only meaningful steps render.
- When a real thought/action string is present, surface it.

This single change flips the marquee feature from "debug log" to "watch the agent work." Evidence: `03-agentview-later.png`, `02-agentview.png`.

### 2. De-dupe + throttle the feed so steps land as beats (impact 4, S)
Even humanized, collapse consecutive identical events ("Scanning listings ×6"), skip pure `MetricsUpdateEvent` telemetry, and optionally fade each new line in (`AgentViewPanel.tsx`). A handful of clean sequential beats reads as deliberate; a fast-scrolling wall reads as noise. Evidence: `03-agentview-later.png`.

---

## The dead canvas problem

### 3. Make the map alive during discovery — scanning sweep + ghost pins (impact 4, M)
During the `discovering` phase, the right ~75% of the screen is a perfectly still, empty map for 60-120s — the exact window judges watch most. The panel claims the machine is working while the largest surface contradicts it. Add a restrained scan-line/radial sweep over the center and 3-6 faint pulsing ghost price pins that resolve into real pins when results land. Evidence: `02-agentview.png`, `01-idle.png`.

### 4. Stronger idle/hero state (impact 4, M)
First frame a judge sees: an empty map plus one tiny dashed box reading "Enter your search and the agent will scout Craigslist live." It looks unfinished and explains nothing. Add a centered map hero (name + tagline + 3-step "Scout → Shortlist → Negotiate on WhatsApp") **or** pre-seed the cached listing pins so the canvas is never blank. Fade it out on first search. Evidence: `01-idle.png`.

---

## Quick brand/consistency wins

### 5. Product tagline under the brand (impact 3, S)
Header is `Homeless` + `APARTMENTAGENT` with zero explanation. Add one muted line: *"An AI agent that scouts Craigslist and negotiates your lease over WhatsApp."* The name is memorable but opaque; one sentence removes all ambiguity. Evidence: `01-idle.png`.

### 6. Fix the muddy-brown loading button (impact 2, S)
The primary button while searching is amber at `opacity:.55` (disabled) → renders muddy brown behind "Agent is searching Craigslist…". It reads as broken during the most important moment. Give the working state its own look: bright amber + progress shimmer / pulsing border instead of dimming. Evidence: `02-agentview.png`.

### 7. Recolor the Agent View "RUNNING" badge to cyan (impact 2, S)
The design commits to a strict 3-role palette (amber=action, cyan=agent telemetry, green=contact), but the footer "RUNNING" badge inside the cyan telemetry panel is amber (`.badge.live`). Within one cyan-framed panel an amber pill breaks the self-imposed grammar. Add a cyan status variant. Evidence: `02-agentview.png`.

---

## Second surface: Telegram

### 8. Bold prices/titles via Markdown (impact 2, S)
`concierge/main.py` uses `parse_mode` **nowhere** — every message is flat plain text. The Telegram thread is a screenshared demo surface too. Add Markdown/HTML parse_mode and bold prices, titles, and the "✅ Booked!" line; structure the shortlist as clean rows. Near-zero effort, makes the chat read like a product, not a debug echo. Evidence: `04-telegram-map.png`.

### 9. Match Telegram map pins to the web's amber best-match pin (impact 2, S)
`make_map_image` renders all pins as hollow cyan rings; the web app marks the best-match with a glowing filled amber pin. Render the perfect listing's Telegram pin amber too, so both surfaces share one visual language. Evidence: `04-telegram-map.png` vs `05-results.png`.

---

## Positive notes (leave alone)
- The results state (cards + amber best-match rail + WhatsApp-green CTA + map price pins) already looks premium — see `05-results.png`. Don't touch it.
- Mono numerics, amber/cyan role separation, and the Agent View chrome (timer, session id, pulse) are strong bones; the fixes above are about the *content* flowing through them, not the frame.

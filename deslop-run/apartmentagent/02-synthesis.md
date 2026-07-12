# Synthesis — "Signal Dispatch"

Both critics independently converged: kill the emerald+cyan AI-default palette, kill emoji-as-icons, add mono tabular numerics, and rebuild the Agent View as a live machine timeline. That agreement is the mandate.

## Spine: taste "Signal"
- Cool dark ink base + **ONE warm amber signal** accent (`#f5b544`) for brand, best-match, primary CTA, live-source badge.
- **Mono tabular numerics** everywhere (prices, sqft, km, step counters, timer, coords).
- One radius rule (10px surfaces, full pills for chips/badges). Flat app with exactly **one elevated element**: the Agent View panel (solid, not glass).
- Agent View = a **live machine timeline**: connective rail, mono step numbers, step-verb tags, latest step highlighted, status chip, promoted "Watch live in H Agent View" button.
- WhatsApp green (`#25d366`/`#34d39a`) kept as the single semantic exception on the contact CTA.
- No emoji/dingbats: replace 🏠 ● ◆ ✕ ↗ with typographic/SVG marks.

## Grafts from uiux "Night Dispatch"
1. **3-role accent** — add **cyan `#4fd8e8`** as the *agent-telemetry* role (Agent View live dot, timeline nodes, timer, session-id, "Watch live" button outline). So: amber = brand/best-match, cyan = live agent, green = contact/success. Distinct roles = real hierarchy.
2. **Agent View header** carries a LIVE·AGENT label + **elapsed timer** + **session-id chip**.
3. **Bigger mono price** on the best-match card (hero number).
4. **Collapsed "JOB" summary chips** for the searched criteria (city / dates / budget / people) — optional compaction.

## Reject
- uiux's simultaneous toast + popup + panel (too busy) — show the toast only on "booked".
- Glassmorphism (both critics flagged the current blur) — solid surfaces.

## Build note
Restyle in place (globals.css design system + targeted component markup: remove emoji, mono numerics, cyan-telemetry Agent View timeline). Keep ALL React logic + API wiring (page.tsx state machine, discover/contact routes) untouched — visual rebuild only, functionality transplanted unchanged.

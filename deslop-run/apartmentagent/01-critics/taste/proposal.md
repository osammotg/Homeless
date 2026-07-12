# Taste proposal — "Signal": a warm-amber operator console over a cold dark map

**Design read:** App/tool UI for a live AI-agent apartment concierge, dark and map-first, built as a cinematic-but-fast operator console. Language leans native CSS + system-ui/mono type + a single warm signal-amber accent over a restrained cool-ink base. The Agent View panel is the hero moment.

**Dials (app UI, not landing):**
- `DESIGN_VARIANCE: 4` — a fixed app shell; variance comes from ONE dominant element (best match / agent panel), not asymmetric layout play.
- `MOTION_INTENSITY: 5` — instant micro-interactions, a live beacon pulse, streaming-log entrances, a best-match beacon ring. Nothing blocking.
- `VISUAL_DENSITY: 6` — cockpit-leaning: tight, mono numerics, hairlines over boxes, but with air around the search moment.

**The one idea:** the map is cold and technical; the agent is warm and alive. A single **signal amber** owns everything the human should look at (best match, the live agent, the primary action). Everything else is neutral ink. Best match is the ONE beacon on a field of neutral pins.

---

## 1. Layout system

Keep the shell exactly: `display:flex; height:100vh; overflow:hidden`. Left rail + flex map. Do not make it scroll as a page.

- **Left rail: 400px**, `overflow-y:auto`, internal padding `20px 18px`, blocks separated by hairlines + a 4px-based rhythm (not a uniform gap).
  - Rail block order: **Brand strip → Search → Source status → Filters → Shortlist → All results.**
  - Group with `border-top: 1px solid --line` + a `20px` top pad between major blocks, NOT a flat gap. The search moment gets the most air; the results list gets the least.
- **Map: flex:1, position:relative.** The map is the canvas; overlays float on it:
  - Agent View panel, bottom-right.
  - A small mono coordinate/zoom readout, bottom-left (operator-console texture, real data: center lat/lng + zoom).
  - Toast, top-center.
- **Mobile (< 820px):** rail becomes a top sheet (55dvh map on top, rail below) OR a slide-over; declare it, don't rely on flex reflow. Agent panel goes full-width bottom, `left:12px; right:12px`.

---

## 2. Type scale (system fonts only — no fetches)

```
--sans: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
--mono: ui-monospace, "SF Mono", "JetBrains Mono", "Roboto Mono", Menlo, monospace;
```

Mono is a first-class citizen: **every number and machine-string is mono, tabular** (`font-variant-numeric: tabular-nums`) — prices, budgets, distances, sqft, step indices, status codes, coordinates, phone numbers. This single move creates the "console" voice.

| Role | Family / size / weight / tracking |
|---|---|
| Brand wordmark "Homeless" | sans 17px / 650 / -0.01em |
| Brand tag "APARTMENTAGENT" | mono 10px / 600 / 0.16em uppercase, muted |
| Section label (SHORTLIST, FILTERS) | mono 10.5px / 600 / 0.14em uppercase, `--text-3` — **used per block, but quiet** |
| Card title | sans 14px / 600 / -0.005em |
| Card meta | sans 12px / 500, `--text-2` |
| Price (card + pin) | mono 13px / 700 tabular |
| Input value | sans 14px / 500 |
| Input label | mono 10.5px / 600 / 0.1em uppercase, `--text-3` |
| Primary button | sans 13.5px / 650 |
| Agent step verb | mono 11px / 700 / 0.08em uppercase (amber) |
| Agent step body | sans 12.5px / 450, `--text` |
| Agent status chip | mono 10.5px / 700 / 0.08em uppercase |
| Toast | sans 14px / 600 |

No oversized headings anywhere — this is chrome, hierarchy is carried by weight + the amber accent + mono, never by raw scale or glow.

---

## 3. Palette — cool ink base, ONE warm accent

```css
/* Base — cool near-black ink (reads distinct from the CARTO map behind it) */
--bg:        #0a0d12;   /* app backdrop */
--surface:   #111620;   /* rail, panel */
--surface-2: #0d121a;   /* inset: inputs, cards */
--surface-3: #161d29;   /* hover / raised row */
--line:        rgba(255,255,255,0.07);
--line-strong: rgba(255,255,255,0.12);
--text:   #e7ecf3;      /* primary */
--text-2: #9aa7b8;      /* secondary */
--text-3: #64707f;      /* faint / labels */

/* THE accent — signal amber. One color, owns focus/best-match/live/primary. */
--accent:       #ffb627;
--accent-hi:    #ffc85a;   /* hover */
--accent-press: #e89b12;   /* active */
--accent-ink:   #17120a;   /* text on amber fill */
--accent-tint:  rgba(255,182,39,0.12);  /* wash behind live/best-match */
--accent-line:  rgba(255,182,39,0.42);

/* Semantic-only exceptions (used ONCE each, justified) */
--wa:     #25d366;  /* real WhatsApp brand green — ONLY on the WhatsApp CTA */
--wa-ink: #06180d;
--warn:   #d8a13a;  /* muted amber-brown for "cached / fallback" state (a desaturated accent, not a new hue) */
```

**Why amber:** the CARTO dark basemap is cold blue-grey/near-black. A warm sodium-amber pin reads as a beacon light against cold streets — maximum legibility, unmistakably NOT the emerald/cyan or AI-purple default, and it maps perfectly to the product metaphor (a light finding you a home). It clears WCAG AA on `--surface` for large/mono text; amber-on-ink fill (`--accent` bg + `--accent-ink` text) is high-contrast for buttons.

**Color Consistency Lock:** amber is the ONLY accent. Neutral pins, neutral cards, amber for the one best match, the live agent, focus rings, and the primary button. The single documented exception is the WhatsApp CTA (real brand green, because it names a real channel and appears exactly once). "Cached" state uses a desaturated amber (`--warn`), not a new color.

**No neon glow.** Emphasis = amber fill / amber hairline / amber tint wash + weight. The only "glow" permitted is the one soft best-match beacon ring on the map (a low-opacity amber pulse, motivated: it points the eye at the single best listing).

---

## 4. Spacing, radius, elevation

- **Spacing scale (4px base):** 4 / 8 / 12 / 16 / 20 / 24 / 32. Rail padding 20/18. Card inner 12. Agent-log row gap 10.
- **Radius (Shape Lock, one documented rule):** surfaces (cards, panels, inputs, buttons, thumbnails) = **10px**; pills/badges/pins/status-chips = **full (999px)**. Nothing else.
- **Elevation:** the app is flat — hairline borders do the separating, no card drop-shadows in the rail. Exactly ONE element is elevated: the **Agent View panel**, which gets a real shadow `0 24px 70px -28px rgba(0,0,0,.82)` + a 1px top inner highlight `inset 0 1px 0 rgba(255,255,255,.06)` and a **solid** dark surface (NOT backdrop-blur glass). Elevation means "this is the live layer above the map," and only one thing earns it.

---

## 5. Motion / micro-interactions

Global easing `cubic-bezier(.2,.8,.2,1)`, durations 120-200ms. All of the below collapse to static under `prefers-reduced-motion`.

- **Live beacon (agent + best-match pin):** a 2-ring amber pulse, 2.2s ease-in-out, opacity+scale on a `::after` ring. Motivated: signals "alive / look here." Reduced-motion: static amber dot.
- **Streaming log entry:** new step fades in + rises 8px over 160ms; the connective rail draws down 120ms. Motivated: feedback that the machine just acted.
- **Active scan bar:** a 2px indeterminate amber shimmer under the agent header while status is non-terminal. Motivated: shows work in progress. Hidden on terminal states.
- **Card hover:** border `--line → --line-strong`, translateY(-1px), 140ms. **Active:** translateY(1px).
- **Primary button:** hover brightens to `--accent-hi`; active translateY(1px) + `--accent-press`. Focus-visible: 2px amber ring offset.
- **Toast:** drop-in from -12px, 240ms; auto-dismiss.
- **Filter slider:** thumb scales 1.0→1.12 on drag.

No infinite decorative loops beyond the two beacons + the scan bar. Every animation names a reason (feedback / state / attention).

---

## 6. Component blueprint

**Brand strip:** amber beacon mark (8px dot + pulse ring) · "Homeless" wordmark · mono "APARTMENTAGENT" tag, right-aligned to a hairline underline. No glow dot.

**Search form:** mono uppercase micro-labels ABOVE inputs; inputs are `--surface-2`, 10px radius, 1px `--line`, focus → 1px `--accent-line` + 2px amber ring. Date/number inputs restyled to match (custom, not native chrome look). Primary button full-width amber, `--accent-ink` text: idle "Find me a place"; loading shows a 14px amber-ring spinner + "Agent is scouting Craigslist…".

**Source status:** a pill, dot + mono label. Live = amber dot (pulsing) + `LIVE · CRAIGSLIST (H AGENT)` on `--accent-tint`. Cached = `--warn` dot + `CACHED LISTINGS` muted. This replaces the `●`-in-string hack with a real dot element.

**Filters:** custom-styled range sliders (webkit + moz thumbs amber, track `--surface-2` with an amber fill left of thumb). Value read out in mono to the right of the label (`MAX PRICE  $3,200/mo`).

**Listing card (regular):** `--surface-2`, 10px, hairline. Left: 96×68 thumbnail (10px radius). Right: title (14/600) → mono price + neutral meta chips (beds · sqft) → muted line (neighborhood · `1.4 km` mono · from date). No glow. Differentiation from best match is structural, not color-bloom.

**Listing card (best match):** the ONE amber element in the rail. Amber hairline (`--accent-line`) + a 3px amber left spine + a faint `--accent-tint` wash top-strip carrying a mono `BEST MATCH · CONTACTABLE` tag (with a small inline-SVG diamond, not `◆`). Full-width **WhatsApp CTA** in `--wa` green with an inline WhatsApp SVG glyph: "Reach out on WhatsApp". This is the single justified non-amber affordance.

**All-results list:** compact rows, thumb 44×34 + ellipsized title + mono price, `divide` by hover-tint rather than a border per row. Capped-height scroll.

**Price pins (map):** full-pill, mono price. Neutral pin = `--surface` fill, `--line-strong` 1px border, `--text` price, a small 6px CSS pointer tail anchoring it to the coordinate, `0 6px 16px -6px #000` shadow for lift off the map. Best-match pin = amber fill, `--accent-ink` price, the beacon ring behind it. High contrast against CARTO dark; the single amber pin is unmistakable.

**Leaflet popup:** override the default white popup to the dark surface (`--surface`, `--line`, `--text`, mono amber price, dark WhatsApp/close). Fixes the light-mode break.

**Icons:** one tiny inline-SVG set at `stroke-width:1.6` — close (×), external-arrow, pin, whatsapp, diamond, search. Replaces every emoji/text-glyph.

---

## 7. The Agent View panel — the wow

Treat it as a **live machine terminal**, not a chat card. Bottom-right, 420px, solid `--surface` (no glass), the one elevated element, 10px radius.

**Header:** left — amber beacon (pulse ring) + "AGENT" (sans 13/600) + a mono state chip that changes per phase: `BROWSING CRAIGSLIST` / `NEGOTIATING · WHATSAPP`. Right — inline-SVG close. Directly under the header: the **active scan bar** (2px amber indeterminate shimmer) while running; it vanishes on `completed/failed`.

**Body — the timeline (the centerpiece):** a vertical connective rail runs down the left. Each event is a row:
- mono step index `02` in a small circular node on the rail;
- an amber mono **verb** tag (`SCAN` / `OPEN` / `READ` / `DRAFT` / `SEND` / `WAIT` / `REPLY`) derived from the event;
- a sans description line (the real event text).
- The **latest** step is emphasized: amber node fill, `--accent-tint` row wash, and it's what auto-scroll lands on. Earlier steps recede to `--text-2`. This gives a real sense of a machine progressing, not a flat log.
- Empty state: a single mono "Starting session…" node with a spinning amber ring.

**Footer:** left — a stateful status chip (mono): running = amber-tint `● NEGOTIATING`, completed = neutral `✓ DONE`, failed = `--warn`. Then "Watch live in H Agent View" as an amber link with an inline external-arrow SVG. Right — optional action button ("Owner replied") as a neutral ghost with amber hover.

**Why it wins:** mono step verbs + a drawn rail + a latest-step highlight + a live scan bar read like watching an autonomous operator work in real time. It's warm (amber) against the cold map, it's the only elevated surface, and it uses motion only where motion means "the agent just did something."

---

## 8. Per-state blueprint

- **Idle:** rail = brand + search + a quiet empty hint ("Enter a search and the agent scouts Craigslist live."). Map = dark, centered on the city, no pins, faint mono coordinate readout. No agent panel. Calm; the search button is the one amber thing.
- **Discovering:** search button → loading spinner. Agent panel appears bottom-right in `BROWSING CRAIGSLIST` state, scan bar active, steps streaming (SCAN/OPEN/READ). Pins begin dropping onto the map as listings resolve. Source status pill flips to LIVE.
- **Results:** rail fills — source pill, filters, shortlist (best match first, amber), all-results. Map shows neutral price pins + the one amber best-match beacon, fit-bounds. Agent panel can be dismissed or minimized.
- **Agent-view active (contacting/negotiation — the money shot):** best-match WhatsApp CTA pressed → panel switches to `NEGOTIATING · WHATSAPP`, scan bar active, timeline streams the negotiation (DRAFT → SEND → WAIT → READ owner reply → REPLY proposing a viewing). On success → footer chip `✓ DONE` and the top-center toast: "Found you a place. Owner: …" (real owner name, inline home SVG, amber, no gradient).

---

## Pre-flight (self-audit)
Zero em-dashes. One accent (amber) + one documented WhatsApp-green exception. One radius rule (10px surfaces / full pills). Theme locked dark including the Leaflet popup. No neon glow (one motivated beacon only). No emoji — inline-SVG icon set. Mono numerics throughout. Motion all motivated + reduced-motion safe. Every functional item from the parity inventory preserved (search inputs, loading, source badge, both sliders, shortlist + best-match CTA, all-results, map pins/popups/fit-bounds, agent panel with live indicator/streamed steps/status/watch-link/action/close, toast, phase machine).

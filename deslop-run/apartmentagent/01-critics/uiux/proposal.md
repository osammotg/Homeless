# Proposal — "Night Dispatch": a cinematic operator console for a live apartment agent

**Concept.** The screen is a *dispatch console*. You (the operator) hand a job to an autonomous field agent; it goes out into the city — visualized as a live dark map — and reports back through a **telemetry terminal**. The emotional hook of a homelessness→home product is literal light: a warm **signal amber** is the brand's "a light left on for you," reserved for the things that matter (the best match, the found-a-home moment). Cool **cyan** is the machine's live nervous system (agent activity, streaming steps). Green stays strictly for *contact/success* (WhatsApp, "live source"). This 3-role discipline is what the current all-emerald design lacks.

Grounded in the UI/UX Pro Max skill: pattern = **Real-Time / Operations** (dark, status colors, data-dense but scannable); type pairing = **"Modern Dark Cinema" (Sans + Mono)** — humanist system-sans for content, system-mono/tabular for all data; base surfaces follow the **dark financial-dashboard** palette (near-black blue, layered cards). No web fonts (system stack), no external assets — CSS-drawn map/thumbnails.

---

## 1. Layout system
Keep the fixed two-pane shell (it works). Refine the proportions and internal rhythm.

- **App:** `display:flex; height:100dvh; overflow:hidden`. No page scroll.
- **Left rail — 380px** (was 400; give the map more canvas), own scroll, `overflow-y:auto`, `scrollbar-gutter:stable`. Internal structure as **stacked console modules** separated by a hairline + generous section gap, each with a 11px uppercase overline header, so the eye reads: `BRAND → JOB (search) → SOURCE → FILTERS → SHORTLIST → ALL RESULTS`.
- **Main — flex map** as the canvas, edge-to-edge, no border between it and rail except a 1px seam.
- **Agent View** — floating bottom-right, **440px**, `max-height: min(64vh, 620px)`, its own internal scroll on the event log only. It visually "docks" to the map with a 1px cyan top-seam so it reads as instrumentation, not a modal.
- **Toast** — top-center, docked under a thin top status line.
- **Responsive:** ≤980px → rail collapses to a top sheet / the map goes full-bleed with the search as a floating command bar; Agent View becomes a bottom sheet full-width. (Demo is desktop-wide; design desktop-first but don't break.)

**Anti-slop guardrails:** no uniform 3-col card grid; radii are *tiered* not universal (see §5); no glass-by-default (blur used only on the floating panel/toast where it means "above the map"); no gradient blobs (one functional amber glow on the found-home toast only).

---

## 2. Type scale (system fonts)
```
--font-sans: -apple-system, "SF Pro Text", system-ui, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
--font-mono: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, "Cascadia Code", monospace;
```
Every **price, distance, step index, timer, coordinate** → `--font-mono` + `font-variant-numeric: tabular-nums`. Content/labels → sans.

| Token | px / line-height / weight | Use |
|---|---|---|
| `overline` | 11 / 1.2 / 600, **UPPERCASE, tracking .14em** | module headers, field labels, badges |
| `meta` | 12 / 1.4 / 450 | card sub-facts, muted |
| `body-s` | 13 / 1.5 / 450 | event log text, all-results rows |
| `body` | 14 / 1.5 / 450 | inputs, default |
| `label-m` | 14 / 1.2 / 600 | card title, buttons |
| `price` | **20 / 1.1 / 700 mono** | shortlist card price (the hero number) |
| `price-lg` | 26 / 1.05 / 700 mono | best-match price |
| `brand` | 17 / 1.1 / 700, tracking -.01em | "Homeless" wordmark |
| `num-xl` | 30 / 1.0 / 700 mono | toast / big moments |

Type ramp is a clean set (11·12·13·14·17·20·26·30) — no fractional off-grid sizes.

---

## 3. Dark palette + accent (all legible over CARTO dark tiles ≈ #17202b)
```
/* surfaces — layered near-black blue */
--bg:        #080B10;   /* app base / map void behind tiles */
--surface-1: #0D131B;   /* left rail */
--surface-2: #121A24;   /* cards, inputs, all-results */
--surface-3: #17222F;   /* hover / raised / agent panel body */
--hairline:  rgba(255,255,255,.06);   /* default 1px borders */
--line:      #223243;   /* stronger dividers / input borders */

/* text */
--text:      #EAF0F7;   /* primary  (>= 13:1 on surfaces) */
--muted:     #8A98A9;   /* secondary (>= 4.6:1) */
--faint:     #5C6B7C;   /* tertiary / disabled */

/* ROLE ACCENTS — 3 meanings, never mixed */
--signal:    #F4B24C;   /* AMBER  · brand, best-match, attention, "home" */
--signal-ink:#0A0E13;   /* text on amber */
--signal-dim:#7A5A2A;   /* amber hairline/glow base */
--live:      #4FD8E8;   /* CYAN   · live agent telemetry, streaming, pulse */
--go:        #34D39A;   /* GREEN  · contact/WhatsApp, live-source, success */
--danger:    #F26869;   /* RED    · failed/timed-out status */
```
- **Contrast:** text 13:1, muted 4.6:1, amber-on-dark ~9:1, cyan-on-dark ~8:1 — all pass AA. On amber fills, use `--signal-ink` (dark) for AAA legibility.
- **Why amber, not the "AI purple" or generic emerald:** it's warm (on-brand for "home"), rare in dev-tool dark themes (distinctive), and maximally legible as a solid pin over blue-grey map tiles. Cyan is kept exclusively for machine/live states so the two never blur — the mistake the current single-green makes.
- **Semantic status tokens:** live-source badge = `--go`; cached/fallback = `--faint` neutral (not amber — amber is brand, not a warning); agent status `running`=cyan, `completed`=green, `failed/timed_out`=red, `pending`=muted.

---

## 4. Spacing scale
4-pt rhythm: `4 · 8 · 12 · 16 · 20 · 24 · 32 · 48`. Tiers:
- Intra-component (icon↔label, meta gaps): **8**.
- Card padding: **14**. Input padding: **12 / 14** (→ 44px tall targets).
- Between modules in the rail: **24**, with a hairline divider at the midpoint of the gap.
- Rail outer padding: **20**.
- Section overline → content: **12**.

---

## 5. Elevation & radius (tiered, not uniform)
| Level | Use | Spec |
|---|---|---|
| e0 | rail, inputs | flat, `1px --hairline`, no shadow |
| e1 | cards, all-results | `--surface-2`, `1px --hairline`, inset top highlight `inset 0 1px 0 rgba(255,255,255,.03)` |
| e1-best | best-match card | `--surface-2` + **3px left amber bar**, `1px` amber-dim border, faint `0 0 0 1px rgba(244,178,76,.12)` — an *edge accent*, not a full glow ring |
| e2 | pins, hover | chip + `0 2px 8px rgba(0,0,0,.5)` |
| e3 | Agent View, popups | `--surface-3` @ .97 + `backdrop-blur(14px)` + `0 24px 70px -28px #000` + 1px cyan top seam |
| e4 | found-home toast | amber-tinted surface + soft amber glow `0 10px 40px -10px rgba(244,178,76,.45)` |

**Radius:** chips/pins `999px` (only truly pill things), inputs/buttons `9px`, cards `12px`, floating panel `16px`, thumbnails `8px`. Not everything is a pill.

---

## 6. Iconography (replace ALL emoji/dingbats)
One 1.5px-stroke line set, drawn as inline SVG, currentColor-tinted: search, map-pin, sliders, home/roof, whatsapp-glyph, external-link (↗→drawn arrow), close (×→drawn), diamond (best-match→drawn). Icon sizes tokenized 14/16/18. No 🏠/●/◆/✕/↗ as text.

---

## 7. Motion (fast, meaningful, reduced-motion-safe)
- Tokens: enter `180ms cubic-bezier(.2,.7,.2,1)`, exit `120ms ease-in` (exit < enter), hover `140ms`.
- **Agent event stream (the signature):** each new event enters with `translateY(6px)+opacity 0→1` over 180ms; the *current* step shows a blinking cyan caret; a thin cyan "scan" gradient sweeps the panel header on each new event (200ms). Stagger not needed (they arrive live) but the entrance is what sells "alive."
- Live dot: 1.4s opacity pulse + a soft expanding ring.
- Buttons: press `translateY(1px)`, no layout shift; WhatsApp CTA gets a 1px→2px inset-glow on hover.
- Best pin: slow 2.4s amber breathing glow (subtle), so the eye finds it without it screaming.
- Toast: drop-in 320ms spring, amber glow fades up.
- **All wrapped in `@media (prefers-reduced-motion: reduce)`** → pulses/sweeps become static, entrances become instant opacity.

---

## 8. Per-state blueprints

### IDLE
Rail: brand lockup (amber roof glyph + "Homeless" wordmark, "ApartmentAgent" as a mono kicker underneath). Search module fully visible, primary CTA "**Find me a place**" (amber, dark ink). Below: an *empty-state instrument* — a faint cyan dashed "no signal" line + copy "Agent standing by. Enter a job and it scouts Craigslist live." Map is full, dimmed, with a slow-drifting faint grid and the city center marked by a soft ring (no pins yet). No Agent View panel.

### DISCOVERING
CTA → spinner + "Agent is searching Craigslist…". **Agent View docks in** (slide from bottom-right, 180ms) titled "AGENT · scouting Craigslist" with cyan LIVE strip + elapsed timer, streaming mono steps with the timeline rail. Map begins dropping pins as results arrive (each pin scales-in). Source badge appears once resolved.

### RESULTS (the screen we build in preview.html)
Rail shows: brand · search (collapsed summary chip row: `San Francisco · Jul 12–Aug 12 · $2,800 · 2 ppl`, editable) · **live source badge** (green) · Filters (two labeled sliders with a filled cyan track + value chip) · **Shortlist** (overline `SHORTLIST · 4 of 11 fits`): the **best-match card** first (amber left bar, `BEST MATCH · CONTACTABLE` amber overline w/ diamond, big mono price, roof/beds/sqft row, neighborhood·distance·from-date row, full-width green **WhatsApp** button with drawn glyph), then 3 standard cards (price is the hero number, thumbnail as CSS gradient placeholder, tidy 2-row meta) · **All results** compact rows (thumb · title · mono price), no nested scrollbar — flows in the rail scroll.
Map: dark, price-pins (dark chip + hairline), best pin = amber solid with pointer tail + breathing glow, others neutral; a subtle "you are here" center ring; fit-bounds. Popups are **dark** (surface-3, mono price, drawn CTA) — never white.

### CONTACTING / REPLIED (Agent View as negotiator — shown open in preview)
Agent View retitled "AGENT · contacting owner" / subtitle `WhatsApp · <listing>`. Status chip cyan `negotiating`. Event log streams the WhatsApp exchange as agent steps; a mini "sent/received" indent distinguishes owner replies (green left tick) from agent actions (cyan). Footer: **status chip · "Watch live in H Agent View ↗"** promoted to a real bordered button (cyan outline, the demo money-CTA) · optional "Owner replied" ghost action. On reply → status→green `booked`, **toast** drops top-center: amber-glow pill "Found you a place — owner: '…'". 

---

## 9. The Agent View, detailed (the "wow")
This is the piece that must look like mission control, not a log box:
- **Header status strip:** left = cyan pulsing dot + ring, `LIVE` in mono, then title; right = mono **elapsed timer** `00:42` + drawn close ×. A 1px cyan gradient underline sweeps on new events.
- **Session identity line:** subtitle in muted + a mono `session · a3f9…` id chip → feels like a real agent session, reinforces the H-Company integration.
- **Event log = a timeline terminal:** a 1px vertical rail down the left; each event = a small node (cyan filled = agent action, green ring = owner/external reply, amber = milestone like "found 11 listings"), a mono zero-padded step index, then the text (body-s). The **latest** event has a blinking cyan caret and slightly brighter text; older events dim to muted — so the live edge is obvious.
- **Footer:** status chip (semantic color) · the **"Watch live in H Agent View ↗"** as a cyan-outline button (not a tiny link) · spacer · action ghost button. This promotes the single most demo-relevant control from footnote to first-class.
- **Texture:** a barely-there 2px scanline overlay + a faint cyan top glow so it reads as an instrument screen. `aria-live="polite"` on the log for accessibility (fixes the current SR gap).

---

## 10. Accessibility & parity
- Visible focus: `outline: 2px solid --live; outline-offset: 2px` on every interactive element (fixes color-only focus).
- Inputs ≥44px tall; custom-styled dark date/number so system controls don't render light; slider tracks visible in dark with value echoed in a chip.
- Status never color-only — pair color with text/glyph (badges carry a word + a dot).
- All emoji/dingbats → drawn SVG with `aria-label`.
- **Parity preserved 1:1** — component prop APIs, `page.tsx` state machine (idle→discovering→results→contacting→replied), API wiring, filters, shortlist scoring, fit-bounds, auto-scroll, toast trigger all unchanged; this is a restyle of markup/classes + `globals.css` only, exactly as the brief mandates.

The single representative screen (RESULTS + Agent View negotiating) is built to final quality in `preview.html`.

# Critique — current ApartmentAgent UI (UI/UX Pro Max lens)

Note: the supplied screenshots (`00-current/idle.png`, `idle-wide.png`) render a Next.js **Server Error** page, not the app, so this critique is against the *pixels the CSS/markup produce* — read from `app/globals.css` and `components/*.tsx`. Everything below cites the concrete rule + line.

The bones are right: a fixed two-pane, dark, map-first shell with a floating agent log. The problem is that nothing is **crafted** — it reads as a competent default dark theme, not a "cinematic operator console for a live AI agent." The one element that is supposed to be the wow (Agent View) is the least designed thing on the screen.

---

## What already works — KEEP

1. **The shell architecture.** `.app { display:flex; height:100vh; overflow:hidden }` with a fixed 400px `.sidebar` (own scroll) + `flex:1` map (`globals.css:26–47`). Correct app skeleton; no page scroll, map owns the canvas. Keep verbatim.
2. **Map-first commitment.** Leaflet fills the main pane, dark CARTO tiles, `background:#0b0f14` under the tiles so there's no white flash (`globals.css:48`). Right instinct.
3. **Price-bubble divIcon pins with a highlighted best match** (`ListingMap.tsx:9–16`, `.price-pin` / `.price-pin.perfect` `globals.css:186–197`). This is the product's signature; keep the *concept*, upgrade the *skin*.
4. **Tabular numerics already used** on the agent step counter (`font-variant-numeric: tabular-nums`, `globals.css:153`). Good data-UI instinct — extend it to every price.
5. **Auto-scroll + pulsing live dot** in the agent log (`AgentViewPanel.tsx:26–28`, `.pulse` keyframes `globals.css:149–150`). The mechanics of "live" are present.
6. **Semantic source badge** (live=accent, fallback=warn) driven by state (`page.tsx:217–223`, `.badge.live/.fallback`). Keep the semantics.
7. **Uppercase micro-labels** on fields/sections (`globals.css:52, 98`). A real typographic system starts here — keep the device, tighten the scale.
8. **Restrained button motion** — `active { translateY(1px) }`, filter-brightness hover, no layout shift (`globals.css:75–78`). On-spec micro-interaction; preserve.

---

## Faults — evidenced, element by element

### A. Color & brand identity — generic, undifferentiated
- **Emerald `#34d399` is the entire identity.** Accent, price text, brand dot, best-match, primary button, live badge, toast gradient, WhatsApp CTA and pins are *all* the same green (`globals.css:8, 43, 108, 111, 66, 94, 164, 197`). There is no hierarchy left — when everything is the "wow" color, nothing is. This is exactly the "generic SaaS dark theme" the brief warns against.
- **`--accent-2:#22d3ee` (cyan) is defined but barely used** (`:9`) — only the agent pulse and the H-link. The one place a distinct "live telemetry" color would create meaning is under-committed.
- **Toast uses a `linear-gradient(135deg, accent, accent-2)` pill** (`globals.css:164`) — the emerald→cyan gradient blob + full-pill is squarely on the slop list (gradient + pill-everything).
- No warm tone anywhere. A homelessness→home concierge has an obvious emotional lever ("a light on for you") that the palette ignores.

### B. The Agent View panel — the intended wow, currently a plain log box
- It's a `rgba(10,14,20,.96)` rounded rect with `backdrop-filter: blur(8px)` (`globals.css:131–146`) — **glassmorphism-by-default**, the exact anti-pattern called out.
- Events are just left-border lines: `.event { border-left:2px solid var(--border) }` (`:152`). No timeline connectivity, no "current step" emphasis, no elapsed time, no cause→effect motion. It looks like a validation error list, not a live agent "browsing Craigslist / negotiating on WhatsApp."
- Header is title + a bare `✕` **emoji/glyph** button (`AgentViewPanel.tsx:41`). Close affordance is an unstyled ghost button; no status strip, no session identity.
- The `"Watch live in H Agent View ↗"` link — the single most demo-relevant CTA — is a **12px plain text link** wedged in the footer between a badge and a spacer (`AgentViewPanel.tsx:56–60`, `globals.css:155`). The literal money shot for an H-Company demo is styled as an afterthought.
- Status is a neutral grey `.badge` showing raw machine strings like `pending` / `timed_out` (`AgentViewPanel.tsx:55`) — no color semantics, no humanized copy.
- New events just appear (`endRef.scrollIntoView`) with **no entrance motion** — violates `motion-meaning` / `stagger-sequence`. A live stream should feel alive.

### C. Emoji used as UI (Style Selection §4, `no-emoji-icons`)
- Toast is literally `🏠 {message}` (`Toast.tsx:6`); source badge copy carries a `●` char (`page.tsx:220`); close is `✕`; best-match tag is `◆` (`ListingCard.tsx:25`). Emoji/dingbats as structural icons are font-dependent and untokenizable — the brief lists this explicitly.

### D. Listing cards — flat, weak hierarchy, uneven data
- **Price is the same 12px as the neighborhood and distance** — `.card .price` sits inside `.meta` at `font-size:12px` (`globals.css:110–111`). The single most important number on a rental card has no size advantage; it's only differentiated by color (which is the same green as everything). Fails `visual-hierarchy` (hierarchy by size/weight, not color alone).
- **Best-match card = a full green glow ring**: `box-shadow: 0 0 0 1px …, 0 0 24px -8px perfect` (`globals.css:108`). A glowing rounded rectangle is decorative, not informative; it competes with the map's best pin for the same green glow.
- Thumbnail is a fixed `96×68` raster with `object-fit:cover` (`globals.css:114`); no aspect-ratio reservation beyond fixed px, and no skeleton — `image-dimension` / `loading-chart`-style placeholder missing, so cards pop-in as images load (CLS).
- `.card .meta` dumps 3–4 facts as `· ` separated inline spans (`ListingCard.tsx:40–44`) — no rhythm, no alignment, price/beds/sqft and neighborhood/distance/date read as one grey blur.

### E. Typography — no real scale, weak numerics
- Font sizes are scattered and off-grid: 22, 14, 13, 12.5, 12, 11, 10, plus `12.5px`/`13px` fractional values (`globals.css:42, 109, 123, 152, 93, 112`). There's no coherent step scale (`font-scale`).
- Prices are set in the **UI sans**, not a monospaced/tabular face, so columns of `$2450` / `$2800` don't align — a data product should use tabular figures everywhere (`number-tabular`). Only the step counter opts in.
- Brand lockup `Homeless · ApartmentAgent` is `<h1>22px</h1>` + a grey `<small>` on one line (`page.tsx:209–213`) — no considered lockup, the product name and sub-brand fight at similar weight.

### F. Forms & inputs — default, low-contrast, thin targets
- Inputs are `padding:10px 12px` → ~38px tall (`globals.css:57`), under the 44px comfortable target; the native `<input type="date">` and `type="number"` are unstyled system controls in a dark theme (spinners/date picker will render light) — no `system-controls`/dark-mode consideration.
- Focus is communicated **only** by `border-color: var(--accent)` (`globals.css:62`) — no visible focus ring / offset. Fails `focus-states` (2–4px visible ring) and `color-not-only`.
- Range sliders rely solely on `accent-color` (`globals.css:128`); default track is nearly invisible on the dark panel, and the value only lives in the label text.

### G. Map popups — a jarring light-mode island in a dark app
- Popup content is hardcoded **light**: `color:#111`, `#0a7`, `#666`, white Leaflet default bubble (`ListingMap.tsx:56–83`). Clicking a pin in a cinematic dark console pops a bright white card — breaks `dark-mode-pairing` and the whole mood. Inline hex everywhere (`color-semantic` violation).

### H. Spacing & elevation — one note, repeated
- Sidebar is a flat `gap:18px` column (`globals.css:39`) with essentially one elevation level (panel vs panel-2) and one shadow used once (agent panel). No `section-spacing-hierarchy` (16/24/32 tiers), so brand, search, filters, shortlist and all-results all sit at the same rhythm — the eye can't find the structure. Everything is `border-radius: 8–12`, uniformly rounded.
- `.rows` "All results" caps at `max-height:260px` inside an already-scrolling sidebar (`globals.css:119`) — a **nested scroll region** inside the panel scroll (`scroll-behavior` anti-pattern), and the inner list has no header sticky/affordance.

### I. Accessibility gaps
- No visible focus rings (see F). Icon-only `✕` close has no `aria-label` (`AgentViewPanel.tsx:39`). Status conveyed by color-only on badges. Live event stream has no `aria-live` region, so screen readers never hear the agent's progress — for a product whose entire pitch is "watch it work live," that's a meaningful miss.

---

## Verdict
Keep the **two-pane map-first shell, the pin concept, the source-badge semantics, and the restrained button motion.** Rebuild the **identity (stop making everything one green), the Agent View (make it a real live dispatch terminal — the wow), card hierarchy (price must dominate, kill the glow ring), the type scale (add tabular numerics), inputs/focus, and dark popups.** Replace every emoji/dingbat with a drawn SVG glyph. The redesign direction is in `proposal.md`.

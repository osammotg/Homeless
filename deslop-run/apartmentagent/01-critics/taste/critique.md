# Taste critique — Homeless / ApartmentAgent (current design)

**Design read:** App/tool UI for a live AI-agent apartment concierge. Dark, map-first operator console. The design must SERVE the product; the Agent View panel is the intended "wow". Judged as an operator console, not a landing page.

> Note on evidence: the supplied screenshots (`idle.png`, `idle-wide.png`) both show a Next.js server error, not the running UI. So this critique reconstructs the actual pixels from the exact values in `app/globals.css` and the component markup. Every fault below cites a real line/value.

---

## What's already right (KEEP THIS)

1. **The shell is correct.** Fixed full-height two-pane app: 400px left rail + flex map (`.app { display:flex; height:100vh; overflow:hidden }`, `.sidebar { width:400px }`). This is the right IA for a map-first tool. Do not turn it into a scrolling page.
2. **Map-first, CARTO dark tiles** (`dark_all` in `ListingMap.tsx`). The concept of the dark basemap as the主 canvas is the product's spine. Keep it.
3. **Price-bubble `divIcon` pins** with a highlighted best match. The pin-as-price idea is genuinely good product design; it just needs restyling, not replacing.
4. **The floating Agent View panel, bottom-right, reused for discovery AND negotiation.** Correct placement and correct reuse. The panel just isn't dressed for the "wow" it's supposed to deliver.
5. **Source badge (live vs cached), reactive filters, best-match CTA, phase state machine.** All the right affordances exist. This is a restyle, not a re-architecture.

---

## Element-level faults

### 1. Two accents fighting + neon glow everywhere (the biggest tell)
- `--accent: #34d399` (emerald) AND `--accent-2: #22d3ee` (cyan) are both live accents. Emerald-plus-cyan-on-dark is the exact "AI default" palette the brief says to avoid. There is no single owned color.
- Glow is sprayed on five different elements: brand dot `box-shadow: 0 0 12px var(--accent)` (L43), perfect card `0 0 24px -8px var(--perfect)` (L108), perfect pin `0 0 16px -2px` (L197), toast `0 12px 40px -8px var(--accent)` (L170), plus the focus states. Outer neon glow as a default is a hard anti-slop tell. Everything "important" just gets a green bloom, so nothing actually reads as more important than anything else.

### 2. Emoji-as-icons throughout (brief explicitly bans this)
- Toast: `🏠 {message}` (`Toast.tsx` L6).
- Source badge: literal `●` characters baked into the string (`page.tsx` L221-222).
- Best-match tag: `◆ best match · contactable` (`ListingCard.tsx` L25).
- Close button: `✕` (`AgentViewPanel.tsx` L41).
- External link: `↗` (L59).
These are text glyphs standing in for an icon system. On a console that wants to feel engineered, they read as improvised.

### 3. The Agent View panel is under-designed for its job
This is supposed to be the showpiece; right now it's a generic frosted card:
- **Glassmorphism-by-default:** `background: rgba(10,14,20,0.96); backdrop-filter: blur(8px)` (L136-138). The brief names glass-by-default as slop. It also adds nothing here (the panel sits over a near-black map).
- **The live feed is tiny and flat:** events are `12.5px` with a `2px solid var(--border)` grey left border (L152). Every step looks identical; the latest event has no emphasis. There is zero sense of a machine actively working, no progress/scan indication, no state-per-step.
- **The "live" signal is one 8px cyan dot** doing an opacity blink (`.pulse`, L149-150). For the intended wow this is the whole show, and it's a blinking dot.
- **Status is a plain grey pill** (`<span className="badge">{statusLabel}</span>`) that reads a raw enum ("pending", "running"). No visual state language.

### 4. Typography has no hierarchy and no console voice
- Single system sans stack for everything (`globals.css` L22). Nearly the entire UI lives at 12-14px: brand `22px` (L42), card title `14px`, meta `12px`, events `12.5px`. The brand wordmark barely outsizes the body.
- **No monospace anywhere.** A live-agent console with prices, distances, budgets, step numbers, coordinates and status codes is begging for tabular mono numerics. Their absence is why it reads "generic web form" instead of "operator console".
- Uppercase muted micro-labels repeat on every block: form labels `text-transform:uppercase; letter-spacing:0.04em` (L52), `.section-title` same (L98), `.perfect-tag` same (L112). The identical small-caps rhythm above every group is templated.

### 5. Cards are the uniform-rounded-box slop
- `.card` = `border-radius:10px` + `1px border` + `12px padding`, stacked identically (`page.tsx` L231-241). The best match differs from the rest ONLY by a green glow ring (`.card.perfect`, L108). Hierarchy is carried entirely by color bloom, not by layout, weight, or structure. Four identical bordered boxes in a column is the "uniform rounded cards" pattern the brief calls out.

### 6. Price pins read poorly on the map
- `.price-pin` uses `background: var(--panel)` (#121821) with a `1px var(--border)` outline (L186-196). A dark-grey pill on a dark-grey CARTO basemap is low-contrast and hard to scan; the whole point of price pins is instant legibility.
- No pointer/tail, so a pill floats with no clear anchor to its coordinate.
- The best-match pin is differentiated only by the same green glow bloom as everything else.

### 7. Controls are raw and inconsistent
- Filters are unstyled native `input[type=range]` with `accent-color:var(--accent)` (L128). The thumb/track render differently per browser and look nothing like the rest of the surface. On a "crafted console" these are the first thing that betrays it.
- The date and number inputs are default-chrome; the number spinners and native date picker clash with the dark surface.
- The close control is a bordered `.ghost` button wrapping an `✕` (L39-41) — heavy chrome for a dismiss.

### 8. Toast is gradient slop
- `background: linear-gradient(135deg, var(--accent), var(--accent-2))` (L164) plus a glowing shadow and a house emoji. A green-to-cyan gradient pill is exactly the decorative-gradient tell to avoid, and it introduces a THIRD color relationship (emerald→cyan) that appears nowhere else.

### 9. Map popup breaks the theme
- The Leaflet popup renders default white with `color:#111` text and a `#0a7` price (`ListingMap.tsx` L56-84). Clicking a pin drops you into a light-mode card mid-app. The dark theme lock is violated the moment a user interacts with the map.

### 10. Spacing is uniform, not rhythmic
- Sidebar is a flat `gap:18px` stack with `20px` padding (L37-39). Every block has the same air. There's no grouping, no dominant element, no console density where it would help (the agent log) versus breathing room where it would help (the search moment).

---

## Priorities for the redesign
1. Kill the second accent and all the neon glow. One owned color, legible over a cold dark map, expressed through fill/weight/tint rather than bloom.
2. Rebuild the Agent View as a real live-machine timeline (mono step verbs, connective rail, latest-step emphasis, an active scan indicator, a stateful status chip). This is the demo.
3. Introduce a mono numeric voice for prices/distances/steps/status; give the type an actual scale.
4. Replace emoji glyphs with a tiny consistent inline-SVG icon set.
5. Restyle price pins for high contrast with an anchored tail; best match = the one amber beacon, not another green blob.
6. Style the sliders/inputs/close control to the surface. Fix the light-mode Leaflet popup.

# WOW-FACTOR — ApartmentAgent (H Company Computer Use Hackathon)

**Angle:** what makes a judge audibly react, and cheap, reliable ways to amplify it before tomorrow.

---

## The wow moments you already have (rank them, lean into them)

1. **A desktop agent that physically types and sends a real WhatsApp negotiation — and reads the reply off the screen to haggle back.**
   This is the un-fakeable money shot. `contact-svc/main.py` drives the *real* WhatsApp desktop app (`open_whatsapp_chat` deep-link → H desktop session → `_force_send()` presses Return), then runs a **fresh session per owner turn** that reads the whole thread on screen and replies per `_negotiation_policy` (asks for a discount, respects a budget cap, books a viewing). Judges are used to chatbots printing text; watching software move a cursor in a real Mac app and hit send is a different category. This is the single biggest "whoa."

2. **TWO computer-use surfaces in one product.** A *cloud browser* scouts Craigslist (`lib/discovery.ts`, `h/web-surfer-flash`, real `/sessions` + `/changes` streaming) AND a *local desktop* agent operates WhatsApp (`contact-svc`). Almost every other team will show one surface. Two, wired into one flow, is a rare technical flex — say the words "two computer-use agents" out loud.

3. **The whole errand starts from a phone DM.** `concierge/main.py`: you text a Telegram bot in plain English, and software goes and drives a browser *and* your desktop to run a real-world errand end-to-end. The "I just texted it and it did my apartment hunt" framing is the emotional hook.

4. **The map filling with priced pins + the glowing amber "best match."** `results.png` already looks premium: dark Carto map, cyan pins with `$` price labels, one amber pin, a "BEST MATCH · CONTACTABLE" card with the green WhatsApp CTA. Strong visual baseline.

**The core problem to fix:** moments #1 and #2 are the strongest but are currently the *least visible* on stage. The desktop negotiation happens in a window that isn't framed, and the live browser Agent View is only a **text link** ("Watch live in H Agent View", `AgentViewPanel.tsx:82`), not something judges see. Almost every proposal below is about making the un-fakeable stuff impossible to miss — without touching the reliability-critical H session logic.

---

## Proposals (cheap, reliable, implementable before tomorrow)

### 1. Embed the live H Agent View inside the app, next to the streaming timeline — feature/spectacle · S/M · impact 5
`AgentViewPanel` already receives `agentViewUrl` but only renders a link (`AgentViewPanel.tsx:82-86`). Add an `<iframe src={agentViewUrl}>` pane beside the cyan step timeline so judges watch the **real browser being driven live inside your own UI**. Reliability guard: platform.hcompany.ai may send `X-Frame-Options`, so keep the existing "Watch live" link as a guaranteed fallback and hide the iframe on `onError`/load-timeout. Never blocks the demo; when it works, it's a huge upgrade.

### 2. "Desktop Cam": frame the real WhatsApp window during negotiation — feature/spectacle · S · impact 5
The desktop agent already brings WhatsApp to the front (`_opening_task`, `_force_send` via `osascript ... activate`). Make that the hero: a `/demo` presenter layout (or an OBS scene) that mirrors the actual WhatsApp desktop window on the projector while the agent types + sends. Add a slim in-app overlay ("H desktop agent is operating WhatsApp →") so the audience knows to look at the real app. Mostly staging; the un-fakeable cursor-typing moment becomes the centerpiece. Zero change to the H session code.

### 3. Full-screen "THE AGENT IS NEGOTIATING FOR YOU" state with real chat bubbles — ux/demo · M · impact 4
Today the contacting state is a small side panel; the owner↔agent turns already come through tagged (`classify()` handles `owner:`/`agent:`; `contact-svc` emits `Owner:`/`Agent:` events). Promote it to a projector-readable hero overlay that renders those turns as **green/gray WhatsApp-style bubbles inside a phone frame**, with a big "Negotiating…" headline and the live timer. Makes "it's really having a conversation" legible from the back of the room.

### 4. Sound + confetti cues on send and on "Booked!" — ux/demo · S · impact 4
No audio today (the `Toast` on reply is silent, `page.tsx:295`). Add a Web Audio "send" blip when the agent fires a message and a triumphant chime + a confetti burst when `phase === "replied"` / `booked`. No assets needed (Web Audio API + CSS/canvas confetti). Sound cues are literally what make a room go "whoa" at the climax.

### 5. "Saved you $X" negotiation-win callout — feature/spectacle · S · impact 5
The data is already there: listing `price` and the agent's `agreed_price` / `viewing_time` flow back through `_apply_turn_result` and into the concierge's "✅ Booked!" message. On booking, show a big "Negotiated $2450 → $2300 · saved $150/mo · viewing Sat 2pm" callout (in-app and in the Telegram confirmation). This proves the agent didn't just *message* — it *haggled and won money for you*. That's the line judges repeat.

### 6. Persistent "2 computer-use agents" HUD badge — design · S · impact 3
Add a header chip with a browser glyph and a desktop glyph that pulse when each surface is live (browser during `discovering`, desktop during `contacting`). Reuses the existing `.pulse` keyframe (`globals.css:132`). Continuously advertises the rare dual-surface claim instead of relying on the narrator to say it once.

### 7. Staggered live pin-drop animation as listings "arrive" — ux/demo · M · impact 3
Right now `finishDiscovery` sets all listings at once, so the map pops fully formed (`page.tsx:79-84`). Drop the pins one-by-one with a short bounce while the Agent View streams steps, so the map visibly *fills live* as the agent scrolls Craigslist. Purely front-end/cosmetic — no reliability risk to the H session — but it turns a static reveal into a suspenseful "it's finding them right now" beat.

### 8. Telegram "typing…" beats + live-streamed negotiation lines — ux/demo · S · impact 3
The concierge already forwards `Owner:`/`Agent:` lines to the chat (`run_negotiation`). Add a `sendChatAction: typing` before each agent line and pace them, so the judge's own phone lights up in their hand with the back-and-forth as it happens. Cheap, and it makes the "from a phone DM" hook tangible during the pitch. Optionally attach the H live-view link as a QR so judges can open the session on their own phones.

---

## Sequencing before tomorrow
Do the zero-risk, high-payoff staging first: **#2 (Desktop Cam)** and **#5 (Saved you $X)** cost the least and land the two biggest lines ("it drove my real desktop", "it saved me money"). Then **#4 (sound/confetti)** for the climax, **#1 (embedded Agent View)** for the browser surface (with the safe link fallback), and **#3 (hero negotiate state)** if there's time. #6/#7/#8 are polish that reinforce the narrative. None of these touch the reliability-critical session lifecycle in `lib/discovery.ts` or `contact-svc/main.py`.

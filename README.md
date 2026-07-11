# 🏠 Homeless — ApartmentAgent

> An agent that finds and contacts short-term apartment rentals on platforms that **have no API** — using H Company's Computer Use / Browser Use agents.
>
> Built at the **H Company Computer Use Hackathon** · San Francisco · July 11–12, 2026 · **Track 2 (Browser Use)**

You give it a **city, dates, budget, and headcount**. It finds apartment listings on no-API platforms (Craigslist first), plots them on a **map**, filters to what fits (budget + proximity to center + date availability), narrows to ~4, and an agent **reaches out to owners** to book — all watched live in the UI.

---

## ▶ Run this build

Two processes: the Next.js app (UI + live Craigslist discovery) and the Python contact service (WhatsApp via H **local browser control**).

```bash
# 0. API key (from ~/.hcompany/credentials or platform.hcompany.ai)
cp .env.example .env && echo "HAI_API_KEY=hk-..." >> .env    # set your key

# 1. Frontend (Next.js, TypeScript)  — http://localhost:3000
npm install
npm run dev

# 2. Contact service (Python, local browser control) — http://localhost:8000
cd contact-svc
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add the same HAI_API_KEY
uvicorn main:app --reload --port 8000
```

**Before the demo:** the contact agent drives a real Chrome on this laptop, so **log into WhatsApp Web** in the Chrome the H SDK controls (it uses profile `~/.hai/chrome-profile`, or pre-launch Chrome with `--remote-debugging-port=9222 --user-data-dir=...` and sign in there once). Set the controlled "perfect listing" `whatsapp` number in `data/listings.json` to a **consenting teammate's** number.

**Flow:** enter search → the H agent scrapes Craigslist live and fills the map (falls back to `data/listings.json` if it stalls) → filter to a shortlist → click **Reach out on WhatsApp** on the perfect listing → watch the agent send the message in the **Agent View** panel → teammate replies (or hit **Owner replied** in the demo) → **"Found you a place!"** notification.

Architecture and decisions: `.omc/specs/deep-interview-homeless-apartmentagent.md`. Contact service details: `contact-svc/README.md`.

---

## Table of Contents
1. [The Pitch](#the-pitch)
2. [How It Works (Pipeline)](#how-it-works-pipeline)
3. [Key Decisions](#key-decisions)
4. [Feasibility Facts (verified)](#feasibility-facts-verified)
5. [H Company — Setup & Resources](#h-company--setup--resources)
   - [Two different APIs — know which you need](#two-different-apis--know-which-you-need)
   - [A. Agents SDK (Browser Use) — what we use](#a-agents-sdk-browser-use--what-we-use)
   - [B. Models API (raw VLM)](#b-models-api-raw-vlm)
   - [Getting your API key](#getting-your-api-key)
6. [Side Challenges](#side-challenges)
7. [Suggested 48h Build Plan](#suggested-48h-build-plan)
8. [Demo Script (90s)](#demo-script-90s)
9. [Ethics & Rules Guardrails](#ethics--rules-guardrails)
10. [Open Questions for the Team](#open-questions-for-the-team)
11. [All Resources & Links](#all-resources--links)
12. [Hackathon Logistics](#hackathon-logistics)

---

## The Pitch

Finding a place to stay in a new city means tab-hopping across Craigslist, Facebook Marketplace, and a dozen no-API listing sites, copy-pasting into a spreadsheet, then messaging owner after owner one by one. **We automate the whole loop.** Type (or say) what you need once — the agent surfaces every fit on a map and handles outreach for you.

---

## How It Works (Pipeline)

```
  ┌─────────────┐   ┌──────────────┐   ┌───────────────┐   ┌──────────────┐   ┌───────────────┐
  │  1. INPUT   │──▶│ 2. DISCOVER  │──▶│  3. FILTER    │──▶│ 4. SHORTLIST │──▶│  5. CONTACT   │
  │ city/dates/ │   │ listings +   │   │ budget +      │   │  pick ~4     │   │  H agent      │
  │ budget/#ppl │   │ plot on map  │   │ proximity +   │   │              │   │  messages     │
  │             │   │              │   │ availability  │   │              │   │  owners live  │
  └─────────────┘   └──────────────┘   └───────────────┘   └──────────────┘   └───────┬───────┘
                                                                                       │
                                                                          reply lands  ▼
                                                                          ┌───────────────────┐
                                                                          │ 6. NOTIFICATION   │
                                                                          │ "found you a place"│
                                                                          └───────────────────┘
```

---

## Key Decisions

| Decision | Choice | Why |
|---|---|---|
| **Core platform** | **Craigslist only** | No login = fastest to a working demo. FB Marketplace is a stretch goal (login-walled, bot-detected). |
| **Contact loop** | **Controlled listing / teammate acts as owner** | Reply lands live on stage. Consent-clean → no ethics-rule risk. |
| **Voice (Gradium)** | **Stretch goal, after core works** | ~1hr add-on, unlocks side-prize, boosts Creativity/Demo scores. |
| **Architecture** | **OPEN — team to decide** (recommend Hybrid, see below) | Decides whether the demo survives a live Craigslist. |

### Architecture options (the one open call)

- **A — Hybrid (recommended):** Cache/fetch listings for the map *before* the demo. Reserve the live H agent for the un-fakeable moment — navigate a real listing and send the inquiry through Craigslist's actual reply flow, live. Plays to computer-use's strength; demo stays reliable.
- **B — Pure computer-use, scrape live:** H agent crawls + extracts every listing during the demo. Most "autonomous" looking, but slowest tool doing the highest-volume job → rate-limited, CAPTCHA-prone, likely to stall on stage.
- **C — Full autonomous multi-platform:** FB + Craigslist, live scrape + live negotiate on both. Maximum ambition, almost certainly too much to make reliable in 48h.

---

## Feasibility Facts (verified)

**H agent** = cloud browser driven by the Holo family of Vision-Language Models.
- Actions: `navigate`, `click`, `type`, `scroll`, `fill_secret_at` (logins).
- **Strength:** un-scriptable flows — login walls, popups, cookie banners, contact forms.
- **Weakness:** bulk work — every action is seconds of latency. Don't make it do bulk extraction.

**Craigslist**
- Browsable with **no login** (fastest demo path).
- ToS **prohibits scraping**; automated browsing hits CAPTCHA / IP blocks "within minutes."
- Contact = **anonymized email relay** — async (hours → days), no live chat. Threads live ~4 months.

**Facebook Marketplace**
- Login-walled, aggressive bot detection, contact via Messenger. Higher cost + ban risk → **stretch only.**

### Three landmines we design around
1. **Live bulk-scrape via the agent** → stalls/CAPTCHAs on stage. The agent's slowest job should not be its highest-volume one.
2. **"Live booking confirmation" from a real owner** → impossible in a 90s demo (async email). Don't build the demo around a reply you can't guarantee.
3. **Messaging real owners to fake-book** → violates the hackathon consent/ethics rule → possible **disqualification**. Use a controlled listing.

---

## H Company — Setup & Resources

### Two different APIs — know which you need

H exposes **two distinct surfaces**. Don't confuse them:

| | **Agents SDK (Browser Use)** | **Models API (raw VLM)** |
|---|---|---|
| Package | `hai-agents` | `openai` (OpenAI-compatible) |
| What it does | Drives a **cloud browser** end-to-end (click/type/navigate) | Chat/completions against Holo VLMs |
| Base URL | `https://agp.eu.hcompany.ai/api/v2/sessions` | `https://api.hcompany.ai/v1/` |
| Agent / model id | `h/web-surfer-flash` | `holo3-1-35b-a3b`, `holo3-122b-a10b` |
| **Use for our project** | ✅ **YES** — this is the whole point | Only if you want raw VLM calls |

> ⚠️ Track 2 requires H Company Computer Use Agents. **Use the Agents SDK (`hai-agents`).** The Models API alone does not satisfy the track.

### A. Agents SDK (Browser Use) — what we use

**Install**
```bash
pip install hai-agents        # Python
# or
npm install hai-agents        # TypeScript/Node
```

**Auth** (sets `HAI_API_KEY`)
```bash
hai login
# or manually:
export HAI_API_KEY="hk-..."
```

**Run your first browser session (Python)**
```python
from hai_agents import Client

client = Client()
result = client.run_session(
    agent="h/web-surfer-flash",
    messages="On Google Flights, find the cheapest direct flight from Paris (CDG) to Tokyo (NRT) this Saturday. Return the airline and the price."
)
print(result.answer)
```

**For our contact-flow money shot (sketch)**
```python
from hai_agents import Client

client = Client()
result = client.run_session(
    agent="h/web-surfer-flash",
    messages=(
        "Go to this Craigslist listing: <LISTING_URL>. "
        "Click 'reply', then in the email reply form, write a polite inquiry: "
        "'Hi, is this apartment available <DATES> for <N> people? "
        "What is the total price? Thanks!' and send it."
    )
)
print(result.answer)   # confirmation the inquiry was sent
```

**Sessions endpoint (raw API):** `POST https://agp.eu.hcompany.ai/api/v2/sessions`
You can **monitor, steer, and stop** running sessions — see the *Session lifecycle* and *Agent View (observe and steer)* docs. Agent View is what we surface in the UI as the "watch the agent work" panel.

**Available doc sections (Computer-Use Agents):** Quickstart · SDKs · Use cases · Session lifecycle · Agent View (observe and steer) · Plans and limits · Agents (overview) · Environments (overview) · Skills (overview) · Local desktop control · Pre-built agents reference.

### B. Models API (raw VLM)

OpenAI-compatible endpoint for direct Holo VLM calls (element localization, custom loops).
```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://api.hcompany.ai/v1/",
    api_key=os.environ.get("HAI_API_KEY"),
)
response = client.chat.completions.create(
    model="holo3-1-35b-a3b",                # or holo3-122b-a10b for more performance
    messages=[{"role": "user", "content": "Your task here"}],
)
print(response.choices[0].message.content)
```
Free tier: `holo3-1-35b-a3b`, no credit card.

### Getting your API key
1. Go to **[platform.hcompany.ai](https://platform.hcompany.ai)** → **API Keys** in the sidebar.
2. **Create API Key**, name it (e.g. "Hackathon Key"), optionally set expiry.
3. Copy the `hk-...` key **immediately** — shown only once.
4. `export HAI_API_KEY="hk-..."`

---

## Side Challenges

- **Gradium (Voice):** best use of voice — TTS and/or STT. Our plan: **speak the search in**, TTS **narrates the agent's steps**. Redeem credits with code `LETSHACKGRADIUM202607` in the subscription section of the Gradium site.
- **NVIDIA (NemoClaw):** run H's models through NemoClaw. Prize: RTX 5080. (Stretch — only if we have bandwidth.)

---

## Suggested 48h Build Plan

Spine first, stretch last.

1. **Input** — city, dates, budget, #people (typed form; voice later).
2. **Listings + map** — fetch/cache Craigslist housing, geocode, plot pins with price/availability.
3. **Filter** — drop out-of-budget / too-far-from-center / date-unavailable → narrow to ~4.
4. **Contact loop (the money shot)** — H agent opens the (controlled) listing, sends inquiry via the reply flow. Teammate-owner replies → **notification fires on stage.**
5. **Stretch, in order:** voice (Gradium) → FB Marketplace → multiple simultaneous outreaches → NemoClaw integration.

**Suggested repo layout**
```
Homeless/
├── README.md              # this file
├── frontend/              # map + filter UI + Agent View panel + notifications
├── backend/
│   ├── discover/          # listing fetch/cache + geocode
│   ├── filter/            # budget / proximity / availability logic
│   └── contact/           # hai-agents session driver (the money shot)
├── voice/                 # Gradium STT input + TTS narration (stretch)
└── .env.example           # HAI_API_KEY=...
```

---

## Demo Script (90s)

1. Speak/type the search → **map fills with pins.**
2. Filters prune to **4 fits.**
3. Click **"reach out."**
4. **Watch the H agent type and send the inquiry live** (Agent View panel).
5. Owner reply pops → **notification.** End on the closed loop.

Judging is 5 × 20: Technicality · Creativity · Usefulness · Demo · Track/sponsor alignment. This script targets Demo + Track alignment hard, with Usefulness obvious and Creativity via voice.

---

## Ethics & Rules Guardrails

- ✅ **Contact only a listing we control** (teammate posts a test listing / plays the owner). No messaging real strangers to fake-book.
- ✅ **No data used without consent** (explicit hackathon rule).
- ✅ Respect platform ToS in the demo framing; be honest that listings are pre-indexed if we go Hybrid.
- ✅ Follow the law + ethical AI + Code of Conduct. Violations can mean disqualification.

---

## Open Questions for the Team

1. **Architecture: A (Hybrid) / B (live scrape) / C (multi-platform)?** — recommend **A**.
2. Who posts/owns the **controlled test listing** and monitors its inbox during the demo?
3. Who owns **frontend (map + Agent View)** vs **backend (hai-agents contact flow)**?
4. Do we attempt **voice** on day 2, and who?
5. Map/geocoding stack? (e.g. Leaflet + a free geocoder.)

---

## All Resources & Links

**H Company**
- Tech Hub — Computer Use Agents intro: https://hub.hcompany.ai/computer-use-agents/introduction
- Quickstart (Models API): https://hub.hcompany.ai/quickstart
- Platform (API keys): https://platform.hcompany.ai
- Portal (alt key portal): https://portal.hcompany.ai
- Surfer 2 landing: https://surfer.hcompany.ai/
- Runner H: https://www.hcompany.ai/runner-h
- Surfer-H CLI (⚠️ archived/deprecated — migrate to `hai-agents`): https://github.com/hcompai/surfer-h-cli
- hcompai GitHub org: https://github.com/hcompai

**Agents SDK essentials**
- Install: `pip install hai-agents` · Auth: `hai login` · Env: `HAI_API_KEY`
- Agent id: `h/web-surfer-flash` · Sessions: `POST https://agp.eu.hcompany.ai/api/v2/sessions`

**Craigslist references**
- Mail relay (how replies work): https://www.craigslist.org/about/help/posting/features/contact-info/email/mail-relay

**Sponsors / side challenges**
- Gradium credits code: `LETSHACKGRADIUM202607` (redeem in subscription section)
- NVIDIA NemoClaw challenge (prize: RTX 5080)

---

## Hackathon Logistics

- **Event:** The Computer Use Hackathon, by H Company — San Francisco
- **Dates:** Saturday July 11 – Sunday July 12, 2026 (48 hours)
- **Sponsors:** H Company · NVIDIA · Accel · AWS · Gradium (organized by Iterate)
- **Wifi:** SSID `Alchemist` · password `123456789`
- **Discord:** https://discord.gg/6pf9FD42V
- **Team size:** 2–5
- **Prizes:** 1st $1.5k + credits · 2nd $1k + credits · 3rd $500 + credits · NVIDIA RTX 5080 · Gradium credits

### Rules that shape the build
- ✅ **Must use H Company models/agents.**
- ✅ **Build entirely during the event.** No prior commits to the repo (this README = live setup doc, written during the event).
- ✅ Teams of 2–5.
- ✅ Open-source libs / APIs / pre-trained models allowed **if credited.**
- ✅ Follow the law, ethical AI, Code of Conduct; **never use data without consent.**
- ✅ Use partner/sponsor APIs per their ToS.

### Submission
- 2-minute demo · GitHub repo link · short description.
- **Round 1:** 5 min/team — Pitch 1:30 · Demo 1:30 · Q&A 2:00.
- **Round 2 (8–10 finalists):** 3 min/team — Pitch 1:30 · Demo 1:30 · no questions.

---

*Setup doc generated during the hackathon. Keep it updated as decisions land.*

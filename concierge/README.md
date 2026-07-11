# Concierge orchestrator (Telegram front-door)

DM the bot → it parses your request (Nemotron if configured, else heuristic),
runs a LIVE Craigslist search via our H discovery API, sends the live UI link +
a shortlist, and on your pick drives the H desktop WhatsApp negotiation and
reports the booked viewing.

## Run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set TELEGRAM_BOT_TOKEN (via @BotFather) + OWNER_WHATSAPP
python main.py
```
Requires the Next.js app (:3000) and contact-svc (:8000) running.
Telegram uses long-poll getUpdates (no public webhook needed).

## NemoClaw / Nemotron (NVIDIA prize)
Set NEMOTRON_BASE_URL + NEMOTRON_API_KEY to an OpenAI-compatible Nemotron endpoint
(the NemoClaw Brev box via `brev port-forward`, or build.nvidia.com). Without it,
a regex heuristic parses the request so the demo still runs.

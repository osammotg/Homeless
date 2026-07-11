"""
ApartmentAgent — Concierge orchestrator (Telegram front-door).

You DM this bot: "find me a place in SF, 2 people, ~$2500, July-Aug".
It: parses the request (Nemotron llm() if configured, else a heuristic), starts a
LIVE Craigslist search via our H-powered discovery API, sends you the live UI
link, posts a shortlist, and when you pick one it drives the H DESKTOP WhatsApp
negotiation (via contact-svc) and reports the booked viewing back in chat.

Tools = our existing HTTP services (no rebuild):
  discovery: {NEXT_URL}/api/discover , /api/discover/{id}
  negotiate: {CONTACT_URL}/contact , /contact/{id} , /contact/{id}/reply

Run:
  pip install -r requirements.txt
  cp .env.example .env   # set TELEGRAM_BOT_TOKEN + OWNER_WHATSAPP
  python main.py
Telegram uses long-poll getUpdates (no public webhook; venue-wifi friendly).
"""

from __future__ import annotations

import os
import re
import threading
import time
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_API = f"https://api.telegram.org/bot{TG_TOKEN}"
NEXT_URL = os.getenv("NEXT_URL", "http://localhost:3000")
CONTACT_URL = os.getenv("CONTACT_URL", "http://localhost:8000")
OWNER_WHATSAPP = os.getenv("OWNER_WHATSAPP", "")          # teammate's number (the "owner")
OWNER_CONTACT_NAME = os.getenv("OWNER_CONTACT_NAME") or None
# Optional Nemotron (NVIDIA) OpenAI-compatible endpoint for intent parsing.
NEMOTRON_BASE = os.getenv("NEMOTRON_BASE_URL", "")        # e.g. https://integrate.api.nvidia.com/v1
NEMOTRON_KEY = os.getenv("NEMOTRON_API_KEY", "")
NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct")
ADVANCE_INTERVAL_S = int(os.getenv("ADVANCE_INTERVAL_S", "25"))

# chat_id -> {phase, criteria, discoverId, listings, shortlist, contactId, negoThread}
STATE: dict[int, dict[str, Any]] = {}

CITY_CENTERS = {
    "san francisco": "San Francisco", "sf": "San Francisco", "new york": "New York",
    "nyc": "New York", "los angeles": "Los Angeles", "la": "Los Angeles",
    "chicago": "Chicago", "austin": "Austin",
}


# ---------------------------------------------------------------- Telegram I/O
def send(chat_id: int, text: str) -> None:
    try:
        requests.post(f"{TG_API}/sendMessage", json={"chat_id": chat_id, "text": text,
                      "disable_web_page_preview": False}, timeout=15)
    except Exception as e:
        print("send err", e)


# ------------------------------------------------------------------- llm seam
def llm_parse(text: str) -> Optional[dict[str, Any]]:
    """Parse a free-text request into search criteria. Nemotron if configured, else None."""
    if not (NEMOTRON_BASE and NEMOTRON_KEY):
        return None
    try:
        prompt = (
            "Extract apartment search criteria from the message as JSON with keys "
            "city, checkIn (YYYY-MM-DD), checkOut (YYYY-MM-DD), budget (int monthly USD), "
            f"headcount (int). Message: {text!r}. Reply with ONLY the JSON."
        )
        r = requests.post(
            f"{NEMOTRON_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {NEMOTRON_KEY}"},
            json={"model": NEMOTRON_MODEL, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.1, "max_tokens": 200},
            timeout=30,
        )
        import json as _j
        content = r.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", content, re.S)
        return _j.loads(m.group(0)) if m else None
    except Exception as e:
        print("nemotron parse err", e)
        return None


def heuristic_parse(text: str) -> dict[str, Any]:
    t = text.lower()
    city = "San Francisco"
    for k, v in CITY_CENTERS.items():
        if k in t:
            city = v
            break
    budget = 2500
    m = re.search(r"\$?\s?(\d{3,5})", t.replace(",", ""))
    if m:
        budget = int(m.group(1))
    headcount = 2
    m = re.search(r"(\d+)\s*(?:people|ppl|persons?|guests?|of us)", t)
    if m:
        headcount = int(m.group(1))
    return {"city": city, "checkIn": "2026-07-15", "checkOut": "2026-08-15",
            "budget": budget, "headcount": headcount}


def parse_request(text: str) -> dict[str, Any]:
    return llm_parse(text) or heuristic_parse(text)


# --------------------------------------------------------------------- tools
def start_discovery(criteria: dict[str, Any]) -> dict[str, Any]:
    return requests.post(f"{NEXT_URL}/api/discover", json=criteria, timeout=20).json()


def poll_discovery(sid: str) -> dict[str, Any]:
    return requests.get(f"{NEXT_URL}/api/discover/{sid}", timeout=20).json()


def start_contact(listing: dict[str, Any], criteria: dict[str, Any]) -> dict[str, Any]:
    body = {
        "whatsapp_number": OWNER_WHATSAPP,          # ALWAYS the configured owner number
        "contact_name": OWNER_CONTACT_NAME,
        "listing_title": listing.get("title", "the apartment"),
        "price": listing.get("priceUsd"),
        "dates": f"{criteria['checkIn']} to {criteria['checkOut']}",
        "headcount": criteria["headcount"],
        "budget": criteria["budget"],
        "mode": "desktop",
    }
    return requests.post(f"{CONTACT_URL}/contact", json=body, timeout=20).json()


def poll_contact(cid: str) -> dict[str, Any]:
    return requests.get(f"{CONTACT_URL}/contact/{cid}", timeout=20).json()


def advance_contact(cid: str) -> None:
    try:
        requests.post(f"{CONTACT_URL}/contact/{cid}/reply", json={}, timeout=20)
    except Exception:
        pass


# ------------------------------------------------------------------ workflows
def run_search(chat_id: int, criteria: dict[str, Any]) -> None:
    try:
        res = start_discovery(criteria)
        sid = res.get("sessionId")
        if not sid:
            send(chat_id, "Couldn't start the search — is the app running?")
            return
        STATE[chat_id]["discoverId"] = sid
        send(chat_id, f"🔎 On it — searching {criteria['city']} under ${criteria['budget']} for "
                      f"{criteria['headcount']}. Watch me live: {NEXT_URL}")
        deadline = time.time() + 150
        listings = None
        while time.time() < deadline:
            time.sleep(3)
            d = poll_discovery(sid)
            if d.get("listings"):
                listings = d["listings"]
                break
        if not listings:
            send(chat_id, "Search timed out. Try again?")
            return
        # rank: cheapest that fit, keep the 'perfect' first if present
        perfect = [l for l in listings if l.get("isPerfect")]
        rest = sorted([l for l in listings if not l.get("isPerfect")], key=lambda l: l["priceUsd"])
        short = (perfect + rest)[:3]
        STATE[chat_id]["shortlist"] = short
        STATE[chat_id]["criteria"] = criteria
        STATE[chat_id]["phase"] = "shortlist"
        lines = ["Here are the top 3 that fit:"]
        for i, l in enumerate(short, 1):
            br = "Studio" if l.get("bedrooms") == 0 else (f"{l.get('bedrooms')}BR" if l.get("bedrooms") else "")
            lines.append(f"{i}) {l['title'][:60]} — ${l['priceUsd']}/mo {br} · {l.get('neighborhood','')}")
        lines.append("\nReply with 1, 2, or 3 and I'll reach out and negotiate.")
        send(chat_id, "\n".join(lines))
    except Exception as e:
        send(chat_id, f"Search error: {e}")


def run_negotiation(chat_id: int, listing: dict[str, Any], criteria: dict[str, Any]) -> None:
    try:
        if not OWNER_WHATSAPP:
            send(chat_id, "No OWNER_WHATSAPP configured — set it in concierge/.env.")
            return
        res = start_contact(listing, criteria)
        cid = res.get("session_id")
        if not cid:
            send(chat_id, f"Couldn't start the negotiation: {res}")
            return
        STATE[chat_id]["contactId"] = cid
        STATE[chat_id]["phase"] = "negotiating"
        send(chat_id, f"🤝 Reaching out about '{listing['title'][:50]}' and negotiating now. "
                      f"Watch the agent: {poll_contact(cid).get('agent_view_url','')}")
        deadline = time.time() + 480
        last_advance = 0.0
        seen_events = 0
        while time.time() < deadline:
            time.sleep(4)
            c = poll_contact(cid)
            # stream a couple of human-readable milestones
            evs = c.get("events", [])
            for e in evs[seen_events:]:
                txt = e.get("text", "")
                if txt.startswith(("Owner:", "Agent:")):
                    send(chat_id, txt)
            seen_events = len(evs)
            if c.get("done"):
                if c.get("reply"):
                    send(chat_id, f"✅ {c['reply']}")
                else:
                    send(chat_id, f"Negotiation ended: {c.get('phase')}")
                STATE[chat_id]["phase"] = "done"
                return
            # auto-advance: when awaiting the owner, periodically re-check the screen
            if c.get("phase") == "awaiting_owner" and not c.get("turn_running"):
                if time.time() - last_advance > ADVANCE_INTERVAL_S:
                    advance_contact(cid)
                    last_advance = time.time()
        send(chat_id, "Negotiation timed out — the owner may be slow. Check the agent view.")
    except Exception as e:
        send(chat_id, f"Negotiation error: {e}")


# --------------------------------------------------------------------- router
def handle(chat_id: int, text: str) -> None:
    st = STATE.setdefault(chat_id, {"phase": "idle"})
    t = text.strip().lower()

    if t in ("/start", "start", "hi", "hello"):
        send(chat_id, "👋 I'm your ApartmentAgent. Tell me where, budget, dates and how many "
                      "people — e.g. 'find me a place in SF for 2, ~$2500, mid July to mid Aug'.")
        return

    # pick a shortlist item
    m = re.search(r"\b([123])\b", t)
    if st.get("phase") == "shortlist" and (m or "go with" in t):
        idx = int(m.group(1)) - 1 if m else 0
        short = st.get("shortlist", [])
        if 0 <= idx < len(short):
            threading.Thread(target=run_negotiation, args=(chat_id, short[idx], st["criteria"]),
                             daemon=True).start()
            return

    # otherwise treat as a search request
    criteria = parse_request(text)
    st["phase"] = "searching"
    threading.Thread(target=run_search, args=(chat_id, criteria), daemon=True).start()


def main() -> None:
    if not TG_TOKEN:
        raise SystemExit("Set TELEGRAM_BOT_TOKEN in concierge/.env (create a bot via @BotFather).")
    print("Concierge up. Owner:", OWNER_WHATSAPP or "(unset!)",
          "| Nemotron:", "on" if NEMOTRON_BASE and NEMOTRON_KEY else "heuristic")
    offset = 0
    while True:
        try:
            r = requests.get(f"{TG_API}/getUpdates", params={"timeout": 25, "offset": offset}, timeout=35)
            for upd in r.json().get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg or "text" not in msg:
                    continue
                handle(msg["chat"]["id"], msg["text"])
        except Exception as e:
            print("poll err", e)
            time.sleep(3)


if __name__ == "__main__":
    main()

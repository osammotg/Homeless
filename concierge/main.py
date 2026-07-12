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
def md_safe(s: Any) -> str:
    """Neutralize Markdown-breaking chars in free-text (listing titles etc.).

    Telegram's legacy 'Markdown' parse mode 400s on unbalanced _ * [ ] ` — so we
    strip them from any user/listing-supplied text we drop into a formatted message.
    """
    return re.sub(r"[_*\[\]`]", " ", str(s or "")).strip()


def send(chat_id: int, text: str, parse_mode: Optional[str] = "Markdown") -> None:
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": False}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        r = requests.post(f"{TG_API}/sendMessage", json=payload, timeout=15)
        # If odd formatting makes Telegram 400, retry once as plain text so we
        # never silently drop a message.
        if parse_mode and r.status_code == 400:
            payload.pop("parse_mode", None)
            requests.post(f"{TG_API}/sendMessage", json=payload, timeout=15)
    except Exception as e:
        print("send err", e)


def send_photo_url(chat_id: int, url: Optional[str], caption: str = "",
                   parse_mode: Optional[str] = "Markdown") -> None:
    if not url:
        return
    data = {"chat_id": chat_id, "photo": url, "caption": caption}
    if parse_mode:
        data["parse_mode"] = parse_mode
    try:
        r = requests.post(f"{TG_API}/sendPhoto", data=data, timeout=30)
        if parse_mode and r.status_code == 400:
            data.pop("parse_mode", None)
            requests.post(f"{TG_API}/sendPhoto", data=data, timeout=30)
    except Exception as e:
        print("send_photo_url err", e)


def send_photo_file(chat_id: int, path: str, caption: str = "",
                    parse_mode: Optional[str] = "Markdown") -> None:
    try:
        data = {"chat_id": chat_id, "caption": caption}
        if parse_mode:
            data["parse_mode"] = parse_mode
        with open(path, "rb") as f:
            r = requests.post(f"{TG_API}/sendPhoto", data=data, files={"photo": f}, timeout=45)
        if parse_mode and r.status_code == 400:
            data.pop("parse_mode", None)
            with open(path, "rb") as f:
                requests.post(f"{TG_API}/sendPhoto", data=data, files={"photo": f}, timeout=45)
    except Exception as e:
        print("send_photo_file err", e)


def _beds(l: dict[str, Any]) -> str:
    b = l.get("bedrooms")
    return "Studio" if b == 0 else (f"{b} BR" if b else "")


def _parse_price(raw: Any) -> Optional[int]:
    """Pull an integer dollar amount out of an agreed-price string like '$2,400' or '2400'."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    digits = re.sub(r"[^\d]", "", str(raw))
    return int(digits) if digits else None


BROWSE = os.path.expanduser("~/.claude/skills/gstack/browse/dist/browse")


def make_map_image(short: list, path: str = "/tmp/apt-map.png") -> Optional[str]:
    """Render a dark map with a pin per shortlist item and screenshot it via the browse binary."""
    import json as _j
    import subprocess
    pts = [l for l in short if l.get("lat") and l.get("lng")]
    if not pts:
        return None
    pts_json = _j.dumps([{"lat": l["lat"], "lng": l["lng"], "price": l["priceUsd"],
                          "perfect": bool(l.get("isPerfect"))} for l in pts])
    html = f"""<!doctype html><html><head><meta charset="utf8">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>html,body,#m{{height:100%;margin:0;background:#080b10}}
/* Price pins mirror the web app: amber = best match, muted dark pill for the rest. */
.pin{{display:inline-block;white-space:nowrap;font:700 12px ui-monospace,monospace;
  border-radius:999px;padding:3px 9px;box-shadow:0 2px 6px rgba(0,0,0,.55);
  background:#141a24;color:#f4f7fb;border:1px solid #2a3646}}
.pin.perfect{{background:#f5b544;color:#1a1204;border-color:#f5b544;
  box-shadow:0 2px 10px rgba(245,181,68,.55)}}</style></head>
<body><div id="m"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
var pts={pts_json};
var m=L.map('m',{{zoomControl:false,attributionControl:false}});
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}.png').addTo(m);
var g=[];
pts.forEach(function(p){{
  var cls=p.perfect?'pin perfect':'pin';
  var icon=L.divIcon({{className:'',html:'<span class="'+cls+'">$'+p.price+'</span>',iconSize:null}});
  var mk=L.marker([p.lat,p.lng],{{icon:icon,zIndexOffset:p.perfect?1000:0}}).addTo(m);
  g.push(mk);
}});
m.fitBounds(L.featureGroup(g).getBounds().pad(0.35));
</script></body></html>"""
    try:
        with open("/tmp/apt-map.html", "w") as f:
            f.write(html)
        subprocess.run([BROWSE, "viewport", "760x480"], timeout=20, capture_output=True)
        subprocess.run([BROWSE, "goto", "file:///tmp/apt-map.html"], timeout=30, capture_output=True)
        time.sleep(2.5)
        subprocess.run([BROWSE, "screenshot", path], timeout=30, capture_output=True)
        return path if os.path.exists(path) else None
    except Exception as e:
        print("make_map_image err", e)
        return None


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
                      f"{criteria['headcount']}. Watch me live: {NEXT_URL}", parse_mode=None)
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
        lines = ["*Here are the top 3 that fit:*"]
        for i, l in enumerate(short, 1):
            br = "Studio" if l.get("bedrooms") == 0 else (f"{l.get('bedrooms')}BR" if l.get("bedrooms") else "")
            title = md_safe(l.get("title", ""))[:60]
            hood = md_safe(l.get("neighborhood", ""))
            tag = " ⭐" if l.get("isPerfect") else ""
            lines.append(f"{i}) {title} — *${l['priceUsd']}/mo* {br} · {hood}{tag}")
        lines.append("\nReply with 1, 2, or 3 and I'll reach out and negotiate.")
        send(chat_id, "\n".join(lines))
        # pictures + prices for each, then a map of where they are
        for i, l in enumerate(short, 1):
            title = md_safe(l.get("title", ""))[:64]
            hood = md_safe(l.get("neighborhood", ""))
            cap = f"{i}) {title}\n*${l['priceUsd']}/mo* · {_beds(l)} · {hood}"
            send_photo_url(chat_id, l.get("imageUrl"), cap)
        try:
            mp = make_map_image(short)
            if mp:
                send_photo_file(chat_id, mp, "Where they are on the map")
        except Exception as e:
            print("map send err", e)
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
        send(chat_id, f"🤝 Reaching out about '{md_safe(listing.get('title',''))[:50]}' and "
                      f"negotiating now. Watch the agent: "
                      f"{poll_contact(cid).get('agent_view_url','')}", parse_mode=None)
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
                    send(chat_id, txt, parse_mode=None)  # raw convo text, no Markdown parsing
            seen_events = len(evs)
            if c.get("done"):
                if c.get("reply"):
                    # A24 — compute the negotiated savings for a punchy win callout.
                    asking = listing.get("priceUsd")
                    agreed = _parse_price(c.get("agreed_price"))
                    reply = md_safe(c.get("reply"))
                    if agreed and asking and agreed < asking:
                        savings = int(asking) - agreed
                        send(chat_id,
                             f"💰 *Negotiated ${savings}/mo off — booked at ${agreed}!*\n\n"
                             f"✅ *Booked!* {reply}")
                    else:
                        send(chat_id, f"✅ *Booked!* {reply}")
                    price = c.get("agreed_price") or (f"${listing['priceUsd']}/mo" if listing.get("priceUsd") else "")
                    vt = c.get("viewing_time")
                    cap_title = md_safe(listing.get("title", ""))[:64]
                    cap = cap_title
                    if agreed and asking and agreed < asking:
                        cap += f"\n💰 *${int(asking) - agreed}/mo saved* — booked at *${agreed}*"
                    elif price:
                        cap += f"\n*{md_safe(price)}*"
                    if vt:
                        cap += f"\nViewing: {md_safe(vt)}"
                    send_photo_url(chat_id, listing.get("imageUrl"), cap)
                else:
                    send(chat_id, f"Negotiation ended: {md_safe(c.get('phase'))}")
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
    # A19 — harden the front door: kill any stray webhook so it can't swallow our
    # getUpdates. drop_pending_updates clears a backlog queued while a webhook was set.
    try:
        wr = requests.post(f"{TG_API}/deleteWebhook",
                           json={"drop_pending_updates": True}, timeout=15)
        ok = wr.json().get("ok")
        print(f"deleteWebhook(drop_pending_updates=true) -> ok={ok} "
              f"(getUpdates long-poll is now the sole consumer)")
    except Exception as e:
        print("deleteWebhook err (continuing to long-poll anyway):", e)
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

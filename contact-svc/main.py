"""
ApartmentAgent — CONTACT / NEGOTIATION service.

An H DESKTOP computer-use agent drives the WhatsApp desktop app on this Mac
(already logged in) to conduct a MULTI-TURN negotiation with an apartment owner:
open the chat, send an inquiry, then on each owner reply run a fresh session that
reads the latest on-screen message and responds per a guided script, until a
viewing is booked.

Design (per H docs + OMC consensus review):
  - FRESH SESSION PER TURN. H sessions end after the agent answers; a single
    long session cannot "wait" for a human reply. Because desktop control drives
    the real WhatsApp app, each new session sees the full conversation on screen.
  - Turn 1 opens the chat via the whatsapp://send deep link (works for unsaved
    numbers) and sends the inquiry.
  - POST /contact/{id}/reply FIRES THE NEXT TURN (it does not just store text).
  - Each turn returns a structured result (answer_format) so we know whether it
    replied, is awaiting the owner, or booked a viewing.
  - One local desktop session at a time (serialize); max_time_s + watchdog cancel;
    delete the H session after each turn to free the concurrency slot.

Grounded in: computer-use-agents/desktop/local-control, sessions/overview
(interactive), observe-and-steer, structured-output.

Run:
    pip install -r requirements.txt        # hai-agents[browser,desktop]
    CONTACT_MODE=desktop uvicorn main:app --port 8000
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import uuid
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

CONTACT_MODE = os.getenv("CONTACT_MODE", "desktop")
USE_DEEPLINK = os.getenv("USE_DEEPLINK", "1") not in ("0", "false", "False")
MAX_TIME_S = int(os.getenv("MAX_TIME_S", "180"))
WATCHDOG_GRACE_S = 40
MAX_TURNS = int(os.getenv("MAX_TURNS", "10"))
BASE_URL = os.getenv("HAI_BASE_URL", "https://agp.eu.hcompany.ai/api/v2")

try:
    from hai_agents import Client  # type: ignore

    HAI_IMPORT_ERROR: Optional[str] = None
except Exception as exc:  # pragma: no cover
    Client = None  # type: ignore
    HAI_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

app = FastAPI(title="ApartmentAgent — Negotiation Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# conversation_id -> conversation record (multi-turn)
CONV: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
_DESKTOP_BUSY = threading.Lock()  # one local desktop session at a time

# Structured result each negotiation turn returns.
TURN_ANSWER_FORMAT = {
    "type": "object",
    "properties": {
        "replied": {"type": "boolean"},
        "awaiting_owner": {"type": "boolean"},
        "owner_said": {"type": "string"},
        "we_said": {"type": "string"},
        "booked": {"type": "boolean"},
        "agreed_price": {"type": "string"},
        "viewing_time": {"type": "string"},
        "unavailable": {"type": "boolean"},
    },
    "required": ["replied", "awaiting_owner", "booked"],
}


class ContactRequest(BaseModel):
    whatsapp_number: str
    listing_title: str
    dates: str
    headcount: int
    budget: int
    price: Optional[int] = None            # listing asking price (for the negotiation)
    mode: Optional[str] = None             # "desktop" | "browser"
    contact_name: Optional[str] = None     # preferred WhatsApp selector


class ReplyInject(BaseModel):
    reply: Optional[str] = None            # optional hint; the agent reads the screen anyway


def _now() -> float:
    return time.time()


def _hai_key() -> Optional[str]:
    return os.getenv("HAI_API_KEY") or None


def _digits(number: str) -> str:
    return "".join(ch for ch in number if ch.isdigit())


def _add_event(conv: dict[str, Any], text: str) -> None:
    with _LOCK:
        conv["events"].append({"step": len(conv["events"]), "text": text, "ts": _now()})


def _opening_message(c: dict[str, Any]) -> str:
    return (
        f"Hi! I'm interested in '{c['listing_title']}'. Is it available for "
        f"{c['dates']} for {c['headcount']} people? What's the total price? Thanks!"
    )


def _negotiation_policy(c: dict[str, Any]) -> str:
    ask = f"${c['price']}" if c.get("price") else "the listed price"
    target = f"${int(c['price'] * 0.95)}" if c.get("price") else "a small discount"
    return (
        f"GOAL: rent '{c['listing_title']}' for {c['dates']} ({c['headcount']} people). "
        f"Budget cap: ${c['budget']} total per month — never agree above it. Asking is {ask}. "
        "NEGOTIATION POLICY (one reply per turn, polite and concise):\n"
        f"- If the owner confirms it's available: thank them, then ask for a small discount "
        f"(propose {target} for taking it the full term) and ask when we can view it.\n"
        f"- If the owner counters with a price: accept if it is <= ${c['budget']}; otherwise say "
        f"our max is ${c['budget']} total incl. fees and ask if they can make it work.\n"
        f"- If the owner asks a question (move-in date, number of people, pets): answer from the "
        f"facts (dates {c['dates']}, {c['headcount']} people, no pets), then re-ask to book a viewing.\n"
        "- If the owner says it's unavailable/rented: thank them, ask if anything similar is coming up, and stop.\n"
        "- Once a price <= budget is agreed, propose or confirm a specific viewing time to BOOK a viewing.\n"
        "- Keep messages short and human. Do not overcommit beyond the budget or dates."
    )


def open_whatsapp_chat(number: str, text: str) -> None:
    url = f"whatsapp://send?phone={_digits(number)}&text={urllib.parse.quote(text)}"
    subprocess.run(["open", url], check=False)


def _opening_task(c: dict[str, Any], message: str) -> str:
    who = c.get("contact_name") or f"the number {c['whatsapp_number']}"
    return (
        "You are operating the macOS desktop. Do exactly this, then stop. Do not open "
        "any other app.\n"
        f"1. Bring WhatsApp to the front. A chat for {who} should be open with a message "
        "pre-typed. If a login/QR screen shows, report BLOCKED on WhatsApp login and stop.\n"
        f"2. Confirm the chat is for {who} and the message box contains: \"{message}\". "
        "If empty, click it and type exactly that message.\n"
        "3. If the wrong chat / no chat is open, report 'contact not found' and stop.\n"
        "4. Send it (click send or press Return) and confirm it shows as sent.\n"
        "Then answer the structured result: replied=true, awaiting_owner=true, "
        f"owner_said=\"\", we_said=the message, booked=false."
    )


def _respond_task(c: dict[str, Any]) -> str:
    who = c.get("contact_name") or f"the number {c['whatsapp_number']}"
    return (
        "You are operating the macOS desktop and the WhatsApp app is open. Do not open any "
        f"other app.\n1. Make sure the WhatsApp chat with {who} is in front (click it in the "
        "chat list if needed). Read the ENTIRE visible conversation.\n"
        "2. Decide: is the owner's LATEST message unanswered by us?\n"
        "   - If YES: compose ONE reply following the policy below and send it (Return).\n"
        "   - If NO (our message is the most recent, owner hasn't replied yet): do NOT send "
        "anything; report awaiting_owner=true.\n\n"
        f"{_negotiation_policy(c)}\n\n"
        "3. Answer the structured result honestly: replied (did you send a message this turn), "
        "awaiting_owner (are we now waiting on the owner), owner_said (their latest message), "
        "we_said (what you sent, or empty), booked (is a viewing time now agreed), agreed_price, "
        "viewing_time, unavailable."
    )


def _extract(obj: Any, *names: str) -> Any:
    for name in names:
        if obj is None:
            return None
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _event_to_text(event: Any) -> str:
    etype = _extract(event, "type", "kind") or "event"
    for f in ("message", "text", "thought", "action", "summary", "content"):
        v = _extract(event, f)
        if isinstance(v, str) and v.strip():
            return f"{etype}: {v.strip()}"
    return str(etype)


def _http_delete_session(hai_session_id: str) -> None:
    key = _hai_key()
    if not key or not hai_session_id:
        return
    try:
        urllib.request.urlopen(
            urllib.request.Request(
                f"{BASE_URL}/sessions/{hai_session_id}", method="DELETE",
                headers={"Authorization": f"Bearer {key}"},
            ), timeout=10,
        )
    except Exception:
        pass


def _apply_turn_result(conv: dict[str, Any], answer: Any) -> None:
    """Parse a turn's structured answer and update conversation phase."""
    data = answer
    if isinstance(answer, str):
        try:
            data = json.loads(answer)
        except Exception:
            data = {}
    if not isinstance(data, dict):
        data = {}
    with _LOCK:
        if data.get("owner_said"):
            _add_event_nl(conv, f"Owner: {data['owner_said']}")
        if data.get("we_said"):
            _add_event_nl(conv, f"Agent: {data['we_said']}")
        if data.get("unavailable"):
            conv["phase"] = "unavailable"
            conv["done"] = True
        elif data.get("booked"):
            conv["phase"] = "booked"
            conv["done"] = True
            conv["agreed_price"] = data.get("agreed_price")
            conv["viewing_time"] = data.get("viewing_time")
            conv["reply"] = (
                f"Booked a viewing{(' at ' + str(conv['viewing_time'])) if conv.get('viewing_time') else ''}"
                f"{(' — ' + str(conv['agreed_price'])) if conv.get('agreed_price') else ''}."
            )
        elif data.get("awaiting_owner"):
            conv["phase"] = "awaiting_owner"


def _add_event_nl(conv: dict[str, Any], text: str) -> None:
    conv["events"].append({"step": len(conv["events"]), "text": text, "ts": _now()})


def _run_turn(conv_id: str, task: str, opening: bool) -> None:
    """Run ONE negotiation turn as a fresh H desktop session."""
    conv = CONV[conv_id]
    handle_box: dict[str, Any] = {}
    try:
        client = Client()
        env = (
            {"id": "my-mac", "kind": "desktop", "host": "user_device"}
            if conv["mode"] == "desktop"
            else {"id": "my-laptop", "kind": "web", "host": "user_device"}
        )
        agent = client.agents.create_agent(
            name=f"nego-{conv_id[:6]}-{len(conv['turns'])}",
            description="Negotiates an apartment on the WhatsApp desktop app.",
            instructions="Ground every action in what you see on screen. Never invent messages. "
                         "Send at most ONE message this turn. If blocked or the contact is missing, say so and stop.",
            environments=[env],
            answer_format=TURN_ANSWER_FORMAT,
        )
        messages = [{"type": "user_message", "message": task}]
        start_session = getattr(client, "start_session", None)
        if callable(start_session):
            try:
                handle = start_session(agent=agent, messages=messages, max_time_s=MAX_TIME_S)
            except TypeError:
                handle = start_session(agent=agent, messages=messages)
            handle_box["h"] = handle
            hid = _extract(handle, "id", "session_id")
            with _LOCK:
                conv["current_session_id"] = hid
                conv["agent_view_url"] = _extract(handle, "agent_view_url") or (
                    f"https://platform.hcompany.ai/agents/sessions/{hid}" if hid else None
                )
                conv["turns"].append({"session_id": hid, "opening": opening})
            _add_event(conv, f"Turn {len(conv['turns'])} started (session {hid})")
            threading.Timer(MAX_TIME_S + WATCHDOG_GRACE_S,
                            lambda: (getattr(handle, "cancel", lambda: None)())).start()
            _stream_turn(conv, handle)
            _http_delete_session(hid or "")  # free the slot after the turn
        else:
            try:
                result = client.run_session(agent=agent, messages=messages, max_time_s=MAX_TIME_S)
            except TypeError:
                result = client.run_session(agent=agent, messages=messages)
            _finalize_turn(conv, result)
    except Exception as exc:
        with _LOCK:
            conv["phase"] = "failed"
            conv["error"] = f"{type(exc).__name__}: {exc}"
        _add_event(conv, f"Turn error: {conv['error']}")
    finally:
        with _LOCK:
            conv["turn_running"] = False
        if _DESKTOP_BUSY.locked():
            try:
                _DESKTOP_BUSY.release()
            except RuntimeError:
                pass


def _stream_turn(conv: dict[str, Any], handle: Any) -> None:
    stream = getattr(handle, "stream", None)
    if callable(stream):
        try:
            for event in stream():
                _add_event(conv, _event_to_text(event))
        except Exception as exc:
            _add_event(conv, f"stream ended: {type(exc).__name__}: {exc}")
    result = None
    for meth in ("wait_for_completion", "get"):
        fn = getattr(handle, meth, None)
        if callable(fn):
            try:
                result = fn()
                break
            except Exception:
                continue
    _finalize_turn(conv, result)


def _finalize_turn(conv: dict[str, Any], result: Any) -> None:
    answer = _extract(result, "answer", "latest_answer")
    outcome = _extract(result, "outcome")
    if outcome == "blocked":
        _add_event(conv, "Blocked — login wall / missing permissions")
    _apply_turn_result(conv, answer)
    _add_event(conv, f"Turn settled (phase={conv.get('phase')})")


def _start_turn(conv_id: str, task: str, opening: bool = False) -> bool:
    """Serialize desktop turns; returns False if one is already running."""
    conv = CONV[conv_id]
    if conv["mode"] == "desktop" and not _DESKTOP_BUSY.acquire(blocking=False):
        return False
    with _LOCK:
        conv["turn_running"] = True
    threading.Thread(target=_run_turn, args=(conv_id, task, opening), daemon=True).start()
    return True


# --------------------------------------------------------------------------- #
@app.get("/health")
def health() -> dict[str, Any]:
    whatsapp = os.path.exists("/Applications/WhatsApp.app")
    ax = sr = None
    try:
        from ApplicationServices import AXIsProcessTrusted
        ax = bool(AXIsProcessTrusted())
    except Exception:
        pass
    try:
        from Quartz import CGPreflightScreenCaptureAccess
        sr = bool(CGPreflightScreenCaptureAccess())
    except Exception:
        pass
    return {
        "ok": True, "mode": CONTACT_MODE,
        "hai_key_present": _hai_key() is not None,
        "hai_sdk_installed": Client is not None, "hai_import_error": HAI_IMPORT_ERROR,
        "whatsapp_installed": whatsapp, "accessibility": ax, "screen_recording": sr,
        "desktop_ready": bool(whatsapp and ax and sr),
        "desktop_busy": _DESKTOP_BUSY.locked(),
    }


@app.post("/contact")
def contact(req: ContactRequest) -> dict[str, str]:
    if Client is None:
        raise HTTPException(status_code=400, detail='hai-agents not installed. pip install "hai-agents[browser,desktop]".')
    if _hai_key() is None:
        raise HTTPException(status_code=400, detail="HAI_API_KEY not set.")
    mode = (req.mode or CONTACT_MODE).lower()

    conv_id = str(uuid.uuid4())
    c = {
        "session_id": conv_id, "mode": mode, "phase": "opening", "done": False,
        "events": [], "turns": [], "turn_running": False,
        "whatsapp_number": req.whatsapp_number, "contact_name": req.contact_name,
        "listing_title": req.listing_title, "dates": req.dates,
        "headcount": req.headcount, "budget": req.budget, "price": req.price,
        "current_session_id": None, "agent_view_url": None,
        "reply": None, "agreed_price": None, "viewing_time": None, "error": None,
        "created_at": _now(),
    }
    CONV[conv_id] = c
    message = _opening_message(c)
    _add_event(c, f"Contacting {req.contact_name or req.whatsapp_number} about '{req.listing_title}'")

    if mode == "desktop" and USE_DEEPLINK:
        open_whatsapp_chat(req.whatsapp_number, message)
        _add_event(c, f"Opened WhatsApp to {req.whatsapp_number} (deep link, prefilled)")
        time.sleep(1.5)

    if not _start_turn(conv_id, _opening_task(c, message), opening=True):
        raise HTTPException(status_code=409, detail="A desktop session is already running.")
    return {"session_id": conv_id}


@app.get("/contact/{conv_id}")
def contact_status(conv_id: str) -> dict[str, Any]:
    c = CONV.get(conv_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    with _LOCK:
        return {
            "status": "completed" if c["done"] else ("running" if c["turn_running"] else "idle"),
            "phase": c["phase"], "events": list(c["events"]),
            "turns": len(c["turns"]), "turn_running": c["turn_running"],
            "agent_view_url": c.get("agent_view_url"),
            "reply": c.get("reply"), "agreed_price": c.get("agreed_price"),
            "viewing_time": c.get("viewing_time"), "error": c.get("error"),
            "done": c["done"],
        }


@app.post("/contact/{conv_id}/reply")
def owner_replied(conv_id: str, body: ReplyInject) -> dict[str, Any]:
    """The owner replied on WhatsApp → FIRE THE NEXT TURN (read latest + respond)."""
    c = CONV.get(conv_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    if c["done"]:
        return {"ok": True, "note": "conversation already finished", "phase": c["phase"]}
    if c["turn_running"]:
        raise HTTPException(status_code=409, detail="A turn is already running; try again shortly.")
    if len(c["turns"]) >= MAX_TURNS:
        with _LOCK:
            c["done"] = True
        return {"ok": True, "note": "max turns reached", "phase": c["phase"]}
    if body.reply:
        _add_event(c, f"(owner reply hint: {body.reply})")
    started = _start_turn(conv_id, _respond_task(c), opening=False)
    return {"ok": started, "turn": len(c["turns"]), "phase": c["phase"]}


@app.post("/contact/{conv_id}/cancel")
def cancel(conv_id: str) -> dict[str, Any]:
    c = CONV.get(conv_id)
    if c is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    _http_delete_session(c.get("current_session_id") or "")
    with _LOCK:
        c["done"] = True
        c["phase"] = "cancelled"
    _add_event(c, "Cancelled by user")
    return {"ok": True, "phase": "cancelled"}


@app.on_event("shutdown")
def _shutdown() -> None:
    for c in list(CONV.values()):
        if not c.get("done"):
            _http_delete_session(c.get("current_session_id") or "")

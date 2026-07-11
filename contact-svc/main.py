"""
ApartmentAgent — CONTACT service.

An H Computer-Use Agent messages an apartment owner on WhatsApp and this FastAPI
app watches the run live and exposes the reply path.

Two modes (CONTACT_MODE, default "desktop"):
  - desktop: H DESKTOP local control (kind=desktop, host=user_device) drives the
    WhatsApp *desktop app* on this Mac (already logged in). Grounded in
    https://hub.hcompany.ai/computer-use-agents/desktop/local-control
  - browser: H local browser control drives WhatsApp Web (fallback; only real if
    the ~/.hai/chrome-profile is pre-logged into WhatsApp Web).

To reliably open a chat for an UNSAVED number, we use the macOS WhatsApp deep
link `whatsapp://send?phone=<digits>&text=<msg>` (WhatsApp desktop search only
matches saved contacts). The agent then confirms and sends.

Run:
    pip install -r requirements.txt        # hai-agents[browser,desktop]
    CONTACT_MODE=desktop uvicorn main:app --port 8000
macOS: grant the terminal Accessibility + Screen Recording (System Settings →
Privacy & Security); first run errors until granted, then restart.
"""

from __future__ import annotations

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
WATCHDOG_GRACE_S = 30
BASE_URL = os.getenv("HAI_BASE_URL", "https://agp.eu.hcompany.ai/api/v2")

try:
    from hai_agents import Client  # type: ignore

    HAI_IMPORT_ERROR: Optional[str] = None
except Exception as exc:  # pragma: no cover
    Client = None  # type: ignore
    HAI_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"

app = FastAPI(title="ApartmentAgent — Contact Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()
# R3: one local desktop session per process. Guard so a 2nd desktop request
# doesn't silently cancel the 1st (local-control.md:13).
_DESKTOP_BUSY = threading.Lock()
_active_desktop_session: Optional[str] = None


class ContactRequest(BaseModel):
    whatsapp_number: str
    listing_title: str
    dates: str
    headcount: int
    budget: int
    mode: Optional[str] = None          # "desktop" | "browser"; defaults to CONTACT_MODE
    contact_name: Optional[str] = None  # R4: preferred selector for the WhatsApp chat


class ReplyInject(BaseModel):
    reply: str


def _now() -> float:
    return time.time()


def _hai_key() -> Optional[str]:
    return os.getenv("HAI_API_KEY") or None


def _digits(number: str) -> str:
    return "".join(ch for ch in number if ch.isdigit())


def _add_event(rec: dict[str, Any], text: str, step: Optional[int] = None) -> None:
    with _LOCK:
        if step is None:
            step = len(rec["events"])
        rec["events"].append({"step": step, "text": text, "ts": _now()})


def _build_inquiry(req: ContactRequest) -> str:
    return (
        f"Hi! Is '{req.listing_title}' available for {req.dates} "
        f"for {req.headcount} people? What's the total price? Thanks!"
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
    for field in ("message", "text", "thought", "action", "summary", "content"):
        val = _extract(event, field)
        if isinstance(val, str) and val.strip():
            return f"{etype}: {val.strip()}"
    return str(etype)


def open_whatsapp_chat(number: str, text: str) -> None:
    """Foreground the WhatsApp desktop app at the chat for `number`, prefilled.
    Works for unsaved numbers (the deep link, unlike desktop search)."""
    url = f"whatsapp://send?phone={_digits(number)}&text={urllib.parse.quote(text)}"
    subprocess.run(["open", url], check=False)


def _desktop_task(req: ContactRequest, message: str) -> str:
    who = req.contact_name or f"the number {req.whatsapp_number}"
    return (
        "You are operating the macOS desktop of this machine. Do exactly the "
        "following, one step at a time, and stop after the message is sent. Do "
        "not open any other app or take any unrelated action.\n"
        "1. Bring the WhatsApp desktop app to the front. A chat should already be "
        f"open for {who}, with a message pre-typed in the input box. If WhatsApp "
        "shows a login/QR screen instead of chats, report you are BLOCKED on "
        "WhatsApp login and stop.\n"
        f"2. Confirm the open chat is for {who} and the message box contains: "
        f"\"{message}\". If the message box is empty, click it and type exactly "
        f"that message.\n"
        "3. If no chat is open or it is the wrong person, report 'contact not "
        "found' and stop — do NOT message anyone else.\n"
        "4. Click the green send button (or press Return) to send the message.\n"
        "5. Confirm the message appears in the conversation as sent (a check mark "
        "appears under it), then finish and report that the inquiry was sent."
    )


def _browser_task(req: ContactRequest, message: str) -> str:
    return (
        "You are operating WhatsApp Web in a real Chrome on this machine. Open "
        "https://web.whatsapp.com; if a QR/login screen shows, report blocked and "
        f"stop. Open the chat for {req.contact_name or req.whatsapp_number}, type "
        f"exactly: \"{message}\", send it, confirm it shows as sent, and finish."
    )


def _http_delete_session(hai_session_id: str) -> None:
    key = _hai_key()
    if not key or not hai_session_id:
        return
    req = urllib.request.Request(
        f"{BASE_URL}/sessions/{hai_session_id}", method="DELETE",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def _cancel_record(rec: dict[str, Any]) -> None:
    """R1: cancel via the persisted handle, falling back to DELETE /sessions/{id}."""
    handle = rec.get("_handle")
    fn = getattr(handle, "cancel", None) if handle is not None else None
    if callable(fn):
        try:
            fn()
            return
        except Exception:
            pass
    _http_delete_session(rec.get("hai_session_id") or "")


def _run_contact_session(session_id: str, req: ContactRequest, message: str, mode: str) -> None:
    rec = SESSIONS[session_id]
    global _active_desktop_session
    try:
        client = Client()

        if mode == "desktop":
            if USE_DEEPLINK:
                open_whatsapp_chat(req.whatsapp_number, message)
                _add_event(rec, f"Opened WhatsApp to {req.whatsapp_number} (deep link, prefilled)")
                time.sleep(1.5)  # let the app foreground before the first screenshot
            env = {"id": "my-mac", "kind": "desktop", "host": "user_device"}
            desc = "Drives the WhatsApp desktop app on my Mac to send a rental inquiry."
            task = _desktop_task(req, message)
        else:
            env = {"id": "my-laptop", "kind": "web", "host": "user_device"}
            desc = "Drives WhatsApp Web in a browser on my machine to send a rental inquiry."
            task = _browser_task(req, message)

        _add_event(rec, f"Creating {mode} agent (host=user_device)")
        agent = client.agents.create_agent(
            name=f"whatsapp-{mode}-{session_id[:8]}",
            description=desc,
            instructions=(
                "Ground every action in what you actually see. Never invent contacts "
                "or messages. If blocked (login wall, permissions) or the contact is "
                "not found, say so plainly and stop."
            ),
            environments=[env],
        )

        _add_event(rec, "Starting H session")
        start_session = getattr(client, "start_session", None)
        messages = [{"type": "user_message", "message": task}]

        if callable(start_session):
            # R2: pass the doc-correct soft cap; retry without it if the SDK rejects it.
            try:
                handle = start_session(agent=agent, messages=messages, max_time_s=MAX_TIME_S)
            except TypeError:
                handle = start_session(agent=agent, messages=messages)
            hid = _extract(handle, "id", "session_id")
            with _LOCK:
                rec["_handle"] = handle
                rec["hai_session_id"] = hid
                rec["agent_view_url"] = _extract(handle, "agent_view_url") or (
                    f"https://platform.hcompany.ai/agents/sessions/{hid}" if hid else None
                )
            _add_event(rec, f"H session started (id={hid})")

            # R2: hard watchdog — the cap is soft (asks for a final answer, does not
            # kill), so force-cancel past the grace window to free the slot.
            threading.Timer(MAX_TIME_S + WATCHDOG_GRACE_S, lambda: _cancel_record(rec)).start()

            _stream_handle(rec, handle)
        else:
            _add_event(rec, "SDK has no start_session; blocking run_session")
            try:
                result = client.run_session(agent=agent, messages=messages, max_time_s=MAX_TIME_S)
            except TypeError:
                result = client.run_session(agent=agent, messages=messages)
            _finalize_from_result(rec, result)

    except Exception as exc:
        with _LOCK:
            rec["status"] = "failed"
            rec["error"] = f"{type(exc).__name__}: {exc}"
        _add_event(rec, f"Error: {rec['error']}")
    finally:
        if mode == "desktop":
            with _LOCK:
                if _active_desktop_session == session_id:
                    _active_desktop_session = None
            if _DESKTOP_BUSY.locked():
                try:
                    _DESKTOP_BUSY.release()
                except RuntimeError:
                    pass


def _note_outcome(rec: dict[str, Any], outcome: Any) -> None:
    # R5: surface blocked/infeasible as soon as they appear, not only at settle.
    if isinstance(outcome, str) and outcome and rec.get("_outcome_seen") != outcome:
        rec["_outcome_seen"] = outcome
        human = {
            "blocked": "Blocked — login wall / missing permissions",
            "infeasible": "Infeasible — contact not found or task impossible",
            "partial": "Partial completion",
            "success": "Success",
        }.get(outcome, f"outcome: {outcome}")
        _add_event(rec, human)


def _stream_handle(rec: dict[str, Any], handle: Any) -> None:
    with _LOCK:
        rec["status"] = "running"
    streamed = False
    stream = getattr(handle, "stream", None)
    if callable(stream):
        try:
            for event in stream():
                _add_event(rec, _event_to_text(event))
                st = _extract(event, "status")
                if isinstance(st, str):
                    with _LOCK:
                        rec["status"] = st
                _note_outcome(rec, _extract(event, "outcome"))
            streamed = True
        except Exception as exc:
            _add_event(rec, f"Stream ended: {type(exc).__name__}: {exc}")
    if not streamed:
        _poll_changes(rec, handle)

    result = None
    for meth in ("wait_for_completion", "get"):
        fn = getattr(handle, meth, None)
        if callable(fn):
            try:
                result = fn()
                break
            except Exception:
                continue
    _finalize_from_result(rec, result)


def _poll_changes(rec: dict[str, Any], handle: Any) -> None:
    changes = getattr(handle, "changes", None)
    if not callable(changes):
        return
    from_index = 0
    terminal = {"completed", "failed", "timed_out", "interrupted", "cancelled"}
    while True:
        try:
            batch = changes(from_index=from_index)
        except Exception as exc:
            _add_event(rec, f"changes() error: {type(exc).__name__}: {exc}")
            return
        if batch is None:
            continue
        new_events = _extract(batch, "new_events", "events") or []
        for event in new_events:
            _add_event(rec, _event_to_text(event))
            _note_outcome(rec, _extract(event, "outcome"))
        from_index += len(new_events)
        st = _extract(batch, "status")
        if isinstance(st, str):
            with _LOCK:
                rec["status"] = st
            if st in terminal:
                return


def _finalize_from_result(rec: dict[str, Any], result: Any) -> None:
    status = _extract(result, "status") or rec.get("status") or "completed"
    answer = _extract(result, "answer", "latest_answer")
    outcome = _extract(result, "outcome")
    error = _extract(result, "error")
    error_code = _extract(result, "error_code")
    with _LOCK:
        rec["status"] = status if isinstance(status, str) else rec.get("status", "completed")
        if answer is not None:
            rec["answer"] = answer
        if outcome is not None:
            rec["outcome"] = outcome
        if error:
            rec["error"] = error
        if error_code:
            rec["error_code"] = error_code
    _note_outcome(rec, outcome)
    _add_event(rec, f"Session settled: status={rec['status']} outcome={rec.get('outcome')}")


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
def _perm_state() -> dict[str, Any]:
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
    return {"accessibility": ax, "screen_recording": sr}


@app.get("/health")
def health() -> dict[str, Any]:
    whatsapp = os.path.exists("/Applications/WhatsApp.app")
    perms = _perm_state()  # evaluated in THIS (service) process's TCC context
    return {
        "ok": True,
        "mode": CONTACT_MODE,
        "hai_key_present": _hai_key() is not None,
        "hai_sdk_installed": Client is not None,
        "hai_import_error": HAI_IMPORT_ERROR,
        "whatsapp_installed": whatsapp,
        "accessibility": perms["accessibility"],
        "screen_recording": perms["screen_recording"],
        "desktop_ready": bool(whatsapp and perms["accessibility"] and perms["screen_recording"]),
        "desktop_busy": _active_desktop_session is not None,
    }


@app.post("/contact")
def contact(req: ContactRequest) -> dict[str, str]:
    if Client is None:
        raise HTTPException(status_code=400, detail='hai-agents not installed. pip install "hai-agents[browser,desktop]".')
    if _hai_key() is None:
        raise HTTPException(status_code=400, detail="HAI_API_KEY not set (see .env.example).")

    mode = (req.mode or CONTACT_MODE).lower()
    global _active_desktop_session

    if mode == "desktop":
        # R3: only one local desktop session at a time.
        if not _DESKTOP_BUSY.acquire(blocking=False):
            raise HTTPException(status_code=409, detail="A desktop contact session is already running. Try again when it finishes.")

    session_id = str(uuid.uuid4())
    message = _build_inquiry(req)
    SESSIONS[session_id] = {
        "session_id": session_id, "mode": mode, "status": "pending", "events": [],
        "answer": None, "outcome": None, "reply": None, "error": None,
        "hai_session_id": None, "agent_view_url": None, "_handle": None,
        "request": req.model_dump(), "message": message, "created_at": _now(),
    }
    if mode == "desktop":
        _active_desktop_session = session_id
    _add_event(SESSIONS[session_id], f"Queued {mode} contact to {req.contact_name or req.whatsapp_number}")

    threading.Thread(target=_run_contact_session, args=(session_id, req, message, mode), daemon=True).start()
    return {"session_id": session_id}


@app.get("/contact/{session_id}")
def contact_status(session_id: str) -> dict[str, Any]:
    rec = SESSIONS.get(session_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    with _LOCK:
        return {
            "status": rec["status"], "events": list(rec["events"]),
            "answer": rec.get("answer"), "outcome": rec.get("outcome"),
            "error": rec.get("error"), "agent_view_url": rec.get("agent_view_url"),
            "hai_session_id": rec.get("hai_session_id"), "mode": rec.get("mode"),
        }


@app.post("/contact/{session_id}/cancel")
def cancel_session(session_id: str) -> dict[str, Any]:
    rec = SESSIONS.get(session_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    _cancel_record(rec)
    with _LOCK:
        rec["status"] = "interrupted"
    _add_event(rec, "Cancelled by user")
    return {"ok": True, "status": "interrupted"}


@app.get("/contact/{session_id}/reply")
def get_reply(session_id: str) -> dict[str, Optional[str]]:
    rec = SESSIONS.get(session_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    with _LOCK:
        return {"reply": rec.get("reply")}


@app.post("/contact/{session_id}/reply")
def inject_reply(session_id: str, body: ReplyInject) -> dict[str, Any]:
    rec = SESSIONS.get(session_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    with _LOCK:
        rec["reply"] = body.reply
    _add_event(rec, f"Owner reply received: {body.reply}")
    return {"ok": True, "session_id": session_id, "reply": body.reply}


@app.on_event("shutdown")
def _shutdown() -> None:
    for rec in list(SESSIONS.values()):
        if rec.get("status") not in ("completed", "failed", "interrupted", "timed_out", "cancelled"):
            _cancel_record(rec)

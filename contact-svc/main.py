"""
ApartmentAgent — CONTACT service.

An H Computer-Use Agent drives WhatsApp Web in a real Chrome on THIS laptop
(local browser control) to send a polite rental inquiry to an apartment owner,
and this FastAPI app watches the run live and exposes the reply path.

H integration is written against the official docs (local browser control):
  https://hub.hcompany.ai/computer-use-agents/browser/local-control
Local browser control is Python-SDK-only: an agent whose web environment sets
host="user_device". The SDK attaches to a Chrome with remote-debugging on port
9222, or launches one with profile ~/.hai/chrome-profile (logins persist).

Run:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

# ---------------------------------------------------------------------------
# H SDK — imported lazily / defensively so the service still boots (and /health
# still reports) even when hai-agents is not installed in the environment.
# ---------------------------------------------------------------------------
try:
    from hai_agents import Client  # type: ignore

    HAI_IMPORT_ERROR: Optional[str] = None
except Exception as exc:  # pragma: no cover - depends on install state
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

# In-memory session store. session_id -> record.
# Not persisted; fine for a hackathon single-process demo.
SESSIONS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class ContactRequest(BaseModel):
    whatsapp_number: str
    listing_title: str
    dates: str
    headcount: int
    budget: int


class ReplyInject(BaseModel):
    reply: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now() -> float:
    return time.time()


def _hai_key() -> Optional[str]:
    return os.getenv("HAI_API_KEY") or None


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


def _build_task(req: ContactRequest, message: str) -> str:
    """The natural-language task the H agent executes in the local browser."""
    return (
        "You are operating WhatsApp Web in a real Chrome on this machine. "
        "Do the following, one step at a time, and stop after the message is sent.\n"
        "1. Open https://web.whatsapp.com and wait until the chat list is loaded. "
        "If a QR / login screen is shown, report that you are blocked and stop.\n"
        f"2. Open the chat with the phone number {req.whatsapp_number}. "
        "Use the search box at the top of the chat list, type the number, and open "
        "the matching contact. If no existing chat matches, open a new chat with that number.\n"
        "3. Click the message input box at the bottom and type EXACTLY this message:\n"
        f"{message}\n"
        "4. Send the message (press Enter or click the send button).\n"
        "5. Confirm the message appears as sent in the conversation, then finish and "
        "report that the inquiry was sent."
    )


def _extract(obj: Any, *names: str) -> Any:
    """Read the first present attribute or dict key from a result/status object."""
    for name in names:
        if obj is None:
            return None
        if isinstance(obj, dict) and name in obj:
            return obj[name]
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _event_to_text(event: Any) -> str:
    """Best-effort human-readable line for one H event, across SDK shapes."""
    etype = _extract(event, "type", "kind") or "event"
    # Common fields that may carry human-readable content.
    for field in ("message", "text", "thought", "content", "action", "summary"):
        val = _extract(event, field)
        if isinstance(val, str) and val.strip():
            return f"{etype}: {val.strip()}"
    return str(etype)


# ---------------------------------------------------------------------------
# Background worker: runs one local-browser H session and streams its events
# into the in-memory record. Adapts to whatever the installed SDK exposes.
# ---------------------------------------------------------------------------
def _run_contact_session(session_id: str, req: ContactRequest, message: str) -> None:
    rec = SESSIONS[session_id]
    try:
        client = Client()  # picks up HAI_API_KEY from env
        _add_event(rec, "Creating local-browser agent (host=user_device)")

        agent = client.agents.create_agent(
            name=f"whatsapp-contact-{session_id[:8]}",
            description="Drives WhatsApp Web in a browser on my own machine to send a rental inquiry.",
            instructions=(
                "Operate the real browser on this machine. Ground every action in what "
                "you actually see on screen. Do not invent contacts or messages. If you "
                "hit a login/QR wall or cannot find the contact, say so plainly and stop."
            ),
            environments=[{"id": "my-laptop", "kind": "web", "host": "user_device"}],
        )

        task = _build_task(req, message)
        _add_event(rec, "Starting H session (opening WhatsApp Web locally)")

        # Preferred path: start_session -> handle we can stream live.
        # Fallback: blocking run_session in this same thread.
        start_session = getattr(client, "start_session", None)

        if callable(start_session):
            handle = start_session(
                agent=agent,
                messages=[{"type": "user_message", "message": task}],
            )
            hid = _extract(handle, "id", "session_id")
            with _LOCK:
                rec["hai_session_id"] = hid
                rec["agent_view_url"] = _extract(handle, "agent_view_url")
            _add_event(rec, f"H session started (id={hid})")

            _stream_handle(rec, handle)
        else:
            _add_event(rec, "SDK has no start_session; using blocking run_session")
            result = client.run_session(
                agent=agent,
                messages=[{"type": "user_message", "message": task}],
            )
            _finalize_from_result(rec, result)

    except Exception as exc:  # keep the endpoint contract stable
        with _LOCK:
            rec["status"] = "failed"
            rec["error"] = f"{type(exc).__name__}: {exc}"
        _add_event(rec, f"Error: {rec['error']}")


def _stream_handle(rec: dict[str, Any], handle: Any) -> None:
    """Consume the live event feed of a session handle, then read the answer."""
    with _LOCK:
        rec["status"] = "running"

    streamed = False
    stream = getattr(handle, "stream", None)
    if callable(stream):
        try:
            for event in stream():  # yields events until the session settles
                _add_event(rec, _event_to_text(event))
                status = _extract(event, "status")
                if isinstance(status, str):
                    with _LOCK:
                        rec["status"] = status
            streamed = True
        except Exception as exc:
            _add_event(rec, f"Stream ended: {type(exc).__name__}: {exc}")

    if not streamed:
        # Manual long-poll loop via changes(from_index=...) as a fallback.
        _poll_changes(rec, handle)

    # Settle: read the final answer/outcome off the completed session.
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
            continue  # 204 no-content, keep waiting
        new_events = _extract(batch, "new_events", "events") or []
        for event in new_events:
            _add_event(rec, _event_to_text(event))
        from_index += len(new_events)
        status = _extract(batch, "status")
        if isinstance(status, str):
            with _LOCK:
                rec["status"] = status
            if status in terminal:
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
    _add_event(rec, f"Session settled: status={rec['status']} outcome={rec.get('outcome')}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "hai_key_present": _hai_key() is not None,
        "hai_sdk_installed": Client is not None,
        "hai_import_error": HAI_IMPORT_ERROR,
    }


@app.post("/contact")
def contact(req: ContactRequest) -> dict[str, str]:
    if Client is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "hai-agents SDK is not installed. Run: "
                'pip install "hai-agents[browser]" (see requirements.txt / README).'
            ),
        )
    if _hai_key() is None:
        raise HTTPException(
            status_code=400,
            detail="HAI_API_KEY is not set. Put it in .env (see .env.example) or export it.",
        )

    session_id = str(uuid.uuid4())
    message = _build_inquiry(req)
    SESSIONS[session_id] = {
        "session_id": session_id,
        "status": "pending",
        "events": [],
        "answer": None,
        "outcome": None,
        "reply": None,
        "error": None,
        "hai_session_id": None,
        "agent_view_url": None,
        "request": req.model_dump(),
        "message": message,
        "created_at": _now(),
    }
    _add_event(SESSIONS[session_id], f"Queued contact to {req.whatsapp_number}")

    thread = threading.Thread(
        target=_run_contact_session,
        args=(session_id, req, message),
        daemon=True,
    )
    thread.start()

    return {"session_id": session_id}


@app.get("/contact/{session_id}")
def contact_status(session_id: str) -> dict[str, Any]:
    rec = SESSIONS.get(session_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    with _LOCK:
        return {
            "status": rec["status"],
            "events": list(rec["events"]),
            "answer": rec.get("answer"),
            "outcome": rec.get("outcome"),
            "error": rec.get("error"),
            "agent_view_url": rec.get("agent_view_url"),
            "hai_session_id": rec.get("hai_session_id"),
        }


@app.get("/contact/{session_id}/reply")
def get_reply(session_id: str) -> dict[str, Optional[str]]:
    """
    Best-effort: has the owner replied?

    Reading the latest incoming WhatsApp message live is unreliable (it needs a
    second browser session and precise DOM reading), so the robust demo path is
    a manual/poll hook: POST /contact/{session_id}/reply injects the reply text
    (the owner-side, a poller, or you during the demo call it). This GET returns
    whatever reply has been recorded, or null if none yet.
    """
    rec = SESSIONS.get(session_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    with _LOCK:
        return {"reply": rec.get("reply")}


@app.post("/contact/{session_id}/reply")
def inject_reply(session_id: str, body: ReplyInject) -> dict[str, Any]:
    """Inject the owner's reply so the demo notification can fire."""
    rec = SESSIONS.get(session_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    with _LOCK:
        rec["reply"] = body.reply
    _add_event(rec, f"Owner reply received: {body.reply}")
    return {"ok": True, "session_id": session_id, "reply": body.reply}

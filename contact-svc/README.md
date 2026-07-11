# ApartmentAgent — Contact Service

A tiny FastAPI service for the **CONTACT** step of ApartmentAgent. An
[H Computer-Use Agent](https://hub.hcompany.ai/computer-use-agents/browser/local-control)
drives **WhatsApp Web in a real Chrome on your own laptop** (local browser
control) to send a polite rental inquiry to an apartment owner. The app watches
the run live and exposes the reply path so a demo notification can fire.

Local browser control is **Python-SDK-only**: the agent's web environment sets
`host="user_device"`, and the `hai-agents[browser]` extra provides the
`hai-drivers` local driver that connects your Chrome to H.

## Setup

```bash
cd contact-svc
pip install -r requirements.txt
cp .env.example .env
# put your key in .env:  HAI_API_KEY=hk-...
```

### Log WhatsApp Web into the Chrome the agent will drive

The SDK attaches to a Chrome with remote debugging on **port 9222**. If none is
running, it launches one with its own profile at **`~/.hai/chrome-profile`**,
which **persists across runs** — so you log in to WhatsApp once and the agent
finds you signed in next time. Your everyday Chrome profile is never touched
(Chrome refuses remote debugging on it).

You have two options:

1. **Let the SDK launch Chrome** the first time, then scan the WhatsApp Web QR
   code in that window with your phone. The `~/.hai/chrome-profile` keeps the
   session for later runs.

2. **Pre-launch your own dedicated Chrome** and log in once (recommended for the
   demo, so you control the window):

   ```bash
   # macOS
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-for-agents"
   ```

   Chrome only opens the debugging port on a profile passed with
   `--user-data-dir`, so keep this dedicated directory for the logins the agent
   should have. Open `https://web.whatsapp.com`, scan the QR once, and leave it
   running. The SDK attaches to this instance instead of launching its own.

### Run the API

```bash
uvicorn main:app --reload --port 8000
```

CORS is open to `http://localhost:3000` for the frontend.

## Endpoints

| Method | Path                          | Purpose |
| ------ | ----------------------------- | ------- |
| `GET`  | `/health`                     | `{ok, hai_key_present, hai_sdk_installed, hai_import_error}` |
| `POST` | `/contact`                    | Start a local-browser H session that messages the owner. Returns `{session_id}` immediately. |
| `GET`  | `/contact/{session_id}`       | Live status: `{status, events:[{step,text,ts}], answer, outcome, agent_view_url, ...}` |
| `GET`  | `/contact/{session_id}/reply` | `{reply: str|null}` — the owner's reply, or null if none yet |
| `POST` | `/contact/{session_id}/reply` | Inject the owner's reply text: `{reply: "..."}` |

### `POST /contact`

```json
{
  "whatsapp_number": "+15551234567",
  "listing_title": "Sunny 2BR near the park",
  "dates": "Aug 1-7",
  "headcount": 3,
  "budget": 1200
}
```

The agent opens `https://web.whatsapp.com`, finds/opens the chat for the number,
types and sends:

> Hi! Is '<listing_title>' available for <dates> for <headcount> people? What's the total price? Thanks!

The H session runs in a background thread, so `POST /contact` returns
`{session_id}` right away. Poll `GET /contact/{session_id}` to watch it work.

## How live events are surfaced

The background worker prefers `client.start_session(...)`, which returns a
session handle, and consumes its **live event feed** via `handle.stream()`
(the SDK's long-poll loop over `changes`). Each event is appended to an
in-memory `events` list as `{step, text, ts}`, which `GET /contact/{id}` returns.
If `stream()` isn't available it falls back to a manual `handle.changes(from_index=...)`
long-poll loop; if `start_session` itself isn't available it falls back to the
blocking `client.run_session(...)` (run inside the same background thread) and
surfaces the final answer/outcome. When the session settles, the final `answer`,
`outcome`, and any `error_code` are read off the result. The record also stores
the H `agent_view_url` so you can watch the run in Agent View on the H Platform.

> The code reads SDK fields **defensively** (attribute-or-dict, multiple candidate
> names) so it adapts to the installed SDK's actual surface rather than assuming
> one exact shape.

## How the reply / notification path works

Reading the owner's latest **incoming** WhatsApp message live is unreliable (it
needs a second browser session and precise DOM reading), so the robust path is a
**manual/poll hook**:

- `POST /contact/{session_id}/reply` with `{"reply": "..."}` injects the reply
  text. The owner-side, a poller, or you during the demo call it, and it records
  the reply plus an event so a notification can fire.
- `GET /contact/{session_id}/reply` returns `{reply: ...}` (or `null`), which a
  frontend can poll to show "Owner replied!".

This keeps the demo robust: the send path is fully automated by H, and the reply
path has a dependable injection hook instead of depending on flaky live reads.

## Ethics

Only message a **consenting teammate's** number. This drives real WhatsApp on
your machine and sends real messages — do not contact strangers or real listing
owners without consent.

#!/usr/bin/env bash
#
# sweep-h-sessions.sh — Free the H (hcompany) 3-session concurrency cap before a demo.
#
# Lists the org's H sessions and DELETEs any still in a non-terminal state
# (running / idle / pending / paused / awaiting_tool_results), then prints the
# remaining /sessions/quota so you can confirm you have headroom.
#
# Reads HAI_API_KEY from ~/.hcompany/credentials.
# Usage:  scripts/sweep-h-sessions.sh
#
set -euo pipefail

BASE="${HAI_BASE:-https://agp.eu.hcompany.ai/api/v2}"
CRED_FILE="${HOME}/.hcompany/credentials"

# --- load the API key ------------------------------------------------------
if [[ ! -f "$CRED_FILE" ]]; then
  echo "ERROR: credentials file not found at $CRED_FILE" >&2
  exit 1
fi
# Accept either  HAI_API_KEY=xxx  or  HAI_API_KEY = "xxx"  formatting.
HAI_API_KEY="$(grep -E '^[[:space:]]*HAI_API_KEY' "$CRED_FILE" \
  | head -n1 \
  | sed -E 's/^[[:space:]]*HAI_API_KEY[[:space:]]*=[[:space:]]*//; s/^["'"'"']//; s/["'"'"'][[:space:]]*$//')"

if [[ -z "${HAI_API_KEY:-}" ]]; then
  echo "ERROR: HAI_API_KEY not found in $CRED_FILE" >&2
  exit 1
fi

# Requires jq for JSON parsing.
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required but not installed." >&2
  exit 1
fi

AUTH=(-H "Authorization: Bearer ${HAI_API_KEY}" -H "Accept: application/json")

# Non-terminal states that hold a concurrency slot.
NON_TERMINAL="running idle pending paused awaiting_tool_results"

is_non_terminal() {
  local st="$1"
  for n in $NON_TERMINAL; do
    [[ "$st" == "$n" ]] && return 0
  done
  return 1
}

echo "==> Listing H sessions ($BASE/sessions?limit=30)"
SESSIONS_JSON="$(curl -sS "${AUTH[@]}" "${BASE}/sessions?limit=30")"

# Sessions may be returned as a bare array or under a 'sessions'/'data'/'items' key.
ROWS="$(printf '%s' "$SESSIONS_JSON" | jq -c '
  (if type=="array" then . else (.sessions // .data // .items // []) end)[]
  | {id: (.id // .session_id // .sessionId), status: (.status // .state // "unknown")}
' 2>/dev/null || true)"

if [[ -z "$ROWS" ]]; then
  echo "No sessions found (or unexpected response shape). Raw response:"
  printf '%s\n' "$SESSIONS_JSON"
else
  CANCELLED=0
  while IFS= read -r row; do
    [[ -z "$row" ]] && continue
    id="$(printf '%s' "$row" | jq -r '.id')"
    status="$(printf '%s' "$row" | jq -r '.status')"
    [[ -z "$id" || "$id" == "null" ]] && continue
    if is_non_terminal "$status"; then
      echo "   - cancelling session $id (status=$status)"
      code="$(curl -sS -o /dev/null -w '%{http_code}' -X DELETE "${AUTH[@]}" "${BASE}/sessions/${id}" || echo "ERR")"
      echo "       DELETE -> HTTP $code"
      CANCELLED=$((CANCELLED + 1))
    else
      echo "   - keeping   session $id (status=$status, terminal)"
    fi
  done <<< "$ROWS"
  echo "==> Cancelled $CANCELLED non-terminal session(s)."
fi

echo "==> Remaining quota ($BASE/sessions/quota)"
curl -sS "${AUTH[@]}" "${BASE}/sessions/quota" | jq . 2>/dev/null \
  || curl -sS "${AUTH[@]}" "${BASE}/sessions/quota"
echo

# scripts

Operational helpers for ApartmentAgent.

- **`sweep-h-sessions.sh`** — Before a demo, cancels any non-terminal H
  (hcompany) sessions to free the 3-session concurrency cap, then prints the
  remaining `/sessions/quota`. Reads `HAI_API_KEY` from `~/.hcompany/credentials`.
  Run: `scripts/sweep-h-sessions.sh` (requires `jq`).
- **`test-hai.mjs`** — Ad-hoc HAI API smoke test.

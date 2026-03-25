#!/bin/bash
# Usato da LaunchAgent (PATH ridotto rispetto al Terminale).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  exec "$ROOT/.venv/bin/python3" "$ROOT/run_web.py"
fi
if [[ -x "$ROOT/venv/bin/python3" ]]; then
  exec "$ROOT/venv/bin/python3" "$ROOT/run_web.py"
fi
exec python3 "$ROOT/run_web.py"

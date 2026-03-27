#!/bin/bash
# Entry point: run_web.py (unico launcher documentato). Usato da LaunchAgent (PATH ridotto).
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Imposta GENSHIN_WEB_WRITE_PASSWORD nel plist LaunchAgent o in environment del sistema.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  exec "$ROOT/.venv/bin/python3" "$ROOT/run_web.py"
fi
if [[ -x "$ROOT/venv/bin/python3" ]]; then
  exec "$ROOT/venv/bin/python3" "$ROOT/run_web.py"
fi
exec python3 "$ROOT/run_web.py"

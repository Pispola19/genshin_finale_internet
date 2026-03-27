#!/bin/bash
# Avvio: solo run_web.py (README.md). Stesso comportamento di «Genshin Manager — progetto.command».
# La cartella del progetto è sempre quella che contiene questo file e run_web.py (nessun percorso fisso nel repo).
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/run_web.py" ]]; then
  ROOT="$SCRIPT_DIR"
elif [[ -n "${GENSHIN_PROJECT_ROOT:-}" ]] && [[ -f "${GENSHIN_PROJECT_ROOT}/run_web.py" ]]; then
  ROOT="$GENSHIN_PROJECT_ROOT"
else
  echo "Errore: run_web.py non trovato." >&2
  echo "  • Metti questo .command nella cartella del progetto (accanto a run_web.py), oppure" >&2
  echo "  • export GENSHIN_PROJECT_ROOT=/percorso/del/progetto" >&2
  exit 1
fi
cd "$ROOT"
# Obbligatorio: stessa password usata per login su login.html (non committare valori reali).
# export GENSHIN_WEB_WRITE_PASSWORD='...'
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  PYTHON="$ROOT/.venv/bin/python3"
elif [[ -x "$ROOT/venv/bin/python3" ]]; then
  PYTHON="$ROOT/venv/bin/python3"
else
  PYTHON="python3"
fi
echo "Genshin Manager — $ROOT"
exec "$PYTHON" "$ROOT/run_web.py"

#!/bin/bash
# Genshin Manager — avvio via run_web.py (vedi README.md). Doppio clic su macOS.
#
# Risoluzione percorso (in ordine):
# 1) Stessa cartella del .command → run_web.py accanto allo script
# 2) Variabile GENSHIN_PROJECT_ROOT → punta alla root del repo (dove c’è run_web.py)
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/run_web.py" ]]; then
  ROOT="$SCRIPT_DIR"
elif [[ -n "${GENSHIN_PROJECT_ROOT:-}" ]] && [[ -f "${GENSHIN_PROJECT_ROOT}/run_web.py" ]]; then
  ROOT="$GENSHIN_PROJECT_ROOT"
else
  osascript -e 'display alert "Genshin Manager" message "Non trovo run_web.py.\n\n• Sposta questo file nella cartella del progetto (accanto a run_web.py), oppure\n• imposta GENSHIN_PROJECT_ROOT sul percorso della repo.\n\nNome consigliato della cartella: genshin_manager (vedi README)." as critical' 2>/dev/null || echo "Errore: run_web.py non trovato" >&2
  exit 1
fi
cd "$ROOT"
# Obbligatorio: export GENSHIN_WEB_WRITE_PASSWORD='...' (vedi README.md)
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

if [[ -x "$ROOT/.venv/bin/python3" ]]; then
  PYTHON="$ROOT/.venv/bin/python3"
elif [[ -x "$ROOT/venv/bin/python3" ]]; then
  PYTHON="$ROOT/venv/bin/python3"
else
  PYTHON="python3"
fi

echo "Genshin Manager — cartella: $ROOT"
echo "Python: $PYTHON"
echo ""
exec "$PYTHON" "$ROOT/run_web.py"

#!/bin/bash
# Genshin Manager — avvio server web (doppio clic per aprire in Terminale).
# Avvio automatico all’accesso: vedi istruzioni sotto o usa mac/com.genshinmanager.web.plist

set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"

if [[ -x "$DIR/.venv/bin/python3" ]]; then
  PYTHON="$DIR/.venv/bin/python3"
elif [[ -x "$DIR/venv/bin/python3" ]]; then
  PYTHON="$DIR/venv/bin/python3"
else
  PYTHON="python3"
fi

echo "Genshin Manager — cartella: $DIR"
echo "Python: $PYTHON"
echo ""
echo "Per avvio automatico all’accesso:"
echo "  Opzione A — Elementi di apertura: Impostazioni di Sistema → Generale → Accesso → Elementi di apertura"
echo "            → + → scegli questo file: $DIR/Genshin_Manager.command"
echo "  Opzione B — LaunchAgent: cp mac/com.genshinmanager.web.plist ~/Library/LaunchAgents/"
echo "            poi: launchctl bootstrap gui/\$(id -u) ~/Library/LaunchAgents/com.genshinmanager.web.plist"
echo ""

exec "$PYTHON" run_web.py

#!/bin/bash
# Genera ~/Library/LaunchAgents/com.genshinmanager.web.plist con il percorso
# **attuale** della repo (qualunque sia il nome della cartella).
#
# Uso: dalla root del progetto — bash mac/install_launchagent.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMPLATE="$SCRIPT_DIR/com.genshinmanager.web.plist.template"
PLIST_NAME="com.genshinmanager.web.plist"
OUT_DIR="${HOME}/Library/LaunchAgents"
OUT_PLIST="$OUT_DIR/$PLIST_NAME"

if [[ ! -f "$REPO_ROOT/run_web.py" ]]; then
  echo "Errore: run_web.py non trovato in $REPO_ROOT (esegui lo script dalla repo)." >&2
  exit 1
fi
if [[ ! -f "$TEMPLATE" ]]; then
  echo "Errore: template mancante: $TEMPLATE" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
GENSHIN_INSTALL_ROOT="$REPO_ROOT" perl -pe 's/__PROJECT_ROOT__/$ENV{GENSHIN_INSTALL_ROOT}/g' "$TEMPLATE" > "$OUT_PLIST.tmp"
mv "$OUT_PLIST.tmp" "$OUT_PLIST"

echo "OK: $OUT_PLIST"
echo "Carica o ricarica l'agent:"
echo "  launchctl bootout gui/\$(id -u) \"$OUT_PLIST\" 2>/dev/null || true"
echo "  launchctl bootstrap gui/\$(id -u) \"$OUT_PLIST\""
echo "(oppure: disconnetti sessione dopo la prima installazione.)"

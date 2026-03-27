"""Entry point deprecato: l’app si avvia solo tramite il server web.

Il punto di ingresso ufficiale è ``run_web.py`` (Flask). Questo file reindirizza lì
per evitare avvii accidentali della vecchia GUI Tk, ormai non più supportata come entry point.

Uso consigliato::

    python3 run_web.py

Poi apri nel browser l’URL mostrato in console.

Codici di uscita anticipata (prima che parta Flask): 1 = ``run_web.py`` assente, 2 = porta non disponibile.

Pausa 2 secondi prima di avviare Flask (per leggere l’avviso su stderr); disattiva con ``GENSHIN_MAIN_NO_SLEEP=1``.
"""

from __future__ import annotations

import logging
import os
import runpy
import sys
import time
from pathlib import Path

_DEPRECATED = (
    "\n*** ATTENZIONE: main.py è deprecato — entry point ufficiale: python3 run_web.py ***\n"
)

_LOG = logging.getLogger("genshin_manager.main")

_EXIT_RUNWEB_MISSING = 1
_EXIT_PORT_FAILED = 2


def main() -> None:
    try:
        from logging_config import setup_logging

        setup_logging()
    except Exception:
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s %(name)s %(message)s",
            stream=sys.stderr,
        )

    print(_DEPRECATED, file=sys.stderr)
    root = Path(__file__).resolve().parent
    run_web = root / "run_web.py"
    if not run_web.is_file():
        print(f"Errore: run_web.py non trovato in {root}", file=sys.stderr)
        _LOG.error("run_web_missing path=%s", run_web)
        sys.exit(_EXIT_RUNWEB_MISSING)

    try:
        from run_web import local_base_url, resolve_listen_port
    except ImportError as e:
        print(f"Errore import run_web: {e}", file=sys.stderr)
        _LOG.exception("import_run_web_failed")
        sys.exit(_EXIT_RUNWEB_MISSING)

    try:
        port = resolve_listen_port()
        base = local_base_url(port=port)
    except (RuntimeError, OSError, ValueError) as e:
        print(f"Errore: impossibile determinare la porta di ascolto: {e}", file=sys.stderr)
        _LOG.error("listen_port_failed: %s", e, exc_info=True)
        sys.exit(_EXIT_PORT_FAILED)

    print(
        f"*** Server: apri nel browser → {base}/dashboard.html "
        f"(o {base}/personaggio.html ) ***\n",
        file=sys.stderr,
    )
    _LOG.warning(
        "deprecated_entrypoint entrypoint=main.py use_instead=run_web.py local_url=%s listen_port=%s",
        base,
        port,
    )

    if (os.environ.get("GENSHIN_MAIN_NO_SLEEP") or "").strip().lower() not in ("1", "true", "yes"):
        time.sleep(2)

    runpy.run_path(str(run_web), run_name="__main__")


if __name__ == "__main__":
    main()

"""Punto di ingresso ufficiale e unico documentato: server web Genshin Manager (Flask).

Vedi anche README.md nella root del progetto.

In locale: ``python3 run_web.py`` — apri nel browser l’URL stampato (porta da env PORT
o, se libera, 5001+). Su hosting (es. Render) si usa tipicamente gunicorn ``web.app:app``.
"""
import os
import socket
import sys
from typing import Final

_DEFAULT_HOST: Final[str] = "127.0.0.1"


def _port_bindable(p: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", p))
            return True
        except OSError:
            return False


def resolve_listen_port() -> int:
    """
    Porta su cui avvieremo Flask in locale (stessa logica di avvio server).

    - Se ``PORT`` è in env → quel valore (es. PaaS).
    - Altrimenti prima porta libera tra 5001 e 5040.
    """
    env_port = os.environ.get("PORT")
    if env_port is not None and str(env_port).strip():
        return int(env_port)
    base = 5001
    for p in range(base, base + 40):
        if _port_bindable(p):
            return p
    raise RuntimeError(f"Nessuna porta libera tra {base} e {base + 39}")


def local_base_url(*, host: str = _DEFAULT_HOST, port: int | None = None) -> str:
    """URL base per aprire il sito nel browser (senza slash finale)."""
    p = resolve_listen_port() if port is None else port
    return f"http://{host}:{p}"


if __name__ == "__main__":
    from logging_config import setup_logging

    from web.app import app

    log = setup_logging()
    log.getChild("web").info("Avvio server Flask (run_web)")

    port = resolve_listen_port()
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    if port != 5001 and os.environ.get("PORT") is None:
        print(f"Nota: la porta 5001 è occupata, uso la {port}.", file=sys.stderr)
    base = local_base_url(port=port)
    print(f"Apri {base} nel browser (es. {base}/dashboard.html )")
    app.run(debug=debug, host="0.0.0.0", port=port)

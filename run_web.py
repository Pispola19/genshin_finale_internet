"""Avvia l'app web Genshin Manager (Flask). In locale usa PORT da ambiente se presente (come Render)."""
import os
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from web.app import app


def _port_bindable(p: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", p))
            return True
        except OSError:
            return False


def _resolve_port() -> int:
    env_port = os.environ.get("PORT")
    if env_port is not None:
        return int(env_port)
    base = 5001
    for p in range(base, base + 40):
        if _port_bindable(p):
            return p
    raise RuntimeError(f"Nessuna porta libera tra {base} e {base + 39}")


if __name__ == "__main__":
    port = _resolve_port()
    debug = os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    if port != 5001 and os.environ.get("PORT") is None:
        print(f"Nota: la porta 5001 è occupata, uso la {port}.", file=sys.stderr)
    print(f"Apri http://127.0.0.1:{port} nel browser")
    app.run(debug=debug, host="0.0.0.0", port=port)

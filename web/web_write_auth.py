"""
Autenticazione sessione web (single-user protetta): una sola password condivisa.

- **Locale**: se ``GENSHIN_WEB_WRITE_PASSWORD`` non è impostata, le API dati sono accessibili senza login
  (nessun cookie richiesto). Su Render / se ``GENSHIN_WEB_FORCE_PASSWORD=1``, la password è obbligatoria
  all’avvio del server (vedi ``web.app``).
- Con password configurata, serve **lettura e scrittura** tramite sessione valida.
- La password non va nel JavaScript: cookie HttpOnly dopo ``POST /api/auth/login``.
"""
from __future__ import annotations

import hmac
import os
from functools import wraps
from typing import Any, Callable, Optional, Tuple

from flask import jsonify, session


SESSION_WRITE_KEY = "gm_web_write"


def write_password_configured() -> bool:
    """Login web disattivato temporaneamente: API accessibili senza sessione."""
    return False


def session_write_ok() -> bool:
    return session.get(SESSION_WRITE_KEY) is True


def password_matches(attempt: str) -> bool:
    exp = (os.environ.get("GENSHIN_WEB_WRITE_PASSWORD") or "").strip()
    if not exp:
        return False
    a = (attempt or "").encode("utf-8")
    b = exp.encode("utf-8")
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a, b)


def gate_web_session() -> Optional[Tuple[Any, int]]:
    """None se la sessione è autenticata; altrimenti (jsonify(...), 401)."""
    if not write_password_configured():
        return None
    if session_write_ok():
        return None
    return (
        jsonify(
            {
                "error": "Accesso negato: accedi dalla pagina Login.",
                "code": "auth_required",
            }
        ),
        401,
    )


# Alias per compatibilità con codice esistente
gate_write = gate_web_session


def require_web_auth(f: Callable) -> Callable:
    @wraps(f)
    def wrapped(*args, **kwargs):
        denied = gate_web_session()
        if denied:
            return denied
        return f(*args, **kwargs)

    return wrapped


require_write_auth = require_web_auth

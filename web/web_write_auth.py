"""
Protezione scritture web: se è impostata GENSHIN_WEB_WRITE_PASSWORD nel server,
solo le sessioni autenticate possono salvare / importare / eliminare.

La password non va mai nel JavaScript: solo cookie di sessione HttpOnly dopo POST /api/auth/login.
"""
from __future__ import annotations

import hmac
import os
from functools import wraps
from typing import Any, Callable, Optional, Tuple

from flask import jsonify, session


SESSION_WRITE_KEY = "gm_web_write"


def write_password_configured() -> bool:
    return len((os.environ.get("GENSHIN_WEB_WRITE_PASSWORD") or "").strip()) > 0


def session_write_ok() -> bool:
    if not write_password_configured():
        return True
    return session.get(SESSION_WRITE_KEY) is True


def password_matches(attempt: str) -> bool:
    exp = os.environ.get("GENSHIN_WEB_WRITE_PASSWORD") or ""
    if not exp:
        return True
    a = (attempt or "").encode("utf-8")
    b = exp.encode("utf-8")
    if len(a) != len(b):
        return False
    return hmac.compare_digest(a, b)


def gate_write() -> Optional[Tuple[Any, int]]:
    """None se la richiesta può procedere; altrimenti (jsonify(...), 401)."""
    if not write_password_configured():
        return None
    if session_write_ok():
        return None
    return (
        jsonify(
            {
                "error": "Accesso negato: accedi dalla pagina Login (password impostata sul server).",
                "code": "auth_required",
            }
        ),
        401,
    )


def require_write_auth(f: Callable) -> Callable:
    @wraps(f)
    def wrapped(*args, **kwargs):
        denied = gate_write()
        if denied:
            return denied
        return f(*args, **kwargs)

    return wrapped

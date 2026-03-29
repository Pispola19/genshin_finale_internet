"""
Autenticazione sessione web (single-user).

- **Avvio (Render)**: ``GENSHIN_WEB_WRITE_PASSWORD`` può essere obbligatoria all’avvio del processo
  (vedi ``web.app``) senza attivare il login applicativo.
- **Gate applicativo**: si attiva solo se ``GENSHIN_WEB_AUTH_ENABLED=1`` (o ``true`` / ``yes``)
  **e** è impostata ``GENSHIN_WEB_WRITE_PASSWORD``. In quel caso:
  **GET** / **HEAD** / **OPTIONS** restano liberi; **POST** / **PUT** / **PATCH** / **DELETE**
  richiedono sessione (dopo ``POST /api/auth/login``).
- Senza flag o senza password: lettura e scrittura API senza login.
"""

from __future__ import annotations

import hmac
import os
import unicodedata
from functools import wraps
from typing import Any, Callable, FrozenSet, Optional, Tuple

from flask import jsonify, request, session


SESSION_WRITE_KEY = "gm_web_write"

_WRITE_METHODS: FrozenSet[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_SAFE_METHODS: FrozenSet[str] = frozenset({"GET", "HEAD", "OPTIONS"})


def web_auth_enabled() -> bool:
    """
    Gate applicativo (login + protezione scritture) solo se esplicitamente acceso.
    Opt-in stretto: solo 1 / true / yes dopo normalizzazione Unicode (NFKC) e strip.
    Assente, vuoto, 0, false, no, off, disabled, qualsiasi altro valore → spento.
    """
    raw = os.environ.get("GENSHIN_WEB_AUTH_ENABLED")
    if raw is None:
        return False
    v = unicodedata.normalize("NFKC", str(raw)).strip().lower()
    if not v or v in ("0", "false", "no", "off", "disabled"):
        return False
    return v in ("1", "true", "yes")


def write_password_present() -> bool:
    """True se GENSHIN_WEB_WRITE_PASSWORD è non vuota (requisito avvio Render ≠ gate applicativo)."""
    return len((os.environ.get("GENSHIN_WEB_WRITE_PASSWORD") or "").strip()) > 0


def write_password_configured() -> bool:
    """True solo se password presente E GENSHIN_WEB_AUTH_ENABLED esplicitamente attivo (entrambe le condizioni)."""
    if not web_auth_enabled():
        return False
    return write_password_present()


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
    """
    None se la richiesta è consentita.
    Con password configurata, blocca solo i metodi di scrittura senza sessione valida.
    """
    if not write_password_configured():
        return None
    method = (request.method or "GET").upper()
    if method in _SAFE_METHODS or method not in _WRITE_METHODS:
        return None
    if session_write_ok():
        return None
    return (
        jsonify(
            {
                "error": "Accesso negato: per modificare i dati accedi dalla pagina Login.",
                "code": "auth_required",
            }
        ),
        401,
    )


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

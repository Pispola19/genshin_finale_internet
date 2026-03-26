"""
Wrapper per chiamate GUI: evita che eccezioni non gestite chiudano il processo.
Il service layer non viene toccato; gli errori tecnici vanno solo in log.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional, TypeVar

from tkinter import messagebox

logger = logging.getLogger(__name__)

GENERIC_USER_MSG = "Qualcosa non ha funzionato, riprova."

T = TypeVar("T")


def gui_safe_call(
    parent: Any,
    fn: Callable[[], T],
    *,
    generic_message: str = GENERIC_USER_MSG,
) -> Optional[T]:
    """
    Esegue ``fn``; in caso di eccezione mostra un messaggio semplice e ritorna ``None``.
    L’eccezione viene sempre registrata nel log (stack trace).
    """
    try:
        return fn()
    except Exception:
        logger.exception("gui_safe_call")
        try:
            messagebox.showwarning("Attenzione", generic_message, parent=parent)
        except Exception:
            pass
        return None


def notify_unexpected(parent: Any, message: str = GENERIC_USER_MSG) -> None:
    """Solo messaggio utente (dopo un except con log manuale)."""
    try:
        messagebox.showwarning("Attenzione", message, parent=parent)
    except Exception:
        pass

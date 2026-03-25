"""Punto di ingresso - avvia l'applicazione."""
from __future__ import annotations

import os
import sys

from logging_config import setup_logging

_LOG = setup_logging()


def _fatal_error_dialog(title: str, message: str) -> None:
    """Mostra un errore fatale senza creare una seconda root Tk se ne esiste già una."""
    import tkinter as tk
    from tkinter import messagebox

    root = tk._default_root
    if root is None:
        dialog_root = tk.Tk()
        dialog_root.withdraw()
        try:
            messagebox.showerror(title, message, parent=dialog_root)
        finally:
            dialog_root.destroy()
    else:
        messagebox.showerror(title, message, parent=root)


def main() -> None:
    debug = os.environ.get("GENSHIN_DEBUG", "").lower() in ("1", "true", "yes")
    try:
        from gui.app import GenshinApp

        GenshinApp().run()
    except KeyboardInterrupt:
        raise
    except SystemExit:
        raise
    except Exception as e:
        _LOG.exception("Avvio o crash imprevisto della GUI: %s", e)
        if debug:
            raise
        hint = (
            f"{e}\n\n"
            "Traccia completa nel file logs/genshin_manager.log\n"
            "(modalità sviluppo: avvia con GENSHIN_DEBUG=1 per lasciare passare l’eccezione.)"
        )
        _fatal_error_dialog("Errore", hint)
        sys.exit(1)


if __name__ == "__main__":
    main()

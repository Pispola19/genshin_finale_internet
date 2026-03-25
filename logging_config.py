"""Logging centralizzato: file ruotato sotto PROJECT_ROOT/logs e stream (INFO)."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging() -> logging.Logger:
    """Configura una volta il logger ``genshin_manager`` (e figli che propagano)."""
    log = logging.getLogger("genshin_manager")
    if log.handlers:
        return log

    from config import PROJECT_ROOT

    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "genshin_manager.log"

    log.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = RotatingFileHandler(
        log_file,
        maxBytes=1_048_576,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    log.addHandler(fh)

    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    log.addHandler(sh)

    return log

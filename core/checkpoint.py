"""
Checkpoint automatico dei database locali (genshin + artefatti + set utente).

Uso: chiusura GUI, salvataggio (throttle), opzionale atexit sul server web.
Disattiva con GENSHIN_CHECKPOINT=0. Cartella: accanto ai file .db (stesso data root).

Backup via API SQLite ``backup()`` quando possibile; fallback ``copy2``.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import ARTEFATTI_DB_PATH, DB_PATH, PROJECT_ROOT

_last_save_checkpoint_ts: Optional[float] = None


def checkpoint_enabled() -> bool:
    v = (os.environ.get("GENSHIN_CHECKPOINT") or "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def checkpoint_dir() -> Path:
    """Directory che contiene le sottocartelle ``auto-*``."""
    return DB_PATH.parent / "checkpoints"


def max_keep() -> int:
    try:
        n = int((os.environ.get("GENSHIN_CHECKPOINT_MAX") or "12").strip())
        return max(3, min(n, 96))
    except ValueError:
        return 12


def save_throttle_seconds() -> float:
    try:
        return max(30.0, float((os.environ.get("GENSHIN_CHECKPOINT_SAVE_SEC") or "120").strip()))
    except ValueError:
        return 120.0


def _backup_sqlite_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.is_file():
        return
    try:
        src_uri = src.resolve().as_uri()
        ro = sqlite3.connect(f"{src_uri}?mode=ro", uri=True, timeout=15.0)
    except sqlite3.Error:
        shutil.copy2(src, dst)
        return
    try:
        out = sqlite3.connect(dst)
        try:
            ro.backup(out)
        finally:
            out.close()
    finally:
        ro.close()


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _prune_old_run_dirs(root: Path, keep: int) -> None:
    if not root.is_dir():
        return
    dirs: List[Path] = sorted(
        [p for p in root.iterdir() if p.is_dir() and p.name.startswith("auto-")],
        key=lambda p: p.name,
        reverse=True,
    )
    for old in dirs[keep:]:
        try:
            shutil.rmtree(old, ignore_errors=True)
        except OSError:
            pass


def run_automatic_checkpoint(reason: str = "manual") -> Dict[str, Any]:
    """
    Crea una cartella ``checkpoints/auto-YYYYMMDD-HHMMSS`` con copie dei DB (+ JSON set utente).

    ``reason``: \"exit\" | \"save\" | \"server_stop\" | \"manual\" — solo diagnostica nel risultato.
    """
    if not checkpoint_enabled():
        return {"ok": True, "skipped": True, "reason": reason, "message": "GENSHIN_CHECKPOINT disattivato."}

    root = checkpoint_dir()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = root / f"auto-{stamp}"
    errors: List[str] = []
    copied: List[str] = []

    try:
        if DB_PATH.is_file():
            try:
                _backup_sqlite_file(DB_PATH, run_dir / "genshin.db")
                copied.append("genshin.db")
            except OSError as e:
                errors.append(f"genshin.db: {e}")
        if ARTEFATTI_DB_PATH.is_file():
            try:
                _backup_sqlite_file(ARTEFATTI_DB_PATH, run_dir / "artefatti.db")
                copied.append("artefatti.db")
            except OSError as e:
                errors.append(f"artefatti.db: {e}")

        sets_file = PROJECT_ROOT / "user_artifact_sets.json"
        if _copy_if_exists(sets_file, run_dir / "user_artifact_sets.json"):
            copied.append("user_artifact_sets.json")

        if copied:
            _prune_old_run_dirs(root, max_keep())
    except OSError as e:
        errors.append(str(e))

    ok = not errors and bool(copied)
    return {
        "ok": ok,
        "skipped": False,
        "reason": reason,
        "path": str(run_dir) if copied else "",
        "copied": copied,
        "errors": errors,
    }


def maybe_checkpoint_after_save() -> Dict[str, Any]:
    """Chiamare dopo un salvataggio riuscito: rispetta throttle tra un checkpoint e l'altro."""
    global _last_save_checkpoint_ts
    if not checkpoint_enabled():
        return {"ok": True, "skipped": True, "reason": "save"}
    now = time.monotonic()
    if (
        _last_save_checkpoint_ts is not None
        and now - _last_save_checkpoint_ts < save_throttle_seconds()
    ):
        return {"ok": True, "skipped": True, "reason": "save_throttle"}
    _last_save_checkpoint_ts = now
    return run_automatic_checkpoint("save")

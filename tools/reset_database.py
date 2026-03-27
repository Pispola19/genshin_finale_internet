"""
Reset totale dei database locali (SQLite) del progetto.

Obiettivo: ripartire da DB vuoti (schema invariato), pronti per inserimento manuale.
- Fa backup dei file DB con timestamp
- Elimina i file originali
- Reinizializza lo schema tramite db.connection.init_databases

Uso:
  python3 tools/reset_database.py --yes
  python3 tools/reset_database.py --yes --no-backup
  python3 tools/reset_database.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# Permette `import config` anche se lo script è in tools/
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@dataclass(frozen=True)
class TargetFile:
    label: str
    path: Path


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _backup_path(original: Path, suffix: str) -> Path:
    return original.with_name(f"{original.name}.bak_{suffix}")


def _safe_unlink(p: Path) -> None:
    try:
        p.unlink()
    except FileNotFoundError:
        return


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _human(p: Path) -> str:
    try:
        return str(p.resolve())
    except Exception:
        return str(p)


def _collect_targets() -> List[TargetFile]:
    # Import locali per rispettare GINSHIN_DATA_DIR.
    from config import ARTEFATTI_DB_PATH, DB_PATH

    files: List[TargetFile] = [
        TargetFile("db_main", Path(DB_PATH)),
        TargetFile("db_artefatti", Path(ARTEFATTI_DB_PATH)),
    ]
    return files


def _ensure_db_closed_best_effort() -> None:
    # In un processo separato, tipicamente non ci sono connessioni aperte,
    # ma proviamo a chiudere quelle thread-local per sicurezza.
    try:
        import db.connection as conn_mod

        try:
            conn_mod.close_thread_connections()
        except Exception:
            pass
        try:
            conn_mod._schema_initialized = False  # type: ignore[attr-defined]
        except Exception:
            pass
    except Exception:
        pass


def reset(*, yes: bool, dry_run: bool, do_backup: bool) -> Tuple[List[str], List[str]]:
    _ensure_db_closed_best_effort()
    suffix = _ts()

    actions: List[str] = []
    warnings: List[str] = []

    targets = _collect_targets()

    if not yes and not dry_run:
        raise SystemExit("ERRORE: per sicurezza serve --yes (oppure --dry-run).")

    # Backup
    if do_backup:
        for t in targets:
            if not t.path.exists():
                continue
            b = _backup_path(t.path, suffix)
            actions.append(f"backup {t.label}: {_human(t.path)} -> {_human(b)}")
            if not dry_run:
                _copy_if_exists(t.path, b)
    else:
        actions.append("backup: disattivato (--no-backup)")

    # Delete originals
    for t in targets:
        if t.path.exists():
            actions.append(f"delete {t.label}: {_human(t.path)}")
            if not dry_run:
                _safe_unlink(t.path)
        else:
            actions.append(f"skip delete {t.label}: file non presente ({_human(t.path)})")

    # Recreate empty DB files with schema (log file stays absent until next import).
    from config import ARTEFATTI_DB_PATH, DB_PATH
    from db.connection import init_databases

    actions.append(f"init schema: {_human(Path(DB_PATH))} + {_human(Path(ARTEFATTI_DB_PATH))}")
    if not dry_run:
        c_m = sqlite3.connect(DB_PATH)
        c_a = sqlite3.connect(ARTEFATTI_DB_PATH)
        try:
            init_databases(c_m, c_a)
        finally:
            c_m.close()
            c_a.close()

    # Post-check
    if not dry_run:
        for t in targets:
            if t.label.startswith("db_") and not t.path.exists():
                warnings.append(f"ATTENZIONE: non trovo {t.label} dopo reset: {_human(t.path)}")

    return actions, warnings


def main(argv: Optional[Iterable[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Reset totale DB Genshin Manager (con backup).")
    ap.add_argument("--yes", action="store_true", help="Conferma reset (operazione distruttiva).")
    ap.add_argument("--dry-run", action="store_true", help="Mostra cosa verrebbe fatto senza modifiche.")
    ap.add_argument("--no-backup", action="store_true", help="Non creare backup .bak_* (sconsigliato).")
    ns = ap.parse_args(list(argv) if argv is not None else None)

    actions, warnings = reset(yes=ns.yes, dry_run=ns.dry_run, do_backup=not ns.no_backup)

    print("RESET DATABASE — piano operazioni")
    for a in actions:
        print("-", a)
    if warnings:
        print("\nWARNINGS")
        for w in warnings:
            print("-", w)
    if ns.dry_run:
        print("\n(dry-run: nessuna modifica eseguita)")
    else:
        print("\nOK: database reinizializzati e pronti per dati manuali.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


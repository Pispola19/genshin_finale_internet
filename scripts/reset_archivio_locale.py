#!/usr/bin/env python3
"""
Svuota l’archivio locale (personaggi, armi, manufatti, set utente).

Chiudi prima il server web e la GUI se sono aperti (altrimenti SQLite può essere occupato).

Uso dalla cartella del progetto:
  python3 scripts/reset_archivio_locale.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import ARTEFATTI_DB_PATH, DB_PATH, PROJECT_ROOT  # noqa: E402


def main() -> None:
    extra = PROJECT_ROOT / "user_artifact_sets.json"
    targets = [
        ("Personaggi / armi (DB principale)", DB_PATH),
        ("Manufatti (DB inventario)", ARTEFATTI_DB_PATH),
        ("Set aggiunti a mano", extra),
    ]
    for label, p in targets:
        try:
            if p.is_file():
                p.unlink()
                print(f"Rimosso ({label}): {p}")
            else:
                print(f"Già assente ({label}): {p}")
        except OSError as e:
            print(f"Errore su {p}: {e}", file=sys.stderr)
            sys.exit(1)
    print("\nArchivio locale vuoto. Al prossimo avvio i file ricompiono con schema vuoto.")
    print("(Il menu «Cerca nome» in Personaggio include suggerimenti dal catalogo interno.)")


if __name__ == "__main__":
    main()

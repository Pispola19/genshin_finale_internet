#!/usr/bin/env python3
"""
Pipeline raccolta dati controllata: validazione, normalizzazione, merge idempotente in custom_entities.json.

Uso (dalla root del progetto):
  PYTHONPATH=. python3 tools/pipeline/cli.py validate --batch data/pipeline_inbox/esempio.json
  PYTHONPATH=. python3 tools/pipeline/cli.py ingest --batch data/pipeline_inbox/esempio.json [--approve] [--source fandom]

Nessun fetch HTTP: si depositano JSON curati in data/pipeline_inbox/.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import CUSTOM_ENTITIES_PATH  # noqa: E402

from tools.pipeline.merge_registry import (  # noqa: E402
    _load_registry,
    _save_registry,
    append_log,
    merge_armi,
    merge_manufatti_rows,
    merge_personaggi,
)
from tools.pipeline.normalize import (  # noqa: E402
    normalize_arma_record,
    normalize_manufatto_record,
    normalize_personaggio_record,
)
from tools.pipeline.validate_records import (  # noqa: E402
    validate_arma,
    validate_batch,
    validate_manufatto,
    validate_personaggio,
)


def _read_batch(path: Path) -> object:
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.batch)
    if not path.is_file():
        print(f"File non trovato: {path}", file=sys.stderr)
        return 2
    data = _read_batch(path)
    pg, ar, mf, errs = validate_batch(data)
    for e in errs:
        print(f"[globale] {e}")
    n_ok = 0
    n_bad = 0
    for i, r in enumerate(pg):
        x = normalize_personaggio_record(r)
        ok, msg = validate_personaggio(x)
        if ok:
            n_ok += 1
            print(f"[personaggio {i}] OK {x.get('nome')}")
        else:
            n_bad += 1
            print(f"[personaggio {i}] ERR {msg}")
    for i, r in enumerate(ar):
        x = normalize_arma_record(r)
        ok, msg = validate_arma(x)
        if ok:
            n_ok += 1
            print(f"[arma {i}] OK {x.get('nome')}")
        else:
            n_bad += 1
            print(f"[arma {i}] ERR {msg}")
    for i, r in enumerate(mf):
        x = normalize_manufatto_record(r)
        ok, msg = validate_manufatto(x)
        if ok:
            n_ok += 1
            print(f"[manufatto {i}] OK {x.get('set')} / {x.get('slot')}")
        else:
            n_bad += 1
            print(f"[manufatto {i}] ERR {msg}")
    print(f"--- Riepilogo: {n_ok} OK, {n_bad} errori, errori globali batch: {len(errs)}.")
    return 0 if not errs and n_bad == 0 else 1


def cmd_ingest(args: argparse.Namespace) -> int:
    path = Path(args.batch)
    if not path.is_file():
        print(f"File non trovato: {path}", file=sys.stderr)
        return 2
    reg_path = Path(args.registry) if args.registry else Path(CUSTOM_ENTITIES_PATH)
    data = _read_batch(path)
    pg, ar, mf, errs = validate_batch(data)
    for e in errs:
        print(f"[globale] {e}", file=sys.stderr)
    if errs and not (pg or ar or mf):
        return 1

    registry = _load_registry(reg_path)
    source = (args.source or "manual").strip() or "manual"
    approve = bool(args.approve)
    all_warn: list[str] = []

    np, w = merge_personaggi(registry, pg, approve=approve, source_tag=source)
    all_warn.extend(w)
    na, w = merge_armi(registry, ar, approve=approve, source_tag=source)
    all_warn.extend(w)
    nm_rows, nm_sets, w = merge_manufatti_rows(registry, mf, approve=approve, source_tag=source)
    all_warn.extend(w)

    if not args.dry_run:
        _save_registry(reg_path, registry)
        log_dir = Path(args.log_dir) if args.log_dir else ROOT / "data" / "pipeline_logs"
        log_file = log_dir / f"import_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        append_log(
            log_file,
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "batch": str(path),
                "registry": str(reg_path),
                "source": source,
                "approve": approve,
                "counts": {
                    "personaggi": np,
                    "armi": na,
                    "manufatti_righe": nm_rows,
                    "manufatti_set_aggiornati": nm_sets,
                },
                "warnings": all_warn,
            },
        )
    for w in all_warn:
        print(f"[warn] {w}")
    print(
        f"Ingest {'(dry-run) ' if args.dry_run else ''}personaggi={np} armi={na} "
        f"manufatti righe={nm_rows} set_aggiornati={nm_sets} → {reg_path}"
    )
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Pipeline import controllato (JSON → custom_entities.json)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pv = sub.add_parser("validate", help="Valida batch senza scrivere file")
    pv.add_argument("--batch", required=True, help="Percorso JSON batch")

    pi = sub.add_parser("ingest", help="Normalizza, valida, merge idempotente nel registry")
    pi.add_argument("--batch", required=True, help="Percorso JSON batch")
    pi.add_argument("--registry", default="", help="Override percorso custom_entities.json")
    pi.add_argument("--source", default="manual", help="Tag tracciamento (es. fandom, honey, kqm)")
    pi.add_argument("--approve", action="store_true", help="Imposta approved=true (set solo se 5 pezzi completi)")
    pi.add_argument("--dry-run", action="store_true", help="Non salvare registry/log")
    pi.add_argument("--log-dir", default="", help="Directory log JSONL (default data/pipeline_logs)")

    args = p.parse_args()
    if args.cmd == "validate":
        return cmd_validate(args)
    if args.cmd == "ingest":
        return cmd_ingest(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

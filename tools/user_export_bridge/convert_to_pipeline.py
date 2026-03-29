#!/usr/bin/env python3
"""
Bridge file-only: JSON export utente → batch compatibile con tools/pipeline (validate / ingest).

Nessuna rete, nessun token. Vedi README.md nella stessa cartella.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.pipeline.normalize import (  # noqa: E402
    normalize_arma_record,
    normalize_manufatto_record,
    normalize_personaggio_record,
)
from tools.pipeline.validate_records import validate_arma, validate_batch, validate_manufatto, validate_personaggio  # noqa: E402


def _list(d: Dict[str, Any], it_key: str, en_key: str) -> List[dict]:
    v = d.get(it_key)
    if v is not None:
        return list(v) if isinstance(v, list) else []
    v = d.get(en_key)
    return list(v) if isinstance(v, list) else []


def user_export_to_pipeline_batch(raw: Dict[str, Any], *, source_tag: str) -> Dict[str, Any]:
    ver = raw.get("user_export_version")
    if ver != 1:
        raise ValueError(f"user_export_version non supportata: {ver!r} (atteso 1)")

    personaggi = _list(raw, "personaggi", "characters")
    armi = _list(raw, "armi", "weapons")
    manufatti = _list(raw, "manufatti", "artifacts")

    out_pg = [normalize_personaggio_record(x) for x in personaggi if isinstance(x, dict)]
    out_ar = [normalize_arma_record(x) for x in armi if isinstance(x, dict)]
    out_mf = [normalize_manufatto_record(x) for x in manufatti if isinstance(x, dict)]

    batch: Dict[str, Any] = {
        "personaggi": out_pg,
        "armi": out_ar,
        "manufatti": out_mf,
        "_meta": {
            "source": source_tag,
            "converted_at": datetime.now(timezone.utc).isoformat(),
            "origin_note": (raw.get("origin_note") or "") if isinstance(raw.get("origin_note"), str) else "",
            "bridge": "tools.user_export_bridge",
        },
    }
    return batch


def validate_pipeline_batch(batch: Dict[str, Any]) -> tuple[bool, List[str]]:
    errs: List[str] = []
    pg, ar, mf, ge = validate_batch(batch)
    errs.extend(ge)
    for i, r in enumerate(pg):
        ok, msg = validate_personaggio(r)
        if not ok:
            errs.append(f"personaggi[{i}]: {msg}")
    for i, r in enumerate(ar):
        ok, msg = validate_arma(r)
        if not ok:
            errs.append(f"armi[{i}]: {msg}")
    for i, r in enumerate(mf):
        ok, msg = validate_manufatto(r)
        if not ok:
            errs.append(f"manufatti[{i}]: {msg}")
    return (len(errs) == 0, errs)


def main() -> int:
    ap = argparse.ArgumentParser(description="Converti export utente JSON → batch pipeline")
    ap.add_argument("-i", "--input", type=Path, required=True)
    ap.add_argument("-o", "--output", type=Path, default=None, help="Default: data/pipeline_inbox/batch_user_export_<ts>.json")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--source-tag", default="user_file_export", help="Valore _meta.source nel batch")
    args = ap.parse_args()

    if not args.input.is_file():
        print(f"File non trovato: {args.input}", file=sys.stderr)
        return 2

    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"Lettura JSON fallita: {e}", file=sys.stderr)
        return 2
    if not isinstance(raw, dict):
        print("Il file deve essere un oggetto JSON radice.", file=sys.stderr)
        return 2

    try:
        batch = user_export_to_pipeline_batch(raw, source_tag=args.source_tag)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    ok, problems = validate_pipeline_batch(batch)
    if not ok:
        for p in problems:
            print(f"[ERR] {p}", file=sys.stderr)
        print("Validazione fallita.", file=sys.stderr)
        return 1

    if args.validate_only:
        print("OK: export valido; nessun file scritto (--validate-only).")
        return 0

    out = args.output
    if out is None:
        inbox = ROOT / "data" / "pipeline_inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out = inbox / f"batch_user_export_{ts}.json"

    out.parent.mkdir(parents=True, exist_ok=True)
    # Output senza _meta per compatibilità validate_batch (ignora chiavi extra nelle liste)
    payload = {k: v for k, v in batch.items() if not str(k).startswith("_")}
    payload["_meta"] = batch.get("_meta", {})
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Scritto batch pipeline: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

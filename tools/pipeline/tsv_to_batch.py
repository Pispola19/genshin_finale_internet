#!/usr/bin/env python3
"""
Converte righe TSV (senza fetch web) in JSON batch per la pipeline.

Formato atteso (intestazione opzionale, colonne tab-separated):
  set<TAB>slot<TAB>pezzo[<TAB>bonus_2p[<TAB>bonus_4p]]

slot: fiore|piuma|sabbie|calice|corona oppure sands|flower|...

Esempio:
  printf 'set\\tslot\\tpezzo\\nMio set\\tfiore\\tFiore x\\n' | PYTHONPATH=. python3 tools/pipeline/tsv_to_batch.py -o out.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def tsv_to_manufatti_rows(lines: list[str]) -> list[dict]:
    if not lines:
        return []
    r = csv.DictReader(lines, delimiter="\t")
    if not r.fieldnames:
        return []
    fn = [f.strip().lower() for f in r.fieldnames]
    # Normalizza nomi colonne
    key_map = {}
    for i, h in enumerate(fn):
        if h in ("set", "set_nome"):
            key_map[r.fieldnames[i]] = "set"
        elif h == "slot":
            key_map[r.fieldnames[i]] = "slot"
        elif h in ("pezzo", "nome_pezzo", "piece"):
            key_map[r.fieldnames[i]] = "pezzo"
        elif h in ("bonus_2p", "2p"):
            key_map[r.fieldnames[i]] = "bonus_2p"
        elif h in ("bonus_4p", "4p"):
            key_map[r.fieldnames[i]] = "bonus_4p"
    out = []
    for row in r:
        if not row:
            continue
        item: dict = {}
        for k, v in row.items():
            if k is None:
                continue
            nk = key_map.get(k, k.strip().lower() if k else "")
            if nk in ("set", "slot", "pezzo", "bonus_2p", "bonus_4p") and v:
                item[nk] = v.strip()
        if item.get("set") and item.get("slot") and item.get("pezzo"):
            out.append(item)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="TSV → JSON batch manufatti")
    ap.add_argument("-i", "--input", type=Path, help="File TSV (default: stdin)")
    ap.add_argument("-o", "--output", type=Path, required=True)
    args = ap.parse_args()
    if args.input:
        text = args.input.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    lines = text.splitlines()
    rows = tsv_to_manufatti_rows(lines)
    payload = {"manufatti": rows, "_meta": {"source": "tsv_to_batch"}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(rows)} righe → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

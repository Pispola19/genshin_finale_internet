#!/usr/bin/env python3
"""
Esporta batch JSON per la pipeline dai cataloghi **già nel repository** (nessun web).

Esempi:
  PYTHONPATH=. python3 tools/pipeline/export_from_catalog.py manufatti --out data/pipeline_inbox/generated_manufatti.json
  PYTHONPATH=. python3 tools/pipeline/export_from_catalog.py manufatti --out /tmp/m.json --limit 5
  PYTHONPATH=. python3 tools/pipeline/export_from_catalog.py personaggi-seed --out data/pipeline_inbox/batch_seed_personaggi.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.manufatti_ufficiali import CATALOGO_ARTEFATTI, SLOT_ORDER  # noqa: E402

# Seed operativo: nomi roster + elemento + tipo arma tipico (client IT). Estendibile a mano.
PERSONAGGI_SEED: list[dict] = [
    {"nome": "Hu Tao", "elemento": "Pyro", "arma": "Lancia", "base_stats": {}},
    {"nome": "Raiden Shogun", "elemento": "Electro", "arma": "Lancia", "base_stats": {}},
    {"nome": "Furina", "elemento": "Hydro", "arma": "Spada", "base_stats": {}},
    {"nome": "Nahida", "elemento": "Dendro", "arma": "Catalizzatore", "base_stats": {}},
    {"nome": "Kazuha", "elemento": "Anemo", "arma": "Spada", "base_stats": {}},
    {"nome": "Ganyu", "elemento": "Cryo", "arma": "Arco", "base_stats": {}},
    {"nome": "Zhongli", "elemento": "Geo", "arma": "Lancia", "base_stats": {}},
    {"nome": "Bennett", "elemento": "Pyro", "arma": "Spada", "base_stats": {}},
    {"nome": "Yelan", "elemento": "Hydro", "arma": "Arco", "base_stats": {}},
    {"nome": "Albedo", "elemento": "Geo", "arma": "Spada", "base_stats": {}},
]

# Armi seed: sottoinsieme noto con valori plausibili (verificabili in gioco / wiki curata).
ARMI_SEED: list[dict] = [
    {
        "nome": "Lama celeste",
        "tipo": "Spada",
        "rarita": 5,
        "atk_base": 608,
        "stat_secondaria": "ER%",
        "valore_stat": 55.1,
    },
    {
        "nome": "Arco di Amos",
        "tipo": "Arco",
        "rarita": 5,
        "atk_base": 608,
        "stat_secondaria": "ATK%",
        "valore_stat": 49.6,
    },
    {
        "nome": "Bastone di Homa",
        "tipo": "Lancia",
        "rarita": 5,
        "atk_base": 608,
        "stat_secondaria": "CR%",
        "valore_stat": 66.2,
    },
    {
        "nome": "Aquila Favonia",
        "tipo": "Spada",
        "rarita": 5,
        "atk_base": 674,
        "stat_secondaria": "ATK%",
        "valore_stat": 41.3,
    },
    {
        "nome": "Aqua simulacra",
        "tipo": "Arco",
        "rarita": 5,
        "atk_base": 542,
        "stat_secondaria": "CD%",
        "valore_stat": 88.2,
    },
]


def export_manufatti(out: Path, limit: int | None) -> int:
    rows: list[dict] = []
    n_set = 0
    for set_nome, pezzi in CATALOGO_ARTEFATTI:
        if limit is not None and n_set >= limit:
            break
        for slot, pezzo in zip(SLOT_ORDER, pezzi):
            rows.append({"set": set_nome, "slot": slot, "pezzo": pezzo})
        n_set += 1
    payload = {"manufatti": rows, "_meta": {"source": "core.manufatti_ufficiali", "sets": n_set}}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Scritti {len(rows)} righe manufatti ({n_set} set) → {out}")
    return 0


def export_personaggi_seed(out: Path) -> int:
    payload = {
        "personaggi": [dict(x) for x in PERSONAGGI_SEED],
        "_meta": {"source": "tools.pipeline.export_from_catalog.PERSONAGGI_SEED"},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Scritti {len(PERSONAGGI_SEED)} personaggi seed → {out}")
    return 0


def export_armi_seed(out: Path) -> int:
    payload = {
        "armi": [dict(x) for x in ARMI_SEED],
        "_meta": {"source": "tools.pipeline.export_from_catalog.ARMI_SEED"},
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Scritte {len(ARMI_SEED)} armi seed → {out}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Export batch JSON dai cataloghi in codice")
    sub = p.add_subparsers(dest="cmd", required=True)

    pm = sub.add_parser("manufatti", help="Espandi CATALOGO_ARTEFATTI in righe manufatto")
    pm.add_argument("--out", required=True, type=Path)
    pm.add_argument("--limit", type=int, default=None, help="Max numero di set (default: tutti)")

    pp = sub.add_parser("personaggi-seed", help="Piccolo set personaggi con elemento/arma coerenti")
    pp.add_argument("--out", required=True, type=Path)

    pa = sub.add_parser("armi-seed", help="Piccolo set armi 5★ con stat plausibili")
    pa.add_argument("--out", required=True, type=Path)

    pall = sub.add_parser("starter-pack", help="Genera i tre file starter in pipeline_inbox")
    pall.add_argument(
        "--dir",
        type=Path,
        default=None,
        help="Directory output (default: data/pipeline_inbox)",
    )

    args = p.parse_args()
    if args.cmd == "manufatti":
        return export_manufatti(args.out, args.limit)
    if args.cmd == "personaggi-seed":
        return export_personaggi_seed(args.out)
    if args.cmd == "armi-seed":
        return export_armi_seed(args.out)
    if args.cmd == "starter-pack":
        base = args.dir or (ROOT / "data" / "pipeline_inbox")
        export_personaggi_seed(base / "batch_seed_personaggi.json")
        export_armi_seed(base / "batch_seed_armi.json")
        export_manufatti(base / "batch_seed_manufatti.json", limit=3)
        print("Starter pack completato (3 set manufatti + personaggi + armi seed).")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

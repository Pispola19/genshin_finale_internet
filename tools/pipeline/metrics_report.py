#!/usr/bin/env python3
"""
Report da log pipeline (data/pipeline_logs/import_*.jsonl): volume, approvazioni, warning.

Confronto opzionale con data/pipeline_inbox/operational_targets.json (settimana ISO corrente).

  PYTHONPATH=. python3 tools/pipeline/metrics_report.py
  PYTHONPATH=. python3 tools/pipeline/metrics_report.py --from 2026-03-01
  PYTHONPATH=. python3 tools/pipeline/metrics_report.py --no-targets
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_TARGETS = ROOT / "data" / "pipeline_inbox" / "operational_targets.json"


def _parse_ts(ts: str) -> date | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _counts(rec: Dict[str, Any]) -> Dict[str, int]:
    c = rec.get("counts") or {}
    if not isinstance(c, dict):
        return {"personaggi": 0, "armi": 0, "manufatti_righe": 0, "manufatti_set_aggiornati": 0}
    mr = c.get("manufatti_righe")
    if mr is None:
        mr = c.get("manufatti_rows") or 0
    ms = c.get("manufatti_set_aggiornati")
    if ms is None:
        ms = c.get("manufatti_sets") or 0
    return {
        "personaggi": int(c.get("personaggi") or 0),
        "armi": int(c.get("armi") or 0),
        "manufatti_righe": int(mr or 0),
        "manufatti_set_aggiornati": int(ms or 0),
    }


def load_events(log_dir: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not log_dir.is_dir():
        return out
    for p in sorted(log_dir.glob("import_*.jsonl")):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def iso_week_bounds(d: date) -> Tuple[date, date]:
    """Lunedì–domenica della settimana ISO che contiene ``d``."""
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def aggregate_week(events: List[Dict[str, Any]], monday: date, sunday: date) -> Dict[str, Any]:
    ingests = 0
    approve_true = 0
    warnings = 0
    records = 0
    for rec in events:
        dt = _parse_ts(str(rec.get("ts") or ""))
        if dt is None or dt < monday or dt > sunday:
            continue
        ingests += 1
        if rec.get("approve"):
            approve_true += 1
        w = rec.get("warnings")
        warnings += len(w) if isinstance(w, list) else 0
        co = _counts(rec)
        records += co["personaggi"] + co["armi"] + co["manufatti_righe"]
    appr_pct = (100.0 * approve_true / ingests) if ingests else 0.0
    warn_mean = (warnings / ingests) if ingests else 0.0
    return {
        "monday": monday,
        "sunday": sunday,
        "ingests": ingests,
        "approve_true": approve_true,
        "approval_rate_percent": appr_pct,
        "records_sum": records,
        "warnings_total": warnings,
        "warnings_mean_per_ingest": warn_mean,
    }


def load_targets(path: Path) -> Dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return raw if isinstance(raw, dict) else None


def evaluate_targets(m: Dict[str, Any], t: Dict[str, Any]) -> List[Tuple[str, bool, str]]:
    """Ritorna lista (nome, ok, messaggio)."""
    out: List[Tuple[str, bool, str]] = []
    ing = m["ingests"]
    min_i = t.get("min_ingests_per_calendar_week")
    if min_i is not None and isinstance(min_i, (int, float)):
        ok = ing >= int(min_i)
        out.append(
            (
                "min_ingests_per_calendar_week",
                ok,
                f"ingest settimana ISO {m['monday']}–{m['sunday']}: {ing} (target ≥ {int(min_i)})",
            )
        )

    min_r = t.get("min_records_sum_per_calendar_week")
    if min_r is not None and isinstance(min_r, (int, float)):
        ok = m["records_sum"] >= int(min_r) if ing > 0 else (int(min_r) == 0)
        out.append(
            (
                "min_records_sum_per_calendar_week",
                ok,
                f"record sommati (pg+armi+righe manufatti): {m['records_sum']} (target ≥ {int(min_r)})",
            )
        )

    max_w = t.get("max_mean_warnings_per_ingest")
    if max_w is not None and isinstance(max_w, (int, float)):
        if ing == 0:
            out.append(("max_mean_warnings_per_ingest", True, "nessun ingest — soglia non applicata"))
        else:
            ok = m["warnings_mean_per_ingest"] <= float(max_w)
            out.append(
                (
                    "max_mean_warnings_per_ingest",
                    ok,
                    f"warning medi per ingest: {m['warnings_mean_per_ingest']:.2f} (target ≤ {float(max_w)})",
                )
            )

    min_ap = t.get("min_approval_rate_percent")
    if min_ap is not None and isinstance(min_ap, (int, float)):
        if ing < 2:
            out.append(
                (
                    "min_approval_rate_percent",
                    True,
                    f"ingest < 2 — percentuale approve non valutata (serve campione minimo)",
                )
            )
        else:
            ok = m["approval_rate_percent"] >= float(min_ap)
            out.append(
                (
                    "min_approval_rate_percent",
                    ok,
                    f"tasso approve: {m['approval_rate_percent']:.1f}% (target ≥ {float(min_ap)}%)",
                )
            )

    return out


def report(events: List[Dict[str, Any]], day_from: date | None) -> None:
    by_day: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "ingests": 0,
            "approve_true": 0,
            "approve_false": 0,
            "personaggi": 0,
            "armi": 0,
            "manufatti_righe": 0,
            "manufatti_set_aggiornati": 0,
            "warnings": 0,
            "sources": defaultdict(int),
        }
    )

    for rec in events:
        d = _parse_ts(str(rec.get("ts") or ""))
        if d is None:
            continue
        if day_from and d < day_from:
            continue
        key = d.isoformat()
        bucket = by_day[key]
        bucket["ingests"] += 1
        if rec.get("approve"):
            bucket["approve_true"] += 1
        else:
            bucket["approve_false"] += 1
        co = _counts(rec)
        bucket["personaggi"] += co["personaggi"]
        bucket["armi"] += co["armi"]
        bucket["manufatti_righe"] += co["manufatti_righe"]
        bucket["manufatti_set_aggiornati"] += co["manufatti_set_aggiornati"]
        w = rec.get("warnings")
        bucket["warnings"] += len(w) if isinstance(w, list) else 0
        src = str(rec.get("source") or "unknown")
        bucket["sources"][src] += 1

    if not by_day:
        print("Nessun evento nel periodo (log vuoti o assenti in data/pipeline_logs/).")
        return

    print("Pipeline — metriche da log ingest\n")
    total_ing = sum(b["ingests"] for b in by_day.values())
    total_appr = sum(b["approve_true"] for b in by_day.values())
    total_records = sum(
        b["personaggi"] + b["armi"] + b["manufatti_righe"] for b in by_day.values()
    )
    print(f"Giorni con attività: {len(by_day)} | Ingest totali: {total_ing}")
    if total_ing:
        print(f"Tasso approvazione (flag --approve): {100.0 * total_appr / total_ing:.1f}% ({total_appr}/{total_ing})")
    print(f"Record processati (somma conteggi): personaggi+armi+righe manufatti = {total_records}")
    print()

    for day_key in sorted(by_day.keys()):
        b = by_day[day_key]
        ing = b["ingests"]
        appr = b["approve_true"]
        rate = (100.0 * appr / ing) if ing else 0.0
        warn_avg = b["warnings"] / ing if ing else 0.0
        print(f"  {day_key}  ingest={ing}  approve%={rate:.0f}%  "
              f"pg={b['personaggi']} armi={b['armi']} m_rows={b['manufatti_righe']} "
              f"m_sets={b['manufatti_set_aggiornati']}  warn_medio={warn_avg:.1f}")
        srcs = dict(b["sources"])
        if len(srcs) > 1 or (len(srcs) == 1 and "unknown" not in srcs):
            print(f"         sources: {srcs}")


def report_targets_section(events: List[Dict[str, Any]], targets_path: Path) -> None:
    t = load_targets(targets_path)
    if not t:
        print(f"\n(File target assente o non valido: {targets_path})")
        return
    today = date.today()
    mon, sun = iso_week_bounds(today)
    m = aggregate_week(events, mon, sun)
    print(f"\n=== Target operativi (settimana ISO {mon} → {sun}) ===\n")
    if m["ingests"] == 0:
        print("Nessun ingest in questa settimana — valutazione target limitata.\n")
    prio = t.get("sprint_priority_order")
    if isinstance(prio, list) and prio:
        print("Priorità dinamiche predefinite (sprint):", " → ".join(str(x) for x in prio))
        note = t.get("sprint_note")
        if isinstance(note, str) and note.strip():
            print(f"Nota: {note.strip()}")
        print()
    for name, ok, msg in evaluate_targets(m, t):
        tag = "OK " if ok else "KO "
        print(f"  [{tag}] {msg}")
    cmt = t.get("comment")
    if isinstance(cmt, str) and cmt.strip():
        print(f"\n(commento file target: {cmt.strip()})")


def main() -> int:
    ap = argparse.ArgumentParser(description="Report metriche da log pipeline")
    ap.add_argument("--log-dir", type=Path, default=None, help="Default: data/pipeline_logs")
    ap.add_argument("--from", dest="day_from", default="", help="Data inizio YYYY-MM-DD (UTC date da ts)")
    ap.add_argument("--targets", type=Path, default=None, help="JSON target (default: data/pipeline_inbox/operational_targets.json)")
    ap.add_argument("--no-targets", action="store_true", help="Non stampare sezione confronto target")
    args = ap.parse_args()
    log_dir = args.log_dir or (ROOT / "data" / "pipeline_logs")
    df = None
    if args.day_from:
        try:
            df = date.fromisoformat(args.day_from)
        except ValueError:
            print("Data --from non valida (usa YYYY-MM-DD)", file=sys.stderr)
            return 2
    events = load_events(log_dir)
    report(events, df)
    if not args.no_targets:
        tp = args.targets if args.targets is not None else DEFAULT_TARGETS
        report_targets_section(events, tp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Processa in sequenza i file JSON in data/pipeline_inbox (esclusi esempi/sottocartelle).

Idempotenza: un manifest JSON ricorda i file già ingestiti (per path assoluto + hash SHA256).

Uso:
  PYTHONPATH=. python3 tools/pipeline/inbox_runner.py
  PYTHONPATH=. python3 tools/pipeline/inbox_runner.py --approve --source cron
  PYTHONPATH=. python3 tools/pipeline/inbox_runner.py --dry-run

Schedulazione: cron o LaunchAgent che invoca questo script 1×/giorno.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import CUSTOM_ENTITIES_PATH  # noqa: E402

DEFAULT_INBOX = ROOT / "data" / "pipeline_inbox"
MANIFEST_NAME = ".ingest_manifest.json"
SKIP_PREFIXES = ("generated_",)  # opzionale: non auto-ingestire export massivi senza flag
CLI = ROOT / "tools" / "pipeline" / "cli.py"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest(path: Path) -> dict:
    if not path.is_file():
        return {"version": 1, "processed": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "processed": []}


def _save_manifest(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Inbox pipeline: ingest automatico file JSON")
    ap.add_argument("--inbox", type=Path, default=DEFAULT_INBOX)
    ap.add_argument("--registry", type=Path, default=None, help="Override custom_entities.json")
    ap.add_argument("--approve", action="store_true", help="Passa --approve alla CLI ingest")
    ap.add_argument("--source", default="inbox_runner", help="Tag --source")
    ap.add_argument("--dry-run", action="store_true", help="Solo elenco azioni, nessuna scrittura")
    ap.add_argument(
        "--include-generated",
        action="store_true",
        help="Includi file il cui nome inizia con generated_",
    )
    args = ap.parse_args()

    inbox = args.inbox
    manifest_path = inbox / MANIFEST_NAME
    manifest = _load_manifest(manifest_path)
    processed = {
        (x.get("path"), x.get("sha256"))
        for x in manifest.get("processed", [])
        if isinstance(x, dict) and x.get("path") and x.get("sha256")
    }

    reg = str(args.registry or CUSTOM_ENTITIES_PATH)
    candidates = sorted(inbox.glob("*.json"))
    ran = 0
    for f in candidates:
        if f.name.startswith(".") or f.name == MANIFEST_NAME:
            continue
        if not args.include_generated and f.name.startswith(SKIP_PREFIXES):
            print(f"[skip] {f.name} (usa --include-generated per processarlo)")
            continue
        key = (str(f.resolve()), _sha256(f))
        if key in processed:
            print(f"[ok] già processato {f.name}")
            continue
        print(f"[ingest] {f.name}")
        cmd = [
            sys.executable,
            str(CLI),
            "ingest",
            "--batch",
            str(f),
            "--source",
            args.source,
            "--registry",
            reg,
        ]
        if args.approve:
            cmd.append("--approve")
        if args.dry_run:
            print("  dry-run:", " ".join(cmd))
            continue
        r = subprocess.run(cmd, cwd=str(ROOT), env={**__import__("os").environ, "PYTHONPATH": str(ROOT)})
        if r.returncode != 0:
            print(f"[err] ingest fallito per {f.name} (exit {r.returncode})", file=sys.stderr)
            return r.returncode
        manifest.setdefault("processed", []).append(
            {
                "path": str(f.resolve()),
                "sha256": key[1],
                "ts": datetime.now(timezone.utc).isoformat(),
                "file": f.name,
            }
        )
        _save_manifest(manifest_path, manifest)
        processed.add(key)
        ran += 1

    if args.dry_run:
        print(f"Dry-run: {len(candidates)} file .json in inbox.")
        return 0
    print(f"Completato: {ran} nuovi file ingestiti.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

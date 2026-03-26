"""Log append-only degli import HoYoLab (JSONL). Non modifica lo schema DB principale."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from config import IMPORT_LOG_PATH


def append_import_log(entry: Dict[str, Any]) -> None:
    """Aggiunge una riga JSON con timestamp UTC."""
    row = dict(entry)
    row["timestamp"] = datetime.now(timezone.utc).isoformat()
    path = Path(IMPORT_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

"""
Merge idempotente verso data/custom_entities.json (estensioni approvabili).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from core.nome_normalization import norm_key_nome

from tools.pipeline.normalize import (
    normalize_arma_record,
    normalize_manufatto_record,
    normalize_personaggio_record,
)
from tools.pipeline.validate_records import validate_arma, validate_manufatto, validate_personaggio

SLOT_ORDER = ("fiore", "piuma", "sabbie", "calice", "corona")


def _load_registry(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {"version": 1, "characters": [], "weapons": [], "sets": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "characters": [], "weapons": [], "sets": []}
    if not isinstance(raw, dict):
        return {"version": 1, "characters": [], "weapons": [], "sets": []}
    raw.setdefault("characters", [])
    raw.setdefault("weapons", [])
    raw.setdefault("sets", [])
    return raw


def _save_registry(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _char_key(item: Dict) -> str:
    return norm_key_nome((item.get("name") or ""))


def _weapon_key(item: Dict) -> str:
    return norm_key_nome((item.get("name") or ""))


def _set_key(item: Dict) -> str:
    return norm_key_nome((item.get("name") or ""))


def merge_personaggi(
    registry: Dict[str, Any],
    records: List[dict],
    *,
    approve: bool,
    source_tag: str,
) -> Tuple[int, List[str]]:
    """Ritorna (num_inseriti_o_aggiornati, warnings)."""
    warnings: List[str] = []
    chars: List[dict] = list(registry.get("characters") or [])
    by_k: Dict[str, int] = {}
    for i, c in enumerate(chars):
        k = _char_key(c)
        if k:
            by_k[k] = i

    n = 0
    for raw in records:
        rec = normalize_personaggio_record(raw)
        ok, msg = validate_personaggio(rec)
        if not ok:
            warnings.append(f"personaggio skip: {msg}")
            continue
        entry = {
            "name": rec["nome"],
            "approved": approve,
            "note": f"pipeline:{source_tag} elemento={rec['elemento']} arma={rec['arma']}",
            "pipeline": {
                "elemento": rec["elemento"],
                "arma": rec["arma"],
                "base_stats": rec.get("base_stats") or {},
            },
        }
        k = norm_key_nome(rec["nome"])
        if k in by_k:
            chars[by_k[k]] = entry
        else:
            by_k[k] = len(chars)
            chars.append(entry)
        n += 1
    registry["characters"] = chars
    return n, warnings


def merge_armi(
    registry: Dict[str, Any],
    records: List[dict],
    *,
    approve: bool,
    source_tag: str,
) -> Tuple[int, List[str]]:
    warnings: List[str] = []
    weapons: List[dict] = list(registry.get("weapons") or [])
    by_k: Dict[str, int] = {}
    for i, w in enumerate(weapons):
        k = _weapon_key(w)
        if k:
            by_k[k] = i

    n = 0
    for raw in records:
        rec = normalize_arma_record(raw)
        ok, msg = validate_arma(rec)
        if not ok:
            warnings.append(f"arma skip: {msg}")
            continue
        entry = {
            "name": rec["nome"],
            "approved": approve,
            "note": f"pipeline:{source_tag}",
            "pipeline": {
                "tipo": rec["tipo"],
                "rarita": rec.get("rarita"),
                "atk_base": rec.get("atk_base"),
                "stat_secondaria": rec.get("stat_secondaria"),
                "valore_stat": rec.get("valore_stat"),
            },
        }
        k = norm_key_nome(rec["nome"])
        if k in by_k:
            weapons[by_k[k]] = entry
        else:
            by_k[k] = len(weapons)
            weapons.append(entry)
        n += 1
    registry["weapons"] = weapons
    return n, warnings


def merge_manufatti_rows(
    registry: Dict[str, Any],
    records: List[dict],
    *,
    approve: bool,
    source_tag: str,
) -> Tuple[int, int, List[str]]:
    """
    Aggrega righe (set, slot, pezzo) in voci set con 5 pezzi.
    Set incompleti: aggiorna pezzi parziali su voce esistente o crea bozza non approvabile finché mancano slot.
    Ritorna (righe_applicate, set_riscritti, warnings).
    """
    warnings: List[str] = []
    rows_applied = 0
    sets_list: List[dict] = list(registry.get("sets") or [])
    by_k: Dict[str, int] = {}
    for i, s in enumerate(sets_list):
        k = _set_key(s)
        if k:
            by_k[k] = i

    # Accumula pezzi per set
    partial: Dict[str, Dict[str, str]] = {}
    meta: Dict[str, Dict[str, Any]] = {}

    for s in sets_list:
        k = _set_key(s)
        if not k:
            continue
        pcs = s.get("pieces") or {}
        if not isinstance(pcs, dict):
            continue
        partial[k] = {
            sl: str(pcs.get(sl) or "").strip()
            for sl in SLOT_ORDER
        }
        meta[k] = {
            "bonus_2p": str(s.get("bonus_2p") or ""),
            "bonus_4p": str(s.get("bonus_4p") or ""),
            "canonical_name": (s.get("name") or "").strip(),
        }

    for raw in records:
        rec = normalize_manufatto_record(raw)
        ok, msg = validate_manufatto(rec)
        if not ok:
            warnings.append(f"manufatto skip: {msg}")
            continue
        sk = norm_key_nome(rec["set"])
        if sk not in partial:
            partial[sk] = {sl: "" for sl in SLOT_ORDER}
            meta[sk] = {"bonus_2p": "", "bonus_4p": "", "canonical_name": rec["set"]}
        slot = rec["slot"]
        if slot not in SLOT_ORDER:
            continue
        partial[sk][slot] = rec["pezzo"]
        if rec.get("bonus_2p"):
            meta[sk]["bonus_2p"] = rec["bonus_2p"]
        if rec.get("bonus_4p"):
            meta[sk]["bonus_4p"] = rec["bonus_4p"]
        rows_applied += 1

    n_sets = 0
    for sk, pieces in partial.items():
        missing = [sl for sl in SLOT_ORDER if not (pieces.get(sl) or "").strip()]
        complete = not missing
        name = (meta[sk].get("canonical_name") or "").strip()
        if not name:
            name = sk

        entry = {
            "name": name,
            "approved": approve and complete,
            "note": f"pipeline:{source_tag}" + ("" if complete else f" incomplete={','.join(missing)}"),
            "pieces": {sl: pieces.get(sl, "") for sl in SLOT_ORDER},
            "bonus_2p": meta[sk].get("bonus_2p") or "",
            "bonus_4p": meta[sk].get("bonus_4p") or "",
        }
        if not complete:
            warnings.append(
                f"manufatto set {name!r}: slot mancanti {missing} — approved=false fino a completamento."
            )
        if sk in by_k:
            sets_list[by_k[sk]] = entry
        else:
            by_k[sk] = len(sets_list)
            sets_list.append(entry)
        n_sets += 1

    registry["sets"] = sets_list
    return rows_applied, n_sets, warnings


def append_log(log_path: Path, event: Dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False) + "\n"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)

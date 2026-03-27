"""
Registry esterno (Approccio B): entità approvate oltre al catalogo in codice.

File: ``data/custom_entities.json`` (o sotto ``GINSHIN_DATA_DIR`` quando il DB è su disco persistente).
Solo voci con ``\"approved\": true`` entrano nella whitelist effettiva e nel catalogo manufatti.

Struttura (estensibile):
  characters: [{ "name": "...", "approved": false, "note": "..." }]
  weapons:    [{ "name": "...", "approved": false }]
  sets:       [{ "name": "...", "approved": false, "pieces": { "fiore", "piuma", "sabbie", "calice", "corona" } }]
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from config import CUSTOM_ENTITIES_PATH

_REGISTRY_PATH = Path(CUSTOM_ENTITIES_PATH)


def registry_path() -> Path:
    return _REGISTRY_PATH


def load_registry_raw() -> Dict[str, Any]:
    if not _REGISTRY_PATH.is_file():
        return {"version": 1, "characters": [], "weapons": [], "sets": []}
    try:
        raw = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "characters": [], "weapons": [], "sets": []}
    if not isinstance(raw, dict):
        return {"version": 1, "characters": [], "weapons": [], "sets": []}
    return raw


def approved_personaggi_names() -> Set[str]:
    out: Set[str] = set()
    for item in load_registry_raw().get("characters") or []:
        if not isinstance(item, dict) or not item.get("approved"):
            continue
        n = (item.get("name") or "").strip()
        if n:
            out.add(n)
    return out


def approved_armi_names() -> Set[str]:
    out: Set[str] = set()
    for item in load_registry_raw().get("weapons") or []:
        if not isinstance(item, dict) or not item.get("approved"):
            continue
        n = (item.get("name") or "").strip()
        if n:
            out.add(n)
    return out


def approved_sets_as_catalog_tuples() -> List[Tuple[str, Tuple[str, str, str, str, str]]]:
    """Set approvati con esattamente 5 pezzi (nomi per slot)."""
    out: List[Tuple[str, Tuple[str, str, str, str, str]]] = []
    for item in load_registry_raw().get("sets") or []:
        if not isinstance(item, dict) or not item.get("approved"):
            continue
        sn = (item.get("name") or "").strip()
        pcs = item.get("pieces") or {}
        if not sn or not isinstance(pcs, dict):
            continue
        fi = (pcs.get("fiore") or "").strip()
        pi = (pcs.get("piuma") or "").strip()
        sa = (pcs.get("sabbie") or "").strip()
        ca = (pcs.get("calice") or "").strip()
        co = (pcs.get("corona") or "").strip()
        if fi and pi and sa and ca and co:
            out.append((sn, (fi, pi, sa, ca, co)))
    return out

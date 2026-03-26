"""
Validazione, metriche e flag qualità per import JSON stile HoYoLab (data.avatars).

Nessun accesso DB qui: solo strutture JSON. La struttura tabelle artefatti non cambia.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

#
# Modalità equip manufatti post-import personaggio
# - replace: sostituisce i pezzi equipaggiati (distruttivo sull'equip del personaggio)
# - update: aggiorna SOLO gli slot presenti in JSON, preservando stat DB se HoYo non le fornisce
# - append_dedup: aggiunge righe in inventario senza toccare equip; dedup opzionale
# - append_force: aggiunge righe in inventario senza dedup
#
IMPORT_MODE_REPLACE = "replace"
IMPORT_MODE_UPDATE = "update"
IMPORT_MODE_APPEND_DEDUP = "append_dedup"
IMPORT_MODE_APPEND_FORCE = "append_force"

# Backward-compat: "append" viene interpretato come dedup
IMPORT_MODE_APPEND = IMPORT_MODE_APPEND_DEDUP

IMPORT_MODES = (
    IMPORT_MODE_REPLACE,
    IMPORT_MODE_UPDATE,
    IMPORT_MODE_APPEND_DEDUP,
    IMPORT_MODE_APPEND_FORCE,
)


def normalize_import_mode(raw: Any) -> str:
    s = str(raw or IMPORT_MODE_REPLACE).strip().lower()
    # compat sinonimi
    if s in ("append", "append_dedup", "dedup_append", "appenddedup"):
        return IMPORT_MODE_APPEND_DEDUP
    if s in ("append_force", "force_append", "appendforce", "append_forced"):
        return IMPORT_MODE_APPEND_FORCE
    if s in IMPORT_MODES:
        return s
    return IMPORT_MODE_REPLACE


def weapon_min_present_in_avatar(av: dict) -> bool:
    """
    True se l'avatar ha almeno un minimo info arma (id o name).
    Serve per evitare import di personaggi senza arma (UX e calcoli futuri).
    """
    if not isinstance(av, dict):
        return False
    w = av.get("weapon")
    if not isinstance(w, dict):
        return False
    w_name = w.get("name") or w.get("nome") or w.get("weaponName") or w.get("itemName") or ""
    if isinstance(w_name, str) and w_name.strip():
        return True
    # id può essere numerico o stringa
    for k in ("id", "weaponId", "weapon_id"):
        if w.get(k) is not None:
            return True
    return False


def relics_list_or_empty(av: dict) -> bool:
    """
    Se "relics" è presente ma non è una lista, ritorna False.
    L'import non deve crashare: la conversione lato parser userà [] ma qui forniamo info.
    """
    if not isinstance(av, dict):
        return False
    if "relics" not in av:
        return True
    rel = av.get("relics")
    return isinstance(rel, list) or rel is None


def validate_hoyolab_bulk_envelope(root: dict) -> None:
    """
    Validazione rigida per risposte battle chronicle / game record.
    Solleva ImportParseError se mancano campi obbligatori o tipi errati.
    """
    from core.manual_import import ImportParseError

    if not isinstance(root, dict):
        raise ImportParseError("JSON HoYoLab: la radice deve essere un oggetto.")
    inner = root.get("data")
    if inner is None:
        raise ImportParseError("JSON HoYoLab: manca l'oggetto obbligatorio «data».")
    if not isinstance(inner, dict):
        raise ImportParseError("JSON HoYoLab: «data» deve essere un oggetto JSON.")
    avatars = inner.get("avatars")
    if avatars is None:
        raise ImportParseError("JSON HoYoLab: manca «data.avatars».")
    if not isinstance(avatars, list):
        raise ImportParseError("JSON HoYoLab: «data.avatars» deve essere un array.")
    if len(avatars) == 0:
        raise ImportParseError("JSON HoYoLab: «data.avatars» è vuoto (nessun personaggio).")
    for i, a in enumerate(avatars):
        if not isinstance(a, dict):
            raise ImportParseError(f"JSON HoYoLab: data.avatars[{i}] non è un oggetto.")
        nm = a.get("name")
        if nm is None or (isinstance(nm, str) and not nm.strip()):
            raise ImportParseError(
                f"JSON HoYoLab: data.avatars[{i}] senza «name» valido."
            )


def relic_missing_stats(rel: dict) -> bool:
    """
    True se il pezzo non ha informazioni sufficienti per main + almeno una sub
    (tipico export HoYoLab senza fight props).
    """
    if not isinstance(rel, dict):
        return True
    mp = rel.get("main_property")
    main_ok = False
    if isinstance(mp, dict):
        if (mp.get("name") or mp.get("property_name") or "").strip():
            main_ok = True
        if mp.get("final") is not None or mp.get("value") is not None:
            main_ok = True
    elif mp not in (None, ""):
        main_ok = True
    subs = rel.get("sub_property_list")
    subs_ok = False
    if isinstance(subs, list) and len(subs) > 0:
        for s in subs:
            if not isinstance(s, dict):
                continue
            if (s.get("name") or s.get("property_name") or "").strip():
                subs_ok = True
                break
            if s.get("final") is not None or s.get("value") is not None:
                subs_ok = True
                break
    return not (main_ok and subs_ok)


def enrich_import_item_flags(imp: dict) -> None:
    """Aggiorna ``imp`` con conteggi missing_stats (solo in memoria, niente DB)."""
    rels = imp.get("relics_raw") or []
    flags = [relic_missing_stats(r) for r in rels if isinstance(r, dict)]
    imp["relics_missing_stats_flags"] = flags
    imp["n_relics_incomplete"] = sum(1 for f in flags if f)


def compute_hoyo_preview_stats(parsed: dict) -> Dict[str, int]:
    """Conteggi per anteprima e log (personaggi, armi, manufatti, incompleti)."""
    if parsed.get("bulk"):
        imps = list(parsed.get("imports") or [])
        n_char = len(imps)
        n_weap = sum(1 for i in imps if (i.get("weapon") or {}).get("nome"))
        n_rel = 0
        n_inc = 0
        for imp in imps:
            enrich_import_item_flags(imp)
            rels = imp.get("relics_raw") or []
            n_rel += len(rels)
            n_inc += imp.get("n_relics_incomplete") or 0
        return {
            "n_characters": n_char,
            "n_weapons": n_weap,
            "n_relics": n_rel,
            "n_relics_incomplete": n_inc,
        }
    enrich_import_item_flags(parsed)
    rels = parsed.get("relics_raw") or []
    return {
        "n_characters": 1,
        "n_weapons": 1 if (parsed.get("weapon") or {}).get("nome") else 0,
        "n_relics": len(rels),
        "n_relics_incomplete": parsed.get("n_relics_incomplete") or 0,
    }

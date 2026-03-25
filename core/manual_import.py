"""
Import manuale di dati personaggio da testo/JSON incollato (senza login, senza scraping).

Flusso pensato: l’utente copia dal browser (es. risposta JSON da DevTools) o incolla un JSON
nel formato documentato qui, oppure un dizionario “piatto” con chiavi alias.

L’output è compatibile con ``PersonaggioService.salva_completo`` tramite
``build_forms_for_salva_completo`` + ``apply_manual_import``.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple, Union

from config import TIPI_ARMA

JsonValue = Union[dict, list, str, int, float, bool, None]

# --- Formato canonico consigliato (estendibile, es. API future) ---
# {
#   "version": 1,
#   "source": "manual",
#   "character": {
#     "nome": "Beidou", "livello": 90, "elemento": "Electro",
#     "hp_flat": 18500, "atk_flat": 2100, "def_flat": 900,
#     "crit_rate": 65.2, "crit_dmg": 120.5, "energy_recharge": 180, "elemental_mastery": 120
#   },
#   "weapon": { "nome": "...", "tipo": "Claymore", "livello": 90, "stelle": 5, ... }  # opzionale
# }

# Chiavi esterne (alias) → chiavi interne form personaggio
_STAT_ALIASES: Dict[str, str] = {
    "hp": "hp_flat",
    "max_hp": "hp_flat",
    "hp_flat": "hp_flat",
    "atk": "atk_flat",
    "attack": "atk_flat",
    "atk_flat": "atk_flat",
    "def": "def_flat",
    "defense": "def_flat",
    "def_flat": "def_flat",
    "em": "em_flat",
    "elemental_mastery": "em_flat",
    "mastery": "em_flat",
    "em_flat": "em_flat",
    "crit_rate": "cr",
    "critical": "cr",
    "crate": "cr",
    "cr": "cr",
    "crit_dmg": "cd",
    "critical_damage": "cd",
    "cdmg": "cd",
    "cd": "cd",
    "energy_recharge": "er",
    "recharge": "er",
    "er": "er",
}

_ELEMENT_NORMALIZE = {
    "fire": "Pyro",
    "water": "Hydro",
    "ice": "Cryo",
    "electric": "Electro",
    "electro": "Electro",
    "wind": "Anemo",
    "rock": "Geo",
    "grass": "Dendro",
    "flame": "Pyro",
    "thunder": "Electro",
}

# Indici comuni in fightPropMap / propMap (API stile client Genshin). Valori possono essere float.
# CR/CD talvolta come frazione (0.55), talvolta come percentuale già *100.
_FIGHT_PROP_TO_INTERNAL: Dict[str, Tuple[str, bool]] = {
    "1": ("hp_flat", False),
    "2000": ("hp_flat", False),
    "2": ("atk_flat", False),
    "2001": ("atk_flat", False),
    "4": ("atk_flat", False),  # alcuni payload usano 4 per ATK
    "3": ("def_flat", False),
    "2002": ("def_flat", False),
    "6": ("def_flat", False),
    "7": ("em_flat", False),
    "28": ("em_flat", False),
    "2005": ("em_flat", False),
    "20": ("cr", True),  # fraction → percent
    "2008": ("cr", True),
    "22": ("cd", True),
    "2009": ("cd", True),
    "23": ("er", True),
    "2010": ("er", True),
    "11": ("er", True),  # ER alternativo in alcuni dump
    "2007": ("er", True),
}


class ImportParseError(ValueError):
    """Testo non JSON valido o struttura non riconosciuta."""


def _norm_pct(val: Any, likely_fraction: bool) -> Optional[float]:
    if val is None:
        return None
    try:
        x = float(val)
    except (TypeError, ValueError):
        return None
    if likely_fraction and 0 < x < 2:
        x *= 100.0
    return round(x, 2)


def _flatten_stat_keys(d: dict) -> dict:
    out = {}
    lk = {str(k).strip().lower().replace(" ", "_"): v for k, v in d.items()}
    for k, v in lk.items():
        if k in _STAT_ALIASES:
            out[_STAT_ALIASES[k]] = v
    return out


def _normalize_element(raw: Any) -> str:
    if raw is None:
        return "Pyro"
    s = str(raw).strip()
    if not s:
        return "Pyro"
    low = s.lower()
    if low in _ELEMENT_NORMALIZE:
        return _ELEMENT_NORMALIZE[low]
    # Nomi gioco EN
    for canon in ("Pyro", "Hydro", "Electro", "Cryo", "Anemo", "Geo", "Dendro"):
        if s.lower() == canon.lower():
            return canon
    return s[:1].upper() + s[1:] if s else "Pyro"


def _consume_fight_prop_map(props: Any) -> Dict[str, Any]:
    if not isinstance(props, dict):
        return {}
    out: Dict[str, Any] = {}
    for k, v in props.items():
        key = str(k).strip()
        if key not in _FIGHT_PROP_TO_INTERNAL:
            continue
        field, is_frac = _FIGHT_PROP_TO_INTERNAL[key]
        if field in ("cr", "cd", "er"):
            n = _norm_pct(v, is_frac)
            if n is not None:
                out[field] = n
        else:
            try:
                out[field] = int(round(float(v)))
            except (TypeError, ValueError):
                pass
    return out


def _score_avatar_candidate(d: dict) -> int:
    s = 0
    if any(k in d for k in ("name", "nome", "nickname", "avatarName")):
        s += 3
    if any(k in d for k in ("level", "livello", "expLevel")):
        s += 3
    if d.get("fightPropMap") or d.get("propMap") or d.get("fight_prop_map"):
        s += 4
    return s


def _character_blob_has_name(blob: dict) -> bool:
    nome = (
        blob.get("nome")
        or blob.get("name")
        or blob.get("nickname")
        or blob.get("avatarName")
    )
    return bool(str(nome or "").strip())


def _avatar_quality(d: dict) -> int:
    """Preferisce dict più ricchi (evita wrapper ridondanti con lo stesso nome)."""
    base = _score_avatar_candidate(d)
    pm = d.get("fightPropMap") or d.get("propMap") or d.get("fight_prop_map") or {}
    extra = len(pm) * 5
    fk = _flatten_stat_keys(d)
    for k in ("hp_flat", "atk_flat", "def_flat", "em_flat", "cr", "cd", "er"):
        v = fk.get(k)
        if v not in (None, ""):
            extra += 3
    return base * 1000 + extra


def _collect_avatar_like_dicts(obj: JsonValue, out: List[dict], seen: Optional[set] = None) -> None:
    if seen is None:
        seen = set()
    oid = id(obj)
    if oid in seen:
        return
    seen.add(oid)
    if isinstance(obj, dict):
        if _score_avatar_candidate(obj) >= 4:
            out.append(obj)
        for v in obj.values():
            _collect_avatar_like_dicts(v, out, seen)
    elif isinstance(obj, list):
        for v in obj:
            _collect_avatar_like_dicts(v, out, seen)


def _pick_character_blob(root: dict) -> dict:
    """Estrae un singolo blocco personaggio da un JSON arbitrario."""
    for key in ("character", "personaggio"):
        if key not in root:
            continue
        val = root[key]
        if val is None:
            continue
        if not isinstance(val, dict):
            raise ImportParseError(
                f'Chiave "{key}" deve essere un oggetto JSON con i dati del personaggio.'
            )
        if _character_blob_has_name(val):
            return val

    candidates: List[dict] = []
    _collect_avatar_like_dicts(root, candidates)
    candidates.sort(key=_avatar_quality, reverse=True)
    for c in candidates:
        if _blob_to_internal_character(c).get("nome"):
            return c
    raise ImportParseError(
        "Nessun blocco personaggio riconosciuto. Usa il formato documentato in core/manual_import.py "
        "oppure incolla JSON con nome, livello e fightPropMap / propMap."
    )


def _blob_to_internal_character(blob: dict) -> dict:
    nome = (
        blob.get("nome")
        or blob.get("name")
        or blob.get("nickname")
        or blob.get("avatarName")
        or ""
    )
    nome = str(nome).strip()
    livello = blob.get("livello") if blob.get("livello") is not None else blob.get("level") or blob.get("expLevel") or 1
    try:
        livello = int(livello)
    except (TypeError, ValueError):
        livello = 1

    elemento = _normalize_element(blob.get("elemento") or blob.get("element") or blob.get("elemType"))

    stats: Dict[str, Any] = {}
    stats.update(_flatten_stat_keys(blob))
    for pm_key in ("fightPropMap", "propMap", "fight_prop_map"):
        if pm_key in blob:
            merged = _consume_fight_prop_map(blob[pm_key])
            for k, v in merged.items():
                stats.setdefault(k, v)

    return {
        "nome": nome,
        "livello": livello,
        "elemento": elemento,
        "hp_flat": stats.get("hp_flat", ""),
        "atk_flat": stats.get("atk_flat", ""),
        "def_flat": stats.get("def_flat", ""),
        "em_flat": stats.get("em_flat", ""),
        "cr": stats.get("cr", ""),
        "cd": stats.get("cd", ""),
        "er": stats.get("er", ""),
    }


def _normalize_weapon_tipo(raw: Any) -> str:
    s = str(raw or "Spada").strip()
    if s in TIPI_ARMA:
        return s
    low = s.lower()
    if "claymore" in low:
        return "Claymore"
    if "sword" in low or "spada" in low:
        return "Spada"
    if "bow" in low or "arco" in low:
        return "Arco"
    if "polearm" in low or "lance" in low or "lancia" in low:
        return "Lancia"
    if "catalyst" in low or "catalizzatore" in low:
        return "Catalizzatore"
    for t in TIPI_ARMA:
        if t.lower() == low:
            return t
    return "Spada"


def _extract_weapon(blob: dict) -> Optional[dict]:
    w = blob.get("weapon") or blob.get("equip") or blob.get("Weapon")
    if not isinstance(w, dict):
        return None
    nome = str(w.get("nome") or w.get("name") or "").strip()
    if not nome:
        return None
    tipo = _normalize_weapon_tipo(w.get("tipo") or w.get("typeName") or w.get("weaponType") or "Spada")
    liv = w.get("livello") or w.get("level") or 1
    stelle = w.get("stelle") or w.get("rankLevel") or w.get("maxLevel") or 5
    try:
        liv = int(liv)
    except (TypeError, ValueError):
        liv = 1
    try:
        stelle = min(5, max(1, int(stelle)))
    except (TypeError, ValueError):
        stelle = 5
    return {
        "nome": nome,
        "tipo": tipo,
        "livello": liv,
        "stelle": stelle,
        "atk_base": w.get("atk_base") or w.get("atk") or "",
        "stat_secondaria": str(w.get("stat_secondaria") or "")[:48],
        "valore_stat": w.get("valore_stat") or "",
    }


def _strip_json_text(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("\ufeff"):
        text = text[1:].lstrip()
    return text


def parse_pasted_payload(raw: str) -> dict:
    """
    Parsa il testo incollato: deve essere JSON oggetto o array (usa il primo elemento se array di personaggi).

    Raises:
        ImportParseError: JSON invalido o contenuto inutilizzabile.
    """
    text = _strip_json_text(raw)
    if not text:
        raise ImportParseError("Incolla prima del testo o JSON.")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ImportParseError(f"JSON non valido: {e}") from e

    if isinstance(data, list):
        dicts = [x for x in data if isinstance(x, dict)]
        if not dicts:
            raise ImportParseError("Array JSON: serve almeno un oggetto personaggio.")
        valid: List[Tuple[dict, dict]] = []
        for item in dicts:
            ch = _blob_to_internal_character(item)
            if ch.get("nome"):
                valid.append((item, ch))
        if not valid:
            raise ImportParseError("Array JSON: nessun personaggio con nome valido.")
        blob, char = valid[0]
        weapon = _extract_weapon(blob)
    elif isinstance(data, dict):
        blob = _pick_character_blob(data)
        char = _blob_to_internal_character(blob)
        weapon = _extract_weapon(data) if isinstance(data.get("weapon"), dict) else _extract_weapon(blob)
    else:
        raise ImportParseError("Il JSON deve essere un oggetto o un array.")

    if not char.get("nome"):
        raise ImportParseError("Nome personaggio mancante nel JSON.")

    out = {
        "version": data.get("version", 1) if isinstance(data, dict) else 1,
        "source": (data.get("source") if isinstance(data, dict) else None) or "clipboard",
        "character": char,
        "weapon": weapon,
        "raw_candidates": None,
    }
    if isinstance(data, dict):
        cand: List[dict] = []
        _collect_avatar_like_dicts(data, cand)
        cand.sort(key=_avatar_quality, reverse=True)
        unique: List[dict] = []
        seen_n = set()
        for c in cand:
            ch = _blob_to_internal_character(c)
            n = ch.get("nome")
            if n and n not in seen_n:
                seen_n.add(n)
                unique.append(ch)
        if len(unique) > 1:
            out["raw_candidates"] = unique
    elif isinstance(data, list):
        dicts = [x for x in data if isinstance(x, dict)]
        scored: List[Tuple[int, dict, dict]] = []
        for item in dicts:
            ch = _blob_to_internal_character(item)
            if ch.get("nome"):
                scored.append((_avatar_quality(item), item, ch))
        scored.sort(key=lambda t: t[0], reverse=True)
        uniq: List[dict] = []
        sn = set()
        for _q, _item, ch in scored:
            if ch["nome"] not in sn:
                sn.add(ch["nome"])
                uniq.append(ch)
        if len(uniq) > 1:
            out["raw_candidates"] = uniq

    return out


def map_to_form_personaggio(internal_char: dict) -> dict:
    """Dizionario personaggio già con chiavi form GUI/API."""
    return {k: internal_char.get(k, "") for k in ("nome", "livello", "elemento", "hp_flat", "atk_flat", "def_flat", "em_flat", "cr", "cd", "er")}


def build_forms_for_salva_completo(parsed: dict) -> Tuple[dict, dict, dict, dict]:
    """
    Da output ``parse_pasted_payload`` → tuple accettata da ``salva_completo``.
    Costellazioni / talenti: default neutri; equip manufatti: non inclusi (None).
    """
    c = parsed["character"]
    fp = map_to_form_personaggio(c)
    fp["livello"] = c.get("livello", 1)

    weapon = parsed.get("weapon") or {}
    fa = {
        "nome": weapon.get("nome", ""),
        "tipo": weapon.get("tipo", "Spada"),
        "livello": weapon.get("livello", 1),
        "stelle": weapon.get("stelle", 5),
        "atk_base": weapon.get("atk_base", ""),
        "stat_secondaria": weapon.get("stat_secondaria", ""),
        "valore_stat": weapon.get("valore_stat", ""),
    }

    fc = {f"c{i}": "0" for i in range(1, 7)}
    ft = {k: "-" for k in ("aa", "skill", "burst", "pas1", "pas2", "pas3", "pas4")}
    return fp, fa, fc, ft


def apply_manual_import(
    service: Any,
    parsed: dict,
    selected_id: Optional[int],
    *,
    touch_equipment: bool = False,
) -> int:
    """
    Salva tramite AppService.salva_completo. ``touch_equipment=False`` lascia manufatti invariati (come API web).
    """
    fp, fa, fc, ft = build_forms_for_salva_completo(parsed)
    feq = None if not touch_equipment else {s: None for s in ("fiore", "piuma", "sabbie", "calice", "corona")}
    return service.salva_completo(selected_id, fp, fa, fc, ft, feq)


def preview_summary(parsed: dict) -> str:
    c = parsed["character"]
    lines = [
        f"Nome: {c.get('nome')}",
        f"Livello: {c.get('livello')} | Elemento: {c.get('elemento')}",
        f"HP: {c.get('hp_flat')} | ATK: {c.get('atk_flat')} | DEF: {c.get('def_flat')}",
        f"EM: {c.get('em_flat')} | CR: {c.get('cr')} | CD: {c.get('cd')} | ER: {c.get('er')}",
    ]
    w = parsed.get("weapon")
    if w:
        lines.append(f"Arma: {w.get('nome')} ({w.get('tipo')}) Lv.{w.get('livello')} ★{w.get('stelle')}")
    else:
        lines.append("Arma: (nessuna dal JSON — resterà vuota o da compilare)")
    return "\n".join(lines)


def list_character_choices(parsed: dict) -> List[dict]:
    """Lista nomi per selezione se ``parse_pasted_payload`` ha trovato più personaggi."""
    cand = parsed.get("raw_candidates")
    if cand:
        return cand
    return [parsed["character"]]

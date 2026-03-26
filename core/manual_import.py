"""
Import manuale di dati personaggio da testo/JSON incollato (senza login, senza scraping).

Flusso pensato: l’utente copia dal browser (es. risposta JSON da DevTools) o incolla un JSON
nel formato documentato qui, oppure un dizionario “piatto” con chiavi alias.

Il parser accetta anche incolla “sporco”: testo attorno al JSON, markdown ``` fence,
virgole finali, virgolette tipografiche, prefissi anti-XSSI, blocchi annidati
(estrazione del valore JSON bilanciato più promettente).

L’output è compatibile con ``PersonaggioService.salva_completo`` tramite
``build_forms_for_salva_completo`` + ``apply_manual_import``.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from config import TIPI_ARMA

JsonValue = Union[dict, list, str, int, float, bool, None]

# Tipi arma numerici (API HoYoLab / game record).
_HOYO_WEAPON_TYPE_INT: Dict[int, str] = {
    1: "Spada",
    10: "Catalizzatore",
    11: "Claymore",
    12: "Arco",
    13: "Lancia",
}

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
    "39": ("em_flat", False),  # varianti client / dump4969
    "40": ("em_flat", False),
    "20": ("cr", True),  # fraction → percent
    "2008": ("cr", True),
    "22": ("cd", True),
    "2009": ("cd", True),
    "23": ("er", True),
    "2010": ("er", True),
    "11": ("er", True),  # ER alternativo in alcuni dump
    "2007": ("er", True),
    "26": ("er", True),
    "29": ("er", True),
}


class ImportParseError(ValueError):
    """Testo non JSON valido o struttura non riconosciuta."""


# Prefissi che a volte precedono il corpo JSON nelle risposte web
_XSSI_PREFIXES = (")]}'\n", ")]}'\r\n", "while(1);", "while(1);\n")


def _coerce_stat_number(val: Any) -> Optional[float]:
    """Accetta int/float, stringhe con virgole (migliaia o decimale), % e spazi."""
    if val is None:
        return None
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        if isinstance(val, float) and math.isnan(val):
            return None
        return float(val)
    s = str(val).strip().replace("\u00a0", " ").replace("%", "").strip()
    if not s or s in ("-", "—", "n/a", "N/A"):
        return None
    s = s.replace(" ", "")
    # decimale: 1,5 (EU) | 18,500 (migliaia) | 1.250,5 (EU) | 1,250.5 (US)
    if "," in s and "." not in s:
        parts = s.split(",")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            a, b = parts[0], parts[1]
            if len(b) <= 2:
                s = f"{a}.{b}"
            elif len(b) == 3 and len(a) <= 4:
                s = a + b
            else:
                s = s.replace(",", "")
        else:
            s = s.replace(",", "")
    elif "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        x = float(s)
    except ValueError:
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return x


def _norm_pct(val: Any, likely_fraction: bool) -> Optional[float]:
    x = _coerce_stat_number(val)
    if x is None:
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
    # Solo cifre: incerto tra API diverse → default neutro
    if s.isdigit():
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
            cn = _coerce_stat_number(v)
            if cn is not None:
                try:
                    out[field] = int(round(cn))
                except (OverflowError, ValueError):
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
    fk = _flatten_stat_keys(d)
    if any(fk.get(k) not in (None, "") for k in ("hp_flat", "atk_flat", "def_flat", "em_flat", "cr", "cd", "er")):
        s += 2
    return s


def _character_blob_has_name(blob: dict) -> bool:
    nome = (
        blob.get("nome")
        or blob.get("name")
        or blob.get("nickname")
        or blob.get("avatarName")
    )
    return bool(str(nome or "").strip())


def _is_collectable_avatar_dict(d: dict) -> bool:
    """
    Include blocchi “magri” (solo nome o nome+livello) così import incompleti restano utilizzabili;
    richiede un nome con almeno 2 caratteri per evitare rumore.
    """
    if _score_avatar_candidate(d) >= 4:
        return True
    if not _character_blob_has_name(d):
        return False
    nome = str(
        d.get("nome") or d.get("name") or d.get("nickname") or d.get("avatarName") or ""
    ).strip()
    if len(nome) < 2:
        return False
    if any(
        k in d
        for k in ("level", "livello", "expLevel", "fightPropMap", "propMap", "fight_prop_map")
    ):
        return True
    if any(_flatten_stat_keys(d).get(k) not in (None, "") for k in set(_STAT_ALIASES.values())):
        return True
    # Solo nome: ultima risorsa per incolla incompleto
    return True


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
        if _is_collectable_avatar_dict(obj):
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
    nome = _sanitize_hoyolab_character_name(str(nome).strip())
    livello = blob.get("livello") if blob.get("livello") is not None else blob.get("level") or blob.get("expLevel") or 1
    try:
        livello = int(livello)
    except (TypeError, ValueError):
        livello = 1

    elemento = _normalize_element(
        blob.get("elemento")
        or blob.get("element")
        or blob.get("elemType")
        or blob.get("Element")
        or blob.get("elementType")
    )

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


def _weapon_tipo_from_hoyo_int(code: Any) -> Optional[str]:
    try:
        i = int(code)
    except (TypeError, ValueError):
        return None
    return _HOYO_WEAPON_TYPE_INT.get(i)


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


def _sanitize_hoyolab_character_name(raw: Any) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    if "#Viaggiat" in s or "{M#" in s or "{F#" in s:
        return "Traveler"
    return s


def _costellazioni_form_from_actived(n: Any) -> Dict[str, str]:
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 0
    n = max(0, min(6, n))
    return {f"c{i}": ("1" if i <= n else "0") for i in range(1, 7)}


def _extract_weapon(blob: dict) -> Optional[dict]:
    w = (
        blob.get("weapon")
        or blob.get("equip")
        or blob.get("Weapon")
        or blob.get("equipWeapon")
        or blob.get("weaponData")
    )
    if not isinstance(w, dict):
        return None
    nome = str(w.get("nome") or w.get("name") or "").strip()
    if not nome:
        return None
    tipo_raw = w.get("tipo") or w.get("typeName") or w.get("weaponType") or w.get("weapon_type") or w.get("type")
    from_int = _weapon_tipo_from_hoyo_int(tipo_raw)
    if from_int:
        tipo = from_int
    else:
        tipo = _normalize_weapon_tipo(tipo_raw or "Spada")
    liv = w.get("livello") or w.get("level") or 1
    stelle = w.get("stelle") or w.get("rankLevel") or w.get("maxLevel") or w.get("rarity") or 5
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


def _strip_xssi_prefix(text: str) -> str:
    t = text.lstrip()
    for p in _XSSI_PREFIXES:
        if t.startswith(p):
            return t[len(p) :].lstrip()
    return text


def _normalize_quotes_and_dashes(text: str) -> str:
    """Sostituisce caratteri tipografici comuni dal copia-incolla."""
    return (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u00ab", '"')
        .replace("\u00bb", '"')
    )


_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*([\s\S]*?)```", re.MULTILINE)


def _unwrap_markdown_fences(text: str) -> str:
    m = _FENCE_RE.search(text)
    if m:
        inner = m.group(1).strip()
        if inner:
            return inner
    return text


def _remove_trailing_commas(text: str) -> str:
    """Rimuove virgole illegali prima di } o ] (incolla sporco)."""
    out = text
    for _ in range(64):
        nxt = re.sub(r",(\s*[}\]])", r"\1", out)
        if nxt == out:
            break
        out = nxt
    return out


def _extract_balanced_json_fragment(text: str, start: int) -> Optional[Tuple[str, int]]:
    """
    Da ``start`` su ``{`` o ``[``, restituisce (frammento, indice dopo la chiusura) o None.
    Rispetta stringhe JSON con virgolette doppie e escape.
    """
    if start < 0 or start >= len(text) or text[start] not in "{[":
        return None
    depth = 1
    in_string = False
    escape = False
    for j in range(start + 1, len(text)):
        ch = text[j]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
            if depth == 0:
                return text[start : j + 1], j + 1
    return None


def _iter_json_substrings(text: str) -> List[str]:
    """Tutti gli oggetti/array top-level bilanciati (anche annidati nel testo)."""
    found: List[str] = []
    seen: set[str] = set()
    i = 0
    while i < len(text):
        if text[i] in "{[":
            got = _extract_balanced_json_fragment(text, i)
            if got:
                frag, end = got
                if frag not in seen:
                    seen.add(frag)
                    found.append(frag)
                i = end
                continue
        i += 1
    # Più grandi prima: spesso contengono il payload completo
    found.sort(key=len, reverse=True)
    return found


def _try_json_loads(text: str) -> Any:
    return json.loads(text)


def _unwrap_string_json_root(data: Any) -> Any:
    """Se il JSON è una stringa che contiene a sua volta JSON (export annidati), espande."""
    out: Any = data
    for _ in range(5):
        if not isinstance(out, str):
            return out
        s = out.strip()
        if len(s) < 2 or s[0] not in "{[" or s[-1] not in "}]":
            return out
        try:
            out = json.loads(s)
        except json.JSONDecodeError:
            return data if _ == 0 else out
    return out


def _decode_pasted_structures(text: str) -> Tuple[Any, List[str]]:
    """
    Restituisce (data_parsed, note_di_tentativo) o solleva l’ultimo JSONDecodeError.
    Prova: testo diretto, fence, xssi, virgole finali, sottostringhe bilanciate { } / [ ].
    """
    attempts: List[str] = []
    candidates: List[str] = []
    base = _strip_json_text(text)
    if not base:
        raise json.JSONDecodeError("empty", "", 0)

    chain = [
        base,
        _unwrap_markdown_fences(base),
        _normalize_quotes_and_dashes(_unwrap_markdown_fences(base)),
        _strip_xssi_prefix(_normalize_quotes_and_dashes(_unwrap_markdown_fences(base))),
    ]
    for step in chain:
        if step and step not in candidates:
            candidates.append(step)
    subs = _iter_json_substrings(base)
    for s in subs:
        if s not in candidates:
            candidates.append(s)
        fixed = _remove_trailing_commas(s)
        if fixed not in candidates:
            candidates.append(fixed)
        fq = _normalize_quotes_and_dashes(fixed)
        if fq not in candidates:
            candidates.append(fq)

    last_err: Optional[Exception] = None
    for cand in candidates:
        if not cand.strip():
            continue
        for version in (cand, _remove_trailing_commas(cand)):
            if not version.strip():
                continue
            try:
                data = _try_json_loads(version)
                attempts.append("ok")
                return data, attempts
            except json.JSONDecodeError as e:
                last_err = e
                attempts.append(str(e))
                continue
    if last_err:
        raise last_err
    raise json.JSONDecodeError("no candidate", text[:50], 0)


def _single_parsed_from_avatar_dict(av: dict) -> dict:
    """Un avatar dall’array ``data.avatars`` (HoYoLab) → struttura ``parsed`` singola."""
    blob = dict(av)
    char = _blob_to_internal_character(blob)
    if not char.get("nome"):
        raise ValueError("missing_avatar_name")
    weapon = _extract_weapon(blob)
    from core.hoyolab_import import weapon_min_present_in_avatar
    if not weapon_min_present_in_avatar(av):
        raise ValueError("missing_weapon_min")
    rel = av.get("relics")
    relics_raw: List[dict] = [x for x in rel] if isinstance(rel, list) else []
    relics_raw = [x for x in relics_raw if isinstance(x, dict)]
    return {
        "version": 1,
        "source": "hoyolab",
        "bulk": False,
        "character": char,
        "weapon": weapon,
        "costellazioni_form": _costellazioni_form_from_actived(av.get("actived_constellation_num")),
        "relics_raw": relics_raw,
        "raw_candidates": None,
    }


def parse_pasted_payload(raw: str) -> dict:
    """
    Parsa il testo incollato: JSON oggetto o array; tollera rumore attorno al JSON.

    Raises:
        ImportParseError: nessun JSON decodificabile o contenuto inutilizzabile.
    """
    text = _strip_json_text(raw)
    if not text:
        raise ImportParseError("Incolla prima del testo o JSON.")

    try:
        data, _attempts = _decode_pasted_structures(text)
    except json.JSONDecodeError as e:
        raise ImportParseError(
            "Non sono riuscito a leggere dati strutturati nell’incolla. "
            "Controlla di aver copiato un blocco completo dal browser (senza tagli a metà). "
            f"Dettaglio: {e}"
        ) from e

    data = _unwrap_string_json_root(data)

    if isinstance(data, dict):
        if data.get("retcode") is not None and data.get("retcode") != 0:
            raise ImportParseError(
                f"Risposta API non OK (retcode={data.get('retcode')}). "
                "Copia la risposta JSON completa quando retcode è 0."
            )
        inner = data.get("data")
        if isinstance(inner, dict):
            avatars = inner.get("avatars")
            if (
                isinstance(avatars, list)
                and len(avatars) > 0
                and all(isinstance(a, dict) for a in avatars)
            ):
                from core.hoyolab_import import validate_hoyolab_bulk_envelope

                validate_hoyolab_bulk_envelope(data)
                imports: List[dict] = []
                parse_skips: List[dict] = []
                for i, av in enumerate(avatars):
                    try:
                        imports.append(_single_parsed_from_avatar_dict(av))
                    except ValueError as e:
                        # Non blocchiamo tutto il bulk: scartiamo solo l'avatar problematico.
                        # (il parser è resiliente a JSON parziali)
                        try:
                            nm = _sanitize_hoyolab_character_name(
                                av.get("name") or av.get("nome") or av.get("nickname") or av.get("avatarName") or ""
                            )
                        except Exception:
                            nm = ""
                        parse_skips.append(
                            {
                                "index": i,
                                "nome": nm or None,
                                "reason": str(e) or "unknown_skip",
                            }
                        )
                        continue
                if not imports:
                    raise ImportParseError(
                        "Nessun personaggio importabile in data.avatars (tutti scartati)."
                    )
                from core.hoyolab_import import enrich_import_item_flags

                for imp in imports:
                    enrich_import_item_flags(imp)
                first = imports[0]
                return {
                    "version": 1,
                    "source": "hoyolab",
                    "bulk": True,
                    "character": first["character"],
                    "weapon": first["weapon"],
                    "costellazioni_form": first.get("costellazioni_form"),
                    "relics_raw": first.get("relics_raw") or [],
                    "raw_candidates": None,
                    "imports": imports,
                    "parse_skips": parse_skips,
                }

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
        "relics_raw": [],
        "costellazioni_form": None,
        "bulk": False,
        "parse_skips": [],
    }
    if isinstance(blob, dict):
        rel = blob.get("relics")
        if isinstance(rel, list):
            out["relics_raw"] = [x for x in rel if isinstance(x, dict)]
        if blob.get("actived_constellation_num") is not None:
            out["costellazioni_form"] = _costellazioni_form_from_actived(
                blob.get("actived_constellation_num")
            )
    from core.hoyolab_import import enrich_import_item_flags

    enrich_import_item_flags(out)
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
    ov = parsed.get("costellazioni_form")
    if isinstance(ov, dict):
        for k in fc:
            if k in ov and str(ov[k]) in ("0", "1"):
                fc[k] = str(ov[k])
    ft = {k: "-" for k in ("aa", "skill", "burst", "pas1", "pas2", "pas3", "pas4")}
    return fp, fa, fc, ft


def apply_manual_import(
    service: Any,
    parsed: dict,
    selected_id: Optional[int],
    *,
    touch_equipment: Optional[bool] = None,
    import_mode: str = "replace",
) -> int:
    """
    Salva tramite ``salva_completo`` e applica manufatti secondo ``import_mode``:
    replace (default), update (merge per slot), append (solo inventario).

    ``touch_equipment=None`` → applica manufatti solo se ``relics_raw`` non è vuoto.
    """
    from core.hoyolab_import import (
        IMPORT_MODE_APPEND_DEDUP,
        IMPORT_MODE_APPEND_FORCE,
        normalize_import_mode,
    )

    if touch_equipment is None:
        touch_equipment = bool(parsed.get("relics_raw"))
    fp, fa, fc, ft = build_forms_for_salva_completo(parsed)
    new_id = service.salva_completo(selected_id, fp, fa, fc, ft, None)
    if touch_equipment and parsed.get("relics_raw"):
        mode = normalize_import_mode(import_mode)
        pid = None if mode in (IMPORT_MODE_APPEND_DEDUP, IMPORT_MODE_APPEND_FORCE) else new_id
        service.apply_hoyo_relic_import(pid, parsed["relics_raw"], mode)
    return new_id


def preview_summary(parsed: dict) -> str:
    from core.hoyolab_import import compute_hoyo_preview_stats

    stats = compute_hoyo_preview_stats(parsed)
    head = (
        f"Quantità: {stats['n_characters']} personaggi · {stats['n_weapons']} armi · "
        f"{stats['n_relics']} manufatti ({stats['n_relics_incomplete']} senza main+sub completi da HoYo).\n"
    )
    psk = parsed.get("parse_skips") or []
    if psk:
        head += f"Scartati in lettura JSON: {len(psk)} righe in data.avatars.\n"
    head += "\n"
    if parsed.get("bulk"):
        imps = parsed.get("imports") or []
        n = len(imps)
        incompleti = [((imp.get("character") or {}).get("nome") or "?") for imp in imps if (imp.get("n_relics_incomplete") or 0) > 0]
        lines = [
            head,
            f"Importazione gruppo HoYoLab: {n} personaggi.",
            "Modalità manufatti: scegli replace / update / append nel modulo prima di confermare.",
            "Elenco:",
        ]
        for imp in imps[:15]:
            c = (imp.get("character") or {})
            nm = c.get("nome") or "?"
            lv = c.get("livello", "?")
            el = c.get("elemento") or "?"
            nrel = len(imp.get("relics_raw") or [])
            nin = imp.get("n_relics_incomplete") or 0
            lines.append(f"  • {nm} — Lv.{lv} {el} — {nrel} manufatti ({nin} incompleti)")
        if incompleti:
            lines.append("Incompleti: " + ", ".join(incompleti[:10]) + (" ..." if len(incompleti) > 10 else ""))
        if n > 15:
            lines.append(f"  … altri {n - 15} personaggi.")
        if parsed.get("parse_skips"):
            skip_names = []
            for s in parsed.get("parse_skips") or []:
                nm = s.get("nome") or ""
                rs = s.get("reason") or ""
                if nm:
                    skip_names.append(f"{nm}({rs})")
            if skip_names:
                lines.append("Scartati (lettura): " + ", ".join(skip_names[:8]) + (" ..." if len(skip_names) > 8 else ""))
        return "\n".join(lines)
    c = parsed["character"]
    lines = [
        head,
        f"Nome: {c.get('nome')}",
        f"Livello: {c.get('livello')} | Elemento: {c.get('elemento')}",
        f"HP: {c.get('hp_flat')} | ATK: {c.get('atk_flat')} | DEF: {c.get('def_flat')}",
        f"EM: {c.get('em_flat')} | CR: {c.get('cr')} | CD: {c.get('cd')} | ER: {c.get('er')}",
    ]
    w = parsed.get("weapon")
    if w:
        lines.append(f"Arma: {w.get('nome')} ({w.get('tipo')}) Lv.{w.get('livello')} ★{w.get('stelle')}")
    else:
        lines.append("Arma: (non trovata nei dati copiati — resterà vuota o da compilare)")
    nr = len(parsed.get("relics_raw") or [])
    if nr:
        lines.append(f"Manufatti nell’incolla: {nr} pezzi (verranno importati negli slot)")
    return "\n".join(lines)


def list_character_choices(parsed: dict) -> List[dict]:
    """Lista nomi per selezione se ``parse_pasted_payload`` ha trovato più personaggi."""
    if parsed.get("bulk"):
        return [i["character"] for i in (parsed.get("imports") or []) if i.get("character")]
    cand = parsed.get("raw_candidates")
    if cand:
        return cand
    return [parsed["character"]]

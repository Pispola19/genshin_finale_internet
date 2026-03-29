"""
Validazione record pipeline: campi obbligatori, range, coerenza con config app.
"""
from __future__ import annotations

from typing import Any, List, Tuple

from config import ELEMENTI, STATS, TIPI_ARMA

from tools.pipeline.normalize import normalize_slot

SLOT_ORDER = ("fiore", "piuma", "sabbie", "calice", "corona")


def _err(msg: str) -> Tuple[bool, str]:
    return False, msg


def _ok() -> Tuple[bool, str]:
    return True, ""


def validate_personaggio(rec: dict) -> Tuple[bool, str]:
    if not isinstance(rec, dict):
        return _err("Record personaggio non è un oggetto JSON.")
    nome = (rec.get("nome") or "").strip()
    if len(nome) < 2:
        return _err("Personaggio: nome obbligatorio (min 2 caratteri).")
    el = rec.get("elemento") or ""
    if el not in ELEMENTI:
        return _err(f"Personaggio: elemento non valido ({el!r}). Valori: {', '.join(ELEMENTI)}.")
    arma = rec.get("arma") or ""
    if arma and arma not in TIPI_ARMA:
        return _err(f"Personaggio: tipo arma non valido ({arma!r}). Valori: {', '.join(TIPI_ARMA)}.")
    bs = rec.get("base_stats") or {}
    if not isinstance(bs, dict):
        return _err("Personaggio: base_stats deve essere un oggetto.")
    for k in ("hp", "atk", "def"):
        v = bs.get(k)
        if v is None:
            continue
        try:
            n = float(v)
        except (TypeError, ValueError):
            return _err(f"Personaggio: base_stats.{k} non numerico.")
        if n < 0 or n > 100_000:
            return _err(f"Personaggio: base_stats.{k} fuori range plausibile (0–100000).")
    return _ok()


def validate_arma(rec: dict) -> Tuple[bool, str]:
    if not isinstance(rec, dict):
        return _err("Record arma non è un oggetto JSON.")
    nome = (rec.get("nome") or "").strip()
    if len(nome) < 2:
        return _err("Arma: nome obbligatorio (min 2 caratteri).")
    tipo = rec.get("tipo") or ""
    if tipo not in TIPI_ARMA:
        return _err(f"Arma: tipo non valido ({tipo!r}). Valori: {', '.join(TIPI_ARMA)}.")
    r = rec.get("rarita")
    if r is not None:
        try:
            ri = int(r)
        except (TypeError, ValueError):
            return _err("Arma: rarità non intera.")
        if ri < 1 or ri > 5:
            return _err("Arma: rarità deve essere 1–5.")
    atk = rec.get("atk_base")
    if atk is not None:
        try:
            af = float(atk)
        except (TypeError, ValueError):
            return _err("Arma: atk_base non numerico.")
        if af < 1 or af > 950:
            return _err("Arma: atk_base fuori range plausibile (1–950).")
    stat = (rec.get("stat_secondaria") or "").strip()
    if stat and stat not in STATS:
        return _err(f"Arma: stat_secondaria non in elenco STATS ({stat!r}).")
    vs = rec.get("valore_stat")
    if vs is not None and stat:
        try:
            vf = float(vs)
        except (TypeError, ValueError):
            return _err("Arma: valore_stat non numerico.")
        if vf < 0 or vf > 500:
            return _err("Arma: valore_stat fuori range plausibile (0–500).")
    return _ok()


def validate_manufatto(rec: dict) -> Tuple[bool, str]:
    if not isinstance(rec, dict):
        return _err("Record manufatto non è un oggetto JSON.")
    sn = (rec.get("set") or "").strip()
    if len(sn) < 2:
        return _err("Manufatto: nome set obbligatorio.")
    slot = normalize_slot(str(rec.get("slot", "")))
    if slot not in SLOT_ORDER:
        return _err(f"Manufatto: slot non valido ({rec.get('slot')!r}). Usa: {', '.join(SLOT_ORDER)}.")
    pz = (rec.get("pezzo") or "").strip()
    if len(pz) < 1:
        return _err("Manufatto: nome pezzo obbligatorio.")
    return _ok()


def validate_batch(
    data: Any,
) -> Tuple[List[dict], List[dict], List[dict], List[str]]:
    """
    Accetta:
    - { "personaggi": [...], "armi": [...], "manufatti": [...] }
    - oppure lista di oggetti con campo \"_type\": \"personaggio\"|\"arma\"|\"manufatto\"
    Ritorna (personaggi_ok, armi_ok, manufatti_ok, errori_globali).
    """
    errors: List[str] = []
    pg: List[dict] = []
    ar: List[dict] = []
    mf: List[dict] = []

    if isinstance(data, dict) and any(k in data for k in ("personaggi", "armi", "manufatti")):
        pg = list(data.get("personaggi") or [])
        ar = list(data.get("armi") or [])
        mf = list(data.get("manufatti") or [])
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append(f"Elemento [{i}]: non è un oggetto.")
                continue
            t = (item.get("_type") or item.get("type") or "").strip().lower()
            if t in ("personaggio", "character"):
                pg.append(item)
            elif t in ("arma", "weapon"):
                ar.append(item)
            elif t in ("manufatto", "artifact", "artefatto"):
                mf.append(item)
            else:
                errors.append(f"Elemento [{i}]: _type mancante o sconosciuto.")
    else:
        errors.append("Formato file: atteso oggetto con chiavi personaggi/armi/manufatti o array con _type.")
        return [], [], [], errors

    return pg, ar, mf, errors

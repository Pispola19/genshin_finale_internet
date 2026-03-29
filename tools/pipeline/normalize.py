"""
Normalizzazione record pipeline (allineata a specifica: trim, spazi, prima maiuscola + resto minuscolo).
"""
from __future__ import annotations

from typing import Any, Mapping

from config import STATS
from core.nome_normalization import (
    canonicalizza_nome_arma,
    canonicalizza_nome_personaggio,
    normalize_manufatto_display_label,
)

JsonMap = Mapping[str, Any]

SLOT_ALIASES = {
    "fiore": "fiore",
    "flower": "fiore",
    "piuma": "piuma",
    "feather": "piuma",
    "plume": "piuma",
    "sabbie": "sabbie",
    "sands": "sabbie",
    "sand": "sabbie",
    "calice": "calice",
    "goblet": "calice",
    "corona": "corona",
    "circlet": "corona",
}

ELEMENT_ALIASES = {
    "pyro": "Pyro",
    "hydro": "Hydro",
    "electro": "Electro",
    "cryo": "Cryo",
    "anemo": "Anemo",
    "geo": "Geo",
    "dendro": "Dendro",
}

WEAPON_TYPE_ALIASES = {
    "spada": "Spada",
    "sword": "Spada",
    "claymore": "Claymore",
    "lancia": "Lancia",
    "polearm": "Lancia",
    "lance": "Lancia",
    "catalizzatore": "Catalizzatore",
    "catalyst": "Catalizzatore",
    "arco": "Arco",
    "bow": "Arco",
}


def normalize_label(s: str) -> str:
    return normalize_manufatto_display_label((s or "").strip())


def normalize_slot(raw: str) -> str:
    k = (raw or "").strip().lower()
    if k in SLOT_ALIASES:
        return SLOT_ALIASES[k]
    return k


def normalize_element(raw: str) -> str:
    k = (raw or "").strip().lower()
    if k in ELEMENT_ALIASES:
        return ELEMENT_ALIASES[k]
    return normalize_label(raw or "")


def normalize_weapon_tipo(raw: str) -> str:
    k = (raw or "").strip().lower()
    if k in WEAPON_TYPE_ALIASES:
        return WEAPON_TYPE_ALIASES[k]
    return normalize_label(raw or "")


def normalize_stat_secondaria(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    st_up = s.upper().replace(" ", "_")
    if (
        st_up in ("ER", "ER%", "ENERGY_RECHARGE", "RICARICA_ENERGIA", "ENERGY_RECHARGE%")
        or "ENERGY_RECHARGE" in st_up
        or st_up.startswith("RICARICA")
    ):
        return "ER%"
    sl = s.lower()
    for st in STATS:
        if st.lower() == sl:
            return st
    return normalize_label(s)


def normalize_personaggio_record(d: JsonMap) -> dict[str, Any]:
    out: dict[str, Any] = {}
    raw_nome = " ".join(str(d.get("nome", "")).split())
    out["nome"] = canonicalizza_nome_personaggio(raw_nome) or normalize_label(raw_nome)
    out["elemento"] = normalize_element(str(d.get("elemento", "")))
    out["arma"] = normalize_weapon_tipo(str(d.get("arma", "")))
    bs = d.get("base_stats") or {}
    if isinstance(bs, Mapping):
        out["base_stats"] = {
            "hp": bs.get("hp"),
            "atk": bs.get("atk"),
            "def": bs.get("def"),
        }
    else:
        out["base_stats"] = {"hp": None, "atk": None, "def": None}
    if "scaling" in d:
        out["scaling"] = d.get("scaling")
    return out


def normalize_arma_record(d: JsonMap) -> dict[str, Any]:
    raw_n = " ".join(str(d.get("nome", "")).split())
    nome_ar = canonicalizza_nome_arma(raw_n) or normalize_label(raw_n)
    return {
        "nome": nome_ar,
        "tipo": normalize_weapon_tipo(str(d.get("tipo", ""))),
        "rarita": d.get("rarita") or d.get("rarity"),
        "atk_base": d.get("atk_base"),
        "stat_secondaria": normalize_stat_secondaria(str(d.get("stat_secondaria", "") or "")),
        "valore_stat": d.get("valore_stat"),
    }


def normalize_manufatto_record(d: JsonMap) -> dict[str, Any]:
    slot_raw = str(d.get("slot", ""))
    set_name = str(d.get("set", d.get("set_nome", "")))
    pezzo = str(d.get("pezzo", d.get("nome_pezzo", "")))
    return {
        "set": normalize_label(set_name),
        "slot": normalize_slot(slot_raw),
        "pezzo": normalize_label(pezzo),
        "bonus_2p": _norm_optional_text(d.get("bonus_2p")),
        "bonus_4p": _norm_optional_text(d.get("bonus_4p")),
    }


def _norm_optional_text(v: Any) -> str:
    if v is None or v == "":
        return ""
    return normalize_label(str(v))

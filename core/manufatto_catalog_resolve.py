"""
Catalogo manufatti: merge statico (codice/registry) + estensioni DB; normalizzazione e dedup.
"""
from __future__ import annotations

import sqlite3
from typing import List, Optional, Tuple

from core.manufatti_pezzi_suggerimenti_extra import resolve_pezzo_alias_to_canonical
from core.nome_normalization import norm_key_nome, normalize_manufatto_display_label
from db.artifact_catalog import (
    CATALOGO_ARTEFATTI,
    SLOT_ORDER,
    lista_set,
    pezzi_catalogo_per_set_e_slot,
)
from db.repositories import CatalogoManufattiEstensioniRepository


def merged_lista_set(conn_art: sqlite3.Connection) -> List[str]:
    by_k: dict[str, str] = {norm_key_nome(s): s for s in lista_set()}
    for s in CatalogoManufattiEstensioniRepository.distinct_set_nomi(conn_art):
        k = norm_key_nome(s)
        if k not in by_k:
            by_k[k] = s
    return sorted(by_k.values(), key=str.lower)


def merged_pezzi_per_set_slot(conn_art: sqlite3.Connection, set_nome: str, slot: str) -> List[str]:
    """
    Suggerimenti mostrati in UI: solo nomi canonici (catalogo statico ∪ estensioni DB).
    Le varianti EN restano gestite in ``canonical_pezzo_name`` via ``resolve_pezzo_alias_to_canonical``.
    """
    static = pezzi_catalogo_per_set_e_slot(set_nome, slot)
    ext = CatalogoManufattiEstensioniRepository.pezzi_for_set_slot(conn_art, set_nome, slot)
    by_k: dict[str, str] = {}
    for p in static:
        by_k[norm_key_nome(p)] = p
    for p in ext:
        k = norm_key_nome(p)
        if k not in by_k:
            by_k[k] = p
    return sorted(by_k.values(), key=str.lower)


def canonical_set_name(conn_art: sqlite3.Connection, user_input: str) -> str:
    disp = normalize_manufatto_display_label((user_input or "").strip())
    if not disp:
        return disp
    k = norm_key_nome(disp)
    for s in merged_lista_set(conn_art):
        if norm_key_nome(s) == k:
            return s
    return disp


def canonical_pezzo_name(conn_art: sqlite3.Connection, set_canon: str, slot: str, user_input: str) -> str:
    raw = (user_input or "").strip()
    if not raw:
        return raw
    alias_hit = resolve_pezzo_alias_to_canonical(set_canon, slot, raw)
    if alias_hit:
        return alias_hit
    disp = normalize_manufatto_display_label(raw)
    if not disp:
        return disp
    k = norm_key_nome(disp)
    for p in merged_pezzi_per_set_slot(conn_art, set_canon, slot):
        if norm_key_nome(p) == k:
            return p
    return disp


def _official_pezzo_wrong_slot_message(set_nome: str, slot: str, pezzo_key: str) -> Optional[str]:
    sk = norm_key_nome(set_nome)
    for sn, pezzi_tuple in CATALOGO_ARTEFATTI:
        if norm_key_nome(sn) != sk:
            continue
        for sl, pname in zip(SLOT_ORDER, pezzi_tuple):
            if norm_key_nome(pname) != pezzo_key:
                continue
            if sl != slot:
                return (
                    f"Il nome del pezzo è quello dello slot «{sl}» in questo set, "
                    f"non «{slot}». Scegli il nome corretto per lo slot oppure un nome personalizzato."
                )
            return None
        return None
    return None


def _is_official_set_and_pair(set_canon: str, slot: str, pezzo_canon: str) -> bool:
    want_s = norm_key_nome(set_canon)
    want_p = norm_key_nome(pezzo_canon)
    for sn, pezzi_tuple in CATALOGO_ARTEFATTI:
        if norm_key_nome(sn) != want_s:
            continue
        idx = SLOT_ORDER.index(slot) if slot in SLOT_ORDER else -1
        if idx < 0 or idx >= len(pezzi_tuple):
            return False
        return norm_key_nome(pezzi_tuple[idx]) == want_p
    return False


def register_manufatto_extension_if_needed(
    conn_art: sqlite3.Connection, set_canon: str, slot: str, pezzo_canon: str
) -> None:
    if _is_official_set_and_pair(set_canon, slot, pezzo_canon):
        return
    CatalogoManufattiEstensioniRepository.insert_ignore(conn_art, set_canon, slot, pezzo_canon)


def resolve_manufatto_set_pezzo_for_save(
    conn_art: sqlite3.Connection,
    set_nome_raw: str,
    nome_pezzo_raw: str,
    slot: str,
    *,
    register_extension: bool = True,
) -> Tuple[str, str]:
    """
    Normalizza, deduplica su catalogo (statico ∪ DB), registra estensione se necessario.
    Solleva ValueError se input non valido o pezzo ufficiale di altro slot.
    """
    slot_clean = (slot or "fiore").strip().lower()
    if slot_clean not in SLOT_ORDER:
        slot_clean = "fiore"

    s0 = (set_nome_raw or "").strip()
    n0 = (nome_pezzo_raw or "").strip()
    if not s0:
        raise ValueError("Il set manufatti è obbligatorio.")
    if not n0:
        raise ValueError("Il nome del pezzo è obbligatorio.")
    from core.validation import validate_testo_nome_visualizzabile

    ok_s, err_s = validate_testo_nome_visualizzabile(s0)
    if not ok_s:
        raise ValueError(f"Set manufatti: {err_s}")
    ok_n, err_n = validate_testo_nome_visualizzabile(n0)
    if not ok_n:
        raise ValueError(f"Nome pezzo: {err_n}")

    set_c = canonical_set_name(conn_art, s0)
    pezzo_c = canonical_pezzo_name(conn_art, set_c, slot_clean, n0)

    msg = _official_pezzo_wrong_slot_message(set_c, slot_clean, norm_key_nome(pezzo_c))
    if msg:
        raise ValueError(msg)

    if register_extension:
        register_manufatto_extension_if_needed(conn_art, set_c, slot_clean, pezzo_c)

    return set_c, pezzo_c

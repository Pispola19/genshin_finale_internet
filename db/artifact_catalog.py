"""
Funzioni catalogo manufatti: builtin in ``core.manufatti_ufficiali`` ∪ set approvati in registry.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from core.custom_registry import approved_sets_as_catalog_tuples
from core.manufatti_ufficiali import (
    CATALOGO_ARTEFATTI as _CATALOGO_BUILTIN,
    MAIN_STATS_PER_SLOT,
    SLOT_ORDER,
)

_built_keys = {sn.strip().lower() for sn, _ in _CATALOGO_BUILTIN}
_registry_extra = [
    t for t in approved_sets_as_catalog_tuples()
    if t[0].strip().lower() not in _built_keys
]
CATALOGO_ARTEFATTI: List[Tuple[str, Tuple[str, str, str, str, str]]] = list(_CATALOGO_BUILTIN) + _registry_extra

__all__ = [
    "CATALOGO_ARTEFATTI",
    "SLOT_ORDER",
    "MAIN_STATS_PER_SLOT",
    "lista_set",
    "pezzi_catalogo_per_set_e_slot",
    "filtra_per_slot",
    "filtra_progressivo",
    "cerca_nome_pezzo",
]


def lista_set() -> List[str]:
    """Lista unica di nomi set (ufficiali ∪ registry approvato), ordinata."""
    seen: set[str] = set()
    out: List[str] = []
    for set_nome, _ in CATALOGO_ARTEFATTI:
        ln = set_nome.strip().lower()
        if ln not in seen:
            seen.add(ln)
            out.append(set_nome)
    return sorted(out, key=str.lower)


def pezzi_catalogo_per_set_e_slot(set_nome: str, slot: str) -> List[str]:
    """Nomi pezzo ufficiali (catalogo) per set + slot; deduplicati, ordine stabile."""
    if not (set_nome or "").strip():
        return []
    idx = SLOT_ORDER.index(slot) if slot in SLOT_ORDER else 0
    want = (set_nome or "").strip().lower()
    seen = set()
    out: List[str] = []
    for sn, pezzi in CATALOGO_ARTEFATTI:
        if sn.strip().lower() != want:
            continue
        p = (pezzi[idx] or "").strip()
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def filtra_per_slot(slot: str) -> List[Tuple[str, str]]:
    """Ritorna [(set_nome, nome_pezzo), ...] per lo slot dato."""
    idx = SLOT_ORDER.index(slot) if slot in SLOT_ORDER else 0
    out = []
    seen = set()
    for set_nome, pezzi in CATALOGO_ARTEFATTI:
        nome_pezzo = pezzi[idx]
        key = (set_nome, nome_pezzo)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return sorted(out, key=lambda x: (x[0].lower(), x[1].lower()))


def filtra_progressivo(
    slot: str,
    set_partial: str = "",
    nome_partial: str = "",
    main_stat: str = "",
    extra_pairs: Optional[List[Tuple[str, str]]] = None,
) -> List[Tuple[str, str]]:
    """
    Filtraggio progressivo: set_partial, nome_partial, main_stat riducono la lista.
    Ritorna [(set_nome, nome_pezzo), ...].
    Se ``extra_pairs`` è valorizzato, unisce coppie (set, pezzo) aggiuntive (es. da DB).
    """
    candidati = list(filtra_per_slot(slot))
    if extra_pairs:
        seen = {(a.lower(), b.lower()) for a, b in candidati}
        for s, n in extra_pairs:
            key = (s.lower(), n.lower())
            if key not in seen:
                seen.add(key)
                candidati.append((s, n))
        candidati.sort(key=lambda x: (x[0].lower(), x[1].lower()))
    set_lower = set_partial.strip().lower()
    nome_lower = nome_partial.strip().lower()
    main_lower = main_stat.strip().lower()

    if set_lower:
        candidati = [(s, n) for s, n in candidati if set_lower in s.lower()]
    if nome_lower:
        candidati = [(s, n) for s, n in candidati if nome_lower in n.lower()]
    if main_lower:
        stats_validi = MAIN_STATS_PER_SLOT.get(slot, [])
        if stats_validi and main_lower not in [st.lower() for st in stats_validi]:
            pass
        elif main_lower:
            candidati = candidati

    return candidati


def cerca_nome_pezzo(nome: str) -> List[Tuple[str, str, str]]:
    """Cerca nome pezzo in tutto il catalogo. Ritorna [(set_nome, slot, nome_pezzo), ...]."""
    nome_lower = nome.strip().lower()
    if not nome_lower:
        return []
    out = []
    for set_nome, pezzi in CATALOGO_ARTEFATTI:
        for slot, nome_pezzo in zip(SLOT_ORDER, pezzi):
            if nome_lower in nome_pezzo.lower():
                out.append((set_nome, slot, nome_pezzo))
    return out

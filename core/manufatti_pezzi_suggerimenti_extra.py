"""
Alias e varianti (principalmente EN) per il **riconoscimento input** sul nome pezzo manufatto.

I dati EN provengono da ``manufatti_pezzi_en_by_fingerprint`` + alias manuali; in salvataggio
``resolve_pezzo_alias_to_canonical`` ricondurrà al canonico IT. La lista suggerimenti in UI
(``merged_pezzi_per_set_slot``) mostra solo italiano + estensioni DB; l’EN non compare nel datalist.

Aggiornare ``manufatti_pezzi_en_by_fingerprint.py`` quando si aggiungono set al catalogo.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from core.manufatti_pezzi_en_by_fingerprint import ENGLISH_PEZZI_BY_IT_FINGERPRINT
from core.manufatti_ufficiali import CATALOGO_ARTEFATTI, SLOT_ORDER
from core.nome_normalization import norm_key_nome

Row = Tuple[str, str, str, Tuple[str, ...]]


def _fingerprint_pezzi(pezzi: Tuple[str, str, str, str, str]) -> Tuple[str, str, str, str, str]:
    return tuple(norm_key_nome(p) for p in pezzi)


def _build_generated_rows() -> Tuple[Row, ...]:
    rows: List[Row] = []
    for set_nome, pezzi in CATALOGO_ARTEFATTI:
        fp = _fingerprint_pezzi(pezzi)
        en5 = ENGLISH_PEZZI_BY_IT_FINGERPRINT.get(fp)
        if not en5:
            continue
        for slot, itp, enp in zip(SLOT_ORDER, pezzi, en5):
            en_clean = (enp or "").strip()
            if not en_clean:
                continue
            if norm_key_nome(en_clean) == norm_key_nome(itp):
                continue
            rows.append((set_nome, slot, itp, (en_clean,)))
    return tuple(rows)


# Alias aggiuntivi (stesso canonico IT per quel set+slot). Utile per etichette storiche / community.
_MANUAL_PEZZO_ALIASES: Tuple[Row, ...] = (
    ("Reminiscenza di shimenawa", "fiore", "Fermaglio dorato", ("Golden Hairpin",)),
    ("Emblema dell'ombra colorata", "fiore", "Fiore intrecciato", ("Golden Hairpin",)),
    ("Reminiscenza di shimenawa", "sabbie", "Bussola di rame", ("Copper Compass",)),
)

_PEZZO_VARIANTI: Tuple[Row, ...] = _build_generated_rows() + _MANUAL_PEZZO_ALIASES


def _sk(set_nome: str) -> str:
    return norm_key_nome(set_nome or "")


def resolve_pezzo_alias_to_canonical(set_nome: str, slot: str, user_input: str) -> Optional[str]:
    """
    Se l'input coincide (per chiave normalizzata) con il canonico o una variante,
    restituisce la stringa **esatta** del catalogo IT; altrimenti None.
    """
    raw = (user_input or "").strip()
    if not raw:
        return None
    nk = norm_key_nome(raw)
    want_set = _sk(set_nome)
    slot_clean = (slot or "").strip().lower()
    for sn, sl, canon, variants in _PEZZO_VARIANTI:
        if _sk(sn) != want_set or sl != slot_clean:
            continue
        if nk == norm_key_nome(canon):
            return canon
        for v in variants:
            if nk == norm_key_nome(v):
                return canon
    return None


def etichette_suggerimento_extra(set_nome: str, slot: str) -> List[str]:
    """
    Etichette alias (es. EN) oltre al canonico IT — **non** incluse in ``merged_pezzi_per_set_slot``
    (UI suggerisce solo italiano); servono a test o strumenti. Il riconoscimento input usa
    ``resolve_pezzo_alias_to_canonical``.
    """
    out: List[str] = []
    seen: set[str] = set()
    want_set = _sk(set_nome)
    slot_clean = (slot or "").strip().lower()
    for sn, sl, _canon, variants in _PEZZO_VARIANTI:
        if _sk(sn) != want_set or sl != slot_clean:
            continue
        for v in variants:
            t = (v or "").strip()
            if not t:
                continue
            k = norm_key_nome(t)
            if k in seen:
                continue
            seen.add(k)
            out.append(t)
    return sorted(out, key=str.lower)


def indice_norm_varianti_per_set_slot() -> Dict[Tuple[str, str], str]:
    """Debug/test: (norm_set, slot) -> canonico per ogni riga definita."""
    m: Dict[Tuple[str, str], str] = {}
    for sn, sl, canon, variants in _PEZZO_VARIANTI:
        m[(_sk(sn), sl)] = canon
    return m

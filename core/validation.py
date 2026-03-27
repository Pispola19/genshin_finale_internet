"""Validazione input - funzioni piccole e specifiche."""
from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

from config import whitelist_strict_effective
from core.nome_normalization import canonicalizza_nome_arma, canonicalizza_nome_personaggio
from core.nomi_whitelist import (
    WHITELIST_ARMI_EFFECTIVE,
    WHITELIST_PERSONAGGI_EFFECTIVE,
    WHITELIST_SET_MANUFATTI,
)

_LOG = logging.getLogger(__name__)

# Blocca caratteri non latini (es. cinese, giapponese, coreano, cirillico, arabo, ecc.) per nomi mostrati in UI.
_NON_LATIN_DISPLAY = re.compile(
    r"[\u3040-\u30ff\u31f0-\u31ff"  # hiragana, katakana
    r"\u4e00-\u9fff\u3400-\u4dbf"  # CJK
    r"\uac00-\ud7af\u1100-\u11ff\u3130-\u318f"  # hangul
    r"\u0400-\u052f"  # cirillico
    r"\u0600-\u06ff\u0750-\u077f"  # arabo
    r"\u0590-\u05ff"  # ebraico
    r"\u0e00-\u0e7f"  # thai
    r"\u0900-\u097f]"  # devanagari
)


def validate_testo_nome_visualizzabile(testo: str) -> Tuple[bool, str]:
    """Rifiuta stringhe con script non latini (nomi personaggio, arma, set/pezzo manufatto in italiano)."""
    s = testo or ""
    if _NON_LATIN_DISPLAY.search(s):
        return (
            False,
            "Usa solo lettere latine (italiano/occidentale): non sono ammessi caratteri cinesi, giapponesi, coreani, cirillici, ecc.",
        )
    return True, ""


def parse_number(val, default=None, min_val=None, max_val=None) -> Optional[float]:
    """Converte stringa in numero. Ritorna default se invalido."""
    if val is None or val == "" or val == "-":
        return default
    s = str(val).strip().replace("%", "").replace(",", ".")
    if not s:
        return default
    try:
        n = float(s)
        if n == int(n):
            n = int(n)
    except (ValueError, TypeError):
        return default
    if min_val is not None and n < min_val:
        return default
    if max_val is not None and n > max_val:
        return default
    return n


def parse_stat_value(val) -> Optional[float]:
    """Parsa valore stat (CR, CD, ATK, ecc.)."""
    return parse_number(val, min_val=0, max_val=10000)


def validate_nome(nome: str, *, custom_confirm: bool = False) -> Tuple[bool, str]:
    """Valida nome personaggio. Fuori dall'elenco effettivo solo con conferma custom (strict) o con warning (dev)."""
    nome = canonicalizza_nome_personaggio(nome or "")
    if not nome:
        return False, "Il nome è obbligatorio."
    if len(nome) < 2:
        return False, "Il nome deve avere almeno 2 caratteri."
    ok, msg = validate_testo_nome_visualizzabile(nome)
    if not ok:
        return False, msg
    if nome in WHITELIST_PERSONAGGI_EFFECTIVE:
        return True, ""
    if custom_confirm:
        return True, ""
    strict = whitelist_strict_effective()
    if strict:
        return (
            False,
            "Il nome non è nell'elenco ufficiale né nel registro approvato. "
            "Usa la conferma esplicita «nome personalizzato» o aggiungi una voce approvata in custom_entities.json.",
        )
    _LOG.warning("Nome personaggio accettato senza conferma custom (GENSHIN_WHITELIST_STRICT=0): %r", nome)
    return True, ""


def validate_arma_nome(nome: str, *, custom_confirm: bool = False) -> Tuple[bool, str]:
    """Nome arma: vuoto consentito; se compilato deve essere nell'elenco effettivo o confermato come custom."""
    s = canonicalizza_nome_arma(nome or "")
    if not s:
        return True, ""
    ok, msg = validate_testo_nome_visualizzabile(s)
    if not ok:
        return False, msg
    if s in WHITELIST_ARMI_EFFECTIVE:
        return True, ""
    if custom_confirm:
        return True, ""
    strict = whitelist_strict_effective()
    if strict:
        return (
            False,
            "L'arma non è nell'elenco ufficiale né nel registro approvato. "
            "Conferma esplicitamente il nome personalizzato o estendi custom_entities.json.",
        )
    _LOG.warning("Nome arma accettato senza conferma custom (GENSHIN_WHITELIST_STRICT=0): %r", s)
    return True, ""


def validate_artefatto_set_e_pezzo(set_nome: str, nome_pezzo: str, slot: str) -> Tuple[bool, str]:
    """Set e nome pezzo manufatto: obbligatori e coerenti con catalogo (ufficiali ∪ set approvati nel registry)."""
    from db.artifact_catalog import SLOT_ORDER, pezzi_catalogo_per_set_e_slot

    s = (set_nome or "").strip()
    n = (nome_pezzo or "").strip()
    slot_clean = (slot or "fiore").strip().lower()
    if slot_clean not in SLOT_ORDER:
        slot_clean = "fiore"
    if not s:
        return False, "Il set manufatti è obbligatorio."
    ok, msg = validate_testo_nome_visualizzabile(s)
    if not ok:
        return False, f"Set manufatti: {msg}"
    if s not in WHITELIST_SET_MANUFATTI:
        return False, "Il set deve essere nell'elenco del catalogo (ufficiale o approvato nel registry esterno)."
    if not n:
        return False, "Il nome del pezzo è obbligatorio."
    ok, msg = validate_testo_nome_visualizzabile(n)
    if not ok:
        return False, f"Nome pezzo: {msg}"
    allowed = pezzi_catalogo_per_set_e_slot(s, slot_clean)
    if n not in allowed:
        return (
            False,
            "Il nome del pezzo non corrisponde al set e allo slot (catalogo ufficiale / registry approvato).",
        )
    return True, ""

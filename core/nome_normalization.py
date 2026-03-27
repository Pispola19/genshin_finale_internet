"""
Normalizzazione nomi personaggio e arma: spazi, case, duplicati logici.
"""
from __future__ import annotations

from personaggi_ufficiali import PERSONAGGI_UFFICIALI

from core.armi_ufficiali import ARMI_UFFICIALI
from core.custom_registry import approved_armi_names, approved_personaggi_names


def norm_key_nome(nome: str) -> str:
    """Chiave di uguaglianza: trim, spazi interni collassati, minuscolo."""
    return " ".join((nome or "").split()).lower()


def canonicalizza_nome_personaggio(nome: str) -> str:
    """
    Strip, collassa spazi; se corrisponde a whitelist/registry (case-insensitive),
    restituisce la grafia canonica del catalogo.
    """
    s = " ".join((nome or "").split())
    if not s:
        return s
    nk = s.lower()
    for o in PERSONAGGI_UFFICIALI:
        if " ".join(o.split()).lower() == nk:
            return o
    for o in sorted(approved_personaggi_names()):
        if " ".join(o.split()).lower() == nk:
            return " ".join(o.split())
    return s


def canonicalizza_nome_arma(nome: str) -> str:
    s = " ".join((nome or "").split())
    if not s:
        return s
    nk = s.lower()
    for o in ARMI_UFFICIALI:
        if " ".join(o.split()).lower() == nk:
            return o
    for o in sorted(approved_armi_names()):
        if " ".join(o.split()).lower() == nk:
            return " ".join(o.split())
    return s


def personaggio_e_ufficiale_o_registry(canonical: str) -> bool:
    if not (canonical or "").strip():
        return False
    if canonical in PERSONAGGI_UFFICIALI:
        return True
    return canonical in approved_personaggi_names()


def arma_e_ufficiale_o_registry(canonical: str) -> bool:
    if not (canonical or "").strip():
        return True
    if canonical in ARMI_UFFICIALI:
        return True
    return canonical in approved_armi_names()


def personaggio_richiede_conferma_custom(canonical: str) -> bool:
    """True se il nome (già canonical) non è in codice né registry approvato."""
    return bool(canonical.strip()) and not personaggio_e_ufficiale_o_registry(canonical)


def arma_richiede_conferma_custom(canonical: str) -> bool:
    """True se arma non vuota e non in codice/registry."""
    if not (canonical or "").strip():
        return False
    return not arma_e_ufficiale_o_registry(canonical)

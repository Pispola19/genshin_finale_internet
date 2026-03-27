"""
Whitelist unificate: personaggi, armi, set manufatti (catalogo effettivo in ``db.artifact_catalog``).
"""
from __future__ import annotations

from db.artifact_catalog import CATALOGO_ARTEFATTI
from personaggi_ufficiali import PERSONAGGI_UFFICIALI

from .armi_ufficiali import ARMI_UFFICIALI
from .custom_registry import approved_armi_names, approved_personaggi_names

WHITELIST_PERSONAGGI: frozenset[str] = frozenset(PERSONAGGI_UFFICIALI)
WHITELIST_ARMI: frozenset[str] = frozenset(ARMI_UFFICIALI)

WHITELIST_PERSONAGGI_EFFECTIVE: frozenset[str] = WHITELIST_PERSONAGGI | frozenset(approved_personaggi_names())
WHITELIST_ARMI_EFFECTIVE: frozenset[str] = WHITELIST_ARMI | frozenset(approved_armi_names())

_sets: set[str] = set()
for _sn, _pz in CATALOGO_ARTEFATTI:
    s = (_sn or "").strip()
    if s:
        _sets.add(s)

WHITELIST_SET_MANUFATTI: frozenset[str] = frozenset(_sets)

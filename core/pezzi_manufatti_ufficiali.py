"""
Nomi pezzo manufatti — unione di tutti i pezzi nel catalogo ufficiale.

La mappatura set → cinque pezzi resta in ``core.manufatti_ufficiali`` (``CATALOGO_ARTEFATTI``);
questo modulo espone solo l’insieme dei nomi pezzo ammessi (utilità, export, controlli).
"""
from __future__ import annotations

from core.manufatti_ufficiali import CATALOGO_ARTEFATTI


def _build_pezzi() -> frozenset[str]:
    out: set[str] = set()
    for _, p5 in CATALOGO_ARTEFATTI:
        for p in p5:
            t = (p or "").strip()
            if t:
                out.add(t)
    return frozenset(out)


NOMI_PEZZI_UFFICIALI: frozenset[str] = _build_pezzi()

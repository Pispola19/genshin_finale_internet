"""
Bonus di set sul damage proxy: percentuali semplici, alto impatto percepito.
Non replica i moltiplicatori reali in gioco; serve al confronto tra build nell’app.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

# Default generosi se il set non è in tabella (nome comunque conteggiato da 2+ pezzi)
DEFAULT_SET_PROXY_2P = 0.22
DEFAULT_SET_PROXY_4P = 0.52

# Override per nome set normalizzato (lower case, strip). IT + EN dove serve.
SET_PROXY_OVERRIDES: Dict[str, Dict[str, float]] = {
    "emblema del fato spezzato": {"2p": 0.20, "4p": 0.58},
    "emblem of severed fate": {"2p": 0.20, "4p": 0.58},
    "reminiscenza di shimenawa": {"2p": 0.21, "4p": 0.55},
    "shimenawa's reminiscence": {"2p": 0.21, "4p": 0.55},
    "ultimo atto del gladiatore": {"2p": 0.20, "4p": 0.50},
    "gladiator's finale": {"2p": 0.20, "4p": 0.50},
    "cacciatrice smeraldo": {"2p": 0.22, "4p": 0.56},
    "gilded dreams": {"2p": 0.23, "4p": 0.54},
    "husk of opulent dreams": {"2p": 0.21, "4p": 0.55},
    "echi dell'offerta": {"2p": 0.21, "4p": 0.53},
    "viridescent venerer": {"2p": 0.22, "4p": 0.52},
    "compagnia del vagabondo": {"2p": 0.22, "4p": 0.52},
    "wanderer's troupe": {"2p": 0.22, "4p": 0.52},
    "noblesse oblige": {"2p": 0.21, "4p": 0.51},
    "bloodstained chivalry": {"2p": 0.21, "4p": 0.50},
    "crimson witch": {"2p": 0.22, "4p": 0.57},
    "stigma delle fiamme cremisi": {"2p": 0.22, "4p": 0.57},
}


def conteggio_set_da_artefatti(artefatti: Sequence[Optional[dict]]) -> Dict[str, int]:
    """Conta pezzi per nome set (come sulle schede)."""
    counts: Dict[str, int] = {}
    for a in artefatti:
        if not a:
            continue
        sn = (a.get("set_nome") or "").strip()
        if not sn or sn == "—":
            continue
        counts[sn] = counts.get(sn, 0) + 1
    return counts


def _spec_for_set_name(nome_set: str) -> Dict[str, float]:
    k = (nome_set or "").strip().lower()
    if k in SET_PROXY_OVERRIDES:
        return SET_PROXY_OVERRIDES[k]
    for key, spec in SET_PROXY_OVERRIDES.items():
        if key in k or k in key:
            return spec
    return {}


def set_bonus_proxy_multiplier(set_counts: Dict[str, int]) -> Tuple[float, List[str]]:
    """
    Moltiplicatore sul proxy (prodotto dei bonus attivi).
    4p: usa solo il bonus 4p (non somma 2p+4p). 2 o 3 pezzi: solo 2p.
    """
    mult = 1.0
    lines: List[str] = []
    for nome_display, n in sorted(set_counts.items(), key=lambda x: (-x[1], x[0].lower())):
        if n < 2:
            continue
        spec = _spec_for_set_name(nome_display)
        p2 = spec.get("2p", DEFAULT_SET_PROXY_2P)
        p4 = spec.get("4p", DEFAULT_SET_PROXY_4P)
        if n >= 4:
            mult *= 1.0 + p4
            lines.append(f"{nome_display} (4p): +{p4 * 100:.0f}% sul proxy")
        else:
            mult *= 1.0 + p2
            lines.append(f"{nome_display} (2p): +{p2 * 100:.0f}% sul proxy")
    return mult, lines

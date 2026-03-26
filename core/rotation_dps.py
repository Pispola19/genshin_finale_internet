"""
DPS da rotazione (stima) — modello v0.1 conservativo.

Non sostituisce il «proxy danno» della build: moltiplica il proxy per un fattore
derivato da peso NA/E/Q e livelli talento (AA, skill, burst), con aggiustamento
leggero sulla ER per il peso del burst. I numeri sono confrontabili tra build
dello stesso salvataggio, non DPS assoluti di gioco.

Curve talento semplificate (non catalogo per-personaggio). Placeholder esplicito
separato per test/API che devono restare «non calcolato».
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.dps_types import FullCombatBuild

# Modello attivo per compute_rotation_estimate (incrementare se cambia il significato dei campi).
ROTATION_MODEL_VERSION = "0.1.0"
PLACEHOLDER_MODEL_VERSION = "0.0.0"


def rotation_dps_placeholder() -> Dict[str, Any]:
    """Risposta esplicita «non implementato» per future API di test."""
    return {
        "ok": False,
        "model_version": PLACEHOLDER_MODEL_VERSION,
        "message_it": "DPS da rotazione non ancora calcolato: serve catalogo talenti/tempistiche.",
        "damage": None,
    }


_PRESETS: Dict[str, Tuple[float, float, float]] = {
    "equilibrato": (0.38, 0.37, 0.25),
    "na_focus": (0.52, 0.33, 0.15),
    "burst_focus": (0.26, 0.34, 0.40),
}


def _talent_multiplier(level: Optional[int]) -> float:
    """Moltiplicatore indicativo da livello talento 0–10 (o None = neutro)."""
    if level is None:
        return 1.0
    try:
        L = int(level)
    except (TypeError, ValueError):
        return 1.0
    if L <= 0:
        return 0.93
    L = min(max(L, 1), 10)
    return 1.0 + 0.056 * (L - 1)


def _normalize_weights(
    w_na: float, w_skill: float, w_burst: float, er_fraction: float
) -> Tuple[float, float, float, float]:
    """
    er_fraction: frazione 0–1 (es. 0.22 = 22% ricarica dal CombatStats).
    Riduce leggermente il peso del burst se ER bassa; rinormalizza a somma 1.
    """
    er = max(0.0, min(float(er_fraction), 1.5))
    burst_scale = 0.76 + 0.28 * min(er / 0.24, 1.0)
    wb = w_burst * burst_scale
    s = w_na + w_skill + wb
    if s <= 0:
        return 1.0 / 3, 1.0 / 3, 1.0 / 3, burst_scale
    return w_na / s, w_skill / s, wb / s, burst_scale


def compute_rotation_estimate(
    full: FullCombatBuild,
    aa: Optional[int],
    skill: Optional[int],
    burst: Optional[int],
    preset: str = "equilibrato",
    personaggio_nome: str = "",
) -> Dict[str, Any]:
    """
    Indice rotazione = damage_proxy × (combinazione lineare moltiplicatori talento).

    `full` deve essere già `build_full_combat_view(...)` sulla stessa build.
    """
    w = _PRESETS.get((preset or "equilibrato").lower(), _PRESETS["equilibrato"])
    w_na0, w_sk0, w_bu0 = w
    er_f = float(full.totale.er_percent)
    w_na, w_sk, w_bu, burst_scale = _normalize_weights(w_na0, w_sk0, w_bu0, er_f)

    m_aa = _talent_multiplier(aa)
    m_sk = _talent_multiplier(skill)
    m_bu = _talent_multiplier(burst)
    rot_mult = w_na * m_aa + w_sk * m_sk + w_bu * m_bu
    proxy = float(full.damage_proxy)
    rotation_index = round(proxy * rot_mult, 1)

    warnings: List[str] = []
    if aa is None or skill is None or burst is None:
        warnings.append(
            "Alcuni talenti (AA/E/Q) non compilati: per quelli si usa moltiplicatore neutro 1.0."
        )
    note_it = (
        "Indice rotazione = proxy build × fattore talenti/pesi NA–E–Q. "
        "Stessa base del «proxy danno» (stessi set/stat), confrontabile tra equip dello stesso PG; "
        "non è DPS reale in gioco."
    )

    return {
        "ok": True,
        "model_version": ROTATION_MODEL_VERSION,
        "personaggio_nome": (personaggio_nome or "").strip(),
        "preset": preset if preset in _PRESETS else "equilibrato",
        "damage_proxy": proxy,
        "damage_proxy_note_it": full.damage_proxy_note_it,
        "rotation_multiplier": round(rot_mult, 4),
        "rotation_index": rotation_index,
        "weights": {
            "na": round(w_na, 4),
            "skill": round(w_sk, 4),
            "burst": round(w_bu, 4),
            "burst_er_scale": round(burst_scale, 4),
        },
        "talent_levels": {"aa": aa, "skill": skill, "burst": burst},
        "talent_multipliers": {"aa": round(m_aa, 4), "skill": round(m_sk, 4), "burst": round(m_bu, 4)},
        "warnings": warnings,
        "note_it": note_it,
        "combat_totale_summary_it": full.totale.format_summary_it(),
    }

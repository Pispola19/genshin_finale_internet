"""
Tipi per calcolo DPS: statistiche di combattimento e risultato strutturato.
Pronti per GUI, API JSON e modelli futuri (effective stats, rotation, set bonus).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

# Versione semantica del modello: incrementare quando cambia il significato dei campi.
DPS_MODEL_VERSION = "1.1.0"
COMBAT_BUILD_VERSION = "1.1"

from core.set_bonus_proxy import conteggio_set_da_artefatti, set_bonus_proxy_multiplier

# Modalità risultato (estendibile).
MODE_ARTIFACT_INDEX = "artifact_index"
MODE_EXPECTED_HIT = "expected_hit"
MODE_ROTATION_DPS = "rotation_dps"

# Unità del valore principale mostrato.
UNIT_INDEX = "index"
UNIT_DAMAGE = "damage"
UNIT_DPS = "dps"


def _f(x: Any, default: float = 0.0) -> float:
    try:
        if x is None or (isinstance(x, str) and not str(x).strip()):
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


@dataclass
class CombatStats:
    """
    Statistiche combattimento unificate.

    - crit_rate, crit_damage: frazioni (es. 0.35 = 35% prob. crit;
      crit_damage 1.0 = +100% danno in crit, come bonus additivo tipico Genshin).
    - atk_percent, er_percent, dmg_* : frazioni (0.15 = +15%).
    - atk_flat, def_flat, hp_flat, em: valori assoluti come in scheda / somma manufatti.
    """

    atk_flat: float = 0.0
    atk_percent: float = 0.0
    def_flat: float = 0.0
    hp_flat: float = 0.0
    em: float = 0.0
    er_percent: float = 0.0
    crit_rate: float = 0.0
    crit_damage: float = 0.0
    dmg_bonus_all: float = 0.0
    dmg_bonus_elemental: float = 0.0
    source_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "atk_flat": self.atk_flat,
            "atk_percent": self.atk_percent,
            "def_flat": self.def_flat,
            "hp_flat": self.hp_flat,
            "em": self.em,
            "er_percent": self.er_percent,
            "crit_rate": self.crit_rate,
            "crit_damage": self.crit_damage,
            "dmg_bonus_all": self.dmg_bonus_all,
            "dmg_bonus_elemental": self.dmg_bonus_elemental,
            "source_note": self.source_note,
        }

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> Optional["CombatStats"]:
        if d is None:
            return None
        return cls(
            atk_flat=_f(d.get("atk_flat")),
            atk_percent=_f(d.get("atk_percent")),
            def_flat=_f(d.get("def_flat")),
            hp_flat=_f(d.get("hp_flat")),
            em=_f(d.get("em")),
            er_percent=_f(d.get("er_percent")),
            crit_rate=_f(d.get("crit_rate")),
            crit_damage=_f(d.get("crit_damage")),
            dmg_bonus_all=_f(d.get("dmg_bonus_all")),
            dmg_bonus_elemental=_f(d.get("dmg_bonus_elemental")),
            source_note=str(d.get("source_note") or ""),
        )

    def format_summary_it(self) -> str:
        """Testo multilinea per finestra / tooltip."""
        lines = [
            f"ATK (flat): {self.atk_flat:g}",
            f"ATK%: {self.atk_percent * 100:.1f}%",
            f"DEF / HP (flat): {self.def_flat:g} / {self.hp_flat:g}",
            f"EM: {self.em:g}",
            f"Ricarica%: {self.er_percent * 100:.1f}%",
            f"Tasso crit: {self.crit_rate * 100:.1f}%",
            f"Bonus danno crit: +{self.crit_damage * 100:.1f}% (come sul foglio personaggio)",
            f"Danno% (generico): {self.dmg_bonus_all * 100:.1f}%",
            f"Danno% (elementale): {self.dmg_bonus_elemental * 100:.1f}%",
        ]
        if self.source_note:
            lines.append(f"Nota: {self.source_note}")
        return "\n".join(lines)


def merge_combat_stats(*parts: CombatStats) -> CombatStats:
    """Somma tutte le componenti numeriche; unisce le note (tranne stringhe vuote)."""
    if not parts:
        return CombatStats(source_note="Nessuna fonte")
    notes = [p.source_note for p in parts if (p.source_note or "").strip()]
    return CombatStats(
        atk_flat=round(sum(p.atk_flat for p in parts), 2),
        atk_percent=round(sum(p.atk_percent for p in parts), 4),
        def_flat=round(sum(p.def_flat for p in parts), 2),
        hp_flat=round(sum(p.hp_flat for p in parts), 2),
        em=round(sum(p.em for p in parts), 2),
        er_percent=round(sum(p.er_percent for p in parts), 4),
        crit_rate=round(sum(p.crit_rate for p in parts), 4),
        crit_damage=round(sum(p.crit_damage for p in parts), 4),
        dmg_bonus_all=round(sum(p.dmg_bonus_all for p in parts), 4),
        dmg_bonus_elemental=round(sum(p.dmg_bonus_elemental for p in parts), 4),
        source_note=" + ".join(notes) if notes else "Somma fonti",
    )


def combat_stats_increment_from_stat_line(stat: Optional[str], val: Any) -> CombatStats:
    """Contributo di una singola riga stat (come main/sub manufatto o secondaria arma)."""
    c = combat_stats_from_artefatto_dict(
        {
            "id": 0,
            "main_stat": stat,
            "main_val": val,
            "sub1_stat": "",
            "sub1_val": None,
            "sub2_stat": "",
            "sub2_val": None,
            "sub3_stat": "",
            "sub3_val": None,
            "sub4_stat": "",
            "sub4_val": None,
        }
    )
    c.source_note = ""
    return c


def combat_stats_from_personaggio_model(pg: Any) -> CombatStats:
    """Foglio personaggio: CR/CD/ER trattati come punti percentuali interi (65 → 0,65)."""
    if pg is None:
        return CombatStats(source_note="Personaggio assente")
    cr = _f(getattr(pg, "cr", None))
    cd = _f(getattr(pg, "cd", None))
    er = _f(getattr(pg, "er", None))
    return CombatStats(
        hp_flat=_f(getattr(pg, "hp_flat", None)),
        atk_flat=_f(getattr(pg, "atk_flat", None)),
        def_flat=_f(getattr(pg, "def_flat", None)),
        em=_f(getattr(pg, "em_flat", None)),
        crit_rate=round(cr / 100.0, 4) if cr else 0.0,
        crit_damage=round(cd / 100.0, 4) if cd else 0.0,
        er_percent=round(er / 100.0, 4) if er else 0.0,
        source_note="Foglio personaggio",
    )


def combat_stats_from_arma_model(arma: Any) -> CombatStats:
    """Arma: ATK base come flat; stat secondaria con stesse regole dei manufatti."""
    if not arma:
        return CombatStats(source_note="Nessuna arma")
    base = CombatStats(
        atk_flat=_f(getattr(arma, "atk_base", None)),
        source_note="Arma",
    )
    line = combat_stats_increment_from_stat_line(
        getattr(arma, "stat_secondaria", None) or "",
        getattr(arma, "valore_stat", None),
    )
    line.source_note = ""
    merged = merge_combat_stats(base, line)
    merged.source_note = "Arma (ATK base + stat secondaria)"
    return merged


def combat_stats_from_artefatti_list(artefatti: Sequence[Optional[dict]]) -> CombatStats:
    """Somma i contributi di tutti i manufatti (lista o equip parziale)."""
    valid = [a for a in artefatti if a]
    if not valid:
        return CombatStats(source_note="Nessun manufatto")
    parts = [combat_stats_from_artefatto_dict(a) for a in valid]
    for p in parts:
        p.source_note = ""
    m = merge_combat_stats(*parts)
    m.source_note = f"Somma {len(valid)} manufatti"
    return m


def compute_build_damage_proxy(stats: CombatStats) -> tuple[float, str]:
    """
    Indicatore numerico da build completa (non DPS di gioco).
    ATK_tot ≈ ATK_flat * (1+ATK%); moltiplicatore crit atteso; danni% ed EM leggeri.
    """
    atk = max(stats.atk_flat, 1.0) * (1.0 + max(stats.atk_percent, 0.0))
    cr = min(max(stats.crit_rate, 0.0), 1.0)
    crit_m = 1.0 + cr * max(stats.crit_damage, 0.0)
    raw_dmg = stats.dmg_bonus_elemental + stats.dmg_bonus_all * 0.8
    dmg_m = 1.0 + min(max(raw_dmg, 0.0), 2.2)
    em_m = 1.0 + min(max(stats.em, 0.0) / 1100.0, 0.14)
    proxy = atk * crit_m * dmg_m * em_m
    note = (
        "Proxy = ATK_flat×(1+ATK%) × (1+CR×CD_bonus) × (1+danni%) × f(EM), "
        "con CR cap al 100%. Indicatore relativo alla build salvata, non DPS reale in combattimento."
    )
    return round(proxy, 1), note


@dataclass
class FullCombatBuild:
    """Vista build: personaggio + arma + manufatti, totale e proxy danno."""

    personaggio: CombatStats
    arma: CombatStats
    artefatti: CombatStats
    totale: CombatStats
    damage_proxy: float
    damage_proxy_note_it: str
    model_version: str = COMBAT_BUILD_VERSION
    set_bonus_multiplier: float = 1.0
    set_bonus_lines: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "personaggio": self.personaggio.to_dict(),
            "arma": self.arma.to_dict(),
            "artefatti": self.artefatti.to_dict(),
            "totale": self.totale.to_dict(),
            "damage_proxy": self.damage_proxy,
            "damage_proxy_note_it": self.damage_proxy_note_it,
            "model_version": self.model_version,
            "set_bonus_multiplier": self.set_bonus_multiplier,
            "set_bonus_lines": list(self.set_bonus_lines),
        }


def build_full_combat_view(
    pg: Any,
    arma: Any,
    artefatti: Sequence[Optional[dict]],
) -> FullCombatBuild:
    cs_pg = combat_stats_from_personaggio_model(pg)
    cs_ar = combat_stats_from_arma_model(arma)
    cs_af = combat_stats_from_artefatti_list(artefatti)
    tot = merge_combat_stats(cs_pg, cs_ar, cs_af)
    tot.source_note = "Totale: foglio + arma + manufatti"
    proxy_base, note = compute_build_damage_proxy(tot)
    set_counts = conteggio_set_da_artefatti(artefatti)
    set_mult, set_lines = set_bonus_proxy_multiplier(set_counts)
    proxy = round(proxy_base * set_mult, 1)
    if set_lines:
        note = note + " | Set (2p/4p, % indicative sul proxy): " + " · ".join(set_lines)
    else:
        note = note + " | Nessun bonus set sul proxy (meno di 2 pezzi uguali o set senza nome)."
    return FullCombatBuild(
        personaggio=cs_pg,
        arma=cs_ar,
        artefatti=cs_af,
        totale=tot,
        damage_proxy=proxy,
        damage_proxy_note_it=note,
        set_bonus_multiplier=round(set_mult, 4),
        set_bonus_lines=set_lines,
    )


@dataclass
class DpsResult:
    """
    Risultato di un calcolo DPS (o indice relativo).

    value_display: numero mostrato in UI (oggi: score manufatto grezzo o derivato).
    ranking: classifica per personaggio (es. score con bonus calice elemento).
    """

    mode: str
    unit: str
    value_display: float
    display_label_it: str
    model_version: str = DPS_MODEL_VERSION
    combat_stats: Optional[CombatStats] = None
    artifact_id: Optional[int] = None
    artifact_label: Optional[str] = None
    breakdown: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    ranking: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "unit": self.unit,
            "value_display": self.value_display,
            "display_label_it": self.display_label_it,
            "model_version": self.model_version,
            "combat_stats": self.combat_stats.to_dict() if self.combat_stats else None,
            "artifact_id": self.artifact_id,
            "artifact_label": self.artifact_label,
            "breakdown": dict(self.breakdown),
            "warnings": list(self.warnings),
            "ranking": list(self.ranking),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DpsResult":
        return cls(
            mode=str(d.get("mode") or MODE_ARTIFACT_INDEX),
            unit=str(d.get("unit") or UNIT_INDEX),
            value_display=_f(d.get("value_display")),
            display_label_it=str(d.get("display_label_it") or ""),
            model_version=str(d.get("model_version") or DPS_MODEL_VERSION),
            combat_stats=CombatStats.from_dict(d.get("combat_stats")),
            artifact_id=d.get("artifact_id"),
            artifact_label=d.get("artifact_label"),
            breakdown=dict(d.get("breakdown") or {}),
            warnings=list(d.get("warnings") or []),
            ranking=list(d.get("ranking") or []),
        )


def combat_stats_from_artefatto_dict(artefatto: Optional[Dict[str, Any]]) -> CombatStats:
    """
    Contributo di un solo manufatto alle stat (come sommate in build_service).

    CR/CD/ER in DB sono trattati come punti percentuali (32.7 → crit_rate 0.327).
    DMG% su main/subs incrementa dmg_bonus_elemental o dmg_bonus_all se non chiaramente elementale.
    """
    if not artefatto:
        return CombatStats(source_note="Nessun manufatto")

    atk, df, hp = 0.0, 0.0, 0.0
    atk_pct, er_pct = 0.0, 0.0
    cr_p, cd_p = 0.0, 0.0
    em = 0.0
    dmga, dmge = 0.0, 0.0

    def proc(stat: Optional[str], val: Any) -> None:
        nonlocal atk, df, hp, atk_pct, er_pct, cr_p, cd_p, em, dmga, dmge
        if not stat:
            return
        v = _f(val)
        m = stat.upper()
        if "ATK" in m and "%" in m:
            atk_pct += v / 100.0
        elif "ATK" in m:
            atk += v
        elif "DEF" in m and "%" not in m:
            df += v
        elif "HP" in m and "%" in m:
            pass
        elif "HP" in m:
            hp += v
        elif "CR" in m or "CRIT RATE" in m:
            cr_p += v
        elif "CD" in m or "CRIT DMG" in m:
            cd_p += v
        elif "ER" in m or "RICARICA" in m:
            er_pct += v / 100.0
        elif "EM" in m or "MAESTRIA" in m:
            em += v
        elif "DMG" in m or "DANNI" in m:
            if any(
                e in m
                for e in (
                    "PYRO",
                    "HYDRO",
                    "ELECTRO",
                    "CRYO",
                    "ANEMO",
                    "GEO",
                    "DENDRO",
                    "PHYSICAL",
                    "FISICO",
                )
            ):
                dmge += v / 100.0
            else:
                dmga += v / 100.0

    proc(artefatto.get("main_stat"), artefatto.get("main_val"))
    for i in range(1, 5):
        proc(artefatto.get(f"sub{i}_stat"), artefatto.get(f"sub{i}_val"))

    return CombatStats(
        atk_flat=round(atk, 2),
        atk_percent=round(atk_pct, 4),
        def_flat=round(df, 2),
        hp_flat=round(hp, 2),
        em=round(em, 2),
        er_percent=round(er_pct, 4),
        crit_rate=round(cr_p / 100.0, 4),
        crit_damage=round(cd_p / 100.0, 4),
        dmg_bonus_all=round(dmga, 4),
        dmg_bonus_elemental=round(dmge, 4),
        source_note="Solo questo pezzo (non include foglio personaggio, arma né altri slot).",
    )


def dps_result_to_message_it(res: DpsResult, max_ranking: int = 8) -> str:
    """Messaggio compatto stile messagebox (retrocompatibilità)."""
    lines = [
        res.display_label_it,
        f"Valore: {res.value_display:g} ({res.unit})",
        f"Modello: {res.model_version}",
        "",
        "Migliori personaggi:",
    ]
    for row in res.ranking[:max_ranking]:
        lines.append(f"  {row.get('nome', '?')}: {row.get('score', 0)}")
    if len(res.ranking) > max_ranking:
        lines.append(f"  … (+{len(res.ranking) - max_ranking} altri)")
    if res.warnings:
        lines.append("")
        lines.extend(f"⚠ {w}" for w in res.warnings)
    return "\n".join(lines)

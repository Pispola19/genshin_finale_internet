"""Calcoli DPS - punteggio artefatto per personaggio e build."""
from __future__ import annotations

import math
from typing import Any, Dict, Iterator, List, Optional, Tuple

from db.models import Personaggio
from core.dps_types import (
    DpsResult,
    MODE_ARTIFACT_INDEX,
    UNIT_INDEX,
    combat_stats_from_artefatto_dict,
)


def _sf(val: Any) -> float:
    try:
        if val is None or (isinstance(val, str) and not str(val).strip()):
            return 0.0
        return float(val)
    except (TypeError, ValueError):
        return 0.0


class DpsCalculator:
    """Calcola score DPS per confronto artefatti."""

    PESI_STAT = {
        "CR": 2,
        "CR%": 2,
        "CD": 2,
        "CD%": 2,
        "CRIT RATE": 2,
        "CRIT DMG": 2,
        "ATK%": 1.5,
        "EM": 0.55,
        "ER": 1.05,
        "DMG": 1.55,
    }

    # Peso EM sul ranking in base all’elemento (reazioni / utilità EM).
    EM_SYNERGY = {
        "Pyro": 0.44,
        "Hydro": 0.44,
        "Electro": 0.4,
        "Dendro": 0.5,
        "Cryo": 0.34,
        "Anemo": 0.3,
        "Geo": 0.2,
    }

    @classmethod
    def iter_piece_lines(cls, artefatto: dict) -> Iterator[Tuple[Optional[str], Any]]:
        yield artefatto.get("main_stat"), artefatto.get("main_val")
        for i in range(1, 5):
            yield artefatto.get(f"sub{i}_stat"), artefatto.get(f"sub{i}_val")

    @classmethod
    def piece_has_elemental_dmg_for(cls, artefatto: dict, elemento_pg: str) -> bool:
        """True se main o una sub è DMG% dell’elemento del personaggio."""
        e = (elemento_pg or "").strip().lower()
        if not e:
            return False
        for st, _ in cls.iter_piece_lines(artefatto):
            s = (st or "").lower()
            if e in s and ("dmg" in s or "danni" in s or "dan" in s):
                return True
        return False

    @classmethod
    def piece_total_em(cls, artefatto: dict) -> float:
        t = 0.0
        for st, val in cls.iter_piece_lines(artefatto):
            su = (st or "").upper()
            if "EM" in su or "MAESTRIA" in su:
                t += _sf(val)
        return t

    @classmethod
    def piece_added_crit_rate_ratio(cls, artefatto: dict) -> float:
        """CR aggiunto dal pezzo in rapporto 0–1 (somma % / 100)."""
        t = 0.0
        for st, val in cls.iter_piece_lines(artefatto):
            su = (st or "").upper()
            if "CR" in su or "CRIT RATE" in su:
                t += _sf(val) / 100.0
        return t

    @classmethod
    def _healing_shield_main_penalty(cls, artefatto: dict) -> float:
        main = (artefatto.get("main_stat") or "").upper()
        if "HEALING" in main or "SHIELD" in main:
            return 0.74
        return 1.0

    @classmethod
    def score_stat(cls, nome: str, valore) -> float:
        """Punteggio singola stat."""
        if not nome or valore is None:
            return 0.0
        try:
            v = float(valore)
        except (TypeError, ValueError):
            return 0.0
        nome_upper = (nome or "").upper()
        peso = 0.2
        for key, p in cls.PESI_STAT.items():
            if key in nome_upper:
                peso = p
                break
        # Cura / scudo: meno rilevanti per ranking DPS danni
        if "HEALING" in nome_upper or "SHIELD" in nome_upper:
            peso *= 0.55
        return v * peso

    @classmethod
    def score_artefatto(cls, artefatto: dict) -> float:
        """Punteggio base artefatto (main + subs)."""
        score = cls.score_stat(artefatto.get("main_stat"), artefatto.get("main_val"))
        for i in range(1, 5):
            score += cls.score_stat(
                artefatto.get(f"sub{i}_stat"),
                artefatto.get(f"sub{i}_val"),
            )
        return score

    @classmethod
    def bonus_elemento(cls, elemento_personaggio: str, main_stat: str) -> float:
        """Retrocompatibilità: solo main (calice). Preferire score_artefatto_per_personaggio."""
        elem = (elemento_personaggio or "").lower()
        main = (main_stat or "").lower()
        return 1.2 if elem in main and ("dmg" in main or "dan" in main) else 1.0

    @classmethod
    def score_artefatto_per_personaggio(cls, artefatto: dict, pg: Personaggio) -> Tuple[float, Dict[str, float]]:
        """
        Punteggio manufatto contestualizzato al personaggio:
        - DMG% elemento su main o sub
        - EM con peso per elemento
        - penalità se CR da foglio + pezzo supera soglia (soft cap)
        - penalità main cura/scudo
        """
        base = cls.score_artefatto(artefatto) * cls._healing_shield_main_penalty(artefatto)
        elem_mult = 1.26 if cls.piece_has_elemental_dmg_for(artefatto, pg.elemento) else 1.0
        em_piece = cls.piece_total_em(artefatto)
        w = cls.EM_SYNERGY.get((pg.elemento or "").strip(), 0.28)
        em_mult = 1.0 + min(math.sqrt(max(em_piece, 0.0)) / 48.0, 0.9) * w * 0.24

        cr_pg = _sf(pg.cr) / 100.0 if pg.cr is not None else 0.0
        cr_add = cls.piece_added_crit_rate_ratio(artefatto)
        overflow = max(0.0, cr_pg + cr_add - 0.78)
        crit_penalty = 1.0 - min(overflow, 0.28) * 0.38

        raw = base * elem_mult * em_mult * crit_penalty
        fattori = {
            "base": round(base, 3),
            "elemento": round(elem_mult, 3),
            "em": round(em_mult, 3),
            "crit_adjust": round(crit_penalty, 3),
        }
        return round(raw, 2), fattori

    @classmethod
    def ordina_per_miglior_personaggio(
        cls,
        artefatto: dict,
        personaggi: List[Personaggio],
    ) -> List[Tuple[int, str, float]]:
        """Per ogni personaggio, score contestualizzato. Ordinato decrescente."""
        risultati = []
        for pg in personaggi:
            sc, _ = cls.score_artefatto_per_personaggio(artefatto, pg)
            risultati.append((pg.id, pg.nome, sc))
        risultati.sort(key=lambda x: -x[2])
        return risultati


def build_dps_result_artefatto_index(
    artefatto: dict,
    personaggi: List[Personaggio],
    *,
    artifact_label: str | None = None,
) -> DpsResult:
    """
    DpsResult con ranking per personaggio (score contestualizzato).
    value_display resta score grezzo del pezzo per confronto assoluto tra manufatti.
    """
    aid = artefatto.get("id")
    score_base = DpsCalculator.score_artefatto(artefatto)
    stats_pezzo = combat_stats_from_artefatto_dict(artefatto)

    ranking: list[dict] = []
    for pg in personaggi:
        sc, fattori = DpsCalculator.score_artefatto_per_personaggio(artefatto, pg)
        ranking.append(
            {
                "personaggio_id": pg.id,
                "nome": pg.nome,
                "elemento": pg.elemento,
                "score": sc,
                "fattori": fattori,
            }
        )
    ranking.sort(key=lambda x: -float(x["score"]))

    warnings: list[str] = []
    if not personaggi:
        warnings.append("Nessun personaggio salvato: classifica vuota.")

    return DpsResult(
        mode=MODE_ARTIFACT_INDEX,
        unit=UNIT_INDEX,
        value_display=round(score_base, 2),
        display_label_it="Indice manufatto (grezzo) + classifica per personaggio con DMG elemento, EM e CR (non DPS reale).",
        combat_stats=stats_pezzo,
        artifact_id=int(aid) if aid is not None else None,
        artifact_label=artifact_label,
        breakdown={
            "score_base_manufatto": round(score_base, 4),
            "ranking_uses": "DMG% elemento su main o sub, EM pesato per elemento, aggiustamento se CR foglio+pezzo > ~78%.",
        },
        warnings=warnings,
        ranking=ranking,
    )

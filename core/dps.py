"""Calcoli DPS - punteggio artefatto per personaggio."""
from typing import List, Tuple

from db.models import Personaggio, Artefatto


class DpsCalculator:
    """Calcola score DPS per confronto artefatti."""

    PESI_STAT = {
        "CR": 2, "CR%": 2, "CD": 2, "CD%": 2, "CRIT RATE": 2, "CRIT DMG": 2,
        "ATK%": 1.5, "EM": 0.5, "ER": 1, "DMG": 1.5,
    }

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
        return v * peso

    @classmethod
    def score_artefatto(cls, artefatto: dict) -> float:
        """Punteggio base artefatto (main + subs)."""
        score = cls.score_stat(artefatto.get("main_stat"), artefatto.get("main_val"))
        for i in range(1, 5):
            score += cls.score_stat(
                artefatto.get(f"sub{i}_stat"),
                artefatto.get(f"sub{i}_val")
            )
        return score

    @classmethod
    def bonus_elemento(cls, elemento_personaggio: str, main_stat: str) -> float:
        """Bonus se artefatto ha DMG% dell'elemento del personaggio."""
        elem = (elemento_personaggio or "").lower()
        main = (main_stat or "").lower()
        return 1.2 if elem in main else 1.0

    @classmethod
    def ordina_per_miglior_personaggio(
        cls,
        artefatto: dict,
        personaggi: List[Personaggio]
    ) -> List[Tuple[int, str, float]]:
        """Per ogni personaggio, score con quell'artefatto. Ordinato decrescente."""
        score_base = cls.score_artefatto(artefatto)
        main_stat = artefatto.get("main_stat") or ""
        risultati = []
        for pg in personaggi:
            bonus = cls.bonus_elemento(pg.elemento, main_stat)
            score = round(score_base * bonus, 1)
            risultati.append((pg.id, pg.nome, score))
        risultati.sort(key=lambda x: -x[2])
        return risultati

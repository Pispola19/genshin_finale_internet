"""
BuildService - logica analisi build attuale vs ottimale.
Tutta la business logic per /api/build passa da qui.
API → Service → Repository (mai salti).
"""
from typing import Optional, List

from core.dps import DpsCalculator
from config import SLOT_DB


def _somma_stats(artefatti: List[dict]) -> dict:
    """Aggrega ATK, CR, CD, ER, EM da lista artefatti."""
    atk, cr, cd, er, em = 0, 0, 0, 0, 0
    for a in artefatti:
        if not a:
            continue
        m = (a.get("main_stat") or "").upper()
        v = float(a.get("main_val") or 0)
        if "ATK" in m:
            atk += v
        elif "CR" in m or "CRIT RATE" in m:
            cr += v
        elif "CD" in m or "CRIT DMG" in m:
            cd += v
        elif "ER" in m:
            er += v
        elif "EM" in m:
            em += v
        for i in range(1, 5):
            s = (a.get(f"sub{i}_stat") or "").upper()
            val = float(a.get(f"sub{i}_val") or 0)
            if "ATK" in s:
                atk += val
            elif "CR" in s or "CRIT RATE" in s:
                cr += val
            elif "CD" in s or "CRIT DMG" in s:
                cd += val
            elif "ER" in s:
                er += val
            elif "EM" in s:
                em += val
    return {"atk": round(atk, 1), "cr": round(cr, 1), "cd": round(cd, 1), "er": round(er, 1), "em": round(em, 1)}


class BuildService:
    """Analisi build: attuale vs ottimale."""

    def __init__(self, personaggio_service, artefatto_service):
        self._pg = personaggio_service
        self._art = artefatto_service

    def analisi_build(self, personaggio_id: int) -> Optional[dict]:
        """
        Build attuale + ottimale per personaggio.
        Ritorna None se personaggio non esiste.
        """
        pg = self._pg.get_personaggio(personaggio_id)
        if not pg:
            return None

        eq_ids = self._pg.get_equipaggiamento_ids(personaggio_id)
        artefatti_attuali = [
            self._art.get_artefatto(aid)
            for slot, aid in eq_ids.items()
            if aid
        ]
        artefatti_attuali = [a for a in artefatti_attuali if a]

        stats_attuali = _somma_stats(artefatti_attuali)
        score_attuale = sum(
            DpsCalculator.score_artefatto(a) * DpsCalculator.bonus_elemento(pg.elemento, a.get("main_stat"))
            for a in artefatti_attuali
        )

        ottimali = []
        for slot in SLOT_DB:
            liberi = self._art.lista_artefatti_liberi_completi(slot)
            if not liberi:
                continue
            migliore = max(
                liberi,
                key=lambda a: DpsCalculator.score_artefatto(a) * DpsCalculator.bonus_elemento(pg.elemento, a.get("main_stat")),
            )
            ottimali.append(migliore)

        stats_ottimali = _somma_stats(ottimali)
        score_ottimale = sum(
            DpsCalculator.score_artefatto(a) * DpsCalculator.bonus_elemento(pg.elemento, a.get("main_stat"))
            for a in ottimali
        )

        dps_attuale = round(score_attuale * 10, 0)
        dps_ottimale = round(score_ottimale * 10, 0)
        diff_dps = round(dps_ottimale - dps_attuale, 0)

        artefatti_tabella = self._art.lista_artefatti_inventario_per_tabella()

        return {
            "personaggio": {"id": pg.id, "nome": pg.nome, "elemento": pg.elemento},
            "build_attuale": {**stats_attuali, "dps": dps_attuale, "artefatti": artefatti_attuali},
            "build_ottimale": {**stats_ottimali, "dps": dps_ottimale, "artefatti": ottimali},
            "differenza": {
                "dps": diff_dps,
                "cr": stats_ottimali["cr"] - stats_attuali["cr"],
                "cd": stats_ottimali["cd"] - stats_attuali["cd"],
            },
            "artefatti_disponibili": artefatti_tabella,
        }

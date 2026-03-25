"""
TeamService - logica ottimizzazione squadre.
Tutta la business logic per /api/teams/calcola passa da qui.
API → Service → Repository (mai salti).
"""
from typing import List
from itertools import combinations


def _score_team(mappa: dict, combo: tuple) -> float:
    """
    Score team: somma livelli + bonus varietà elementi.
    Modulare: sostituire con logica più sofisticata (reazioni, sinergie).
    """
    livelli = [mappa.get(i, ("?", 0, "?"))[1] for i in combo]
    elementi = [mappa.get(i, ("?", 0, "?"))[2] for i in combo]
    score = sum(livelli) * 10
    unici = len(set(elementi))
    score += unici * 15
    return round(score, 0)


class TeamService:
    """Calcolo top team da pool personaggi."""

    def __init__(self, personaggio_service):
        self._pg = personaggio_service

    def calcola_top_teams(self, personaggi_ids: List[int], max_teams: int = 4, max_combinazioni: int = 30) -> dict:
        """
        Top N team. Se personaggi_ids ha >=4 elementi, usa quel pool; altrimenti tutti.
        """
        tutti = self._pg.lista_personaggi_righe()
        if not tutti:
            return {"teams": [], "message": "Nessun personaggio nel database"}

        mappa = {r[0]: (r[1], r[2], r[3]) for r in tutti}
        pool = personaggi_ids if len(personaggi_ids) >= 4 else [r[0] for r in tutti]

        if len(pool) < 4:
            return {"teams": [], "message": "Servono almeno 4 personaggi"}

        combinazioni = list(combinations(pool, 4))[:max_combinazioni]
        team_scores = []

        for combo in combinazioni:
            nomi = [mappa.get(i, ("?", 0, "?"))[0] for i in combo]
            elementi = [mappa.get(i, ("?", 0, "?"))[2] for i in combo]
            score = _score_team(mappa, combo)
            team_scores.append((list(combo), nomi, elementi, score))

        team_scores.sort(key=lambda x: -x[3])
        top = team_scores[:max_teams]

        return {
            "teams": [
                {"personaggi": t[1], "elementi": t[2], "power": t[3], "dps": f"{t[3] - (max_teams - i - 1) * 5}%"}
                for i, t in enumerate(top)
            ]
        }

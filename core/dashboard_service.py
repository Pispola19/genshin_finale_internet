"""
DashboardService - lettura + aggregazione + sintesi.
NON salva, NON modifica. Usa PersonaggioService, BuildService, TeamService.
"""
from typing import List


class DashboardService:
    """Riassunto intelligente: KPI, classifica, build migliorabili."""

    def __init__(self, personaggio_service, build_service, team_service):
        self._pg = personaggio_service
        self._build = build_service
        self._team = team_service

    def get_dati(self) -> dict:
        """
        Raccoglie e sintetizza tutto.
        Ritorna struttura pronta per la pagina dashboard.
        """
        righe = self._pg.lista_personaggi_righe()
        if not righe:
            return {
                "vuoto": True,
                "top_personaggio": {"nome": "—", "dps": 0},
                "dps_medio": 0,
                "team_migliore": {"personaggi": [], "power": 0},
                "top_5": [],
                "build_migliorabili": [],
                "dps_quality": {
                    "ready": 0,
                    "partial": 0,
                    "summary_it": "Nessun personaggio salvato: qualità DPS non calcolabile.",
                },
            }

        # Per ogni personaggio, DPS da build
        con_dps = []
        ready = 0
        partial = 0
        for pid, nome, livello, elemento in righe:
            analisi = self._build.analisi_build(pid)
            if analisi:
                dps = analisi["build_attuale"].get("dps", 0)
                diff = analisi.get("differenza", {}).get("dps", 0)
                q = analisi.get("dps_quality") or {}
                if q.get("ready"):
                    ready += 1
                else:
                    partial += 1
                con_dps.append({
                    "id": pid,
                    "nome": nome,
                    "dps": dps,
                    "dps_ottimale": analisi["build_ottimale"].get("dps", 0),
                    "diff_dps": diff,
                })

        if not con_dps:
            return {
                "vuoto": True,
                "top_personaggio": {"nome": "—", "dps": 0},
                "dps_medio": 0,
                "team_migliore": {"personaggi": [], "power": 0},
                "top_5": [],
                "build_migliorabili": [],
                "dps_quality": {
                    "ready": 0,
                    "partial": 0,
                    "summary_it": "Nessun dato DPS disponibile.",
                },
            }

        # Top personaggio (DPS massimo)
        migliore = max(con_dps, key=lambda x: x["dps"])
        top_personaggio = {"nome": migliore["nome"], "dps": migliore["dps"]}

        # DPS medio
        dps_medio = round(sum(x["dps"] for x in con_dps) / len(con_dps), 1)

        # Top 5 (ordinati per DPS decrescente)
        ordinati = sorted(con_dps, key=lambda x: -x["dps"])
        top_5 = [{"nome": x["nome"], "dps": x["dps"]} for x in ordinati[:5]]

        # Team migliore
        teams_result = self._team.calcola_top_teams([])
        teams = teams_result.get("teams", [])
        if teams:
            tm = teams[0]
            team_migliore = {
                "personaggi": tm.get("personaggi", []),
                "power": tm.get("power", 0),
            }
        else:
            team_migliore = {"personaggi": [], "power": 0}

        # Build migliorabili (dove ottimale > attuale)
        migliorabili = [
            {"nome": x["nome"], "dps_attuale": x["dps"], "dps_ottimale": x["dps_ottimale"], "diff": x["diff_dps"]}
            for x in con_dps
            if x["diff_dps"] > 0
        ]
        migliorabili.sort(key=lambda x: -x["diff"])

        return {
            "vuoto": False,
            "top_personaggio": top_personaggio,
            "dps_medio": dps_medio,
            "team_migliore": team_migliore,
            "top_5": top_5,
            "build_migliorabili": migliorabili,
            "dps_quality": {
                "ready": ready,
                "partial": partial,
                "summary_it": (
                    f"✅ {ready} personaggi pronti per DPS."
                    + (f" ⚠ {partial} con dati incompleti (DPS non affidabile)." if partial else "")
                ),
            },
        }

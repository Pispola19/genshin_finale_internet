"""
Servizi applicativi - interfaccia unica tra GUI e database.
La GUI parla SOLO con AppService. Nessun accesso diretto a Repository o DB.
AppService delega a PersonaggioService, ArtefattoService, BuildService, TeamService.
"""
from core.personaggio_service import PersonaggioService
from core.artefatto_service import ArtefattoService
from core.build_service import BuildService
from core.team_service import TeamService
from core.dashboard_service import DashboardService


class AppService:
    """
    Facade che espone tutti i servizi.
    La GUI/API usa solo questo oggetto. Mai accesso a _personaggio.conn o repository.
    """

    def __init__(self):
        self._personaggio = PersonaggioService()
        self._artefatto = ArtefattoService(
            self._personaggio.conn,
            self._personaggio.conn_art
        )
        self._build = BuildService(self._personaggio, self._artefatto)
        self._team = TeamService(self._personaggio)
        self._dashboard = DashboardService(self._personaggio, self._build, self._team)

    def close(self) -> None:
        self._personaggio.close()

    # --- Personaggio (delega a PersonaggioService) ---
    def valida_nome(self, nome: str, escludi_id=None):
        return self._personaggio.valida_nome(nome, escludi_id)

    def carica_dati_completi(self, id_pg: int):
        return self._personaggio.carica_dati_completi(id_pg)

    def lista_personaggi_righe(self):
        return self._personaggio.lista_personaggi_righe()

    def salva_completo(self, id_pg, form_personaggio, form_arma, form_costellazioni, form_talenti, form_equipaggiamento):
        return self._personaggio.salva_completo(
            id_pg, form_personaggio, form_arma,
            form_costellazioni, form_talenti, form_equipaggiamento
        )

    def elimina_personaggio(self, id_pg: int):
        self._personaggio.elimina_personaggio(id_pg)

    def nomi_per_autocomplete(self):
        return self._personaggio.nomi_per_autocomplete()

    def rimuovi_entrate_test(self):
        return self._personaggio.rimuovi_entrate_test()

    # --- Artefatti (delega a ArtefattoService) ---
    def lista_artefatti_liberi_righe(self, slot: str):
        return self._artefatto.lista_artefatti_liberi_righe(slot)

    def lista_artefatti_per_equip(self, slot: str, personaggio_id=None):
        return self._artefatto.lista_artefatti_per_equip(slot, personaggio_id)

    def lista_artefatti_inventario_righe(self):
        return self._artefatto.lista_artefatti_inventario_righe()

    def lista_artefatti_completa(self):
        return self._artefatto.lista_artefatti_completa()

    def formato_label_artefatto(self, artefatto_id: int):
        return self._artefatto.formato_label_artefatto(artefatto_id)

    def formato_messaggio_dps(self, artefatto_id: int, max_righe: int = 5):
        return self._artefatto.formato_messaggio_dps(artefatto_id, max_righe)

    def aggiungi_artefatto(self, form_values: dict):
        return self._artefatto.aggiungi_artefatto(form_values)

    def assegna_artefatto_utilizzatore(self, artefatto_id: int, personaggio_id):
        """personaggio_id=None → torna in magazzino."""
        self._artefatto.assegna_utilizzatore(artefatto_id, personaggio_id)

    def artefatto_opzione_select(self, a: dict):
        return self._artefatto.artefatto_opzione_select(a)

    def dettaglio_artefatto_json(self, artefatto_id: int):
        return self._artefatto.dettaglio_artefatto_json(artefatto_id)

    def suggerimenti_personaggi_per_artefatto(self, artefatto_id: int):
        return self._artefatto.suggerimenti_personaggi_per_artefatto(artefatto_id)

    def aggiorna_artefatto(self, artefatto_id: int, form_values: dict):
        self._artefatto.aggiorna_artefatto(artefatto_id, form_values)

    def elimina_artefatto(self, artefatto_id: int):
        self._artefatto.elimina_artefatto(artefatto_id)

    def set_per_slot(self, slot: str):
        return self._artefatto.set_per_slot(slot)

    def pezzi_catalogo_set_slot(self, set_nome: str, slot: str):
        return self._artefatto.pezzi_catalogo_set_slot(set_nome, slot)

    def suggerimenti_artefatto(self, slot: str, set_partial="", nome_partial="", main_stat=""):
        return self._artefatto.suggerimenti_artefatto(slot, set_partial, nome_partial, main_stat)

    def main_stats_per_slot(self, slot: str):
        return self._artefatto.main_stats_per_slot(slot)

    def cerca_artefatto_online(self, query: str):
        return self._artefatto.cerca_artefatto_online(query)

    def cerca_artefatto_web(self, query: str):
        return self._artefatto.cerca_artefatto_web(query)

    # --- Build (delega a BuildService) ---
    def get_build_analysis(self, personaggio_id: int):
        return self._build.analisi_build(personaggio_id)

    # --- Team (delega a TeamService) ---
    def calcola_top_teams(self, personaggi_ids: list):
        return self._team.calcola_top_teams(personaggi_ids)

    # --- Dashboard (delega a DashboardService) ---
    def get_dashboard_dati(self):
        return self._dashboard.get_dati()

"""Layer database - connessioni, modelli, repository."""
from db.connection import (
    close_thread_connections,
    get_connection,
    get_artefatti_connection,
    init_databases,
)
from db.models import Personaggio, Arma, Artefatto, Costellazioni, Talenti
from db.repositories import (
    PersonaggioRepository, ArmaRepository,
    ArtefattoRepository, CostellazioniRepository, TalentiRepository
)

__all__ = [
    "close_thread_connections",
    "get_connection", "get_artefatti_connection", "init_databases",
    "Personaggio", "Arma", "Artefatto", "Costellazioni", "Talenti",
    "PersonaggioRepository", "ArmaRepository",
    "ArtefattoRepository", "CostellazioniRepository", "TalentiRepository",
]

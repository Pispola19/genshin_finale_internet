"""Configurazione centralizzata - percorsi, costanti, enumerazioni."""
import os
from pathlib import Path

# Percorsi: sempre derivati da questa repo (nessun percorso assoluto nel codice).
# Nome cartella consigliato sulla macchina: ``genshin_manager`` (stabile, senza versione nel nome).
# Una sola copia del progetto; launcher .command e GENSHIN_PROJECT_ROOT per eccezioni.
PROJECT_ROOT = Path(__file__).parent.resolve()

# Su Render (o altri host): imposta GINSHIN_DATA_DIR sul disco persistente per non perdere i DB ai redeploy.
_data_override = (os.environ.get("GINSHIN_DATA_DIR") or "").strip()
if _data_override:
    _data_root = Path(_data_override).expanduser().resolve()
    _data_root.mkdir(parents=True, exist_ok=True)
    DB_PATH = _data_root / "genshin.db"
    ARTEFATTI_DB_PATH = _data_root / "artefatti.db"
    CUSTOM_ENTITIES_PATH = _data_root / "custom_entities.json"
else:
    _data_root = PROJECT_ROOT
    DB_PATH = PROJECT_ROOT / "genshin.db"
    ARTEFATTI_DB_PATH = PROJECT_ROOT / "artefatti.db"
    CUSTOM_ENTITIES_PATH = PROJECT_ROOT / "data" / "custom_entities.json"


def _env_flag(name: str, default_true: bool = True) -> bool:
    raw = (os.environ.get(name) or ("" if not default_true else "1")).strip().lower()
    if not raw and default_true:
        return True
    return raw not in ("0", "false", "no", "off", "")


def in_production_environment() -> bool:
    """True se l'app gira in contesto tipicamente pubblico (whitelist strict forzato)."""
    if (os.environ.get("RENDER") or "").strip().lower() in ("true", "1", "yes"):
        return True
    if (os.environ.get("FLASK_ENV") or "").strip().lower() == "production":
        return True
    if (os.environ.get("GENSHIN_FORCE_PRODUCTION") or "").strip().lower() in ("1", "true", "yes"):
        return True
    return False


def whitelist_strict_effective() -> bool:
    """
    GENSHIN_WHITELIST_STRICT: default 1 = nome/arma custom solo con conferma esplicita.
    STRICT=0: in sviluppo accetta custom con warning in log (non per produzione).
    In produzione (Render / FLASK_ENV=production) strict è sempre attivo.
    """
    if in_production_environment():
        return True
    return _env_flag("GENSHIN_WHITELIST_STRICT", default_true=True)

# Slot artefatti
SLOT_UI = ("FIORE", "PIUMA", "SABBIE", "CALICE", "CORONA")
SLOT_DB = ("fiore", "piuma", "sabbie", "calice", "corona")

# Personaggi — fonte: ``personaggi_ufficiali`` (whitelist unica; aggiornare lì a ogni patch).
from personaggi_ufficiali import PERSONAGGI_UFFICIALI

PERSONAGGI_GENSHIN = PERSONAGGI_UFFICIALI

# Opzioni per UI
ELEMENTI = ("Pyro", "Hydro", "Electro", "Cryo", "Anemo", "Geo", "Dendro")
TIPI_ARMA = ("Spada", "Claymore", "Lancia", "Catalizzatore", "Arco")

STATS = (
    "HP", "HP%", "ATK", "ATK%", "DEF", "DEF%",
    "EM", "ER", "ER%", "CR", "CR%", "CD", "CD%",
    "Pyro DMG", "Hydro DMG", "Electro DMG", "Cryo DMG", "Anemo DMG", "Geo DMG",
    "Dendro DMG", "Physical DMG", "Healing Bonus", "Shield Strength"
)

SET_ARTEFATTI = (
    "Emblema del fato spezzato",
    "Reminiscenza di shimenawa",
    "Ultimo atto del gladiatore",
    "Compagnia del vagabondo",
    "Cacciatrice smeraldo",
    "Echi dell'offerta",
    "Codice d'ossidiana",
    "Cronache del padiglione del deserto",
    "Aubade della stella del mattino e della luna",
    "Rotolo dell'eroe della città di cenere",
    "Amata fanciulla",
    "Canto dei giorni che furono",
    "Un giorno scolpito dai venti ascendenti",
    "Cavalleria sanguinaria",
    "Memorie di Boscoprofondo",
)

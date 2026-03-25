"""Configurazione centralizzata - percorsi, costanti, enumerazioni."""
import os
from pathlib import Path

# Percorsi
PROJECT_ROOT = Path(__file__).parent.resolve()

# Su Render (o altri host): imposta GINSHIN_DATA_DIR sul disco persistente per non perdere i DB ai redeploy.
_data_override = (os.environ.get("GINSHIN_DATA_DIR") or "").strip()
if _data_override:
    _data_root = Path(_data_override).expanduser().resolve()
    _data_root.mkdir(parents=True, exist_ok=True)
    DB_PATH = _data_root / "genshin.db"
    ARTEFATTI_DB_PATH = _data_root / "artefatti.db"
else:
    DB_PATH = PROJECT_ROOT / "genshin.db"
    ARTEFATTI_DB_PATH = PROJECT_ROOT / "artefatti.db"

# Slot artefatti
SLOT_UI = ("FIORE", "PIUMA", "SABBIE", "CALICE", "CORONA")
SLOT_DB = ("fiore", "piuma", "sabbie", "calice", "corona")

# Personaggi Genshin (Hoyolab) - autocomplete Nome, ordinati alfabeticamente
PERSONAGGI_GENSHIN = (
    "Aether", "Aino", "Albedo", "Alhaitham", "Aloy", "Amber", "Arataki Itto", "Arlecchino",
    "Ayaka", "Ayato", "Baizhu", "Barbara", "Beidou", "Bennett", "Candace", "Chasca",
    "Charlotte", "Chevreuse", "Chiori", "Chongyun", "Childe", "Citlali", "Clorinde",
    "Collei", "Columbina", "Cyno", "Dahlia", "Dehya", "Diluc", "Diona", "Dori",
    "Durin", "Emilie", "Escoffier", "Eula", "Faruzan", "Fischl", "Freminet", "Furina",
    "Gaming", "Ganyu", "Gorou", "Heizou", "Hu Tao", "Iansan", "Ifa", "Illuga",
    "Ineffa", "Jahoda", "Jean", "Kaeya", "Kachina", "Kaveh", "Kazuha", "Keqing",
    "Kinich", "Kirara", "Klee", "Kokomi", "Kujou Sara", "Kuki Shinobu", "Kyryll",
    "Lan Yan", "Lauma", "Layla", "Linnea", "Lisa", "Lumine", "Lyney", "Lynette",
    "Mavuika", "Mika", "Mizuki", "Mona", "Mualani", "Nahida", "Navia",
    "Nefer", "Neuvillette", "Ningguang", "Noelle", "Ororon", "Qiqi", "Raiden Shogun",
    "Razor", "Rosaria", "Sara", "Sayu", "Sethos", "Shenhe", "Shikanoin Heizou",
    "Sigewinne", "Skirk", "Sucrose", "Tartaglia", "Thoma", "Tighnari", "Traveler",
    "Varesa", "Varka", "Venti", "Wanderer", "Wriothesley", "Xiangling", "Xianyun",
    "Xiao", "Xilonen", "Xingqiu", "Xinyan", "Yae Miko", "Yanfei", "Yaoyao", "Yelan",
    "Yoimiya", "Yun Jin", "Zhongli", "Zibai",
)

# UI - pulsanti ricerca (disattivare per parte grafica custom)
MOSTRA_PULSANTE_HOYOLAB = True

# Opzioni per UI
ELEMENTI = ("Pyro", "Hydro", "Electro", "Cryo", "Anemo", "Geo", "Dendro")
TIPI_ARMA = ("Spada", "Claymore", "Lancia", "Catalizzatore", "Arco")

STATS = (
    "HP", "HP%", "ATK", "ATK%", "DEF", "DEF%",
    "EM", "ER", "CR", "CR%", "CD", "CD%",
    "Pyro DMG", "Hydro DMG", "Electro DMG", "Cryo DMG", "Anemo DMG", "Geo DMG",
    "Dendro DMG", "Physical DMG", "Healing Bonus", "Shield Strength"
)

SET_ARTEFATTI = (
    "Emblema del fato spezzato", "Reminiscenza di shimenawa", "Ultimo atto del gladiatore",
    "Compagnia del vagabondo", "Cacciatrice smeraldo", "Echi dell'offerta",
    "Codice d'ossidiana", "Cronache del padiglione del deserto",
    "Aubade della stella del mattino e della luna", "Rotolo dell'eroe della città di cenere",
    "Amata fanciulla", "Canto dei giorni che furono",
    "Un giorno scolpito dai venti ascendenti", "Gladiator's Finale", "Wanderer's Troupe",
    "Noblesse Oblige", "Bloodstained Chivalry", "Emblem of Severed Fate",
    "Shimenawa's Reminiscence", "Husk of Opulent Dreams", "Gilded Dreams",
)

"""
Catalogo artefatti Genshin Impact in italiano.
Fonte: gach.app, genshin-builds, Hoyolab. Set -> (fiore, piuma, sabbie, calice, corona).
I nomi set aggiunti dall’utente sono in ``user_artifact_sets.json`` (merge in lista_set).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

_USER_SETS_FILE = Path(__file__).resolve().parent.parent / "user_artifact_sets.json"


def load_extra_set_names() -> List[str]:
    """Set registrati dall’utente (non nel catalogo builtin)."""
    if not _USER_SETS_FILE.is_file():
        return []
    try:
        raw = json.loads(_USER_SETS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if isinstance(raw, dict):
        arr = raw.get("sets")
        if isinstance(arr, list):
            return [str(x).strip() for x in arr if str(x).strip()]
    return []


# (set_nome, (fiore, piuma, sabbie, calice, corona))
CATALOGO_ARTEFATTI: List[Tuple[str, Tuple[str, str, str, str, str]]] = [
    ("Avventuriere", ("Fiore dell'avventuriere", "Piuma dell'avventuriere", "Orologio dell'avventuriere", "Calice d'oro dell'avventuriere", "Bandana dell'avventuriere")),
    ("Roccia arcaica", ("Fiore rupestre", "Piuma dei picchi aguzzi", "Meridiana di giada perenne", "Calice di falesia", "Maschera di basalto inerte")),
    ("Berserker", ("Rosa del berserker", "Piuma blu del berserker", "Clessidra del berserker", "Calice d'osso del berserker", "Maschera da guerra del berserker")),
    ("Nomade della tormenta", ("Memorie nella neve", "Risolutezza del Rompighiaccio", "Declino della terra del gelo", "Dignità gelata", "Eco dell'inverno")),
    ("Cavalleria sanguinaria", ("Fiore di ferro insanguinato", "Piuma nera insanguinata", "La fine del Cavaliere insanguinato", "Calice del Cavaliere insanguinato", "Maschera di ferro insanguinata")),
    ("Cuore coraggioso", ("Medaglia del coraggioso", "Speranza del coraggioso", "Forza d'animo del coraggioso", "Esordio del coraggioso", "Corona del coraggioso")),
    ("Strega cremisi delle fiamme", ("Fiore di fuoco della strega", "Piuma semprardente della strega", "Fine della strega", "Fiamme del cuore della strega", "Cappello infuocato della strega")),
    ("Viandante del labirinto", ("Viandante del labirinto", "Studioso dei rampicanti", "Un momento di discernimento", "Lampada degli smarriti", "Corona d'alloro")),
    ("Volontà del difensore", ("Fiore del guardiano", "Sigillo del guardiano", "Orologio del guardiano", "Coppa del guardiano", "Benda del guardiano")),
    ("Primi giorni della Città dei Re", ("Primi giorni della Città dei Re", "Fine del regno dorato", "Orologio del sentiero perduto", "Difensore dei sogni ammalianti", "Lascito della nobiltà del deserto")),
    ("Echi dell'offerta", ("Fiore dell'aromaspirito", "Foglia di giada", "Simbolo di giubilo", "Tazza della sorgente", "Orecchini mutevoli")),
    ("Emblema del fato spezzato", ("Tsuba poderosa", "Piuma spaccata", "Inro della tempesta", "Calice scarlatto", "Kabuto decorato")),
    ("Compagnia del vagabondo", ("Fiordacciaio sognante", "Piuma del giudizio", "Gli anni sommersi", "Banchetto mielato", "Ombra del re delle sabbie")),
    ("Ultimo atto del gladiatore", ("Nostalgia del gladiatore", "Destino del gladiatore", "Brama del gladiatore", "Ebbrezza del gladiatore", "Trionfo del gladiatore")),
    ("Reminiscenza di shimenawa", ("Fermaglio dorato", "Brezza nostalgica", "Bussola di rame", "Calice degli abissi", "Tricorno macchiato di vino")),
    ("Istruttore", ("Fermaglio dell'istruttore", "Piuma dell'istruttore", "Orologio dell'istruttore", "Tazza da tè dell'istruttore", "Cappello dell'istruttore")),
    ("Risoluzione dell'Attraversafuochi", ("Risoluzione dell'Attraversafuochi", "Salvezza dell'Attraversafuochi", "Tormento dell'Attraversafuochi", "Rivelazione dell'Attraversafuochi", "Saggezza dell'Attraversafuochi")),
    ("Quadrifoglio di Fortunello", ("Quadrifoglio di Fortunello", "Piuma d'aquila di Fortunello", "Clessidra di Fortunello", "Calice di Fortunello", "Corona d'argento di Fortunello")),
    ("Amata fanciulla", ("Amore lontano della fanciulla", "Delusione d'amore della fanciulla", "Giovinezza effimera della fanciulla", "Passatempo della fanciulla", "Bellezza evanescente della fanciulla")),
    ("Marzialista", ("Fiore vermiglio del marzialista", "Piuma del marzialista", "Clessidra ad acqua del marzialista", "Coppa da vino del marzialista", "Bandana del marzialista")),
    ("Memorie della roccia", ("Fiore reale", "Piuma reale", "Orologio reale", "Urna d'argento reale", "Maschera reale")),
    ("Emblema di Watatsumi", ("Fiore del mare", "Piuma del Palazzo degli abissi", "Ciprea dell'addio", "Inro di perle", "Corona di Watatsumi")),
    ("Codice d'ossidiana", ("Fiore inossidabile", "Piuma del dottore saggio", "Tempo sospeso", "Calice della trascendenza", "Maschera beffarda")),
    ("Risoluzione del viandante", ("Cuore dell'amicizia", "Piuma del ritorno", "Meridiana del viandante", "Calice del viandante", "Corona dell'addio")),
    ("Notti d'estate", ("Fiore delle notti d'estate", "Gran finale delle notti d'estate", "Orologio delle notti d'estate", "Pallone d'acqua delle notti d'estate", "Maschera delle notti d'estate")),
    ("Studiosa", ("Segnalibro della studiosa", "Calamo della studiosa", "Orologio della studiosa", "Tazza per inchiostro della studiosa", "Lente della studiosa")),
    ("Emblema dell'ombra colorata", ("Fiore intrecciato", "Freccia della rimembranza", "Orologio della rugiada mattutina", "Cuore speranzoso", "Maschera capricciosa")),
    ("Reminiscenza della nobiltà", ("Fiore dell'onore", "Piuma da guerra cerimoniale", "Meridiana d'oricalco", "Calice del giuramento del nobile", "Elmetto antico del generale")),
    ("Esule", ("Fiore dell'esule", "Piuma dell'esule", "Orologio dell'esule", "Calice dell'esule", "Corona dell'esule")),
    ("Ira dell'Uccello del tuono", ("Compassione dell'Uccello del tuono", "Superstite della catastrofe", "Clessidra tonante", "Presagio di tempesta", "Corona dell'invocatore di fulmini")),
    ("Domatore di tuoni", ("Cuore del Domatore di tuoni", "Piuma del Domatore di tuoni", "Clessidra del Domatore di tuoni", "Calice del Domatore di tuoni", "Diadema del Domatore di tuoni")),
    ("Miracoloso", ("Fiore miracoloso", "Piuma miracolosa", "Clessidra miracolosa", "Calice miracoloso", "Orecchini miracolosi")),
    ("Dottoressa errante", ("Loto argentato della dottoressa errante", "Piuma di gufo della dottoressa errante", "Orologio della dottoressa errante", "Vaso per medicinali della dottoressa errante", "Fazzoletto della dottoressa errante")),
    ("Fiore della vitalità", ("Fiore della vitalità", "Piuma della luce nascente", "Reliquia solare", "Patto siglato", "Portamento tonante")),
    # Stessi pezzi; nome ufficiale IT in gioco (Honey Hunter / client): “Aldilà vermiglio” (Vermillion Hereafter).
    ("Aldilà vermiglio", ("Fiore della vitalità", "Piuma della luce nascente", "Reliquia solare", "Patto siglato", "Portamento tonante")),
    ("Al di là dell'orizzonte vermiglio", ("Fiore della vitalità", "Piuma della luce nascente", "Reliquia solare", "Patto siglato", "Portamento tonante")),
    ("Cacciatrice smeraldo", ("In memoria dei campi smeraldo", "Piuma della Cacciatrice smeraldo", "Determinazione della Cacciatrice smeraldo", "Borraccia della Cacciatrice smeraldo", "Diadema della Cacciatrice smeraldo")),
    ("Scommettitrice", ("Fermaglio della scommettitrice", "Piuma della scommettitrice", "Orologio della scommettitrice", "Tazza per dadi della scommettitrice", "Orecchini della scommettitrice")),
    ("Cronache del padiglione del deserto", ("Miriade di Ay-Khanoum", "Banchetto appassito", "Coagulo di un istante", "Bottiglia magica del custode dei segreti", "Corona d'ametista")),
    ("Un giorno scolpito dai venti ascendenti", ("Fiore dell'alba pastorale", "Giuramento del brillante alba", "Nota nella primavera", "Racconto inespresso dell'Heldenepos", "Minnesang dell'amore e del lamento")),
    ("Aubade della stella del mattino e della luna", ("Fiore dell'aurora", "Piuma del crepuscolo", "Sera dell'eternità", "Calice del firmamento", "Corona del sognatore")),
    ("Rotolo dell'eroe della città di cenere", ("Seme della fiamma", "Piuma della cenere", "Polvere del tempo", "Calice dell'eroe", "Corona della gloria")),
    ("Canto dei giorni che furono", ("Fiore della giovinezza", "Piuma dell'abbandono", "Meridiana perduta", "Calice della nostalgia", "Maschera del ricordo")),
    ("Gladiator's Finale", ("Nostalgia del gladiatore", "Destino del gladiatore", "Brama del gladiatore", "Ebbrezza del gladiatore", "Trionfo del gladiatore")),
    ("Wanderer's Troupe", ("Luce del mattino della compagnia", "Piuma del bardo", "Ultimo atto dello spettacolo", "Borraccia del vagabondo", "Cappello del direttore")),
    ("Noblesse Oblige", ("Fiore reale", "Piuma reale", "Orologio reale", "Urna d'argento reale", "Maschera reale")),
    ("Bloodstained Chivalry", ("Fiore di ferro insanguinato", "Piuma nera insanguinata", "La fine del Cavaliere insanguinato", "Calice del Cavaliere insanguinato", "Maschera di ferro insanguinata")),
    ("Emblem of Severed Fate", ("Tsuba poderosa", "Piuma spaccata", "Inro della tempesta", "Calice scarlatto", "Kabuto decorato")),
    ("Shimenawa's Reminiscence", ("Fermaglio dorato", "Brezza nostalgica", "Bussola di rame", "Calice degli abissi", "Tricorno macchiato di vino")),
    ("Husk of Opulent Dreams", ("Fiore inossidabile", "Piuma del dottore saggio", "Tempo sospeso", "Calice della trascendenza", "Maschera beffarda")),
    ("Gilded Dreams", ("Fiore dell'aromaspirito", "Foglia di giada", "Simbolo di giubilo", "Tazza della sorgente", "Orecchini mutevoli")),
    ("Memorie di Boscoprofondo", ("Loto del bosco", "Piuma della chiaroveggenza", "Meridiana del branco", "Lampada della foresta", "Corona del lauro")),
    ("Memorie del padiglione", ("Fiore del paradiso perduto", "Piuma del paradiso", "Meridiana del paradiso", "Calice del paradiso", "Corona del paradiso")),
]

SLOT_ORDER = ("fiore", "piuma", "sabbie", "calice", "corona")

# Main stats possibili per slot (per filtraggio)
MAIN_STATS_PER_SLOT = {
    "fiore": ["HP"],
    "piuma": ["ATK"],
    "sabbie": ["HP%", "ATK%", "DEF%", "EM", "ER"],
    "calice": ["HP%", "ATK%", "DEF%", "EM", "Pyro DMG", "Hydro DMG", "Electro DMG", "Cryo DMG", "Anemo DMG", "Geo DMG", "Dendro DMG", "Physical DMG"],
    "corona": ["HP%", "ATK%", "DEF%", "EM", "CR%", "CD%", "Healing Bonus"],
}


def register_extra_set(set_nome: str) -> None:
    """Aggiunge un nome set a ``user_artifact_sets.json`` se non è già nel catalogo né nella lista utente."""
    name = (set_nome or "").strip()
    if not name:
        return
    builtin_lower = {s.strip().lower() for s, _ in CATALOGO_ARTEFATTI}
    if name.lower() in builtin_lower:
        return
    current = load_extra_set_names()
    if name.lower() in {x.lower() for x in current}:
        return
    current.append(name)
    current.sort(key=str.lower)
    _USER_SETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _USER_SETS_FILE.write_text(
        json.dumps({"sets": current}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def lista_set() -> List[str]:
    """Lista unica di nomi set (catalogo + utente), ordinata."""
    seen: set[str] = set()
    out: List[str] = []
    for set_nome, _ in CATALOGO_ARTEFATTI:
        ln = set_nome.strip().lower()
        if ln not in seen:
            seen.add(ln)
            out.append(set_nome)
    for name in load_extra_set_names():
        ln = name.strip().lower()
        if name and ln not in seen:
            seen.add(ln)
            out.append(name)
    return sorted(out, key=str.lower)


def pezzi_catalogo_per_set_e_slot(set_nome: str, slot: str) -> List[str]:
    """Nomi pezzo ufficiali (catalogo) per set + slot; deduplicati, ordine stabile."""
    if not (set_nome or "").strip():
        return []
    idx = SLOT_ORDER.index(slot) if slot in SLOT_ORDER else 0
    want = (set_nome or "").strip().lower()
    seen = set()
    out: List[str] = []
    for sn, pezzi in CATALOGO_ARTEFATTI:
        if sn.strip().lower() != want:
            continue
        p = (pezzi[idx] or "").strip()
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def filtra_per_slot(slot: str) -> List[Tuple[str, str]]:
    """Ritorna [(set_nome, nome_pezzo), ...] per lo slot dato."""
    idx = SLOT_ORDER.index(slot) if slot in SLOT_ORDER else 0
    out = []
    seen = set()
    for set_nome, pezzi in CATALOGO_ARTEFATTI:
        nome_pezzo = pezzi[idx]
        key = (set_nome, nome_pezzo)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return sorted(out, key=lambda x: (x[0].lower(), x[1].lower()))


def filtra_progressivo(
    slot: str,
    set_partial: str = "",
    nome_partial: str = "",
    main_stat: str = "",
) -> List[Tuple[str, str]]:
    """
    Filtraggio progressivo: set_partial, nome_partial, main_stat riducono la lista.
    Ritorna [(set_nome, nome_pezzo), ...].
    """
    candidati = filtra_per_slot(slot)
    set_lower = set_partial.strip().lower()
    nome_lower = nome_partial.strip().lower()
    main_lower = main_stat.strip().lower()

    if set_lower:
        candidati = [(s, n) for s, n in candidati if set_lower in s.lower()]
    if nome_lower:
        candidati = [(s, n) for s, n in candidati if nome_lower in n.lower()]
    if main_lower:
        stats_validi = MAIN_STATS_PER_SLOT.get(slot, [])
        if stats_validi and main_lower not in [st.lower() for st in stats_validi]:
            pass  # main stat non valido per slot, non filtrare
        elif main_lower:
            # Per fiore/piuma main è fisso, non filtrare. Per altri, è solo un hint
            candidati = candidati  # Il main non riduce il catalogo (è scelta utente)

    return candidati


def cerca_nome_pezzo(nome: str) -> List[Tuple[str, str, str]]:
    """Cerca nome pezzo in tutto il catalogo. Ritorna [(set_nome, slot, nome_pezzo), ...]."""
    nome_lower = nome.strip().lower()
    if not nome_lower:
        return []
    out = []
    for set_nome, pezzi in CATALOGO_ARTEFATTI:
        for slot, nome_pezzo in zip(SLOT_ORDER, pezzi):
            if nome_lower in nome_pezzo.lower():
                out.append((set_nome, slot, nome_pezzo))
    return out

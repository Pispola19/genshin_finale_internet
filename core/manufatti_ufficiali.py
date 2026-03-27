"""
Catalogo ufficiale manufatti (client IT / community).

Unica fonte per **set** e **nomi pezzo** (5 slot per set). Aggiornare ``CATALOGO_ARTEFATTI``
a ogni patch con nuovi set; ``PATCH_MANUFATTI`` indica l’ultimo allineamento.

Convenzioni:
  * Mantenere esattamente le stringhe del gioco (maiuscole, apostrofi).
  * Ogni riga: ``(nome_set, (fiore, piuma, sabbie, calice, corona))``.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

# Allineamento catalogo (aggiornare a mano a ogni patch contenuti manufatti)
PATCH_MANUFATTI = "2026-03"

SLOT_ORDER: Tuple[str, ...] = ("fiore", "piuma", "sabbie", "calice", "corona")

# Main stats possibili per slot (UI + filtri)
MAIN_STATS_PER_SLOT: Dict[str, List[str]] = {
    "fiore": ["HP"],
    "piuma": ["ATK"],
    "sabbie": ["HP%", "ATK%", "DEF%", "EM", "ER"],
    "calice": [
        "HP%",
        "ATK%",
        "DEF%",
        "EM",
        "Pyro DMG",
        "Hydro DMG",
        "Electro DMG",
        "Cryo DMG",
        "Anemo DMG",
        "Geo DMG",
        "Dendro DMG",
        "Physical DMG",
    ],
    "corona": ["HP%", "ATK%", "DEF%", "EM", "CR%", "CD%", "Healing Bonus"],
}

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

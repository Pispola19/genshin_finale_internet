"""
ArtefattoService - logica inventario artefatti, DPS, catalogo.
Tutte le chiamate ai Repository per artefatti passano da qui.
"""
from typing import Optional, List, Tuple, Dict, Any

from core.dps import DpsCalculator, build_dps_result_artefatto_index
from core.dps_types import DpsResult, dps_result_to_message_it
from db.connection import get_connection, get_artefatti_connection
from db.repositories import ArtefattoRepository, PersonaggioRepository
from db.artifact_catalog import (
    filtra_progressivo,
    lista_set,
    pezzi_catalogo_per_set_e_slot,
    register_extra_set,
    MAIN_STATS_PER_SLOT,
    cerca_nome_pezzo,
)


class ArtefattoService:
    """Servizio artefatti. Nessun accesso diretto ai Repository dalla GUI."""

    def __init__(self):
        """Usa connessioni SQLite per thread (stesso thread di PersonaggioService / richiesta Flask)."""
        pass

    @staticmethod
    def _main_conn():
        return get_connection()

    @staticmethod
    def _art_conn():
        return get_artefatti_connection()

    # --- Dati pronti per UI ---
    def lista_artefatti_liberi_righe(self, slot: str) -> List[Tuple]:
        """Righe per Treeview selezione artefatto: [(id, set_nome, main_stat, livello, stelle), ...]."""
        lista = ArtefattoRepository.lista_liberi(self._art_conn(), slot)
        return [
            (a["id"], a.get("set_nome", ""), a.get("main_stat", ""),
             a.get("livello", ""), a.get("stelle", ""))
            for a in lista
        ]

    def lista_artefatti_inventario_righe(self) -> List[Tuple]:
        """Righe per Treeview inventario: [(id, slot, set_nome, main_stat, main_val, livello, stelle), ...]."""
        lista = ArtefattoRepository.lista(self._art_conn())
        return [
            (a["id"], a.get("slot", ""), a.get("set_nome", ""),
             a.get("main_stat", ""), a.get("main_val", ""),
             a.get("livello", ""), a.get("stelle", ""))
            for a in lista
        ]

    def formato_label_artefatto(self, artefatto_id: int, max_len: int = 40) -> Optional[str]:
        """Testo per label artefatto equipaggiato."""
        art = ArtefattoRepository.get(self._art_conn(), artefatto_id)
        if not art:
            return None
        txt = f"#{art['id']} {art.get('set_nome', '')} {art.get('main_stat', '')}"
        return txt[:max_len] if len(txt) > max_len else txt

    def dps_result_artefatto(self, artefatto_id: int) -> Optional[DpsResult]:
        """Risultato strutturato DPS/indice per un manufatto (per GUI o API)."""
        art = ArtefattoRepository.get(self._art_conn(), artefatto_id)
        if not art:
            return None
        personaggi = []
        for r in PersonaggioRepository.lista(self._main_conn()):
            pg = PersonaggioRepository.get(self._main_conn(), r[0])
            if pg:
                personaggi.append(pg)
        label = self.formato_label_artefatto(artefatto_id, max_len=200)
        return build_dps_result_artefatto_index(art, personaggi, artifact_label=label or None)

    def formato_messaggio_dps(self, artefatto_id: int, max_righe: int = 5) -> str:
        """Messaggio DPS compatto (retrocompatibilità)."""
        res = self.dps_result_artefatto(artefatto_id)
        if not res:
            return "Artefatto non trovato."
        return dps_result_to_message_it(res, max_ranking=max_righe)

    # --- Operazioni ---
    def get_artefatto(self, artefatto_id: int) -> Optional[dict]:
        return ArtefattoRepository.get(self._art_conn(), artefatto_id)

    def lista_artefatti_liberi_completi(self, slot: str) -> List[dict]:
        """Lista artefatti nel magazzino (non assegnati) per slot, dict completi per DPS."""
        return ArtefattoRepository.lista_liberi(self._art_conn(), slot)

    def lista_artefatti_per_equip(self, slot: str, personaggio_id: Optional[int] = None) -> List[dict]:
        """Assegnabili allo slot: pezzi liberi in magazzino + quello già sul personaggio."""
        liberi = ArtefattoRepository.lista_liberi(self._art_conn(), slot)
        if not personaggio_id:
            return liberi
        eq_ids = ArtefattoRepository.equip_map_for_personaggio(self._art_conn(), personaggio_id)
        aid = eq_ids.get(slot)
        if not aid:
            return liberi
        corrente = ArtefattoRepository.get(self._art_conn(), aid)
        if corrente and not any(a["id"] == aid for a in liberi):
            return [corrente] + liberi
        return liberi

    def artefatto_opzione_select(self, a: dict) -> dict:
        """JSON per select equip / anteprima scheda."""
        subs = []
        for i in range(1, 5):
            s, v = a.get(f"sub{i}_stat"), a.get(f"sub{i}_val")
            if s or v is not None:
                subs.append({"stat": s or "", "val": v})
        sn = a.get("set_nome") or ""
        return {
            "id": a["id"],
            "slot": a.get("slot"),
            "set": sn,
            "nome": a.get("nome") or "",
            "main_stat": a.get("main_stat") or "",
            "main_val": a.get("main_val"),
            "livello": a.get("livello"),
            "stelle": a.get("stelle"),
            "subs": subs,
            "label": f"#{a['id']} {sn} {a.get('main_stat') or ''}".strip(),
        }

    def assegna_utilizzatore(self, artefatto_id: int, personaggio_id: Optional[int]) -> None:
        """Magazzino: nessun utilizzatore (None); altrimenti equipaggia al personaggio (stesso slot)."""
        if personaggio_id is None:
            ArtefattoRepository.unassign_artefatto(self._art_conn(), artefatto_id)
            return
        art = ArtefattoRepository.get(self._art_conn(), artefatto_id)
        if not art:
            raise ValueError("Artefatto non trovato")
        if PersonaggioRepository.get(self._main_conn(), personaggio_id) is None:
            raise ValueError("Personaggio non trovato")
        slot = art["slot"]
        ArtefattoRepository.set_equipaggiamento(self._art_conn(), personaggio_id, slot, artefatto_id)

    def lista_artefatti_inventario_per_tabella(self) -> List[dict]:
        """Lista per tabella build: [{id, slot, set, main, val, score}, ...]."""
        righe = self.lista_artefatti_inventario_righe()
        return [{"id": r[0], "slot": r[1], "set": r[2], "main": r[3], "val": r[4], "score": "—"} for r in righe]

    def lista_artefatti_completa(self) -> List[dict]:
        """Magazzino globale: main + sub + utilizzatore (personaggio_id)."""
        lista = ArtefattoRepository.lista(self._art_conn())
        nomi = {r[0]: r[1] for r in PersonaggioRepository.lista(self._main_conn())}
        out = []
        for a in lista:
            pid = a.get("assegna_a_id")
            util = None
            if pid:
                util = nomi.get(pid)
                if util is None:
                    util = "Scheda non trovata"
            out.append({
                "id": a["id"], "slot": a.get("slot"), "set": a.get("set_nome"), "nome": a.get("nome"),
                "main": a.get("main_stat"), "main_val": a.get("main_val"),
                "livello": a.get("livello"), "stelle": a.get("stelle"),
                "personaggio_id": pid,
                "utilizzatore": util,
                "subs": [
                    {"stat": a.get(f"sub{i}_stat"), "val": a.get(f"sub{i}_val")}
                    for i in range(1, 5)
                    if a.get(f"sub{i}_stat") or a.get(f"sub{i}_val") is not None
                ],
            })
        return out

    def dettaglio_artefatto_json(self, artefatto_id: int) -> Optional[Dict[str, Any]]:
        """Singolo record per modale dettaglio / modifica."""
        a = ArtefattoRepository.get(self._art_conn(), artefatto_id)
        if not a:
            return None
        nomi = {r[0]: r[1] for r in PersonaggioRepository.lista(self._main_conn())}
        pid = a.get("assegna_a_id")
        util = nomi.get(pid) if pid else None
        if pid and util is None:
            util = "Scheda non trovata"
        return {
            "id": a["id"],
            "slot": a.get("slot"),
            "set_nome": a.get("set_nome") or "",
            "nome": a.get("nome") or "",
            "livello": a.get("livello"),
            "stelle": a.get("stelle"),
            "main_stat": a.get("main_stat") or "",
            "main_val": a.get("main_val"),
            "sub1_stat": a.get("sub1_stat") or "",
            "sub1_val": a.get("sub1_val"),
            "sub2_stat": a.get("sub2_stat") or "",
            "sub2_val": a.get("sub2_val"),
            "sub3_stat": a.get("sub3_stat") or "",
            "sub3_val": a.get("sub3_val"),
            "sub4_stat": a.get("sub4_stat") or "",
            "sub4_val": a.get("sub4_val"),
            "personaggio_id": pid,
            "utilizzatore": util,
        }

    def suggerimenti_personaggi_per_artefatto(self, artefatto_id: int) -> Dict[str, Any]:
        """Ranking personaggi salvati (punteggio DPS semplificato sul pezzo)."""
        art = ArtefattoRepository.get(self._art_conn(), artefatto_id)
        if not art:
            return {"artefatto_id": artefatto_id, "ranking": [], "messaggio": "Manufatto non trovato."}
        personaggi = []
        for r in PersonaggioRepository.lista(self._main_conn()):
            pg = PersonaggioRepository.get(self._main_conn(), r[0])
            if pg:
                personaggi.append(pg)
        if not personaggi:
            return {
                "artefatto_id": artefatto_id,
                "ranking": [],
                "messaggio": "Salva i personaggi dalla pagina Personaggio: qui comparirà un ordine indicativo di chi trae più vantaggio da questo pezzo.",
            }
        ranking = []
        for pg in personaggi:
            sc, fattori = DpsCalculator.score_artefatto_per_personaggio(art, pg)
            ranking.append(
                {
                    "personaggio_id": pg.id,
                    "nome": pg.nome,
                    "elemento": pg.elemento,
                    "score": sc,
                    "fattori": fattori,
                }
            )
        ranking.sort(key=lambda x: -float(x["score"]))
        return {
            "artefatto_id": artefatto_id,
            "ranking": ranking,
            "messaggio": (
                "Punteggio indicativo: main/sub, DMG% elemento su tutto il pezzo, EM pesato per elemento, "
                "aggiustamento se CR foglio+pezzo supera ~78%. Assegnazione: Manufatti → modulo Assegnazione."
            ),
        }

    def aggiorna_artefatto(self, artefatto_id: int, form_values: dict) -> None:
        """Aggiorna statistiche (livello, main, sub…). Slot: solo se il pezzo non è assegnato."""
        from core.validation import parse_number
        ex = ArtefattoRepository.get(self._art_conn(), artefatto_id)
        if not ex:
            raise ValueError("Artefatto non trovato")
        slot_in = (form_values.get("slot") or ex.get("slot") or "fiore").strip()
        if ex.get("assegna_a_id") and slot_in != ex.get("slot"):
            raise ValueError(
                "Questo pezzo è assegnato a un personaggio: non puoi cambiare lo slot. "
                "In Manufatti imposta Personaggio su «Solo magazzino (libero)», salva, poi riapri il modulo."
            )
        dati = (
            slot_in,
            form_values.get("set_nome", ex.get("set_nome") or "") or "",
            form_values.get("nome", ex.get("nome") or "") or "",
            parse_number(form_values.get("livello"), default=20) or 20,
            parse_number(form_values.get("stelle"), default=5) or 5,
            form_values.get("main_stat", "") or "",
            parse_number(form_values.get("main_val")),
            form_values.get("sub1_stat", "") or "",
            parse_number(form_values.get("sub1_val")),
            form_values.get("sub2_stat", "") or "",
            parse_number(form_values.get("sub2_val")),
            form_values.get("sub3_stat", "") or "",
            parse_number(form_values.get("sub3_val")),
            form_values.get("sub4_stat", "") or "",
            parse_number(form_values.get("sub4_val")),
        )
        set_n = (dati[1] or "").strip()
        if set_n:
            register_extra_set(set_n)
        ArtefattoRepository.update(self._art_conn(), artefatto_id, dati)
        if "personaggio_id" in form_values:
            raw_pid = form_values.get("personaggio_id")
            if raw_pid in (None, "", 0, "0"):
                self.assegna_utilizzatore(artefatto_id, None)
            else:
                try:
                    pid = int(raw_pid)
                except (TypeError, ValueError) as e:
                    raise ValueError("personaggio_id non valido") from e
                self.assegna_utilizzatore(artefatto_id, pid)

    def elimina_artefatto(self, artefatto_id: int) -> None:
        if not ArtefattoRepository.delete(self._art_conn(), artefatto_id):
            raise ValueError("Artefatto non trovato")

    # --- Catalogo (filtraggio progressivo) ---
    def set_per_slot(self, slot: str) -> List[str]:
        """Tutti i nomi set del catalogo (ogni set ha i 5 pezzi; elenco uguale per ogni slot)."""
        return lista_set()

    def pezzi_catalogo_set_slot(self, set_nome: str, slot: str) -> List[str]:
        """Nomi pezzo ufficiali per set + slot (dal catalogo in `artifact_catalog.py`)."""
        return pezzi_catalogo_per_set_e_slot(set_nome, slot)

    def suggerimenti_artefatto(
        self,
        slot: str,
        set_partial: str = "",
        nome_partial: str = "",
        main_stat: str = "",
    ) -> List[Tuple[str, str]]:
        """[(set_nome, nome_pezzo), ...] filtrati progressivamente."""
        return filtra_progressivo(slot, set_partial, nome_partial, main_stat)

    def main_stats_per_slot(self, slot: str) -> List[str]:
        """Lista main stats possibili per lo slot."""
        return list(MAIN_STATS_PER_SLOT.get(slot, ["HP", "ATK"]))

    def cerca_artefatto_online(self, query: str) -> str:
        """URL ricerca Hoyolab. Ritorna URL da aprire."""
        q = (query or "").strip().replace(" ", "+")
        if not q:
            return "https://www.hoyolab.com/"
        return f"https://www.hoyolab.com/search?keyword={q}"

    def cerca_artefatto_web(self, query: str) -> str:
        """URL ricerca web (Google) - fallback se non su Hoyolab."""
        q = (query or "").strip().replace(" ", "+")
        if not q:
            return "https://www.google.com/search?q=Genshin+Impact+artefatti"
        return f"https://www.google.com/search?q=Genshin+Impact+{q}+artefatto+italiano"

    def aggiungi_artefatto(self, form_values: dict) -> int:
        """Registra artefatto. Ritorna id."""
        from core.validation import parse_number
        dati = (
            form_values.get("slot", "fiore"),
            form_values.get("set_nome", ""),
            form_values.get("nome", ""),
            parse_number(form_values.get("livello"), default=20) or 20,
            parse_number(form_values.get("stelle"), default=5) or 5,
            form_values.get("main_stat", ""),
            parse_number(form_values.get("main_val")),
            form_values.get("sub1_stat", ""),
            parse_number(form_values.get("sub1_val")),
            form_values.get("sub2_stat", ""),
            parse_number(form_values.get("sub2_val")),
            form_values.get("sub3_stat", ""),
            parse_number(form_values.get("sub3_val")),
            form_values.get("sub4_stat", ""),
            parse_number(form_values.get("sub4_val")),
        )
        set_n = (form_values.get("set_nome") or "").strip()
        if set_n:
            register_extra_set(set_n)
        aid = ArtefattoRepository.insert(self._art_conn(), dati)
        raw_pid = form_values.get("personaggio_id")
        if raw_pid not in (None, "", 0, "0"):
            try:
                pid = int(raw_pid)
            except (TypeError, ValueError) as e:
                raise ValueError("personaggio_id non valido") from e
            self.assegna_utilizzatore(aid, pid)
        return aid

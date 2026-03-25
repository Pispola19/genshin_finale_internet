"""
PersonaggioService - logica personaggio, arma, costellazioni, talenti, equipaggiamento.
Tutte le chiamate ai Repository per personaggi passano da qui.
"""
from typing import List, Optional, Tuple

from core.validation import parse_number, validate_nome
from db.connection import close_thread_connections, get_connection, get_artefatti_connection
from config import SLOT_DB, PERSONAGGI_GENSHIN
from db.repositories import (
    PersonaggioRepository, ArmaRepository,
    ArtefattoRepository, CostellazioniRepository, TalentiRepository
)


def _is_test_name(nome: str) -> bool:
    """True se il nome sembra un'entrata di test (test, Test1, test test, ecc.)."""
    n = (nome or "").strip().lower()
    if not n:
        return False
    if n == "test":
        return True
    if " test " in n or n.startswith("test ") or n.endswith(" test"):
        return True
    if n.startswith("test") and (len(n) == 4 or (len(n) > 4 and n[4:].replace(" ", "").isdigit())):
        return True  # test, Test1, Test123
    return False


class PersonaggioService:
    """Servizio personaggi. Nessun accesso diretto ai Repository dalla GUI."""

    def __init__(self):
        """Lo schema DB si inizializza al primo uso; ogni thread ha la sua coppia di connessioni."""
        pass

    def close(self) -> None:
        close_thread_connections()

    @property
    def conn(self):
        return get_connection()

    @property
    def conn_art(self):
        return get_artefatti_connection()

    # --- Validazione ---
    def valida_nome(self, nome: str, escludi_id: Optional[int] = None) -> Tuple[bool, str]:
        ok, msg = validate_nome(nome)
        if not ok:
            return False, msg
        if PersonaggioRepository.nome_esiste(self.conn, nome, escludi_id):
            return False, f"Il nome '{nome}' è già usato."
        return True, ""

    # --- Fetch dati (ritorna strutture pronte per UI) ---
    @staticmethod
    def _fmt_talento_cella(v: Optional[int]) -> str:
        if v is None:
            return "-"
        return str(int(v))

    def carica_dati_completi(self, id_pg: int) -> Optional[dict]:
        """Dati completi personaggio per popolare il form (già formattati per UI)."""
        pg = PersonaggioRepository.get(self.conn, id_pg)
        if not pg:
            return None
        arma = ArmaRepository.get(self.conn, id_pg)
        cost = CostellazioniRepository.get(self.conn, id_pg)
        talenti = TalentiRepository.get(self.conn, id_pg)
        eq = ArtefattoRepository.equip_map_for_personaggio(self.conn_art, id_pg)
        artefatti = {}
        for slot, aid in eq.items():
            if aid:
                art = ArtefattoRepository.get(self.conn_art, aid)
                artefatti[slot] = art

        def _fmt(v):
            return "-" if (v is None or v == "") else str(v)

        return {
            "nome": pg.nome,
            "livello": _fmt(pg.livello),
            "elemento": pg.elemento,
            "hp_flat": _fmt(pg.hp_flat), "atk_flat": _fmt(pg.atk_flat),
            "def_flat": _fmt(pg.def_flat), "em_flat": _fmt(pg.em_flat),
            "cr": _fmt(pg.cr), "cd": _fmt(pg.cd), "er": _fmt(pg.er),
            "arma": {
                "nome": arma.nome if arma else "",
                "tipo": arma.tipo if arma else "Spada",
                "livello": _fmt(arma.livello) if arma else "",
                "stelle": _fmt(arma.stelle) if arma else "",
                "atk_base": _fmt(arma.atk_base) if arma else "",
                "stat_secondaria": (arma.stat_secondaria or "") if arma else "",
                "valore_stat": _fmt(arma.valore_stat) if arma else "",
            } if arma else {"nome": "", "tipo": "Spada", "livello": "", "stelle": "", "atk_base": "", "stat_secondaria": "", "valore_stat": ""},
            "costellazioni": [cost.c1, cost.c2, cost.c3, cost.c4, cost.c5, cost.c6],

            "talenti": [
                self._fmt_talento_cella(talenti.aa),
                self._fmt_talento_cella(talenti.skill),
                self._fmt_talento_cella(talenti.burst),
                self._fmt_talento_cella(talenti.pas1),
                self._fmt_talento_cella(talenti.pas2),
                self._fmt_talento_cella(talenti.pas3),
                self._fmt_talento_cella(talenti.pas4),
            ],
            "artefatti": {
                slot: self._artefatto_per_ui(artefatti[slot])
                if slot in artefatti else {"id": None, "set": "", "main_stat": "", "main_val": None, "subs": []}
                for slot in SLOT_DB
            },
        }

    def _artefatto_per_ui(self, art: dict) -> dict:
        """Artefatto completo per UI: id, set, main_stat, main_val, subs [(stat, val), ...]."""
        subs = []
        for i in range(1, 5):
            s, v = art.get(f"sub{i}_stat"), art.get(f"sub{i}_val")
            if s or v is not None:
                subs.append({"stat": s or "", "val": v})
        return {
            "id": art["id"],
            "set": art.get("set_nome") or "",
            "nome": art.get("nome") or "",
            "main_stat": art.get("main_stat") or "",
            "main_val": art.get("main_val"),
            "livello": art.get("livello"),
            "stelle": art.get("stelle"),
            "subs": subs,
        }

    def get_personaggio(self, id_pg: int):
        """Personaggio raw per logica build/team."""
        return PersonaggioRepository.get(self.conn, id_pg)

    def get_equipaggiamento_ids(self, personaggio_id: int) -> dict:
        """{slot: artefatto_id} per personaggio."""
        return ArtefattoRepository.equip_map_for_personaggio(self.conn_art, personaggio_id)

    def lista_personaggi_righe(self) -> List[Tuple[int, str, int, str]]:
        """Righe pronte per Treeview: [(id, nome, livello, elemento), ...]."""
        return PersonaggioRepository.lista(self.conn)

    def nomi_per_autocomplete(self) -> List[str]:
        """Lista nomi per autocomplete: PERSONAGGI_GENSHIN + personaggi esistenti non in lista."""
        set_base = set(PERSONAGGI_GENSHIN)
        righe = PersonaggioRepository.lista(self.conn)
        extra = [r[1] for r in righe if r[1] and r[1].strip() and r[1] not in set_base]
        return list(PERSONAGGI_GENSHIN) + sorted(set(extra))

    def rimuovi_entrate_test(self) -> int:
        """Elimina personaggi con nome tipo 'test', 'Test1', ecc. Ritorna numero eliminati."""
        cur = self.conn.cursor()
        cur.execute("SELECT id, nome FROM personaggi")
        rows = cur.fetchall()
        eliminati = 0
        for id_pg, nome in rows:
            if nome and _is_test_name(nome):
                self.elimina_personaggio(id_pg)
                eliminati += 1
        return eliminati

    # --- Salvataggio (accetta valori form grezzi, parsing interno) ---
    def salva_completo(
        self,
        id_pg: Optional[int],
        form_personaggio: dict,
        form_arma: dict,
        form_costellazioni: dict,
        form_talenti: dict,
        form_equipaggiamento: Optional[dict],
    ) -> int:
        """Salva personaggio e dati collegati. Ritorna id personaggio.

        Se ``form_equipaggiamento`` è ``None``, l'equip manufatti non viene toccato
        (es. web: assegnazione solo da pagina Manufatti).
        """
        dati_pg = self._parse_personaggio(form_personaggio)
        dati_arma = self._parse_arma(form_arma)
        cost = self._parse_costellazioni(form_costellazioni)
        talenti = self._parse_talenti(form_talenti)

        # Id obsoleto (es. scheda eliminata ma browser con id vecchio) → tratta come nuovo salvataggio
        if id_pg is not None and PersonaggioRepository.get(self.conn, id_pg) is None:
            id_pg = None

        tuple_pg = self._to_tuple_pg(dati_pg)
        if id_pg is None:
            existing_id = PersonaggioRepository.id_per_nome(self.conn, dati_pg["nome"])
            if existing_id is not None:
                id_pg = existing_id
                PersonaggioRepository.update(self.conn, id_pg, tuple_pg)
            else:
                id_pg = PersonaggioRepository.insert(self.conn, tuple_pg)
        else:
            PersonaggioRepository.update(self.conn, id_pg, tuple_pg)

        ArmaRepository.upsert(self.conn, id_pg, self._to_tuple_arma(dati_arma))
        CostellazioniRepository.upsert(self.conn, id_pg, *cost)
        TalentiRepository.upsert(self.conn, id_pg, *talenti)

        if form_equipaggiamento is not None:
            for slot in SLOT_DB:
                raw = form_equipaggiamento.get(slot)
                if raw in (None, "", 0, "0"):
                    ArtefattoRepository.set_equipaggiamento(self.conn_art, id_pg, slot, None)
                else:
                    aid = int(raw)
                    ArtefattoRepository.set_equipaggiamento(self.conn_art, id_pg, slot, aid)
        return id_pg

    def elimina_personaggio(self, id_pg: int) -> None:
        ArtefattoRepository.unassign_all_for_personaggio(self.conn_art, id_pg)
        PersonaggioRepository.delete(self.conn, id_pg)

    # --- Parsing form -> strutture interne ---
    def _parse_personaggio(self, f: dict) -> dict:
        def n(k, default=0):
            return parse_number(f.get(k), default=default) or default
        return {
            "nome": (f.get("nome") or "").strip(),
            "livello": n("livello", 1),
            "elemento": f.get("elemento") or "Pyro",
            "hp_flat": n("hp_flat"), "atk_flat": n("atk_flat"),
            "def_flat": n("def_flat"), "em_flat": n("em_flat"),
            "cr": n("cr"), "cd": n("cd"), "er": n("er"),
        }

    def _parse_arma(self, f: dict) -> dict:
        def n(k, default=0):
            return parse_number(f.get(k), default=default) or default
        return {
            "nome": (f.get("nome") or "").strip(),
            "tipo": f.get("tipo") or "Spada",
            "livello": n("livello", 1),
            "stelle": n("stelle", 5),
            "atk_base": n("atk_base"),
            "stat_secondaria": f.get("stat_secondaria") or "",
            "valore_stat": parse_number(f.get("valore_stat")),
        }

    def _parse_costellazioni(self, f: dict) -> tuple:
        """Solo 0 (spenta) o 1 (accesa) per ogni costellazione."""
        out = []
        for i in range(6):
            v = parse_number(f.get(f"c{i+1}"), default=0)
            v = 0 if (v is None or v < 1) else 1
            out.append(v)
        return tuple(out)

    def _parse_one_talento(self, raw) -> Optional[int]:
        """- o vuoto → None; 0–10 → intero. Valori fuori range → None."""
        if raw is None:
            return None
        s = str(raw).strip()
        if s == "" or s == "-":
            return None
        n = parse_number(s, default=None, min_val=0, max_val=10)
        if n is None:
            return None
        return int(n)

    def _parse_talenti(self, f: dict) -> tuple:
        keys = ("aa", "skill", "burst", "pas1", "pas2", "pas3", "pas4")
        return tuple(self._parse_one_talento(f.get(k)) for k in keys)

    def _to_tuple_pg(self, d: dict) -> tuple:
        def n(k, default=0):
            return d.get(k, default) if isinstance(d.get(k), (int, float)) else (parse_number(d.get(k), default=default) or default)
        return (
            d.get("nome", ""),
            n("livello", 1),
            d.get("elemento", "Pyro"),
            n("hp_flat"), n("atk_flat"), n("def_flat"), n("em_flat"),
            n("cr"), n("cd"), n("er")
        )

    def _to_tuple_arma(self, d: dict) -> tuple:
        def n(k, default=0):
            return d.get(k, default) if isinstance(d.get(k), (int, float)) else (parse_number(d.get(k), default=default) or default)
        return (
            d.get("nome", ""),
            d.get("tipo", "Spada"),
            n("livello", 1),
            n("stelle", 5),
            n("atk_base"),
            d.get("stat_secondaria"),
            parse_number(d.get("valore_stat")) if "valore_stat" in d else d.get("valore_stat")
        )

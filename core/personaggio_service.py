"""
PersonaggioService - logica personaggio, arma, costellazioni, talenti, equipaggiamento.
Tutte le chiamate ai Repository per personaggi passano da qui.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Tuple

from config import SLOT_DB
from core.custom_registry import approved_armi_names, approved_personaggi_names
from core.nome_normalization import (
    canonicalizza_nome_arma,
    canonicalizza_nome_personaggio,
    norm_key_nome,
)
from core.nomi_whitelist import (
    WHITELIST_ARMI,
    WHITELIST_ARMI_EFFECTIVE,
    WHITELIST_PERSONAGGI,
    WHITELIST_PERSONAGGI_EFFECTIVE,
)
from core.validation import parse_number, validate_arma_nome, validate_nome
from db.connection import close_thread_connections, get_connection, get_artefatti_connection
from db.models import Arma, Personaggio
from db.repositories import (
    PersonaggioRepository,
    ArmaRepository,
    ArtefattoRepository,
    CostellazioniRepository,
    TalentiRepository,
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _audit_personaggio_nome(nome: str, existing: Optional[Personaggio], meta: dict) -> Tuple[str, Optional[str], Optional[str]]:
    nome = canonicalizza_nome_personaggio(nome or "")
    reg = approved_personaggi_names()
    if nome in WHITELIST_PERSONAGGI or nome in reg:
        return "ufficiale", None, None
    if existing and norm_key_nome(existing.nome) == norm_key_nome(nome) and (existing.origine_nome or "") == "custom":
        data = existing.data_nome_custom or _iso_now()
        if meta.get("personaggio_custom_note") is not None:
            note = (meta.get("personaggio_custom_note") or "").strip() or None
        else:
            note = existing.nota_nome_custom
        return "custom", data, note
    note = (meta.get("personaggio_custom_note") or "").strip() or None
    return "custom", _iso_now(), note


def _audit_arma_nome(nome: str, existing: Optional[Arma], meta: dict) -> Tuple[str, Optional[str], Optional[str]]:
    s = canonicalizza_nome_arma(nome or "")
    if not s:
        return "ufficiale", None, None
    reg = approved_armi_names()
    if s in WHITELIST_ARMI or s in reg:
        return "ufficiale", None, None
    if existing and norm_key_nome(existing.nome or "") == norm_key_nome(s) and (existing.origine_nome or "") == "custom":
        data = existing.data_nome_custom or _iso_now()
        if meta.get("arma_custom_note") is not None:
            note = (meta.get("arma_custom_note") or "").strip() or None
        else:
            note = existing.nota_nome_custom
        return "custom", data, note
    note = (meta.get("arma_custom_note") or "").strip() or None
    return "custom", _iso_now(), note


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
    def valida_nome(
        self,
        nome: str,
        escludi_id: Optional[int] = None,
        *,
        custom_confirm: bool = False,
    ) -> Tuple[bool, str]:
        nome_c = canonicalizza_nome_personaggio(nome or "")
        if escludi_id is not None:
            ex = PersonaggioRepository.get(self.conn, escludi_id)
            if ex and norm_key_nome(ex.nome) == norm_key_nome(nome_c):
                ok, msg = validate_nome(nome_c, custom_confirm=custom_confirm)
                if not ok:
                    return False, msg
                if PersonaggioRepository.nome_esiste(self.conn, nome_c, escludi_id):
                    return False, f"Il nome '{nome_c}' è già usato (anche con altre maiuscole o spazi)."
                return True, ""
        ok, msg = validate_nome(nome_c, custom_confirm=custom_confirm)
        if not ok:
            return False, msg
        if PersonaggioRepository.nome_esiste(self.conn, nome_c, escludi_id):
            return False, f"Il nome '{nome_c}' è già usato (anche con altre maiuscole o spazi)."
        return True, ""

    def id_per_nome(self, nome: str) -> Optional[int]:
        """Id personaggio se esiste una scheda con questo nome, altrimenti None."""
        return PersonaggioRepository.id_per_nome(self.conn, nome)

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

        arma_block = None
        if arma:
            arma_block = {
                "nome": arma.nome if arma else "",
                "tipo": arma.tipo if arma else "Spada",
                "livello": _fmt(arma.livello) if arma else "",
                "stelle": _fmt(arma.stelle) if arma else "",
                "atk_base": _fmt(arma.atk_base) if arma else "",
                "stat_secondaria": (arma.stat_secondaria or "") if arma else "",
                "valore_stat": _fmt(arma.valore_stat) if arma else "",
                "origine_nome": (arma.origine_nome or "ufficiale") if arma else "ufficiale",
                "data_nome_custom": arma.data_nome_custom,
                "nota_nome_custom": arma.nota_nome_custom,
            }
        else:
            arma_block = {
                "nome": "", "tipo": "Spada", "livello": "", "stelle": "", "atk_base": "",
                "stat_secondaria": "", "valore_stat": "",
                "origine_nome": "ufficiale", "data_nome_custom": None, "nota_nome_custom": None,
            }

        return {
            "nome": pg.nome,
            "livello": _fmt(pg.livello),
            "elemento": pg.elemento,
            "hp_flat": _fmt(pg.hp_flat), "atk_flat": _fmt(pg.atk_flat),
            "def_flat": _fmt(pg.def_flat), "em_flat": _fmt(pg.em_flat),
            "cr": _fmt(pg.cr), "cd": _fmt(pg.cd), "er": _fmt(pg.er),
            "origine_nome": pg.origine_nome or "ufficiale",
            "data_nome_custom": pg.data_nome_custom,
            "nota_nome_custom": pg.nota_nome_custom,
            "arma": arma_block,
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
                if slot in artefatti
                else {"id": None, "set": "", "main_stat": "", "main_val": None, "subs": [], "label": "—"}
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
        sn = art.get("set_nome") or ""
        return {
            "id": art["id"],
            "set": sn,
            "nome": art.get("nome") or "",
            "main_stat": art.get("main_stat") or "",
            "main_val": art.get("main_val"),
            "livello": art.get("livello"),
            "stelle": art.get("stelle"),
            "subs": subs,
            "label": f"#{art['id']} {sn} {art.get('main_stat') or ''}".strip(),
        }

    def get_personaggio(self, id_pg: int):
        """Personaggio raw per logica build/team."""
        return PersonaggioRepository.get(self.conn, id_pg)

    def get_arma(self, personaggio_id: int) -> Optional[Arma]:
        """Arma equipaggiata al personaggio, se presente."""
        return ArmaRepository.get(self.conn, personaggio_id)

    def get_equipaggiamento_ids(self, personaggio_id: int) -> dict:
        """{slot: artefatto_id} per personaggio."""
        return ArtefattoRepository.equip_map_for_personaggio(self.conn_art, personaggio_id)

    def get_talenti(self, personaggio_id: int):
        """Livelli talento AA/E/Q… come da DB (None = non compilato)."""
        return TalentiRepository.get(self.conn, personaggio_id)

    def lista_personaggi_righe(self) -> List[Tuple[int, str, int, str]]:
        """Righe pronte per Treeview: [(id, nome, livello, elemento), ...]."""
        return PersonaggioRepository.lista(self.conn)

    def nomi_per_autocomplete(self) -> List[str]:
        """Elenco effettivo personaggi (codice ∪ registry approvato), ordinato."""
        return sorted(WHITELIST_PERSONAGGI_EFFECTIVE, key=str.lower)

    def nomi_armi_autocomplete(self) -> List[str]:
        """Elenco effettivo armi (codice ∪ registry approvato), ordinato."""
        return sorted(WHITELIST_ARMI_EFFECTIVE, key=str.lower)

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
        meta: Optional[dict] = None,
    ) -> int:
        """Salva personaggio e dati collegati. Ritorna id personaggio.

        ``meta`` opzionale: personaggio_custom_note, arma_custom_note.

        Se ``form_equipaggiamento`` è ``None``, l'equip manufatti non viene toccato
        (es. web: assegnazione solo da pagina Manufatti).
        """
        meta = meta or {}
        dati_pg = self._parse_personaggio(form_personaggio)
        dati_arma = self._parse_arma(form_arma)
        dati_pg["nome"] = canonicalizza_nome_personaggio(dati_pg.get("nome") or "")
        dati_arma["nome"] = canonicalizza_nome_arma(dati_arma.get("nome") or "")
        cost = self._parse_costellazioni(form_costellazioni)
        talenti = self._parse_talenti(form_talenti)

        if id_pg is not None and PersonaggioRepository.get(self.conn, id_pg) is None:
            id_pg = None

        arma_nome = dati_arma.get("nome") or ""

        merge_for_name = id_pg
        ok_n, err_n = self.valida_nome(
            dati_pg["nome"],
            merge_for_name,
            custom_confirm=True,
        )
        if not ok_n:
            raise ValueError(err_n)

        lookup_arma_pid = id_pg if id_pg is not None else PersonaggioRepository.id_per_nome(self.conn, dati_pg["nome"])
        skip_arma_confirm = False
        if lookup_arma_pid is not None:
            old_a = ArmaRepository.get(self.conn, lookup_arma_pid)
            if old_a and norm_key_nome(old_a.nome or "") == norm_key_nome(arma_nome):
                skip_arma_confirm = True
        if not skip_arma_confirm:
            ok_a, err_a = validate_arma_nome(arma_nome, custom_confirm=True)
            if not ok_a:
                raise ValueError(f"Arma: {err_a}")

        merge_id = lookup_arma_pid
        exist_pg = PersonaggioRepository.get(self.conn, merge_id) if merge_id is not None else None
        exist_ar = ArmaRepository.get(self.conn, merge_id) if merge_id is not None else None
        o_p, d_p, n_p = _audit_personaggio_nome(dati_pg["nome"], exist_pg, meta)
        o_a, d_a, n_a = _audit_arma_nome(arma_nome, exist_ar, meta)

        tuple_pg = self._to_tuple_pg(dati_pg, o_p, d_p, n_p)
        tuple_arma = self._to_tuple_arma(dati_arma, o_a, d_a, n_a)

        final_id = id_pg
        if final_id is None:
            existing_id = PersonaggioRepository.id_per_nome(self.conn, dati_pg["nome"])
            if existing_id is not None:
                final_id = existing_id
                PersonaggioRepository.update(self.conn, final_id, tuple_pg)
            else:
                final_id = PersonaggioRepository.insert(self.conn, tuple_pg)
        else:
            PersonaggioRepository.update(self.conn, final_id, tuple_pg)

        ArmaRepository.upsert(self.conn, final_id, tuple_arma)
        CostellazioniRepository.upsert(self.conn, final_id, *cost)
        TalentiRepository.upsert(self.conn, final_id, *talenti)

        if form_equipaggiamento is not None:
            for slot in SLOT_DB:
                raw = form_equipaggiamento.get(slot)
                if raw in (None, "", 0, "0"):
                    ArtefattoRepository.set_equipaggiamento(self.conn_art, final_id, slot, None)
                else:
                    aid = int(raw)
                    ArtefattoRepository.set_equipaggiamento(self.conn_art, final_id, slot, aid)
        return final_id

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

        raw_stat = (f.get("stat_secondaria") or "").strip()
        st_up = raw_stat.upper().replace(" ", "_")
        if raw_stat and (
            st_up
            in (
                "ER",
                "ER%",
                "ENERGY_RECHARGE",
                "RICARICA_ENERGIA",
                "ENERGY_RECHARGE%",
            )
            or "ENERGY_RECHARGE" in st_up
            or st_up.startswith("RICARICA")
        ):
            canon_stat = "ER%"
        else:
            canon_stat = raw_stat

        return {
            "nome": (f.get("nome") or "").strip(),
            "tipo": f.get("tipo") or "Spada",
            "livello": n("livello", 1),
            "stelle": n("stelle", 5),
            "atk_base": n("atk_base"),
            "stat_secondaria": canon_stat,
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

    def _to_tuple_pg(self, d: dict, origine: str, data_c: Optional[str], nota: Optional[str]) -> tuple:
        def n(k, default=0):
            return d.get(k, default) if isinstance(d.get(k), (int, float)) else (parse_number(d.get(k), default=default) or default)
        return (
            d.get("nome", ""),
            n("livello", 1),
            d.get("elemento", "Pyro"),
            n("hp_flat"), n("atk_flat"), n("def_flat"), n("em_flat"),
            n("cr"), n("cd"), n("er"),
            origine,
            data_c,
            nota,
        )

    def _to_tuple_arma(self, d: dict, origine: str, data_c: Optional[str], nota: Optional[str]) -> tuple:
        def n(k, default=0):
            return d.get(k, default) if isinstance(d.get(k), (int, float)) else (parse_number(d.get(k), default=default) or default)
        return (
            d.get("nome", ""),
            d.get("tipo", "Spada"),
            n("livello", 1),
            n("stelle", 5),
            n("atk_base"),
            d.get("stat_secondaria"),
            parse_number(d.get("valore_stat")) if "valore_stat" in d else d.get("valore_stat"),
            origine,
            data_c,
            nota,
        )

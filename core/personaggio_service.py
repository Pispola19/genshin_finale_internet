"""
PersonaggioService - logica personaggio, arma, costellazioni, talenti, equipaggiamento.
Tutte le chiamate ai Repository per personaggi passano da qui.
"""
from typing import Any, List, Optional, Tuple

from core.validation import parse_number, validate_nome
from db.connection import close_thread_connections, get_connection, get_artefatti_connection
from config import SLOT_DB, PERSONAGGI_GENSHIN
from db.models import Arma
from db.repositories import (
    PersonaggioRepository,
    ArmaRepository,
    ArtefattoRepository,
    CostellazioniRepository,
    TalentiRepository,
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

    def replace_equipment_from_hoyo_relics(self, personaggio_id: int, relics: List[dict]) -> None:
        """
        Sostituisce i manufatti equipaggiati dal personaggio con nuove righe ricavate
        da un array ``relics`` stile API HoYoLab (battle chronicle).
        """
        from db.artifact_catalog import register_extra_set

        conn_art = self.conn_art
        cur = conn_art.cursor()
        cur.execute("SELECT id FROM artefatti WHERE assegna_a_id=?", (personaggio_id,))
        old_ids = [r[0] for r in cur.fetchall()]
        for aid in old_ids:
            ArtefattoRepository.delete(conn_art, aid)

        for rel in relics:
            if not isinstance(rel, dict):
                continue
            row, slot = _hoyo_relic_row_and_slot(rel)
            if not row or not slot:
                continue
            set_n = (row[1] or "").strip()
            if set_n:
                register_extra_set(set_n)
            new_id = ArtefattoRepository.insert(conn_art, row)
            ArtefattoRepository.set_equipaggiamento(conn_art, personaggio_id, slot, new_id)

    def append_hoyo_relics_to_warehouse(self, relics: List[dict], *, dedup: bool = True) -> int:
        """Aggiunge solo righe in inventario (non equipaggiate).

        dedup=True: evita duplicati identici nello stesso stato di inventario usando chiave
        (slot, set_nome, livello, stelle).
        """
        from db.artifact_catalog import register_extra_set

        conn_art = self.conn_art
        inserted = 0
        cur = conn_art.cursor()
        for rel in relics:
            if not isinstance(rel, dict):
                continue
            row, slot = _hoyo_relic_row_and_slot(rel)
            if not row or not slot:
                continue
            set_n = (row[1] or "").strip()
            if set_n:
                register_extra_set(set_n)

            if dedup:
                # Chiave dedup basata su slot/set/livello/rarita (richiesta utente).
                # Nota: non considera main/sub per evitare drift tra payload incompleti.
                cur.execute(
                    """
                    SELECT 1 FROM artefatti
                    WHERE assegna_a_id IS NULL
                      AND slot=? AND set_nome=? AND livello=? AND stelle=?
                    LIMIT 1
                    """,
                    (row[0], row[1], row[3], row[4]),
                )
                if cur.fetchone():
                    continue

            ArtefattoRepository.insert(conn_art, row)
            inserted += 1
        return inserted

    def update_equipment_from_hoyo_relics(self, personaggio_id: int, relics: List[dict]) -> None:
        """Aggiorna solo gli slot presenti nel JSON; merge delle stat se HoYo è vuoto; non cancella altri pezzi."""
        from db.artifact_catalog import register_extra_set

        conn_art = self.conn_art
        eq = ArtefattoRepository.equip_map_for_personaggio(conn_art, personaggio_id)
        for rel in relics:
            if not isinstance(rel, dict):
                continue
            row, slot = _hoyo_relic_row_and_slot(rel)
            if not row or not slot:
                continue
            set_n = (row[1] or "").strip()
            if set_n:
                register_extra_set(set_n)
            aid = eq.get(slot)
            if aid:
                ex = ArtefattoRepository.get(conn_art, aid)
                if ex:
                    merged = _overlay_hoyo_row_on_stored(_art_row_to_tuple(ex), row)
                    ArtefattoRepository.update(conn_art, aid, merged)
                    continue
            new_id = ArtefattoRepository.insert(conn_art, row)
            ArtefattoRepository.set_equipaggiamento(conn_art, personaggio_id, slot, new_id)
            eq[slot] = new_id


def _art_row_to_tuple(ex: dict) -> tuple:
    def _i(k, d=0):
        v = ex.get(k)
        if v is None or v == "":
            return d
        try:
            return int(v)
        except (TypeError, ValueError):
            return d

    return (
        ex.get("slot") or "fiore",
        ex.get("set_nome") or "",
        ex.get("nome") or "",
        _i("livello", 0),
        _i("stelle", 5),
        ex.get("main_stat") or "",
        ex.get("main_val"),
        ex.get("sub1_stat") or "",
        ex.get("sub1_val"),
        ex.get("sub2_stat") or "",
        ex.get("sub2_val"),
        ex.get("sub3_stat") or "",
        ex.get("sub3_val"),
        ex.get("sub4_stat") or "",
        ex.get("sub4_val"),
    )


def _overlay_hoyo_row_on_stored(stored: tuple, hoyo: tuple) -> tuple:
    """Conserva stat da DB se HoYo non porta valori; aggiorna set/nome/livello/stelle se arrivano da HoYo."""
    S = list(stored)
    H = list(hoyo)
    if len(S) < 15 or len(H) < 15:
        return tuple(H)
    for i in (1, 2):
        if H[i] and str(H[i]).strip():
            S[i] = H[i]
    for i in (3, 4):
        # livello/stelle: non sovrascriviamo con 0 (HoYo può non fornire info).
        if H[i] is not None and str(H[i]).strip() != "":
            try:
                v = int(H[i])
                if v > 0:
                    S[i] = H[i]
            except (TypeError, ValueError):
                pass
    if (H[5] and str(H[5]).strip()) or (H[6] not in (None, "")):
        S[5], S[6] = H[5], H[6]
    for j in range(4):
        si = 7 + j * 2
        if (H[si] and str(H[si]).strip()) or (H[si + 1] not in (None, "")):
            S[si], S[si + 1] = H[si], H[si + 1]
    return tuple(S)


_HOYO_POS_TO_SLOT = {
    1: "fiore",
    2: "piuma",
    3: "sabbie",
    4: "calice",
    5: "corona",
}


def _hoyo_relic_slot_from_dict(rel: dict) -> Optional[str]:
    p = rel.get("pos")
    try:
        pi = int(p)
    except (TypeError, ValueError):
        pi = None
    if pi in _HOYO_POS_TO_SLOT:
        return _HOYO_POS_TO_SLOT[pi]
    pn = str(rel.get("pos_name") or "").lower()
    if "fiore" in pn:
        return "fiore"
    if "piuma" in pn:
        return "piuma"
    if "sabbie" in pn or "sabbia" in pn:
        return "sabbie"
    if "calice" in pn:
        return "calice"
    if "corona" in pn:
        return "corona"
    return None


def _parse_hoyo_main_property(mp: Any) -> Tuple[str, Optional[float]]:
    if mp is None:
        return "", None
    if isinstance(mp, dict):
        name = str(mp.get("name") or mp.get("property_name") or "").strip()
        val = mp.get("final") if mp.get("final") is not None else mp.get("value")
        cv = parse_number(val)
        return name, cv
    return str(mp).strip(), None


def _parse_hoyo_sub_list(subs: Any) -> List[Tuple[str, Optional[float]]]:
    out: List[Tuple[str, Optional[float]]] = []
    if not isinstance(subs, list):
        return out
    for s in subs[:4]:
        if not isinstance(s, dict):
            continue
        name = str(s.get("name") or s.get("property_name") or "").strip()
        val = s.get("final") if s.get("final") is not None else s.get("value")
        out.append((name, parse_number(val)))
    return out


def _hoyo_relic_row_and_slot(rel: dict) -> Tuple[Optional[tuple], Optional[str]]:
    slot = _hoyo_relic_slot_from_dict(rel)
    if not slot:
        return None, None
    set_nome = ""
    st = rel.get("set")
    if isinstance(st, dict):
        set_nome = str(st.get("name") or "").strip()
    nome = str(rel.get("name") or "").strip()
    try:
        livello = int(rel.get("level") or 0)
    except (TypeError, ValueError):
        livello = 0
    try:
        stelle = int(rel.get("rarity") or 5)
    except (TypeError, ValueError):
        stelle = 5
    stelle = min(5, max(1, stelle))
    main_stat, main_val = _parse_hoyo_main_property(rel.get("main_property"))
    subs = _parse_hoyo_sub_list(rel.get("sub_property_list"))
    while len(subs) < 4:
        subs.append(("", None))
    row = (
        slot,
        set_nome,
        nome,
        livello,
        stelle,
        main_stat or "",
        main_val,
        subs[0][0] or "",
        subs[0][1],
        subs[1][0] or "",
        subs[1][1],
        subs[2][0] or "",
        subs[2][1],
        subs[3][0] or "",
        subs[3][1],
    )
    return row, slot

"""Repository - accesso dati, una responsabilità per repository."""
from typing import Optional, List, Tuple, Dict
import sqlite3

from db.models import Personaggio, Arma, Artefatto, Costellazioni, Talenti


class PersonaggioRepository:
    """Operazioni CRUD personaggi."""

    @staticmethod
    def insert(conn, dati: tuple) -> int:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO personaggi (nome, livello, elemento, hp_flat, atk_flat, def_flat, em_flat, cr, cd, er)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, dati)
        conn.commit()
        return cur.lastrowid

    @staticmethod
    def update(conn, id_pg: int, dati: tuple) -> None:
        cur = conn.cursor()
        cur.execute("""
            UPDATE personaggi SET nome=?, livello=?, elemento=?, hp_flat=?, atk_flat=?, def_flat=?, em_flat=?, cr=?, cd=?, er=?
            WHERE id=?
        """, (*dati, id_pg))
        conn.commit()

    @staticmethod
    def delete(conn, id_pg: int) -> None:
        cur = conn.cursor()
        for table in ("armi", "equipaggiamento", "costellazioni", "talenti"):
            cur.execute(f"DELETE FROM {table} WHERE personaggio_id=?", (id_pg,))
        cur.execute("DELETE FROM personaggi WHERE id=?", (id_pg,))
        conn.commit()

    @staticmethod
    def get(conn, id_pg: int) -> Optional[Personaggio]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM personaggi WHERE id=?", (id_pg,))
        row = cur.fetchone()
        return Personaggio.from_row(row) if row else None

    @staticmethod
    def lista(conn) -> List[Tuple[int, str, int, str]]:
        cur = conn.cursor()
        cur.execute("SELECT id, nome, livello, elemento FROM personaggi ORDER BY nome")
        return cur.fetchall()

    @staticmethod
    def nome_esiste(conn, nome: str, escludi_id: Optional[int] = None) -> bool:
        cur = conn.cursor()
        if escludi_id is not None:
            cur.execute("SELECT 1 FROM personaggi WHERE nome=? AND id!=?", (nome, escludi_id))
        else:
            cur.execute("SELECT 1 FROM personaggi WHERE nome=?", (nome,))
        return cur.fetchone() is not None

    @staticmethod
    def id_per_nome(conn, nome: str) -> Optional[int]:
        cur = conn.cursor()
        cur.execute("SELECT id FROM personaggi WHERE nome=?", ((nome or "").strip(),))
        row = cur.fetchone()
        return int(row[0]) if row else None


class ArmaRepository:
    @staticmethod
    def upsert(conn, personaggio_id: int, dati: tuple) -> None:
        cur = conn.cursor()
        cur.execute("SELECT id FROM armi WHERE personaggio_id=?", (personaggio_id,))
        if cur.fetchone():
            cur.execute("""
                UPDATE armi SET nome=?, tipo=?, livello=?, stelle=?, atk_base=?, stat_secondaria=?, valore_stat=?
                WHERE personaggio_id=?
            """, (*dati, personaggio_id))
        else:
            cur.execute("""
                INSERT INTO armi (personaggio_id, nome, tipo, livello, stelle, atk_base, stat_secondaria, valore_stat)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (personaggio_id, *dati))
        conn.commit()

    @staticmethod
    def get(conn, personaggio_id: int) -> Optional[Arma]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM armi WHERE personaggio_id=?", (personaggio_id,))
        row = cur.fetchone()
        return Arma.from_row(row) if row else None


class CostellazioniRepository:
    @staticmethod
    def upsert(conn, personaggio_id: int, c1: int, c2: int, c3: int, c4: int, c5: int, c6: int) -> None:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO costellazioni (personaggio_id, c1,c2,c3,c4,c5,c6)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (personaggio_id, c1, c2, c3, c4, c5, c6))
        conn.commit()

    @staticmethod
    def get(conn, personaggio_id: int) -> Costellazioni:
        cur = conn.cursor()
        cur.execute("SELECT c1,c2,c3,c4,c5,c6 FROM costellazioni WHERE personaggio_id=?", (personaggio_id,))
        return Costellazioni.from_row(cur.fetchone())


class TalentiRepository:
    @staticmethod
    def upsert(
        conn,
        personaggio_id: int,
        aa: Optional[int],
        skill: Optional[int],
        burst: Optional[int],
        pas1: Optional[int],
        pas2: Optional[int],
        pas3: Optional[int],
        pas4: Optional[int],
    ) -> None:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO talenti
            (personaggio_id, aa, skill, burst, pas1, pas2, pas3, pas4)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (personaggio_id, aa, skill, burst, pas1, pas2, pas3, pas4))
        conn.commit()

    @staticmethod
    def get(conn, personaggio_id: int) -> Talenti:
        cur = conn.cursor()
        cur.execute(
            "SELECT aa, skill, burst, pas1, pas2, pas3, pas4 FROM talenti WHERE personaggio_id=?",
            (personaggio_id,),
        )
        return Talenti.from_row(cur.fetchone())


class ArtefattoRepository:
    """Operazioni su database artefatti."""

    @staticmethod
    def insert(conn, dati: tuple) -> int:
        cur = conn.cursor()
        cols = ("slot", "set_nome", "nome", "livello", "stelle", "main_stat", "main_val",
                "sub1_stat", "sub1_val", "sub2_stat", "sub2_val", "sub3_stat", "sub3_val", "sub4_stat", "sub4_val")
        ph = ",".join("?" * len(cols))
        cur.execute(f"INSERT INTO artefatti ({','.join(cols)}) VALUES ({ph})", dati)
        conn.commit()
        return cur.lastrowid

    @staticmethod
    def get(conn, artefatto_id: int) -> Optional[dict]:
        cur = conn.cursor()
        cur.execute("SELECT * FROM artefatti WHERE id=?", (artefatto_id,))
        row = cur.fetchone()
        if not row:
            return None
        return dict(zip([d[0] for d in cur.description], row))

    @staticmethod
    def lista(conn, slot: Optional[str] = None) -> List[dict]:
        cur = conn.cursor()
        if slot:
            cur.execute("SELECT * FROM artefatti WHERE slot=? ORDER BY id DESC", (slot,))
        else:
            cur.execute("SELECT * FROM artefatti ORDER BY id DESC")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def lista_liberi(conn_art, slot: str) -> List[dict]:
        cur = conn_art.cursor()
        cur.execute(
            "SELECT * FROM artefatti WHERE slot=? AND assegna_a_id IS NULL ORDER BY id DESC",
            (slot,),
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    @staticmethod
    def equip_map_for_personaggio(conn_art, personaggio_id: int) -> Dict[str, int]:
        cur = conn_art.cursor()
        cur.execute(
            "SELECT slot, id FROM artefatti WHERE assegna_a_id=?",
            (personaggio_id,),
        )
        return {r[0]: r[1] for r in cur.fetchall()}

    @staticmethod
    def set_equipaggiamento(
        conn_art, personaggio_id: int, slot: str, artefatto_id: Optional[int]
    ) -> None:
        cur = conn_art.cursor()
        if artefatto_id:
            cur.execute("SELECT slot FROM artefatti WHERE id=?", (artefatto_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("Artefatto non trovato")
            if row[0] != slot:
                raise ValueError("Lo slot dell'artefatto non corrisponde alla posizione")
            cur.execute("UPDATE artefatti SET assegna_a_id=NULL WHERE id=?", (artefatto_id,))
            cur.execute(
                "UPDATE artefatti SET assegna_a_id=NULL WHERE assegna_a_id=? AND slot=?",
                (personaggio_id, slot),
            )
            cur.execute(
                "UPDATE artefatti SET assegna_a_id=? WHERE id=?",
                (personaggio_id, artefatto_id),
            )
        else:
            cur.execute(
                "UPDATE artefatti SET assegna_a_id=NULL WHERE assegna_a_id=? AND slot=?",
                (personaggio_id, slot),
            )
        conn_art.commit()

    @staticmethod
    def unassign_artefatto(conn_art, artefatto_id: int) -> None:
        cur = conn_art.cursor()
        cur.execute("UPDATE artefatti SET assegna_a_id=NULL WHERE id=?", (artefatto_id,))
        conn_art.commit()

    @staticmethod
    def unassign_all_for_personaggio(conn_art, personaggio_id: int) -> None:
        cur = conn_art.cursor()
        cur.execute("UPDATE artefatti SET assegna_a_id=NULL WHERE assegna_a_id=?", (personaggio_id,))
        conn_art.commit()

    @staticmethod
    def update(conn_art, artefatto_id: int, dati: tuple) -> None:
        """Aggiorna tutti i campi tranne id e assegna_a_id (stesso ordine di insert)."""
        cur = conn_art.cursor()
        cur.execute(
            """
            UPDATE artefatti SET
                slot=?, set_nome=?, nome=?, livello=?, stelle=?, main_stat=?, main_val=?,
                sub1_stat=?, sub1_val=?, sub2_stat=?, sub2_val=?,
                sub3_stat=?, sub3_val=?, sub4_stat=?, sub4_val=?
            WHERE id=?
            """,
            (*dati, artefatto_id),
        )
        if cur.rowcount == 0:
            raise ValueError("Artefatto non trovato")
        conn_art.commit()

    @staticmethod
    def delete(conn_art, artefatto_id: int) -> bool:
        cur = conn_art.cursor()
        cur.execute("DELETE FROM artefatti WHERE id=?", (artefatto_id,))
        conn_art.commit()
        return cur.rowcount > 0

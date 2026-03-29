"""Gestione connessioni database."""
from __future__ import annotations

import sqlite3
import threading
from typing import Optional

from config import DB_PATH, ARTEFATTI_DB_PATH

_tls = threading.local()
_init_lock = threading.Lock()
_schema_initialized = False


def _ensure_schema_once() -> None:
    """Esegue init/migrazioni una sola volta per processo (connessioni brevi, thread-safe)."""
    global _schema_initialized
    if _schema_initialized:
        return
    with _init_lock:
        if _schema_initialized:
            return
        c_m = sqlite3.connect(DB_PATH)
        c_a = sqlite3.connect(ARTEFATTI_DB_PATH)
        try:
            init_databases(c_m, c_a)
        finally:
            c_m.close()
            c_a.close()
        _schema_initialized = True


def _configure_live_connection(conn: sqlite3.Connection) -> None:
    """Timeout e pragmas per meno «database is locked»; check_same_thread su connect."""
    try:
        conn.execute("PRAGMA foreign_keys = ON")
    except sqlite3.Error:
        pass
    try:
        conn.execute("PRAGMA busy_timeout = 10000")
    except sqlite3.Error:
        pass


def get_connection():
    """Connessione al database principale per il thread corrente (Flask / gunicorn multi-thread)."""
    _ensure_schema_once()
    main: Optional[sqlite3.Connection] = getattr(_tls, "main", None)
    if main is None:
        # check_same_thread=False: Tkinter/timer e worker diversi possono riusare lo stesso
        # AppService senza ProgrammingError; SQLite serializza comunque le scritture.
        main = sqlite3.connect(DB_PATH, timeout=20.0, check_same_thread=False)
        _configure_live_connection(main)
        _tls.main = main
        art = sqlite3.connect(ARTEFATTI_DB_PATH, timeout=20.0, check_same_thread=False)
        _configure_live_connection(art)
        _tls.art = art
    return main


def get_artefatti_connection():
    """Connessione al database artefatti per il thread corrente (accoppiata a get_connection)."""
    get_connection()
    return _tls.art


def close_thread_connections() -> None:
    """Chiude le connessioni SQLite del thread corrente (es. uscita dalla GUI Tkinter)."""
    for attr in ("art", "main"):
        conn = getattr(_tls, attr, None)
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass
        try:
            delattr(_tls, attr)
        except AttributeError:
            pass


def init_databases(conn_main, conn_artefatti):
    """Inizializza entrambi i database con schema e migrazioni."""
    _init_main_db(conn_main)
    _init_artefatti_db(conn_artefatti)
    _migrate_artefatti_v4_reset_inventario(conn_main, conn_artefatti)
    _migrate_artefatti_v5_assegna_su_artefatto(conn_main, conn_artefatti)
    _migrate_artefatti_v6_meta_custom(conn_artefatti)
    _migrate_artefatti_v7_catalogo_estensioni(conn_artefatti)
    _pulisci_assegna_orfani_artefatti(conn_main, conn_artefatti)


def _init_main_db(conn):
    """Schema e migrazioni database principale."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS personaggi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            livello INTEGER DEFAULT 1,
            elemento TEXT DEFAULT 'Pyro',
            hp_flat INTEGER, atk_flat INTEGER, def_flat INTEGER, em_flat INTEGER,
            cr INTEGER, cd INTEGER, er INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS armi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personaggio_id INTEGER UNIQUE REFERENCES personaggi(id),
            nome TEXT NOT NULL, tipo TEXT DEFAULT 'Spada',
            livello INTEGER DEFAULT 1, stelle INTEGER DEFAULT 5,
            atk_base INTEGER, stat_secondaria TEXT, valore_stat REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS equipaggiamento (
            personaggio_id INTEGER REFERENCES personaggi(id),
            slot TEXT CHECK(slot IN ('fiore','piuma','sabbie','calice','corona')),
            artefatto_id INTEGER,
            PRIMARY KEY(personaggio_id, slot)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS costellazioni (
            personaggio_id INTEGER PRIMARY KEY REFERENCES personaggi(id),
            c1 INTEGER DEFAULT 0, c2 INTEGER DEFAULT 0, c3 INTEGER DEFAULT 0,
            c4 INTEGER DEFAULT 0, c5 INTEGER DEFAULT 0, c6 INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS talenti (
            personaggio_id INTEGER PRIMARY KEY REFERENCES personaggi(id),
            aa INTEGER DEFAULT 1, skill INTEGER DEFAULT 1, burst INTEGER DEFAULT 1
        )
    """)
    _run_migrations_main(cur)
    conn.commit()


def _run_migrations_main(cur):
    """Migrazioni per database esistenti."""
    for col in ("pas1", "pas2", "pas3", "pas4"):
        try:
            cur.execute(f"ALTER TABLE talenti ADD COLUMN {col} INTEGER")
        except sqlite3.OperationalError:
            pass
    for col in ("hp_flat", "atk_flat", "def_flat", "em_flat", "cr", "cd", "er"):
        try:
            cur.execute(f"ALTER TABLE personaggi ADD COLUMN {col} INTEGER")
        except sqlite3.OperationalError:
            pass
    try:
        cur.execute("PRAGMA table_info(armi)")
        if "personaggio_id" not in [r[1] for r in cur.fetchall()]:
            cur.execute("DROP TABLE IF EXISTS armi")
            cur.execute("""
                CREATE TABLE armi (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    personaggio_id INTEGER UNIQUE REFERENCES personaggi(id),
                    nome TEXT NOT NULL, tipo TEXT DEFAULT 'Spada',
                    livello INTEGER DEFAULT 1, stelle INTEGER DEFAULT 5,
                    atk_base INTEGER, stat_secondaria TEXT, valore_stat REAL
                )
            """)
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("PRAGMA table_info(equipaggiamento)")
        cols = [r[1] for r in cur.fetchall()]
        if cols and "slot" not in cols:
            cur.execute("DROP TABLE IF EXISTS equipaggiamento")
    except sqlite3.OperationalError:
        pass
    cur.execute("""
        CREATE TABLE IF NOT EXISTS equipaggiamento (
            personaggio_id INTEGER REFERENCES personaggi(id),
            slot TEXT CHECK(slot IN ('fiore','piuma','sabbie','calice','corona')),
            artefatto_id INTEGER,
            PRIMARY KEY(personaggio_id, slot)
        )
    """)
    _migrate_main_custom_meta_columns(cur)


def _migrate_main_custom_meta_columns(cur):
    """origine / audit per nomi personaggio e arma (Approccio A)."""
    specs = (
        (
            "personaggi",
            (
                ("origine_nome", "ALTER TABLE personaggi ADD COLUMN origine_nome TEXT DEFAULT 'ufficiale'"),
                ("data_nome_custom", "ALTER TABLE personaggi ADD COLUMN data_nome_custom TEXT"),
                ("nota_nome_custom", "ALTER TABLE personaggi ADD COLUMN nota_nome_custom TEXT"),
            ),
        ),
        (
            "armi",
            (
                ("origine_nome", "ALTER TABLE armi ADD COLUMN origine_nome TEXT DEFAULT 'ufficiale'"),
                ("data_nome_custom", "ALTER TABLE armi ADD COLUMN data_nome_custom TEXT"),
                ("nota_nome_custom", "ALTER TABLE armi ADD COLUMN nota_nome_custom TEXT"),
            ),
        ),
    )
    for table, alters in specs:
        try:
            cur.execute(f"PRAGMA table_info({table})")
            have = {r[1] for r in cur.fetchall()}
        except sqlite3.OperationalError:
            continue
        for col_name, stmt in alters:
            if col_name in have:
                continue
            try:
                cur.execute(stmt)
            except sqlite3.OperationalError:
                pass


def _init_artefatti_db(conn):
    """Schema database artefatti."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS artefatti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slot TEXT NOT NULL CHECK(slot IN ('fiore','piuma','sabbie','calice','corona')),
            set_nome TEXT, nome TEXT,
            livello INTEGER DEFAULT 20, stelle INTEGER DEFAULT 5,
            main_stat TEXT, main_val REAL,
            sub1_stat TEXT, sub1_val REAL, sub2_stat TEXT, sub2_val REAL,
            sub3_stat TEXT, sub3_val REAL, sub4_stat TEXT, sub4_val REAL
        )
    """)
    conn.commit()


def _migrate_artefatti_v4_reset_inventario(conn_main, conn_art):
    """
    Una tantum: svuota inventario artefatti e equipaggiamenti sui personaggi.
    user_version su artefatti.db = 4 dopo l'esecuzione.
    """
    cur = conn_art.cursor()
    cur.execute("PRAGMA user_version")
    uv = cur.fetchone()[0] or 0
    if uv >= 4:
        return
    cur.execute("DELETE FROM artefatti")
    conn_art.commit()
    conn_main.execute("DELETE FROM equipaggiamento")
    conn_main.commit()
    cur.execute("PRAGMA user_version = 4")
    conn_art.commit()


def _migrate_artefatti_v5_assegna_su_artefatto(conn_main, conn_art):
    """
    v5: proprietario dell'artefatto in `artefatti.assegna_a_id` (magazzino se NULL).
    Migra le righe da `equipaggiamento` poi svuota quella tabella.
    """
    cur = conn_art.cursor()
    cur.execute("PRAGMA user_version")
    uv = cur.fetchone()[0] or 0
    if uv >= 5:
        return
    try:
        cur.execute("ALTER TABLE artefatti ADD COLUMN assegna_a_id INTEGER")
    except sqlite3.OperationalError:
        pass
    cur_main = conn_main.cursor()
    cur_main.execute(
        "SELECT personaggio_id, slot, artefatto_id FROM equipaggiamento WHERE artefatto_id IS NOT NULL"
    )
    for row in cur_main.fetchall():
        pid, _slot, aid = row[0], row[1], row[2]
        cur.execute("UPDATE artefatti SET assegna_a_id=? WHERE id=?", (pid, aid))
    cur_main.execute("DELETE FROM equipaggiamento")
    conn_main.commit()
    cur.execute("PRAGMA user_version = 5")
    conn_art.commit()


def _migrate_artefatti_v6_meta_custom(conn_art):
    """Colonne audit per righe manufatto (predisposizione Approccio A/B)."""
    cur = conn_art.cursor()
    cur.execute("PRAGMA user_version")
    uv = cur.fetchone()[0] or 0
    if uv >= 6:
        return
    for stmt in (
        "ALTER TABLE artefatti ADD COLUMN origine_riga TEXT DEFAULT 'ufficiale'",
        "ALTER TABLE artefatti ADD COLUMN data_custom_riga TEXT",
        "ALTER TABLE artefatti ADD COLUMN nota_custom_riga TEXT",
    ):
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError:
            pass
    cur.execute("PRAGMA user_version = 6")
    conn_art.commit()


def _migrate_artefatti_v7_catalogo_estensioni(conn_art):
    """Set/pezzo manufatto aggiunti dall'utente (catalogo dinamico su DB artefatti)."""
    cur = conn_art.cursor()
    cur.execute("PRAGMA user_version")
    uv = cur.fetchone()[0] or 0
    if uv >= 7:
        return
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS catalogo_manufatti_estensioni (
            set_nome TEXT NOT NULL,
            slot TEXT NOT NULL CHECK(slot IN ('fiore','piuma','sabbie','calice','corona')),
            nome_pezzo TEXT NOT NULL,
            set_key TEXT NOT NULL,
            pezzo_key TEXT NOT NULL,
            UNIQUE(set_key, slot, pezzo_key)
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_cat_manuf_ext_set_slot ON catalogo_manufatti_estensioni(set_key, slot)"
    )
    cur.execute("PRAGMA user_version = 7")
    conn_art.commit()


def _pulisci_assegna_orfani_artefatti(conn_main, conn_art):
    """Rimuove assegna_a_id se il personaggio non esiste più (DB principale)."""
    cur_m = conn_main.cursor()
    cur_m.execute("SELECT id FROM personaggi")
    valid = {r[0] for r in cur_m.fetchall()}
    cur = conn_art.cursor()
    cur.execute("SELECT id, assegna_a_id FROM artefatti WHERE assegna_a_id IS NOT NULL")
    for row in cur.fetchall():
        aid, pid = row[0], row[1]
        if pid not in valid:
            cur.execute("UPDATE artefatti SET assegna_a_id=NULL WHERE id=?", (aid,))
    conn_art.commit()

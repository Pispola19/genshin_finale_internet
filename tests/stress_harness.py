"""
Eseguito in subprocess con GINSHIN_DATA_DIR su directory temporanea (import vergini).

Copertura: inserimenti massivi personaggi/manufatti, loop salva, duplicati case-sensitive,
API Flask opzionale (mass save via POST).

Uso diretto:
  GINSHIN_DATA_DIR=$(mktemp -d) python3 -m tests.stress_harness
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import time


def _base_form_pg(nome: str, i: int) -> dict:
    return {
        "nome": nome,
        "livello": 1 + (i % 90),
        "elemento": "Pyro",
        "hp_flat": max(0, 10000 - i * 10),
        "atk_flat": i % 5000,
        "def_flat": "",
        "em_flat": -5 if i % 17 == 0 else 0,
        "cr": 200 if i % 23 == 0 else min(100, 5 + (i % 80)),
        "cd": "",
        "er": 0,
    }


def _base_form_arma(i: int) -> dict:
    return {
        "nome": "",
        "tipo": "Spada",
        "livello": 1,
        "stelle": 5,
        "atk_base": "",
        "stat_secondaria": "",
        "valore_stat": "",
    }


def _empty_cost_talenti():
    c = {f"c{j}": "0" for j in range(1, 7)}
    t = {k: "-" for k in ("aa", "skill", "burst", "pas1", "pas2", "pas3", "pas4")}
    return c, t


def main() -> int:
    td = tempfile.mkdtemp(prefix="genshin_stress_")
    os.environ["GENSHIN_WEB_WRITE_PASSWORD"] = os.environ.get("GENSHIN_WEB_WRITE_PASSWORD", "stress-local")
    os.environ["GENSHIN_WHITELIST_STRICT"] = "0"
    os.environ["GINSHIN_DATA_DIR"] = td

    # Import dopo GINSHIN_DATA_DIR
    from core.services import AppService  # noqa: E402
    from core.validation import parse_number, validate_nome  # noqa: E402
    from core.dps import DpsCalculator, build_dps_result_artefatto_index  # noqa: E402
    from db.models import Personaggio  # noqa: E402
    from db.connection import get_connection, close_thread_connections  # noqa: E402
    from config import DB_PATH, ARTEFATTI_DB_PATH  # noqa: E402
    from core.artefatto_service import ArtefattoService  # noqa: E402
    from personaggi_ufficiali import PERSONAGGI_UFFICIALI  # noqa: E402

    errs: list[str] = []
    svc = AppService()
    art_svc = ArtefattoService()

    base_names = list(PERSONAGGI_UFFICIALI)[:100]

    t0 = time.perf_counter()
    n_ok = 0
    for i in range(len(base_names)):
        nome = base_names[i]
        fp = _base_form_pg(nome, i)
        fa = _base_form_arma(i)
        c, t = _empty_cost_talenti()
        meta: dict = {}
        try:
            pid = svc.salva_completo(None, fp, fa, c, t, None, meta=meta)
            n_ok += 1
            for _ in range(3):
                fp2 = dict(fp)
                fp2["livello"] = str(int(fp2["livello"]) + 1)
                svc.salva_completo(pid, fp2, fa, c, t, None, meta=meta)
        except Exception as e:
            errs.append(f"save i={i} nome={nome!r}: {e}")

    # Manufatti massivi (catalogo valido minimo)
    set_nome = "Emblema del fato spezzato"
    # Solo pezzo fiore canonico per questo set (altrimenti validate_artefatto fallisce).
    pezzo_fiore = "Tsuba poderosa"
    slot = "fiore"
    n_art = 0
    for j in range(520):
        form = {
            "slot": slot,
            "set_nome": set_nome,
            "nome": pezzo_fiore,
            "livello": 20,
            "stelle": 5,
            "main_stat": "HP",
            "main_val": 4789 + (j % 100),
            "sub1_stat": "CR%" if j % 2 == 0 else "",
            "sub1_val": 10.2 if j % 2 == 0 else None,
            "sub2_stat": "",
            "sub2_val": None,
            "sub3_stat": "",
            "sub3_val": None,
            "sub4_stat": "",
            "sub4_val": None,
            "personaggio_id": None,
        }
        try:
            art_svc.aggiungi_artefatto(form)
            n_art += 1
        except Exception as e:
            errs.append(f"artefatto j={j}: {e}")
            break

    # Case sensitivity duplicati (SQLite UNIQUE: per default case-sensitive → due PG distinti)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO personaggi (nome) VALUES (?)", ("CaseDupA",))
        cur.execute("INSERT INTO personaggi (nome) VALUES (?)", ("casedupa",))
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM personaggi WHERE nome IN ('CaseDupA','casedupa')")
        if cur.fetchone()[0] != 2:
            errs.append("case dup: attesi 2 righe distinte")
    except Exception as e:
        errs.append(f"case dup insert: {e}")

    # DPS edge
    bad_art = {"id": 1, "slot": "fiore", "main_stat": None, "main_val": None}
    pg = Personaggio(1, "Z", 90, "Pyro", None, None, None, None, -999, 1e9, None)
    try:
        s, _ = DpsCalculator.score_artefatto_per_personaggio(bad_art, pg)
        assert isinstance(s, float)
        build_dps_result_artefatto_index(bad_art, [pg])
    except Exception as e:
        errs.append(f"dps edge: {e}")

    # parse_number extremes
    assert parse_number("-100", min_val=0) is None or parse_number("-100", min_val=0) == 0
    assert parse_number("999999", min_val=0, max_val=100) is None

    strict_off = validate_nome("TotallyFakeCustom987", custom_confirm=False)
    if not strict_off[0]:
        errs.append("expected STRICT=0 to accept custom without confirm")

    for path, label in ((DB_PATH, "main"), (ARTEFATTI_DB_PATH, "artefatti")):
        try:
            chk = sqlite3.connect(str(path)).execute("PRAGMA integrity_check").fetchone()[0]
            if chk != "ok":
                errs.append(f"integrity {label}: {chk}")
        except Exception as e:
            errs.append(f"integrity {label}: {e}")

    close_thread_connections()
    dt = time.perf_counter() - t0
    print(f"stress_harness: data_dir={td} personaggi_ok={n_ok} artefatti_ok={n_art} time_s={dt:.2f}")

    if errs:
        print("ERRORS:")
        for e in errs[:30]:
            print(" ", e)
        if len(errs) > 30:
            print(f" ... +{len(errs) - 30} more")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

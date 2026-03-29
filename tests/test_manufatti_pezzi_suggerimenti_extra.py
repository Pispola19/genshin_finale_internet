"""Catalogo pezzi: varianti extra + merge + canonical verso nome IT ufficiale."""
from __future__ import annotations

import sqlite3

from core.manufatto_catalog_resolve import (
    canonical_pezzo_name,
    merged_pezzi_per_set_slot,
    resolve_manufatto_set_pezzo_for_save,
)
from core.manufatti_pezzi_en_by_fingerprint import ENGLISH_PEZZI_BY_IT_FINGERPRINT
from core.manufatti_pezzi_suggerimenti_extra import (
    etichette_suggerimento_extra,
    resolve_pezzo_alias_to_canonical,
)
from core.manufatti_ufficiali import CATALOGO_ARTEFATTI
from core.nome_normalization import norm_key_nome


def _art_conn() -> sqlite3.Connection:
    cx = sqlite3.connect(":memory:")
    cx.execute(
        """
        CREATE TABLE catalogo_manufatti_estensioni (
            set_nome TEXT NOT NULL,
            slot TEXT NOT NULL,
            nome_pezzo TEXT NOT NULL,
            set_key TEXT NOT NULL,
            pezzo_key TEXT NOT NULL,
            UNIQUE(set_key, slot, pezzo_key)
        )
        """
    )
    cx.commit()
    return cx


def test_resolve_alias_en_to_it_canonical():
    assert resolve_pezzo_alias_to_canonical(
        "Emblema del fato spezzato", "sabbie", "Storm Cage"
    ) == "Inro della tempesta"
    assert resolve_pezzo_alias_to_canonical(
        "Emblema del fato spezzato", "sabbie", "inro della tempesta"
    ) == "Inro della tempesta"


def test_etichette_extra_non_duplicano_canonico():
    ex = etichette_suggerimento_extra("Emblema del fato spezzato", "sabbie")
    assert "Storm Cage" in ex
    assert "Inro della tempesta" not in ex


def test_merged_pezzi_ui_solo_italiano_senza_varianti_en():
    conn = _art_conn()
    try:
        names = merged_pezzi_per_set_slot(conn, "Emblema del fato spezzato", "sabbie")
        assert "Inro della tempesta" in names
        assert "Storm Cage" not in names
    finally:
        conn.close()


def test_canonical_pezzo_prefers_italian_for_en_input():
    conn = _art_conn()
    try:
        assert (
            canonical_pezzo_name(conn, "Emblema del fato spezzato", "sabbie", "Storm Cage")
            == "Inro della tempesta"
        )
    finally:
        conn.close()


def test_all_catalog_fingerprints_have_en_quintuple():
    seen: set[tuple[str, str, str, str, str]] = set()
    for _sn, pz in CATALOGO_ARTEFATTI:
        seen.add(tuple(norm_key_nome(p) for p in pz))
    for fp in seen:
        assert fp in ENGLISH_PEZZI_BY_IT_FINGERPRINT


def test_resolve_save_does_not_treat_en_alias_as_custom_extension():
    conn = _art_conn()
    try:
        set_c, pezzo_c = resolve_manufatto_set_pezzo_for_save(
            conn,
            "Emblema del fato spezzato",
            "Scarlet Vulture",
            "calice",
            register_extension=True,
        )
        assert set_c == "Emblema del fato spezzato"
        assert pezzo_c == "Calice scarlatto"
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM catalogo_manufatti_estensioni")
        assert cur.fetchone()[0] == 0
    finally:
        conn.close()

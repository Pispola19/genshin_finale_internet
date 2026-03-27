"""Whitelist nomi personaggio, arma, manufatti."""
from __future__ import annotations

import unittest

from core.nome_normalization import canonicalizza_nome_personaggio, norm_key_nome
from core.validation import (
    validate_arma_nome,
    validate_artefatto_set_e_pezzo,
    validate_nome,
)


class NomiWhitelistTest(unittest.TestCase):
    def test_personaggio_fuori_lista_rifiutato(self) -> None:
        ok, msg = validate_nome("Personaggio Inventato")
        self.assertFalse(ok)
        self.assertIn("elenco", msg.lower())

    def test_personaggio_custom_con_conferma_ok(self) -> None:
        ok, msg = validate_nome("Nome Custom Verificabile", custom_confirm=True)
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_personaggio_in_lista_accettato(self) -> None:
        ok, msg = validate_nome("Hu Tao")
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_personaggio_spazi_e_case_whitelist(self) -> None:
        ok, msg = validate_nome("  hu tao  ")
        self.assertTrue(ok, msg)
        self.assertEqual(canonicalizza_nome_personaggio("  hu tao  "), "Hu Tao")

    def test_norm_key_duplicati_logici_stesso(self) -> None:
        self.assertEqual(norm_key_nome("Keqing"), norm_key_nome("  keqing  "))
        self.assertEqual(norm_key_nome("Hu  Tao"), norm_key_nome("hu tao"))

    def test_arma_vuota_ok(self) -> None:
        self.assertEqual(validate_arma_nome(""), (True, ""))
        self.assertEqual(validate_arma_nome("  "), (True, ""))

    def test_arma_non_in_lista_rifiutata(self) -> None:
        ok, msg = validate_arma_nome("Spada Finta")
        self.assertFalse(ok)
        self.assertIn("ufficiale", msg.lower())

    def test_arma_in_lista_accettata(self) -> None:
        ok, msg = validate_arma_nome("Lama celeste")
        self.assertTrue(ok)

    def test_manufatto_set_pezzo_coerenti(self) -> None:
        ok, msg = validate_artefatto_set_e_pezzo(
            "Emblema del fato spezzato",
            "Tsuba poderosa",
            "fiore",
        )
        self.assertTrue(ok)
        self.assertEqual(msg, "")

    def test_manufatto_pezzo_sbagliato_per_slot(self) -> None:
        ok, msg = validate_artefatto_set_e_pezzo(
            "Emblema del fato spezzato",
            "Tsuba poderosa",
            "piuma",
        )
        self.assertFalse(ok)

    def test_manufatto_set_inventato(self) -> None:
        ok, msg = validate_artefatto_set_e_pezzo("Set che non esiste", "Pezzo", "fiore")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()

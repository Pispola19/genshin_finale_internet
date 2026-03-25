"""Regression / stress tests per import manuale JSON."""
from __future__ import annotations

import json
import unittest

from core.manual_import import ImportParseError, build_forms_for_salva_completo, parse_pasted_payload


class ManualImportStressTest(unittest.TestCase):
    def test_bom_prefix(self):
        raw = "\ufeff" + json.dumps({"character": {"nome": "A", "livello": 1}})
        p = parse_pasted_payload(raw)
        self.assertEqual(p["character"]["nome"], "A")

    def test_nested_duplicate_name_prefers_richer_fight_map(self):
        payload = {
            "name": "Dup",
            "level": 90,
            "fightPropMap": {"1": 1},
            "inner": {
                "name": "Dup",
                "level": 90,
                "fightPropMap": {"1": 99999, "2": 500},
            },
        }
        p = parse_pasted_payload(json.dumps(payload))
        self.assertEqual(p["character"]["hp_flat"], 99999)
        self.assertEqual(p["character"]["atk_flat"], 500)

    def test_empty_top_level_character_falls_back(self):
        raw = json.dumps(
            {
                "character": {},
                "data": {"name": "Real", "level": 90, "fightPropMap": {"1": 100}},
            }
        )
        p = parse_pasted_payload(raw)
        self.assertEqual(p["character"]["nome"], "Real")
        self.assertEqual(p["character"]["hp_flat"], 100)

    def test_array_skips_entries_without_name(self):
        raw = json.dumps(
            [
                {"name": None, "level": 1},
                {"name": "Good", "level": 90, "fightPropMap": {"1": 5}},
            ]
        )
        p = parse_pasted_payload(raw)
        self.assertEqual(p["character"]["nome"], "Good")
        self.assertEqual(p["character"]["hp_flat"], 5)

    def test_character_must_be_object(self):
        with self.assertRaises(ImportParseError) as ctx:
            parse_pasted_payload('{"character": "oops"}')
        self.assertIn("character", str(ctx.exception).lower())

    def test_build_forms_defaults(self):
        p = parse_pasted_payload(
            json.dumps(
                {
                    "character": {
                        "nome": "X",
                        "livello": 90,
                        "elemento": "Electro",
                        "hp_flat": 1,
                        "atk_flat": 2,
                        "def_flat": 3,
                        "elemental_mastery": 40,
                        "crit_rate": 60,
                        "crit_dmg": 120,
                        "energy_recharge": 130,
                    }
                }
            )
        )
        fp, fa, fc, ft = build_forms_for_salva_completo(p)
        self.assertEqual(fp["em_flat"], 40)
        self.assertEqual(fc["c1"], "0")
        self.assertEqual(ft["aa"], "-")


if __name__ == "__main__":
    unittest.main()

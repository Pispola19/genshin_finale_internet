"""Regression / stress tests per import manuale JSON."""
from __future__ import annotations

import json
import unittest

from core.manual_import import (
    ImportParseError,
    build_forms_for_salva_completo,
    parse_pasted_payload,
    preview_summary,
)


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

    def test_garbage_before_after_json(self):
        inner = {"name": "Yelan", "level": 90, "fightPropMap": {"1": 15000, "2": 2000}}
        raw = "=== log ===\n" + json.dumps(inner) + "\n--- fine ---"
        p = parse_pasted_payload(raw)
        self.assertEqual(p["character"]["nome"], "Yelan")
        self.assertEqual(p["character"]["hp_flat"], 15000)

    def test_trailing_commas(self):
        raw = '{"name":"Sayu","level":70,"fightPropMap":{"1":100,},}'
        p = parse_pasted_payload(raw)
        self.assertEqual(p["character"]["nome"], "Sayu")
        self.assertEqual(p["character"]["hp_flat"], 100)

    def test_markdown_fence(self):
        inner = {"name": "Zhongli", "expLevel": 80}
        raw = "Ecco i dati:\n```json\n" + json.dumps(inner) + "\n```\ngrazie"
        p = parse_pasted_payload(raw)
        self.assertEqual(p["character"]["nome"], "Zhongli")
        self.assertEqual(p["character"]["livello"], 80)

    def test_xssi_prefix(self):
        inner = {"name": "Klee", "level": 50}
        raw = ")]}'\n" + json.dumps(inner)
        p = parse_pasted_payload(raw)
        self.assertEqual(p["character"]["nome"], "Klee")

    def test_typographic_quotes(self):
        # U+201C / U+201D attorno alla chiave name (dopo normalizzazione deve parsare)
        raw = "{\u201cname\u201d: \u201cFischl\u201d, \u201clevel\u201d: 60}"
        p = parse_pasted_payload(raw)
        self.assertEqual(p["character"]["nome"], "Fischl")

    def test_name_only_minimal(self):
        raw = json.dumps({"name": "Collei"})
        p = parse_pasted_payload(raw)
        self.assertEqual(p["character"]["nome"], "Collei")
        self.assertEqual(p["character"]["livello"], 1)

    def test_fight_prop_comma_thousands(self):
        raw = json.dumps({"name": "X", "level": 90, "fightPropMap": {"1": "18,500", "2": "1.250,5"}})
        p = parse_pasted_payload(raw)
        self.assertEqual(p["character"]["hp_flat"], 18500)
        self.assertEqual(p["character"]["atk_flat"], 1250)

    def test_double_json_string(self):
        inner = json.dumps({"name": "Yae", "fightPropMap": {"1": 100}})
        outer = json.dumps(inner)
        p = parse_pasted_payload(outer)
        self.assertEqual(p["character"]["nome"], "Yae")
        self.assertEqual(p["character"]["hp_flat"], 100)

    def test_hoyolab_envelope_bulk_avatars(self):
        payload = {
            "retcode": 0,
            "message": "OK",
            "data": {
                "avatars": [
                    {
                        "name": "Varka",
                        "element": "Anemo",
                        "level": 90,
                        "actived_constellation_num": 0,
                        "weapon": {
                            "name": "Orgoglio celeste",
                            "type": 11,
                            "level": 90,
                            "rarity": 5,
                        },
                        "relics": [
                            {
                                "pos": 1,
                                "name": "Fiore X",
                                "level": 20,
                                "rarity": 5,
                                "set": {"name": "Set prova"},
                                "pos_name": "Fiore della vita",
                            }
                        ],
                    },
                    {
                        "name": "#Viaggiat{M#ore}{F#rice}",
                        "element": "Electro",
                        "level": 90,
                        "actived_constellation_num": 6,
                        "weapon": {"name": "Spada", "type": 1, "level": 90, "rarity": 4},
                        "relics": [],
                    },
                ]
            },
        }
        p = parse_pasted_payload(json.dumps(payload))
        self.assertTrue(p.get("bulk"))
        self.assertEqual(len(p["imports"]), 2)
        self.assertEqual(p["imports"][0]["weapon"]["tipo"], "Claymore")
        self.assertEqual(p["imports"][0]["weapon"]["stelle"], 5)
        self.assertEqual(len(p["imports"][0]["relics_raw"]), 1)
        self.assertEqual(p["imports"][1]["character"]["nome"], "Traveler")
        self.assertEqual(p["imports"][1]["costellazioni_form"]["c6"], "1")
        s = preview_summary(p)
        self.assertIn("2 personaggi", s)
        _, _, fc, _ = build_forms_for_salva_completo(p["imports"][1])
        self.assertEqual(fc["c1"], "1")
        self.assertEqual(fc["c6"], "1")

    def test_retcode_error(self):
        with self.assertRaises(ImportParseError) as ctx:
            parse_pasted_payload(json.dumps({"retcode": -1, "data": {}}))
        self.assertIn("retcode", str(ctx.exception).lower())

    def test_hoyolab_strict_validate_missing_name(self):
        from core.hoyolab_import import validate_hoyolab_bulk_envelope

        with self.assertRaises(ImportParseError) as ctx:
            validate_hoyolab_bulk_envelope(
                {"retcode": 0, "data": {"avatars": [{"level": 90}]}}
            )
        self.assertIn("name", str(ctx.exception).lower())

    def test_hoyolab_strict_validate_missing_data(self):
        from core.hoyolab_import import validate_hoyolab_bulk_envelope

        with self.assertRaises(ImportParseError) as ctx:
            validate_hoyolab_bulk_envelope({"retcode": 0})
        self.assertIn("data", str(ctx.exception).lower())

    def test_import_mode_update_calls_service(self):
        from unittest.mock import MagicMock

        from core.manual_import import apply_manual_import

        svc = MagicMock()
        svc.salva_completo.return_value = 7
        p = {
            "character": {"nome": "X", "livello": 90, "elemento": "Pyro"},
            "weapon": None,
            "costellazioni_form": None,
            "relics_raw": [{"pos": 1, "name": "a", "set": {"name": "S"}, "level": 20, "rarity": 5}],
        }
        apply_manual_import(svc, p, None, touch_equipment=True, import_mode="update")
        svc.apply_hoyo_relic_import.assert_called_once()
        args = svc.apply_hoyo_relic_import.call_args[0]
        self.assertEqual(args[0], 7)
        self.assertEqual(args[2], "update")


if __name__ == "__main__":
    unittest.main()

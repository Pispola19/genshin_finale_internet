"""
Stress / coerenza: core (DPS, build, tipi, somma stat manufatti).
"""
from __future__ import annotations

import random
import unittest

from config import SLOT_DB
from core.build_service import _riepilogo_build_slots, _somma_stats
from core.dps import DpsCalculator, build_dps_result_artefatto_index
from core.dps_types import (
    CombatStats,
    DpsResult,
    build_full_combat_view,
    combat_stats_from_artefatto_dict,
    compute_build_damage_proxy,
    dps_result_to_message_it,
    merge_combat_stats,
)
from core.set_bonus_proxy import set_bonus_proxy_multiplier, conteggio_set_da_artefatti
from db.models import Arma, Personaggio


def _random_artefatto(art_id: int) -> dict:
    stats_pool = ["ATK", "ATK%", "CR", "CD", "ER", "EM", "HP", "DEF", "Pyro DMG", ""]
    a: dict = {
        "id": art_id,
        "slot": random.choice(list(SLOT_DB)),
        "set_nome": random.choice(["", "Test Set", "Emblema del fato spezzato"]),
        "nome": "Pezzo test",
        "main_stat": random.choice(stats_pool[:-1]),
        "main_val": random.choice([0, 3.5, 15.6, 31.1, 46.6, 999, None, ""]),
    }
    for i in range(1, 5):
        a[f"sub{i}_stat"] = random.choice(stats_pool)
        a[f"sub{i}_val"] = random.choice([0, 5.8, 19, 23.3, None, "bad", ""])
    return a


class CoreDpsBuildStressTest(unittest.TestCase):
    def test_combat_stats_roundtrip_dict(self) -> None:
        c = CombatStats(
            atk_flat=100,
            atk_percent=0.2,
            crit_rate=0.35,
            crit_damage=0.66,
            source_note="test",
        )
        c2 = CombatStats.from_dict(c.to_dict())
        assert c2 is not None
        self.assertEqual(c2.atk_flat, 100)
        self.assertAlmostEqual(c2.crit_rate, 0.35)
        txt = c2.format_summary_it()
        self.assertIn("ATK", txt)
        self.assertIn("Bonus danno crit", txt)

    def test_dps_result_roundtrip(self) -> None:
        r = DpsResult(
            mode="artifact_index",
            unit="index",
            value_display=42.5,
            display_label_it="Etichetta",
            ranking=[{"nome": "A", "score": 10}],
        )
        r2 = DpsResult.from_dict(r.to_dict())
        self.assertEqual(r2.value_display, 42.5)
        self.assertEqual(len(r2.ranking), 1)

    def test_atk_percent_not_counted_as_flat_in_somma_stats(self) -> None:
        arts = [
            {
                "main_stat": "ATK%",
                "main_val": 46.6,
                "sub1_stat": "ATK",
                "sub1_val": 19,
            }
        ]
        s = _somma_stats(arts)
        self.assertEqual(s["atk"], 19.0)
        self.assertNotEqual(s["atk"], 19.0 + 46.6)

    def test_somma_stats_many_random_no_crash(self) -> None:
        rng = random.Random(42)
        for _ in range(300):
            n = rng.randint(1, 5)
            batch = [_random_artefatto(1000 + i) for i in range(n)]
            s = _somma_stats(batch)
            for k in ("atk", "cr", "cd", "er", "em"):
                self.assertIsInstance(s[k], (int, float))
                self.assertFalse(__import__("math").isnan(s[k]))

    def test_riepilogo_all_slots_and_bonus_lines(self) -> None:
        slot_to_art = {}
        for i, sl in enumerate(SLOT_DB):
            slot_to_art[sl] = {
                "set_nome": "Sameset",
                "nome": f"P{i}",
                "main_stat": "ATK",
                "main_val": 10 + i,
            }
        r = _riepilogo_build_slots(slot_to_art)
        self.assertEqual(len(r["slots"]), len(SLOT_DB))
        self.assertEqual(r["conteggio_set"].get("Sameset"), len(SLOT_DB))
        self.assertTrue(any("4" in line or "pezzi" in line for line in r["bonus_set"]))

    def test_dps_calculator_score_monotone_subs(self) -> None:
        base = {"id": 1, "main_stat": "ATK", "main_val": 10}
        for i in range(1, 5):
            base[f"sub{i}_stat"] = ""
            base[f"sub{i}_val"] = None
        s0 = DpsCalculator.score_artefatto(base)
        base["sub1_stat"] = "CR"
        base["sub1_val"] = 10
        s1 = DpsCalculator.score_artefatto(base)
        self.assertGreater(s1, s0)

    def test_build_dps_result_artefatto_index_pyro_match(self) -> None:
        art = {
            "id": 7,
            "main_stat": "Pyro DMG",
            "main_val": 46.6,
            "sub1_stat": "CR",
            "sub1_val": 10,
        }
        pg_pyro = Personaggio(1, "X", 90, "Pyro", None, None, None, None, None, None, None)
        pg_hydro = Personaggio(2, "Y", 90, "Hydro", None, None, None, None, None, None, None)
        res = build_dps_result_artefatto_index(art, [pg_pyro, pg_hydro])
        self.assertEqual(res.artifact_id, 7)
        self.assertIn("non DPS", res.display_label_it)
        pyro_row = next(x for x in res.ranking if x["nome"] == "X")
        hydro_row = next(x for x in res.ranking if x["nome"] == "Y")
        self.assertGreater(pyro_row["score"], 0)
        self.assertGreater(pyro_row["score"], hydro_row["score"])
        msg = dps_result_to_message_it(res, max_ranking=5)
        self.assertIn("X", msg)

    def test_combat_stats_from_artefatto_matches_somma_single_piece(self) -> None:
        art = _random_artefatto(55)
        for i in range(1, 5):
            art[f"sub{i}_stat"] = ""
            art[f"sub{i}_val"] = None
        art["main_stat"] = "CR"
        art["main_val"] = 20
        art["sub1_stat"] = "ATK%"
        art["sub1_val"] = 10
        art["sub2_stat"] = "ATK"
        art["sub2_val"] = 50
        cs = combat_stats_from_artefatto_dict(art)
        s = _somma_stats([art])
        self.assertAlmostEqual(cs.crit_rate, s["cr"] / 100.0)
        self.assertAlmostEqual(cs.atk_flat, s["atk"])
        self.assertAlmostEqual(cs.atk_percent, 0.1)
        # _somma_stats non espone ancora ATK% (solo flat); il pezzo ha 10% → 0.1 in CombatStats

    def test_merge_combat_and_proxy_positive(self) -> None:
        a = CombatStats(atk_flat=1000, crit_rate=0.5, crit_damage=1.0, source_note="A")
        b = CombatStats(atk_percent=0.2, em=100, source_note="B")
        m = merge_combat_stats(a, b)
        self.assertEqual(m.atk_flat, 1000)
        self.assertEqual(m.atk_percent, 0.2)
        proxy, note = compute_build_damage_proxy(m)
        self.assertGreater(proxy, 0)
        self.assertIn("Proxy", note)

    def test_build_full_combat_view_layers(self) -> None:
        pg = Personaggio(1, "Z", 90, "Pyro", 10000, 800, 500, 120, 50, 100, 130)
        arma = Arma(1, 1, "Prova", "Spada", 90, 5, 500, "ATK%", 27.6)
        arts = [
            {
                "id": 1,
                "set_nome": "Emblema del fato spezzato",
                "main_stat": "ATK",
                "main_val": 50,
                "sub1_stat": "CR",
                "sub1_val": 10,
                "sub2_stat": "",
                "sub2_val": None,
                "sub3_stat": "",
                "sub3_val": None,
                "sub4_stat": "",
                "sub4_val": None,
            },
            {
                "id": 2,
                "set_nome": "Emblema del fato spezzato",
                "main_stat": "HP",
                "main_val": 100,
                "sub1_stat": "",
                "sub1_val": None,
                "sub2_stat": "",
                "sub2_val": None,
                "sub3_stat": "",
                "sub3_val": None,
                "sub4_stat": "",
                "sub4_val": None,
            },
        ]
        v = build_full_combat_view(pg, arma, arts)
        self.assertGreater(v.damage_proxy, 0)
        self.assertGreater(v.set_bonus_multiplier, 1.0)
        self.assertTrue(any("2p" in x for x in v.set_bonus_lines))
        d = v.to_dict()
        self.assertIn("personaggio", d)
        self.assertIn("arma", d)
        self.assertIn("artefatti", d)
        self.assertIn("totale", d)
        self.assertIn("set_bonus_multiplier", d)

    def test_set_bonus_proxy_4p_large_multiplier(self) -> None:
        counts = conteggio_set_da_artefatti(
            [
                {"set_nome": "TestSet", "main_stat": "ATK", "main_val": 1},
                {"set_nome": "TestSet"},
                {"set_nome": "TestSet"},
                {"set_nome": "TestSet"},
            ]
        )
        self.assertEqual(counts["TestSet"], 4)
        m, lines = set_bonus_proxy_multiplier(counts)
        self.assertGreaterEqual(m, 1.5)
        self.assertTrue(any("4p" in line for line in lines))


if __name__ == "__main__":
    unittest.main()

"""Test stima rotazione v0.1 (proxy × talenti / pesi)."""
import unittest

from core.dps_types import CombatStats, FullCombatBuild
from core.rotation_dps import ROTATION_MODEL_VERSION, compute_rotation_estimate, rotation_dps_placeholder


def _dummy_full(proxy: float = 100.0, er_percent: float = 0.22) -> FullCombatBuild:
    empty = CombatStats(source_note="")
    tot = CombatStats(er_percent=er_percent, source_note="Totale test")
    return FullCombatBuild(
        personaggio=empty,
        arma=empty,
        artefatti=empty,
        totale=tot,
        damage_proxy=proxy,
        damage_proxy_note_it="Nota proxy test.",
    )


class TestRotationDps(unittest.TestCase):
    def test_placeholder_unchanged_contract(self):
        p = rotation_dps_placeholder()
        self.assertFalse(p["ok"])
        self.assertIn("model_version", p)

    def test_compute_rotation_increases_with_talents(self):
        low = compute_rotation_estimate(_dummy_full(), 1, 1, 1, personaggio_nome="X")
        high = compute_rotation_estimate(_dummy_full(), 10, 10, 10, personaggio_nome="X")
        self.assertTrue(low["ok"] and high["ok"])
        self.assertGreater(high["rotation_index"], low["rotation_index"])
        self.assertEqual(low["model_version"], ROTATION_MODEL_VERSION)

    def test_burst_focus_preset_changes_multiplier(self):
        base = compute_rotation_estimate(
            _dummy_full(100.0, 0.35), 6, 6, 10, preset="equilibrato", personaggio_nome="Y"
        )
        burst = compute_rotation_estimate(
            _dummy_full(100.0, 0.35), 6, 6, 10, preset="burst_focus", personaggio_nome="Y"
        )
        self.assertGreater(burst["rotation_index"], base["rotation_index"])

    def test_combat_summary_attached(self):
        r = compute_rotation_estimate(_dummy_full(), None, 5, 5, personaggio_nome="Z")
        self.assertIn("combat_totale_summary_it", r)
        self.assertIn("Ricarica%", r["combat_totale_summary_it"])


if __name__ == "__main__":
    unittest.main()

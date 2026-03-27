"""
Stress / robustezza: harness isolato in subprocess + controlli DPS senza DB globale.
"""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from core.dps import DpsCalculator, build_dps_result_artefatto_index
from core.dps_types import CombatStats, combat_stats_from_artefatto_dict
from db.models import Personaggio


class StressHarnessSubprocessTest(unittest.TestCase):
    def test_stress_harness_exits_zero(self) -> None:
        root = Path(__file__).resolve().parent.parent
        env = os.environ.copy()
        env.setdefault("GENSHIN_WHITELIST_STRICT", "0")
        r = subprocess.run(
            [sys.executable, "-m", "tests.stress_harness"],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(
            r.returncode,
            0,
            msg=(r.stdout or "") + "\n" + (r.stderr or ""),
        )


class DpsRobustnessTest(unittest.TestCase):
    def test_score_with_missing_stats_no_crash(self) -> None:
        art: dict = {"id": 1, "slot": "fiore", "main_stat": None, "main_val": None}
        s = DpsCalculator.score_artefatto(art)
        self.assertIsInstance(s, float)
        self.assertGreaterEqual(s, 0.0)

    def test_score_per_pg_extreme_sheet_stats(self) -> None:
        art = {"id": 1, "slot": "calice", "main_stat": "Pyro DMG", "main_val": 46.6}
        pg = Personaggio(1, "X", 90, "Pyro", 0, 0, 0, 0, 9999, 9999, 9999)
        raw, fatt = DpsCalculator.score_artefatto_per_personaggio(art, pg)
        self.assertIsInstance(raw, float)
        self.assertIn("crit_adjust", fatt)

    def test_build_dps_result_empty_personaggi(self) -> None:
        res = build_dps_result_artefatto_index({"id": 1, "main_stat": "ATK", "main_val": 100}, [])
        self.assertTrue(any("Nessun personaggio" in w for w in (res.warnings or [])))

    def test_combat_stats_from_empty_dict(self) -> None:
        st = combat_stats_from_artefatto_dict({})
        self.assertIsInstance(st, CombatStats)


class NormalizationEdgeTest(unittest.TestCase):
    def test_sqlite_unique_case_due_righe_raw_sql(self) -> None:
        """Vincolo UNIQUE SQLite su TEXT è case-sensitive: INSERT diretti possono creare Keqing e keqing."""
        import sqlite3

        with sqlite3.connect(":memory:") as cx:
            cx.execute(
                "CREATE TABLE personaggi (id INTEGER PRIMARY KEY, nome TEXT NOT NULL UNIQUE)"
            )
            cx.execute("INSERT INTO personaggi (nome) VALUES (?)", ("Keqing",))
            cx.execute("INSERT INTO personaggi (nome) VALUES (?)", ("keqing",))
            n = cx.execute("SELECT COUNT(*) FROM personaggi").fetchone()[0]
            self.assertEqual(n, 2)

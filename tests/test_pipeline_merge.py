"""Test merge idempotente pipeline → registry JSON."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

# Root repo su sys.path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.pipeline.merge_registry import (  # noqa: E402
    _load_registry,
    _save_registry,
    merge_armi,
    merge_manufatti_rows,
    merge_personaggi,
)


class PipelineMergeTest(unittest.TestCase):
    def test_idempotent_character_and_weapon(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reg = Path(td) / "custom_entities.json"
            base = {"version": 1, "characters": [], "weapons": [], "sets": []}
            reg.write_text(json.dumps(base), encoding="utf-8")

            r = _load_registry(reg)
            merge_personaggi(
                r,
                [{"nome": "Test pg", "elemento": "Pyro", "arma": "Spada", "base_stats": {}}],
                approve=False,
                source_tag="test",
            )
            merge_armi(
                r,
                [
                    {
                        "nome": "Test arma",
                        "tipo": "Spada",
                        "rarita": 5,
                        "atk_base": 500,
                        "stat_secondaria": "ER%",
                        "valore_stat": 55,
                    }
                ],
                approve=False,
                source_tag="test",
            )
            _save_registry(reg, r)

            r2 = _load_registry(reg)
            merge_personaggi(
                r2,
                [{"nome": "TEST PG", "elemento": "Pyro", "arma": "Spada", "base_stats": {}}],
                approve=True,
                source_tag="test2",
            )
            _save_registry(reg, r2)

            final = json.loads(reg.read_text(encoding="utf-8"))
            self.assertEqual(len(final["characters"]), 1)
            self.assertTrue(final["characters"][0].get("approved"))
            self.assertEqual(len(final["weapons"]), 1)

    def test_manufatto_partial_set_not_approved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            reg = Path(td) / "custom_entities.json"
            reg.write_text(
                json.dumps({"version": 1, "characters": [], "weapons": [], "sets": []}),
                encoding="utf-8",
            )
            r = _load_registry(reg)
            rows, sets_n, w = merge_manufatti_rows(
                r,
                [
                    {
                        "set": "Set unico test",
                        "slot": "fiore",
                        "pezzo": "Fiore a",
                    }
                ],
                approve=True,
                source_tag="test",
            )
            self.assertEqual(rows, 1)
            self.assertGreaterEqual(sets_n, 1)
            self.assertTrue(any("incomplete" in x or "mancanti" in x for x in w))
            self.assertEqual(r["sets"][0].get("approved"), False)


if __name__ == "__main__":
    unittest.main()

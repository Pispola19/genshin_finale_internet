"""Bridge export utente → batch pipeline."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.user_export_bridge.convert_to_pipeline import (  # noqa: E402
    user_export_to_pipeline_batch,
    validate_pipeline_batch,
)


class UserExportBridgeTest(unittest.TestCase):
    def test_version_required(self) -> None:
        with self.assertRaises(ValueError):
            user_export_to_pipeline_batch({}, source_tag="t")

    def test_english_keys(self) -> None:
        raw = {
            "user_export_version": 1,
            "characters": [{"nome": "Hu Tao", "elemento": "Pyro", "arma": "Lancia"}],
            "weapons": [],
            "artifacts": [],
        }
        b = user_export_to_pipeline_batch(raw, source_tag="test")
        self.assertEqual(len(b["personaggi"]), 1)
        ok, err = validate_pipeline_batch(b)
        self.assertTrue(ok, err)

    def test_example_file_roundtrip(self) -> None:
        p = ROOT / "tools" / "user_export_bridge" / "example_user_export.json"
        raw = json.loads(p.read_text(encoding="utf-8"))
        b = user_export_to_pipeline_batch(raw, source_tag="test")
        ok, err = validate_pipeline_batch(b)
        self.assertTrue(ok, err)


if __name__ == "__main__":
    unittest.main()

"""Test checkpoint automatico (copia DB + retention)."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path


def _make_sqlite(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS t (x INTEGER)")
    conn.commit()
    conn.close()


class TestCheckpoint(unittest.TestCase):
    def test_disabled_skips(self):
        import core.checkpoint as cp

        prev = os.environ.get("GENSHIN_CHECKPOINT")
        try:
            os.environ["GENSHIN_CHECKPOINT"] = "0"
            r = cp.run_automatic_checkpoint("test")
            self.assertTrue(r.get("skipped"))
        finally:
            if prev is None:
                os.environ.pop("GENSHIN_CHECKPOINT", None)
            else:
                os.environ["GENSHIN_CHECKPOINT"] = prev

    def test_creates_snapshot_and_prunes(self):
        import core.checkpoint as cp

        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            db1 = tdp / "genshin.db"
            db2 = tdp / "artefatti.db"
            _make_sqlite(db1)
            _make_sqlite(db2)
            (tdp / "user_artifact_sets.json").write_text("[]", encoding="utf-8")

            prev_kept = os.environ.get("GENSHIN_CHECKPOINT_MAX")
            prev_cp = os.environ.get("GENSHIN_CHECKPOINT")
            try:
                os.environ["GENSHIN_CHECKPOINT"] = "1"
                os.environ["GENSHIN_CHECKPOINT_MAX"] = "4"
                cp.DB_PATH = db1
                cp.ARTEFATTI_DB_PATH = db2
                cp.PROJECT_ROOT = tdp

                for _ in range(6):
                    r = cp.run_automatic_checkpoint("test")
                    self.assertTrue(r.get("ok"), msg=r)
                    self.assertIn("genshin.db", r.get("copied", []))
                    import time

                    time.sleep(1.05)

                root = cp.checkpoint_dir()
                dirs = [p for p in root.iterdir() if p.is_dir() and p.name.startswith("auto-")]
                self.assertLessEqual(len(dirs), 4, [p.name for p in dirs])
            finally:
                if prev_kept is None:
                    os.environ.pop("GENSHIN_CHECKPOINT_MAX", None)
                else:
                    os.environ["GENSHIN_CHECKPOINT_MAX"] = prev_kept
                if prev_cp is None:
                    os.environ.pop("GENSHIN_CHECKPOINT", None)
                else:
                    os.environ["GENSHIN_CHECKPOINT"] = prev_cp

    def test_save_throttle(self):
        import core.checkpoint as cp

        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            db1 = tdp / "genshin.db"
            _make_sqlite(db1)
            prev = os.environ.get("GENSHIN_CHECKPOINT_SAVE_SEC")
            try:
                os.environ["GENSHIN_CHECKPOINT"] = "1"
                os.environ["GENSHIN_CHECKPOINT_SAVE_SEC"] = "9999"
                cp._last_save_checkpoint_ts = None
                cp.DB_PATH = db1
                cp.ARTEFATTI_DB_PATH = tdp / "missing.db"
                cp.PROJECT_ROOT = tdp
                r1 = cp.maybe_checkpoint_after_save()
                self.assertFalse(r1.get("skipped"), msg=r1)
                self.assertTrue(r1.get("ok"), msg=r1)
                r2 = cp.maybe_checkpoint_after_save()
                self.assertTrue(r2.get("skipped"))
                self.assertEqual(r2.get("reason"), "save_throttle")
            finally:
                cp._last_save_checkpoint_ts = None
                if prev is None:
                    os.environ.pop("GENSHIN_CHECKPOINT_SAVE_SEC", None)
                else:
                    os.environ["GENSHIN_CHECKPOINT_SAVE_SEC"] = prev


if __name__ == "__main__":
    unittest.main()

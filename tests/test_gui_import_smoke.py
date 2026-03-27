"""Smoke: pacchetto gui importabile senza avviare il loop Tk."""
from __future__ import annotations

import os
import unittest


class GuiImportSmokeTest(unittest.TestCase):
    def test_gui_app_module_loads(self) -> None:
        import gui.app as ga

        self.assertTrue(hasattr(ga, "GenshinApp"))

    def test_genshin_force_web_blocks_run(self) -> None:
        old = os.environ.get("GENSHIN_FORCE_WEB")
        try:
            os.environ["GENSHIN_FORCE_WEB"] = "1"
            from gui.app import GenshinApp

            app = GenshinApp()
            with self.assertRaises(SystemExit) as ctx:
                app.run()
            self.assertEqual(ctx.exception.code, 3)
        finally:
            if old is None:
                os.environ.pop("GENSHIN_FORCE_WEB", None)
            else:
                os.environ["GENSHIN_FORCE_WEB"] = old


if __name__ == "__main__":
    unittest.main()

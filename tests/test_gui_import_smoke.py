"""Smoke: pacchetto gui importabile senza avviare il loop Tk."""
from __future__ import annotations

import unittest


class GuiImportSmokeTest(unittest.TestCase):
    def test_gui_app_module_loads(self) -> None:
        import gui.app as ga

        self.assertTrue(hasattr(ga, "GenshinApp"))


if __name__ == "__main__":
    unittest.main()

"""Validazione checkpoint GUI."""
import unittest

from config import SLOT_DB, SLOT_UI
from gui import form_checkpoint as fc


class TestFormCheckpoint(unittest.TestCase):
    def test_valid_minimal_state(self):
        st = {
            "version": fc.CHECKPOINT_VERSION,
            "selected_id": None,
            "personaggio": {"nome": "A", "livello": "1", "elemento": "Pyro"},
            "arma": {"nome": "", "tipo": "Spada"},
            "costellazioni": {f"c{i}": "0" for i in range(1, 7)},
            "talenti": {k: "-" for k in fc._TALENT_KEYS},
            "equipaggiamento": {s: None for s in SLOT_DB},
            "artefatti_labels": {u: "—" for u in SLOT_UI},
        }
        ok, _ = fc.validate_gui_checkpoint_state(st)
        self.assertTrue(ok)

    def test_invalid_slot_key_rejected(self):
        st = {
            "version": fc.CHECKPOINT_VERSION,
            "selected_id": None,
            "personaggio": {"nome": "A", "livello": "1", "elemento": "Pyro"},
            "arma": {},
            "costellazioni": {f"c{i}": "0" for i in range(1, 7)},
            "talenti": {k: "-" for k in fc._TALENT_KEYS},
            "equipaggiamento": {"wrong_slot": 1},
            "artefatti_labels": {u: "—" for u in SLOT_UI},
        }
        ok, msg = fc.validate_gui_checkpoint_state(st)
        self.assertFalse(ok)
        self.assertIn("slot", msg.lower())


if __name__ == "__main__":
    unittest.main()

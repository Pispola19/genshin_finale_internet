from __future__ import annotations

import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path


class HoyolabImportSafetyTest(unittest.TestCase):
    def setUp(self) -> None:
        import db.connection as conn_mod

        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.db_path = root / "genshin.db"
        self.art_path = root / "artefatti.db"

        self._orig_db_path = getattr(conn_mod, "DB_PATH", None)
        self._orig_art_path = getattr(conn_mod, "ARTEFATTI_DB_PATH", None)

        # Patch percorsi DB usati dal layer connessioni.
        conn_mod.DB_PATH = str(self.db_path)
        conn_mod.ARTEFATTI_DB_PATH = str(self.art_path)
        conn_mod._schema_initialized = False
        conn_mod._tls = threading.local()

    def tearDown(self) -> None:
        import db.connection as conn_mod

        try:
            conn_mod.close_thread_connections()
        except Exception:
            pass

        # Ripristina i percorsi DB originali per non rompere altri test.
        if self._orig_db_path is not None:
            conn_mod.DB_PATH = self._orig_db_path
        if self._orig_art_path is not None:
            conn_mod.ARTEFATTI_DB_PATH = self._orig_art_path
        conn_mod._schema_initialized = False

        try:
            self._tmp.cleanup()
        except Exception:
            pass

    def _insert_personaggio(self, svc, nome: str = "TestChar") -> int:
        from db.repositories import PersonaggioRepository

        pid = PersonaggioRepository.insert(
            svc.conn,
            (
                nome,
                90,
                "Pyro",
                100,
                200,
                300,
                400,
                50,
                60,
                70,
            ),
        )
        return pid

    def _insert_assigned_art(self, svc, *, pid: int, slot: str, set_nome: str, nome: str) -> int:
        from db.repositories import ArtefattoRepository

        # DB order must match ArtefattoRepository.insert().
        row = (
            slot,
            set_nome,
            nome,
            20,  # livello
            5,  # stelle
            "HP%",  # main_stat
            999.0,  # main_val
            "CR",  # sub1_stat
            12.5,  # sub1_val
            "ATK%",  # sub2_stat
            45.0,
            "ER",  # sub3_stat
            20.0,
            "DEF%",  # sub4_stat
            30.0,
        )
        aid = ArtefattoRepository.insert(svc.conn_art, row)
        ArtefattoRepository.set_equipaggiamento(svc.conn_art, pid, slot, aid)
        return aid

    def test_update_does_not_lose_main_sub_stats_when_missing_from_hoyo(self) -> None:
        from core.personaggio_service import PersonaggioService
        from db.repositories import ArtefattoRepository

        svc = PersonaggioService()
        try:
            pid = self._insert_personaggio(svc, "VarkaTest")
            aid_old = self._insert_assigned_art(
                svc, pid=pid, slot="fiore", set_nome="SetA", nome="FioreOld"
            )
            old = ArtefattoRepository.get(svc.conn_art, aid_old)
            assert old is not None

            # HoYo payload con main/sub vuoti e livello=0 (simula missing).
            relics = [
                {
                    "pos": 1,
                    "set": {"name": "SetB"},
                    "name": "FioreNew",
                    "level": 0,
                    "rarity": 5,
                    "main_property": None,
                    "sub_property_list": [],
                }
            ]

            svc.update_equipment_from_hoyo_relics(pid, relics)

            after = ArtefattoRepository.get(svc.conn_art, aid_old)
            assert after is not None

            # Stat DB devono essere preservate.
            self.assertEqual(after["main_stat"], old["main_stat"])
            self.assertEqual(after["main_val"], old["main_val"])
            self.assertEqual(after["sub1_stat"], old["sub1_stat"])
            self.assertEqual(after["sub1_val"], old["sub1_val"])
            self.assertEqual(after["sub2_stat"], old["sub2_stat"])
            self.assertEqual(after["sub2_val"], old["sub2_val"])
            self.assertEqual(after["sub3_stat"], old["sub3_stat"])
            self.assertEqual(after["sub3_val"], old["sub3_val"])
            self.assertEqual(after["sub4_stat"], old["sub4_stat"])
            self.assertEqual(after["sub4_val"], old["sub4_val"])

            # livello non deve essere sovrascritto con 0
            self.assertEqual(after["livello"], old["livello"])
        finally:
            try:
                svc.close()
            except Exception:
                pass

    def test_append_dedup_vs_force(self) -> None:
        from core.personaggio_service import PersonaggioService
        from db.repositories import ArtefattoRepository

        svc = PersonaggioService()
        try:
            relic = {
                "pos": 1,
                "set": {"name": "SetX"},
                "name": "FioreX",
                "level": 20,
                "rarity": 5,
                "main_property": None,
                "sub_property_list": [],
            }
            inserted_1 = svc.append_hoyo_relics_to_warehouse([relic], dedup=True)
            inserted_2 = svc.append_hoyo_relics_to_warehouse([relic], dedup=True)
            self.assertEqual(inserted_1, 1)
            self.assertEqual(inserted_2, 0)

            # Controllo count su inventario.
            cur = svc.conn_art.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM artefatti WHERE assegna_a_id IS NULL AND slot=? AND set_nome=? AND livello=? AND stelle=?",
                ("fiore", "SetX", 20, 5),
            )
            count = cur.fetchone()[0]
            self.assertEqual(count, 1)

            # Force: duplica.
            svc.append_hoyo_relics_to_warehouse([relic], dedup=False)
            cur.execute(
                "SELECT COUNT(*) FROM artefatti WHERE assegna_a_id IS NULL AND slot=? AND set_nome=? AND livello=? AND stelle=?",
                ("fiore", "SetX", 20, 5),
            )
            count2 = cur.fetchone()[0]
            self.assertEqual(count2, 2)
        finally:
            try:
                svc.close()
            except Exception:
                pass

    def test_replace_deletes_previous_equipped_artifacts(self) -> None:
        from core.personaggio_service import PersonaggioService
        from db.repositories import ArtefattoRepository

        svc = PersonaggioService()
        try:
            pid = self._insert_personaggio(svc, "ReplaceTest")
            aid_old = self._insert_assigned_art(
                svc, pid=pid, slot="fiore", set_nome="SetOld", nome="FioreOld"
            )

            self.assertIsNotNone(ArtefattoRepository.get(svc.conn_art, aid_old))

            relics_new = [
                {
                    "pos": 1,
                    "set": {"name": "SetNew"},
                    "name": "FioreNew",
                    "level": 20,
                    "rarity": 5,
                    "main_property": None,
                    "sub_property_list": [],
                }
            ]
            svc.replace_equipment_from_hoyo_relics(pid, relics_new)

            # Old row deve essere stata eliminata.
            self.assertIsNone(ArtefattoRepository.get(svc.conn_art, aid_old))

            # Deve esistere almeno un artefatto assegnato allo slot.
            eq = ArtefattoRepository.equip_map_for_personaggio(svc.conn_art, pid)
            self.assertIn("fiore", eq)
            self.assertIsNotNone(eq["fiore"])
        finally:
            try:
                svc.close()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()


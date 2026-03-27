"""
Stress HTTP: cartella web (Flask). API dati richiedono sessione.
"""
from __future__ import annotations

import os
import unittest

# Sessione protetta come in produzione quando la password è impostata.
os.environ.setdefault("GENSHIN_WEB_WRITE_PASSWORD", "web-api-stress-test-secret")

from web.web_write_auth import SESSION_WRITE_KEY


class WebApiStressTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from web.app import app as flask_app

        flask_app.config["TESTING"] = True
        cls.client = flask_app.test_client()
        with cls.client.session_transaction() as sess:
            sess[SESSION_WRITE_KEY] = True

    @classmethod
    def tearDownClass(cls) -> None:
        import web.app as wa

        svc = getattr(wa, "_service", None)
        if svc is not None:
            try:
                svc.close()
            except Exception:
                pass
            wa._service = None

    def _get_many(self, path: str, *, times: int = 80) -> None:
        for _ in range(times):
            rv = self.client.get(path)
            self.assertIn(rv.status_code, (200, 301, 302, 404), msg=f"{path} -> {rv.status_code}")

    def test_api_personaggi_repeated(self) -> None:
        self._get_many("/api/personaggi", times=120)

    def test_api_autocomplete_and_catalogo_repeated(self) -> None:
        self._get_many("/api/autocomplete", times=60)
        self._get_many("/api/personaggi/catalogo-nomi", times=40)
        self._get_many("/api/catalogo/armi", times=24)
        for slot in ("fiore", "piuma", "calice", "corona", "sabbie"):
            self._get_many(f"/api/artefatti/catalogo?slot={slot}", times=25)

    def test_api_artefatti_list_repeated(self) -> None:
        self._get_many("/api/artefatti", times=40)

    def test_static_pages(self) -> None:
        for path in (
            "/personaggio.html",
            "/build.html",
            "/artefatti.html",
            "/ottimizzazione.html",
            "/dashboard.html",
            "/team.html",
            "/istruzioni.html",
            "/login.html",
            "/rotation.html",
        ):
            rv = self.client.get(path)
            self.assertEqual(rv.status_code, 200, msg=path)
            data = rv.get_data()
            self.assertIn(b"html", data.lower())
            try:
                rv.close()
            except Exception:
                pass

    def test_api_auth_status(self) -> None:
        self._get_many("/api/auth/status", times=50)

    def test_api_404_stable(self) -> None:
        for _ in range(40):
            r = self.client.get("/api/personaggio/999999999")
            self.assertEqual(r.status_code, 404)
            r2 = self.client.get("/api/build/999999999")
            self.assertEqual(r2.status_code, 404)
            r3 = self.client.get("/api/build/999999999/rotation")
            self.assertEqual(r3.status_code, 404)

    def test_api_build_schema_when_any_personaggio(self) -> None:
        r = self.client.get("/api/personaggi")
        self.assertEqual(r.status_code, 200)
        rows = r.get_json()
        self.assertIsInstance(rows, list)
        if not rows:
            self.skipTest("Nessun personaggio nel DB: schema build non verificabile")
        pid = rows[0]["id"]
        br = self.client.get(f"/api/build/{pid}")
        self.assertEqual(br.status_code, 200)
        data = br.get_json()
        self.assertIn("build_attuale", data)
        self.assertIn("build_ottimale", data)
        self.assertIn("differenza", data)
        self.assertIn("riepilogo", data["build_attuale"])
        self.assertIn("slots", data["build_attuale"]["riepilogo"])
        self.assertIn("bonus_set", data["build_attuale"]["riepilogo"])
        self.assertIn("dps", data["build_attuale"])
        self.assertIn("damage_proxy", data["build_attuale"])
        self.assertIn("combat_build", data)
        self.assertIn("attuale", data["combat_build"])
        self.assertIn("totale", data["combat_build"]["attuale"])
        self.assertIn("damage_proxy", data["combat_build"]["attuale"])
        self.assertIn("set_bonus_multiplier", data["combat_build"]["attuale"])
        self.assertIn("differenza", data)
        self.assertIn("damage_proxy", data["differenza"])
        rot = self.client.get(f"/api/build/{pid}/rotation")
        self.assertEqual(rot.status_code, 200, msg=rot.get_data(as_text=True))
        rot_j = rot.get_json()
        self.assertTrue(rot_j.get("ok"))
        self.assertIn("rotation_index", rot_j)
        self.assertIn("rotation_multiplier", rot_j)
        self.assertIn("combat_totale_summary_it", rot_j)
        self.assertIn("atk", data["differenza"])
        self.assertIn("em", data["differenza"])
        self.assertIn("confronto", data)
        self.assertIn("slot", data["confronto"])
        self.assertIn("set_proxy", data["confronto"])
        self.assertIn("dps_quality", data)
        dq = data["dps_quality"]
        self.assertIn("ready", dq)
        self.assertIn("status_badge_it", dq)
        self.assertIn("summary_it", dq)
        self.assertIn("warnings_it", dq)

    def test_api_dashboard_and_teams(self) -> None:
        self._get_many("/api/dashboard", times=30)
        dash = self.client.get("/api/dashboard")
        self.assertEqual(dash.status_code, 200)
        dj = dash.get_json()
        self.assertIn("dps_quality", dj)
        self.assertIn("summary_it", dj["dps_quality"])
        self._get_many("/api/teams", times=30)
        rv = self.client.post("/api/teams/calcola", json={"personaggi": []})
        self.assertEqual(rv.status_code, 200)
        body = rv.get_json()
        self.assertIsInstance(body, dict)
        self.assertIn("teams", body)

    def test_artefatto_suggerimenti_json(self) -> None:
        rv = self.client.get("/api/artefatti/999999999/suggerimenti-personaggi")
        self.assertEqual(rv.status_code, 200)
        j = rv.get_json()
        self.assertIn("ranking", j)
        self.assertIsInstance(j["ranking"], list)

    def test_api_get_requires_session(self) -> None:
        from web.app import app

        naked = app.test_client()
        r = naked.get("/api/personaggi")
        self.assertEqual(r.status_code, 401)
        self.assertEqual((r.get_json() or {}).get("code"), "auth_required")


if __name__ == "__main__":
    unittest.main()

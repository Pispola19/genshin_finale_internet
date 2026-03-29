"""Verifica interpretazione GENSHIN_WEB_AUTH_ENABLED (nessun accoppiamento col solo write password)."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from web.web_write_auth import web_auth_enabled, write_password_configured, write_password_present


class WebWriteAuthEnvTest(unittest.TestCase):
    def test_auth_off_when_empty_string(self) -> None:
        with patch.dict(os.environ, {"GENSHIN_WEB_AUTH_ENABLED": ""}):
            self.assertFalse(web_auth_enabled())

    def test_auth_off_for_zero_variants(self) -> None:
        for val in ("0", " 0 ", "00", "false", "no", "OFF", "disabled"):
            with self.subTest(val=val):
                with patch.dict(os.environ, {"GENSHIN_WEB_AUTH_ENABLED": val}, clear=False):
                    self.assertFalse(web_auth_enabled(), msg=repr(val))

    def test_auth_on_only_explicit(self) -> None:
        for val in ("1", "true", "yes", " YES "):
            with self.subTest(val=val):
                with patch.dict(os.environ, {"GENSHIN_WEB_AUTH_ENABLED": val}, clear=False):
                    self.assertTrue(web_auth_enabled(), msg=repr(val))

    def test_write_password_configured_requires_both(self) -> None:
        with patch.dict(
            os.environ,
            {
                "GENSHIN_WEB_WRITE_PASSWORD": "secret",
                "GENSHIN_WEB_AUTH_ENABLED": "0",
            },
            clear=False,
        ):
            self.assertTrue(write_password_present())
            self.assertFalse(web_auth_enabled())
            self.assertFalse(write_password_configured())

        with patch.dict(
            os.environ,
            {
                "GENSHIN_WEB_WRITE_PASSWORD": "secret",
                "GENSHIN_WEB_AUTH_ENABLED": "1",
            },
            clear=False,
        ):
            self.assertTrue(write_password_configured())


if __name__ == "__main__":
    unittest.main()

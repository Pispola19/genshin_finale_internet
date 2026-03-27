"""
Imposta password web di test per ``web.app`` (sessione simile alla produzione).
Senza questa variabile il gate web è aperto in locale; i test Flask usano comunque una password fittizia.
"""
from __future__ import annotations

import os

os.environ.setdefault("GENSHIN_WEB_WRITE_PASSWORD", "pytest-web-secret-do-not-use-in-production")

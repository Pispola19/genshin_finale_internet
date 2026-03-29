"""
Password e flag auth per i test: gate scritture attivo come in produzione quando l’auth è on.
"""
from __future__ import annotations

import os

os.environ.setdefault("GENSHIN_WEB_WRITE_PASSWORD", "pytest-web-secret-do-not-use-in-production")
os.environ.setdefault("GENSHIN_WEB_AUTH_ENABLED", "1")

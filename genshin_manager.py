"""
Alias legacy: stesso comportamento di main.py (delega a run_web.py).

Uso ufficiale (documentato in README.md)::

    python3 run_web.py

Per saltare la pausa di 2 secondi: ``GENSHIN_MAIN_NO_SLEEP=1``.
"""
from main import main

if __name__ == "__main__":
    main()

# Genshin Manager

Applicazione locale per personaggi, manufatti e build (Flask + browser).  

## Cartella del progetto (una sola copia)

- **Nome consigliato:** `genshin_manager` — breve, senza suffissi tipo `_ultimo_finito_25`; evita duplicati per typo (`ultino` / `ultimo`) o versioni nel path.
- **Sorgente unica:** tieni un solo clone; DB e log stanno sotto `PROJECT_ROOT` (vedi `config.py`), calcolato da `Path(__file__)`, non da nomi fissi.
- **Launcher macOS (`.command`):** devono stare **nella stessa cartella** di `run_web.py`, oppure imposta `export GENSHIN_PROJECT_ROOT=/percorso/reale/della/repo` prima di aprirli da altrove.
- **LaunchAgent:** non usare plist con path assoluti versionati nel repo. Genera il plist per **questa** macchina con:
  ```bash
  bash mac/install_launchagent.sh
  ```
  (scrive `~/Library/LaunchAgents/com.genshinmanager.web.plist` a partire da `mac/com.genshinmanager.web.plist.template`).

**Entry point ufficiale:**

```bash
export GENSHIN_WEB_WRITE_PASSWORD='scegli-una-password-lunga'
# Opzionale: export GENSHIN_WEB_AUTH_ENABLED=1   # attiva login + gate sulle sole scritture API
python3 run_web.py
```

Su **Render** (o con `GENSHIN_WEB_FORCE_PASSWORD=1`), senza **`GENSHIN_WEB_WRITE_PASSWORD`** il processo **non parte**. Quella variabile **non** attiva da sola il login in app: con **`GENSHIN_WEB_AUTH_ENABLED=1`** le scritture (POST/PUT/DELETE) richiedono sessione dopo **`login.html`**; le GET restano pubbliche. Con il flag assente/spento, accesso e modifiche sono libere anche se la password di avvio è impostata.

In **locale**, senza forzare la password, il server può partire senza `GENSHIN_WEB_WRITE_PASSWORD` (vedi `web.app`).

**Sicurezza (single-user):** quando il flag auth è attivo, una password per installazione e gate solo sulle operazioni di modifica. Nessun multi-tenant nel database.

## Avvio macOS

Doppio clic su **`Genshin_Manager.command`** o **`Genshin Manager — progetto.command`**: entrambi eseguono solo `run_web.py`.

## Deprecati (redirect)

- **`main.py`** e **`genshin_manager.py`** delegano a `run_web.py` con avviso su stderr; prima dell’avvio di Flask aspettano **2 secondi** (disattivabile con `GENSHIN_MAIN_NO_SLEEP=1`). Serve la stessa **`GENSHIN_WEB_WRITE_PASSWORD`** nel ambiente (il caricamento di `web.app` è identico).

## Variabili d’ambiente utili

| Variabile | Effetto |
|-----------|---------|
| `GENSHIN_WEB_WRITE_PASSWORD` | Obbligatoria con `RENDER` (o `GENSHIN_WEB_FORCE_PASSWORD`): avvio del servizio. Non attiva il login da sola. |
| `GENSHIN_WEB_AUTH_ENABLED` | `1` / `true` / `yes`: attiva login applicativo e protezione **solo** delle scritture API (GET libere). |
| `SECRET_KEY` | Firmare cookie sessione (in produzione impostala tu; su Render può essere generata). |
| `PORT` | Porta del server (es. su hosting). |
| `GENSHIN_MAIN_NO_SLEEP=1` | Nessuna pausa quando si lancia tramite `main.py`. |
| `GENSHIN_FORCE_WEB=1` | Blocca **`GenshinApp().run()`** (GUI Tk legacy): uscita con codice 3 e messaggio su stderr. |
| `GENSHIN_PROJECT_ROOT` | Percorso della repo se avvii un `.command` fuori dalla cartella del progetto (deve contenere `run_web.py`). |

## Hosting (es. Render)

Usa `gunicorn web.app:app` come nel `render.yaml` del repo.

## Modulo GUI Tk (`gui/`)

Rimasto per test/sviluppo; **non** è l’entry point documentato e non viene avviato da `main.py` o dagli script di lancio.

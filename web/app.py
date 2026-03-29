"""API Flask per Genshin Manager Web - espone servizi Python."""
import os
import secrets
import sys
from datetime import timedelta
from config import PROJECT_ROOT
from flask import Flask, request, jsonify, send_from_directory, redirect, session
from werkzeug.middleware.proxy_fix import ProxyFix

from web.web_write_auth import (
    SESSION_WRITE_KEY,
    password_matches,
    require_web_auth,
    write_password_configured,
)


def _deploy_requires_web_password() -> bool:
    """In produzione (Render) o se forzato, la password è obbligatoria all’avvio."""
    if (os.environ.get("RENDER") or "").strip():
        return True
    return (os.environ.get("GENSHIN_WEB_FORCE_PASSWORD") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _require_web_password_or_exit() -> None:
    """Locale: server può partire senza password. Host esposti: impostare GENSHIN_WEB_WRITE_PASSWORD."""
    if not _deploy_requires_web_password():
        return
    if not (os.environ.get("GENSHIN_WEB_WRITE_PASSWORD") or "").strip():
        print(
            "ERRORE FATALE: in produzione serve GENSHIN_WEB_WRITE_PASSWORD. "
            "In locale puoi ometterla; per forzarla ovunque usa GENSHIN_WEB_FORCE_PASSWORD=1.",
            file=sys.stderr,
        )
        sys.exit(2)


_require_web_password_or_exit()

ROOT = PROJECT_ROOT

app = Flask(__name__, static_folder=".", static_url_path="")
app.config["JSON_AS_ASCII"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=14)

_secret = (os.environ.get("SECRET_KEY") or "").strip()
if not _secret:
    _secret = secrets.token_hex(32)
app.secret_key = _secret

# Cookie sessione: HTTPS su Render / produzione
_is_production = bool(
    (os.environ.get("RENDER") or "").strip()
    or (os.environ.get("GENSHIN_SESSION_SECURE") or "").lower() in ("1", "true", "yes")
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = _is_production

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

SFONDI_DIR = ROOT / "sfondi"


@app.after_request
def _security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    # Script solo da questo sito; stili inline lasciati per le pagine HTML esistenti
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; "
        "base-uri 'self'; form-action 'self'",
    )
    return response

# Inizializza servizi (lazy)
_service = None


def get_service():
    global _service
    if _service is None:
        from core.services import AppService
        _service = AppService()
    return _service


# --- Autenticazione (password opzionale in locale se non configurata; vedi web_write_auth) ---
@app.route("/api/auth/status")
def api_auth_status():
    need = write_password_configured()
    return jsonify(
        {
            "write_auth_required": need,
            "authenticated": session.get(SESSION_WRITE_KEY) is True,
        }
    )


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    if not write_password_configured():
        session.clear()
        session.permanent = True
        session[SESSION_WRITE_KEY] = True
        return jsonify({"ok": True, "authenticated": True})
    j = request.get_json(silent=True) or {}
    pw = j.get("password")
    if not isinstance(pw, str):
        pw = ""
    if password_matches(pw):
        session.clear()
        session.permanent = True
        session[SESSION_WRITE_KEY] = True
        return jsonify({"ok": True, "authenticated": True})
    return jsonify({"error": "Password errata", "code": "login_failed"}), 401


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    session.pop(SESSION_WRITE_KEY, None)
    return jsonify({"ok": True})


# --- Personaggio ---
@app.route("/api/personaggi")
@require_web_auth
def api_personaggi():
    """Lista personaggi: [{id, nome, livello, elemento}, ...]."""
    svc = get_service()
    righe = svc.lista_personaggi_righe()
    return jsonify([{"id": r[0], "nome": r[1], "livello": r[2], "elemento": r[3]} for r in righe])


@app.route("/api/autocomplete")
@require_web_auth
def api_autocomplete():
    """Suggerimenti nome + personaggi salvati nel DB, ordinati."""
    return jsonify(get_service().nomi_per_autocomplete())


@app.route("/api/personaggi/catalogo-nomi")
@require_web_auth
def api_personaggi_catalogo_nomi():
    """Stesso elenco di /api/autocomplete, formato oggetto per chiarezza."""
    return jsonify({"nomi": get_service().nomi_per_autocomplete()})


@app.route("/api/catalogo/armi")
@require_web_auth
def api_catalogo_armi():
    """Nomi arma: catalogo effettivo (codice ∪ registry approvato)."""
    return jsonify({"nomi": get_service().nomi_armi_autocomplete()})


@app.route("/api/personaggio/<int:pk>")
@require_web_auth
def api_personaggio(pk):
    """Dati completi personaggio."""
    data = get_service().carica_dati_completi(pk)
    if data is None:
        return jsonify({"error": "Personaggio non trovato"}), 404
    return jsonify(data)


@app.route("/api/personaggio", methods=["POST"])
@require_web_auth
def api_salva_personaggio():
    """Salva personaggio completo."""
    svc = get_service()
    j = request.get_json() or {}
    id_pg = j.get("id")
    form_pg = j.get("personaggio", {})
    form_arma = j.get("arma", {})
    form_cost = j.get("costellazioni", {})
    form_talenti = j.get("talenti", {})
    if "equipaggiamento" not in j:
        form_equip = None
    else:
        raw_eq = j.get("equipaggiamento")
        form_equip = None if raw_eq is None else (raw_eq if isinstance(raw_eq, dict) else {})

    meta_raw = j.get("meta")
    meta = meta_raw if isinstance(meta_raw, dict) else {}

    try:
        id_pg = svc.salva_completo(
            id_pg,
            form_pg,
            form_arma,
            form_cost,
            form_talenti,
            form_equip,
            meta=meta,
        )
        return jsonify({"id": id_pg, "ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/personaggio/<int:pk>", methods=["DELETE"])
@require_web_auth
def api_elimina_personaggio(pk):
    get_service().elimina_personaggio(pk)
    return jsonify({"ok": True})


@app.route("/api/personaggi/pulizia-test", methods=["POST"])
@require_web_auth
def api_pulizia_test():
    """Elimina personaggi di test (test, Test1, Test3, ecc.)."""
    n = get_service().rimuovi_entrate_test()
    return jsonify({"ok": True, "eliminati": n})


# --- Artefatti ---
@app.route("/api/artefatti")
@require_web_auth
def api_artefatti():
    """Lista artefatti inventario (completa con substat). Sempre JSON (anche in errore)."""
    try:
        data = get_service().lista_artefatti_completa()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/artefatti", methods=["POST"])
@require_web_auth
def api_aggiungi_artefatto():
    """Registra nuovo artefatto con main stat e 4 substat."""
    j = request.get_json() or {}
    try:
        aid = get_service().aggiungi_artefatto(j)
        return jsonify({"id": aid, "ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/artefatti/<int:aid>", methods=["GET", "PUT", "DELETE"])
@require_web_auth
def api_artefatto_by_id(aid):
    """GET dettaglio; PUT aggiorna stats; DELETE rimuove (fodder / pulizia)."""
    svc = get_service()
    if request.method == "GET":
        d = svc.dettaglio_artefatto_json(aid)
        if d is None:
            return jsonify({"error": "Non trovato"}), 404
        return jsonify(d)
    if request.method == "PUT":
        j = request.get_json() or {}
        try:
            svc.aggiorna_artefatto(aid, j)
            return jsonify({"ok": True})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    try:
        svc.elimina_artefatto(aid)
        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/artefatti/<int:aid>/suggerimenti-personaggi")
@require_web_auth
def api_artefatto_suggerimenti_personaggi(aid):
    """Personaggi salvati ordinati per punteggio indicativo con questo pezzo."""
    return jsonify(get_service().suggerimenti_personaggi_per_artefatto(aid))


@app.route("/api/artefatti/catalogo")
@require_web_auth
def api_artefatti_catalogo():
    """Set, main stats e stats per substat (per form aggiunta)."""
    try:
        slot = request.args.get("slot", "fiore")
        from config import STATS
        return jsonify({
            "set": get_service().set_per_slot(slot),
            "main_stats": get_service().main_stats_per_slot(slot),
            "stats_subs": list(STATS),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/artefatti/catalogo-pezzo")
@require_web_auth
def api_artefatti_catalogo_pezzo():
    """Nomi pezzo dal catalogo per slot + set (di solito un solo nome ufficiale)."""
    try:
        slot = request.args.get("slot", "fiore")
        set_nome = request.args.get("set", "") or ""
        pezzi = get_service().pezzi_catalogo_set_slot(set_nome, slot)
        return jsonify({"pezzi": pezzi})
    except Exception as e:
        return jsonify({"pezzi": [], "error": str(e)})


@app.route("/api/artefatti/per-equip")
@require_web_auth
def api_artefatti_per_equip():
    """Artefatti assegnabili allo slot (liberi + quello equipaggiato al personaggio)."""
    slot = request.args.get("slot", "fiore")
    pid = request.args.get("personaggio_id", type=int)
    svc = get_service()
    lista = svc.lista_artefatti_per_equip(slot, pid)
    return jsonify([svc.artefatto_opzione_select(a) for a in lista])


@app.route("/api/artefatti/<int:aid>/utilizzatore", methods=["PUT"])
@require_web_auth
def api_artefatto_utilizzatore(aid):
    """Assegna a personaggio (body JSON personaggio_id) o libera (null)."""
    j = request.get_json() if request.is_json else {}
    pid = j.get("personaggio_id") if j else None
    if pid in ("", 0, "0"):
        pid = None
    elif pid is not None:
        pid = int(pid)
    try:
        get_service().assegna_artefatto_utilizzatore(aid, pid)
        return jsonify({"ok": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/artefatti/liberi")
@require_web_auth
def api_artefatti_liberi():
    """Artefatti liberi per slot."""
    slot = request.args.get("slot", "fiore")
    righe = get_service().lista_artefatti_liberi_righe(slot)
    return jsonify([
        {"id": r[0], "set": r[1], "main": r[2], "livello": r[3], "stelle": r[4]}
        for r in righe
    ])


@app.route("/api/ottimizzazione-manufatti")
@require_web_auth
def api_ottimizzazione_manufatti():
    """Suggerimenti per slot: equip attuale vs miglior pezzo libero in magazzino (indice DPSCalculator)."""
    return jsonify(get_service().suggerimenti_ottimizzazione_manufatti_tutti())


@app.route("/api/ottimizzazione-manufatti/<int:personaggio_id>")
@require_web_auth
def api_ottimizzazione_manufatti_pg(personaggio_id):
    data = get_service().suggerimenti_ottimizzazione_manufatti(personaggio_id)
    if data is None:
        return jsonify({"error": "Personaggio non trovato"}), 404
    return jsonify(data)


# --- Build Analysis ---
@app.route("/api/build/<int:personaggio_id>")
@require_web_auth
def api_build(personaggio_id):
    """Build attuale + build ottimale per personaggio."""
    data = get_service().get_build_analysis(personaggio_id)
    if data is None:
        return jsonify({"error": "Personaggio non trovato"}), 404
    return jsonify(data)


@app.route("/api/build/<int:personaggio_id>/rotation")
@require_web_auth
def api_build_rotation(personaggio_id):
    """Stima rotazione (indice derivato dal proxy build + talenti AA/E/Q)."""
    preset = (request.args.get("preset") or "equilibrato").strip()
    data = get_service().get_rotation_stima(personaggio_id, preset=preset)
    if not data.get("ok"):
        return jsonify(data), 404 if "non trovato" in str(data.get("message_it") or "").lower() else 400
    return jsonify(data)


# --- Team Builder ---
@app.route("/api/teams")
@require_web_auth
def api_teams():
    """Lista personaggi per team builder."""
    righe = get_service().lista_personaggi_righe()
    return jsonify([{"id": r[0], "nome": r[1], "livello": r[2], "elemento": r[3]} for r in righe])


@app.route("/api/teams/calcola", methods=["POST"])
@require_web_auth
def api_calcola_teams():
    """Calcola top 4 team. Se personaggi dati (>=4), usa quelli; altrimenti tutti."""
    j = request.get_json() or {}
    ids = j.get("personaggi", [])
    return jsonify(get_service().calcola_top_teams(ids))


# --- Dashboard ---
@app.route("/api/dashboard")
@require_web_auth
def api_dashboard():
    """Dati aggregati per dashboard."""
    return jsonify(get_service().get_dashboard_dati())


# --- Pagine HTML ---
@app.route("/")
def index():
    return redirect("/personaggio.html")


@app.route("/personaggio.html")
def page_personaggio():
    return send_from_directory(app.static_folder, "personaggio.html")


@app.route("/build.html")
def page_build():
    return send_from_directory(app.static_folder, "build.html")


@app.route("/rotation.html")
def page_rotation():
    return send_from_directory(app.static_folder, "rotation.html")


@app.route("/team.html")
def page_team():
    return send_from_directory(app.static_folder, "team.html")


@app.route("/inventario.html")
def page_inventario():
    return redirect("/artefatti.html")


@app.route("/artefatti.html")
def page_artefatti():
    return send_from_directory(app.static_folder, "artefatti.html")


@app.route("/dashboard.html")
def page_dashboard():
    return send_from_directory(app.static_folder, "dashboard.html")


@app.route("/istruzioni.html")
def page_istruzioni():
    return send_from_directory(app.static_folder, "istruzioni.html")


@app.route("/login.html")
def page_login():
    return send_from_directory(app.static_folder, "login.html")


@app.route("/sfondi/<path:filename>")
def sfondi_static(filename):
    """Immagini di sfondo dalla cartella progetto sfondi/."""
    return send_from_directory(SFONDI_DIR, filename)


def _register_server_checkpoint_atexit() -> None:
    """Opzionale: snapshot allo stop del processo (single worker / dev). Disattiva con GENSHIN_CHECKPOINT_WEB=0."""
    v = (os.environ.get("GENSHIN_CHECKPOINT_WEB") or "0").strip().lower()
    if v in ("0", "false", "no", "off"):
        return
    import atexit

    def _on_stop() -> None:
        try:
            from core.checkpoint import run_automatic_checkpoint

            run_automatic_checkpoint("server_stop")
        except Exception:
            pass

    atexit.register(_on_stop)


_register_server_checkpoint_atexit()

if __name__ == "__main__":
    app.run(debug=True, port=5001)

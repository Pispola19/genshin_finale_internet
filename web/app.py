"""API Flask per Genshin Manager Web - espone servizi Python."""
import os
import secrets
from datetime import timedelta
from typing import Optional

from config import PROJECT_ROOT
from flask import Flask, request, jsonify, send_from_directory, redirect, session
from werkzeug.middleware.proxy_fix import ProxyFix

from web.web_write_auth import (
    SESSION_WRITE_KEY,
    gate_write,
    password_matches,
    require_write_auth,
    write_password_configured,
)

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


# --- Autenticazione scritture (opzionale, vedi GENSHIN_WEB_WRITE_PASSWORD) ---
@app.route("/api/auth/status")
def api_auth_status():
    need = write_password_configured()
    return jsonify(
        {
            "write_auth_required": need,
            "authenticated": True if not need else (session.get(SESSION_WRITE_KEY) is True),
        }
    )


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    if not write_password_configured():
        return jsonify({"ok": True, "authenticated": True, "message": "Password web non configurata sul server."})
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
def api_personaggi():
    """Lista personaggi: [{id, nome, livello, elemento}, ...]."""
    svc = get_service()
    righe = svc.lista_personaggi_righe()
    return jsonify([{"id": r[0], "nome": r[1], "livello": r[2], "elemento": r[3]} for r in righe])


@app.route("/api/autocomplete")
def api_autocomplete():
    """Tutti i nomi Genshin (Hoyolab) + eventuali personaggi salvati con nome custom, ordinati."""
    return jsonify(get_service().nomi_per_autocomplete())


@app.route("/api/personaggi/catalogo-nomi")
def api_personaggi_catalogo_nomi():
    """Stesso elenco di /api/autocomplete, formato oggetto per chiarezza."""
    return jsonify({"nomi": get_service().nomi_per_autocomplete()})


@app.route("/api/personaggio/<int:pk>")
def api_personaggio(pk):
    """Dati completi personaggio."""
    data = get_service().carica_dati_completi(pk)
    if data is None:
        return jsonify({"error": "Personaggio non trovato"}), 404
    return jsonify(data)


@app.route("/api/personaggio", methods=["POST"])
@require_write_auth
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

    try:
        id_pg = svc.salva_completo(
            id_pg, form_pg, form_arma, form_cost, form_talenti, form_equip
        )
        return jsonify({"id": id_pg, "ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/personaggio/import-incolla", methods=["POST"])
@require_write_auth
def api_personaggio_import_incolla():
    """Import manuale da JSON incollato (stesso parser della GUI Tk)."""
    from core.hoyolab_import import compute_hoyo_preview_stats, normalize_import_mode
    from core.import_log import append_import_log
    from core.manual_import import (
        ImportParseError,
        apply_manual_import,
        list_character_choices,
        parse_pasted_payload,
        preview_summary,
    )

    j = request.get_json() or {}
    import_mode = normalize_import_mode(j.get("import_mode"))
    raw = j.get("raw")
    if not isinstance(raw, str):
        raw = ""
    try:
        parsed = parse_pasted_payload(raw)
    except ImportParseError as e:
        return jsonify({"error": str(e)}), 400

    character_nome = (j.get("character_nome") or "").strip()
    if character_nome and not parsed.get("bulk"):
        chs = list_character_choices(parsed)
        sel = next((c for c in chs if (c.get("nome") or "") == character_nome), None)
        if sel:
            parsed = {**parsed, "character": sel}

    preview_only = bool(j.get("preview"))
    if preview_only:
        chs = list_character_choices(parsed)
        stats = compute_hoyo_preview_stats(parsed)
        out = {
            "ok": True,
            "summary": preview_summary(parsed),
            "nome": (parsed.get("character") or {}).get("nome"),
            "bulk": bool(parsed.get("bulk")),
            "import_count": len(parsed.get("imports") or []) if parsed.get("bulk") else 1,
            "stats": stats,
            "import_mode": import_mode,
            "parse_skips": parsed.get("parse_skips") or [],
        }
        names = [c.get("nome") for c in chs if c.get("nome")]
        if len(names) > 1 and not parsed.get("bulk"):
            out["choices"] = names
        return jsonify(out)

    svc = get_service()
    id_pg = j.get("id")
    if id_pg is not None:
        try:
            id_pg = int(id_pg)
        except (TypeError, ValueError):
            id_pg = None

    if parsed.get("bulk"):
        imports = list(parsed.get("imports") or [])
        if character_nome:
            imports = [
                i
                for i in imports
                if ((i.get("character") or {}).get("nome") or "") == character_nome
            ]
        if not imports:
            return jsonify({"error": "Nessun personaggio da importare (filtro nome o elenco vuoto)."}), 400
        last_id: Optional[int] = None
        errors: list = []
        ok_count = 0
        imported_names: list = []
        for imp in imports:
            nome_i = (imp.get("character") or {}).get("nome") or ""
            if not nome_i:
                continue
            merge_id = svc.id_per_nome(nome_i)
            ok_nome, msg = svc.valida_nome(nome_i, merge_id)
            if not ok_nome:
                errors.append({"nome": nome_i, "error": msg})
                continue
            try:
                last_id = apply_manual_import(
                    svc, imp, merge_id, touch_equipment=None, import_mode=import_mode
                )
                ok_count += 1
                imported_names.append(nome_i)
            except Exception as e:
                errors.append({"nome": nome_i, "error": str(e)})
        if ok_count == 0:
            append_import_log(
                {
                    "source": "web",
                    "bulk": True,
                    "import_mode": import_mode,
                    "imported_ok": 0,
                    "errors": errors,
                    "parse_skips": parsed.get("parse_skips") or [],
                    "imported_names": imported_names,
                    "stats": compute_hoyo_preview_stats(parsed),
                }
            )
            return jsonify(
                {
                    "error": "Import non riuscito per nessun personaggio.",
                    "details": errors,
                }
            ), 400
        dati = svc.carica_dati_completi(last_id) if last_id else None
        stats = compute_hoyo_preview_stats(parsed)
        append_import_log(
            {
                "source": "web",
                "bulk": True,
                "import_mode": import_mode,
                "imported_ok": ok_count,
                "errors": errors,
                "parse_skips": parsed.get("parse_skips") or [],
                "imported_names": imported_names,
                "stats": stats,
            }
        )
        return jsonify(
            {
                "ok": True,
                "bulk": True,
                "id": last_id,
                "imported": ok_count,
                "errors": errors,
                "summary": preview_summary(parsed),
                "dati": dati,
                "import_mode": import_mode,
                "stats": stats,
                "parse_skips": parsed.get("parse_skips") or [],
            }
        )

    nome_pg = (parsed.get("character") or {}).get("nome") or ""
    merge_id = id_pg if id_pg is not None else svc.id_per_nome(nome_pg)
    ok_nome, msg = svc.valida_nome(nome_pg, merge_id)
    if not ok_nome:
        return jsonify({"error": msg}), 400

    try:
        new_id = apply_manual_import(
            svc, parsed, merge_id, touch_equipment=None, import_mode=import_mode
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    dati = svc.carica_dati_completi(new_id)
    stats = compute_hoyo_preview_stats(parsed)
    append_import_log(
        {
            "source": "web",
            "bulk": False,
            "import_mode": import_mode,
            "imported_ok": 1,
            "errors": [],
            "parse_skips": parsed.get("parse_skips") or [],
            "stats": stats,
            "personaggio": (parsed.get("character") or {}).get("nome"),
        }
    )
    return jsonify(
        {
            "ok": True,
            "id": new_id,
            "summary": preview_summary(parsed),
            "dati": dati,
            "import_mode": import_mode,
            "stats": stats,
            "parse_skips": parsed.get("parse_skips") or [],
        }
    )


@app.route("/api/personaggio/<int:pk>", methods=["DELETE"])
@require_write_auth
def api_elimina_personaggio(pk):
    get_service().elimina_personaggio(pk)
    return jsonify({"ok": True})


@app.route("/api/personaggi/pulizia-test", methods=["POST"])
@require_write_auth
def api_pulizia_test():
    """Elimina personaggi di test (test, Test1, Test3, ecc.)."""
    n = get_service().rimuovi_entrate_test()
    return jsonify({"ok": True, "eliminati": n})


# --- Artefatti ---
@app.route("/api/artefatti")
def api_artefatti():
    """Lista artefatti inventario (completa con substat). Sempre JSON (anche in errore)."""
    try:
        data = get_service().lista_artefatti_completa()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/artefatti", methods=["POST"])
@require_write_auth
def api_aggiungi_artefatto():
    """Registra nuovo artefatto con main stat e 4 substat."""
    j = request.get_json() or {}
    try:
        aid = get_service().aggiungi_artefatto(j)
        return jsonify({"id": aid, "ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/artefatti/<int:aid>", methods=["GET", "PUT", "DELETE"])
def api_artefatto_by_id(aid):
    """GET dettaglio; PUT aggiorna stats; DELETE rimuove (fodder / pulizia)."""
    if request.method != "GET":
        denied = gate_write()
        if denied:
            return denied
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
def api_artefatto_suggerimenti_personaggi(aid):
    """Personaggi salvati ordinati per punteggio indicativo con questo pezzo."""
    return jsonify(get_service().suggerimenti_personaggi_per_artefatto(aid))


@app.route("/api/artefatti/catalogo")
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
def api_artefatti_per_equip():
    """Artefatti assegnabili allo slot (liberi + quello equipaggiato al personaggio)."""
    slot = request.args.get("slot", "fiore")
    pid = request.args.get("personaggio_id", type=int)
    svc = get_service()
    lista = svc.lista_artefatti_per_equip(slot, pid)
    return jsonify([svc.artefatto_opzione_select(a) for a in lista])


@app.route("/api/artefatti/<int:aid>/utilizzatore", methods=["PUT"])
@require_write_auth
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
def api_artefatti_liberi():
    """Artefatti liberi per slot."""
    slot = request.args.get("slot", "fiore")
    righe = get_service().lista_artefatti_liberi_righe(slot)
    return jsonify([
        {"id": r[0], "set": r[1], "main": r[2], "livello": r[3], "stelle": r[4]}
        for r in righe
    ])


# --- Build Analysis ---
@app.route("/api/build/<int:personaggio_id>")
def api_build(personaggio_id):
    """Build attuale + build ottimale per personaggio."""
    data = get_service().get_build_analysis(personaggio_id)
    if data is None:
        return jsonify({"error": "Personaggio non trovato"}), 404
    return jsonify(data)


@app.route("/api/build/<int:personaggio_id>/rotation")
def api_build_rotation(personaggio_id):
    """Stima rotazione (indice derivato dal proxy build + talenti AA/E/Q)."""
    preset = (request.args.get("preset") or "equilibrato").strip()
    data = get_service().get_rotation_stima(personaggio_id, preset=preset)
    if not data.get("ok"):
        return jsonify(data), 404 if "non trovato" in str(data.get("message_it") or "").lower() else 400
    return jsonify(data)


# --- Team Builder ---
@app.route("/api/teams")
def api_teams():
    """Lista personaggi per team builder."""
    righe = get_service().lista_personaggi_righe()
    return jsonify([{"id": r[0], "nome": r[1], "livello": r[2], "elemento": r[3]} for r in righe])


@app.route("/api/teams/calcola", methods=["POST"])
def api_calcola_teams():
    """Calcola top 4 team. Se personaggi dati (>=4), usa quelli; altrimenti tutti."""
    j = request.get_json() or {}
    ids = j.get("personaggi", [])
    return jsonify(get_service().calcola_top_teams(ids))


# --- Dashboard ---
@app.route("/api/dashboard")
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

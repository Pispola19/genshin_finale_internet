"""API Flask per Genshin Manager Web - espone servizi Python."""
import os
import sys
from pathlib import Path

# Aggiungi project root al path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, request, jsonify, send_from_directory, redirect

app = Flask(__name__, static_folder=".", static_url_path="")
app.config["JSON_AS_ASCII"] = False
# Su Render impostare SECRET_KEY (es. generateValue nel blueprint).
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "solo-sviluppo-cambia-in-produzione")


@app.after_request
def _security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


SFONDI_DIR = ROOT / "sfondi"

# Inizializza servizi (lazy)
_service = None


def get_service():
    global _service
    if _service is None:
        from core.services import AppService
        _service = AppService()
    return _service


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


@app.route("/api/personaggio/<int:pk>", methods=["DELETE"])
def api_elimina_personaggio(pk):
    get_service().elimina_personaggio(pk)
    return jsonify({"ok": True})


@app.route("/api/personaggi/pulizia-test", methods=["POST"])
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


@app.route("/sfondi/<path:filename>")
def sfondi_static(filename):
    """Immagini di sfondo dalla cartella progetto sfondi/."""
    return send_from_directory(SFONDI_DIR, filename)


if __name__ == "__main__":
    app.run(debug=True, port=5001)

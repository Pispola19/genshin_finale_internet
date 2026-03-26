"""
Checkpoint dello stato moduli GUI principali (personaggio, arma, cost., talenti, equip).
File: accanto ai database (``checkpoint.json``). Ripristino all’avvio senza toccare il service layer.

I file illeggibili o non conformi vengono rimossi per evitare ripristini corrotti.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import DB_PATH, SLOT_DB, SLOT_UI

logger = logging.getLogger(__name__)

CHECKPOINT_VERSION = 1
CHECKPOINT_FILENAME = "checkpoint.json"

_MAX_LEN_NOME = 200
_MAX_LEN_LABEL = 600
_MAX_LEN_FIELD = 64
_TALENT_KEYS = frozenset(("aa", "skill", "burst", "pas1", "pas2", "pas3", "pas4"))
_COST_KEYS = frozenset(f"c{i}" for i in range(1, 7))


def checkpoint_path() -> Path:
    return DB_PATH.parent / CHECKPOINT_FILENAME


def _checkpoint_enabled() -> bool:
    v = (os.environ.get("GENSHIN_GUI_CHECKPOINT") or "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def _truncate_safe(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[:max_len]


def _delete_corrupt_checkpoint_files(path: Path) -> None:
    """Elimina checkpoint e residui .tmp così il prossimo avvio parte pulito."""
    for p in (path, path.with_suffix(".json.tmp")):
        try:
            if p.is_file():
                p.unlink()
                logger.warning("Checkpoint GUI rimosso (file non valido o corrotto): %s", p)
        except OSError as e:
            logger.error("Impossibile eliminare checkpoint corrotto %s: %s", p, e)


def validate_gui_checkpoint_state(state: dict) -> Tuple[bool, str]:
    """
    Verifica struttura e limiti prima di toccare i widget.
    Ritorna (ok, messaggio_diagnostica).
    """
    if not isinstance(state, dict):
        return False, "root non è un oggetto"
    ver = state.get("version")
    if ver != CHECKPOINT_VERSION:
        return False, f"versione attesa {CHECKPOINT_VERSION}, trovata {ver!r}"

    pg = state.get("personaggio")
    if not isinstance(pg, dict):
        return False, "personaggio mancante o non oggetto"
    nome = str(pg.get("nome", "") or "")
    if len(nome) > _MAX_LEN_NOME:
        return False, "nome troppo lungo"

    ar = state.get("arma")
    if not isinstance(ar, dict):
        return False, "arma non oggetto"

    cost = state.get("costellazioni")
    if not isinstance(cost, dict):
        return False, "costellazioni non oggetto"
    for k in cost:
        if k not in _COST_KEYS:
            return False, f"chiave costellazione sconosciuta {k!r}"
        v = cost[k]
        if str(v) not in ("0", "1"):
            return False, f"valore costellazione non valido {k}={v!r}"

    tal = state.get("talenti")
    if not isinstance(tal, dict):
        return False, "talenti non oggetto"
    for k in tal:
        if k not in _TALENT_KEYS:
            return False, f"chiave talento sconosciuta {k!r}"
        tv = str(tal[k] or "")
        if len(tv) > _MAX_LEN_FIELD:
            return False, "talento troppo lungo"

    equip = state.get("equipaggiamento")
    if not isinstance(equip, dict):
        return False, "equipaggiamento non oggetto"
    for k, v in equip.items():
        if k not in SLOT_DB:
            return False, f"slot equip sconosciuto {k!r}"
        if v is not None:
            if isinstance(v, bool):
                return False, "id artefatto booleano non ammesso"
            try:
                int(v)
            except (TypeError, ValueError):
                return False, f"id artefatto non numerico per {k}"

    lbls = state.get("artefatti_labels")
    if not isinstance(lbls, dict):
        return False, "artefatti_labels non oggetto"
    for k, v in lbls.items():
        if k not in SLOT_UI:
            return False, f"etichetta slot sconosciuta {k!r}"
        if len(str(v or "")) > _MAX_LEN_LABEL:
            return False, "etichetta artefatto troppo lunga"

    sid = state.get("selected_id")
    if sid is not None:
        try:
            int(sid)
        except (TypeError, ValueError):
            return False, "selected_id non numerico"

    for key in ("livello", "elemento", "hp_flat", "atk_flat", "def_flat", "em_flat", "cr", "cd", "er"):
        v = pg.get(key, "")
        if len(str(v)) > _MAX_LEN_FIELD:
            return False, f"campo personaggio troppo lungo: {key}"

    for key in ("nome", "tipo", "livello", "stelle", "atk_base", "stat_secondaria", "valore_stat"):
        v = ar.get(key, "")
        if len(str(v)) > _MAX_LEN_FIELD:
            return False, f"campo arma troppo lungo: {key}"

    return True, ""


def serialize_gui_state(app: Any) -> dict:
    """Cattura il form attuale (metodi già presenti su ``GenshinApp``)."""
    equip = app._form_equipaggiamento()
    equip_json: Dict[str, Any] = {}
    for k, v in equip.items():
        equip_json[k] = v if v is not None else None

    labels: Dict[str, str] = {}
    for slot_ui in SLOT_UI:
        w = app.artefatti_widgets.get(slot_ui)
        if w:
            try:
                raw = str(w["label_art"].cget("text") or "—")
                labels[slot_ui] = _truncate_safe(raw, _MAX_LEN_LABEL)
            except Exception:
                labels[slot_ui] = "—"

    return {
        "version": CHECKPOINT_VERSION,
        "selected_id": app.selected_id,
        "personaggio": app._form_personaggio(),
        "arma": app._form_arma(),
        "costellazioni": app._form_costellazioni(),
        "talenti": app._form_talenti(),
        "equipaggiamento": equip_json,
        "artefatti_labels": labels,
    }


def save_gui_checkpoint(app: Any) -> None:
    if not _checkpoint_enabled():
        return
    path = checkpoint_path()
    data = serialize_gui_state(app)
    ok, reason = validate_gui_checkpoint_state(data)
    if not ok:
        logger.error("Serializzazione checkpoint incoerente: %s", reason)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def save_gui_checkpoint_safe(app: Any) -> None:
    try:
        save_gui_checkpoint(app)
    except Exception:
        logger.exception("save_gui_checkpoint_safe")


def apply_gui_state(app: Any, state: dict) -> None:
    """Ripopola widget da dizionario (chiamare solo dopo ``validate_gui_checkpoint_state``)."""
    sid = state.get("selected_id")
    if sid is not None:
        try:
            app.selected_id = int(sid)
        except (TypeError, ValueError):
            app.selected_id = None
    else:
        app.selected_id = None

    pg = state.get("personaggio") or {}
    app.nome_var.set(str(pg.get("nome", "") or "")[:_MAX_LEN_NOME])
    app._set_entry(app.livello_entry, pg.get("livello", ""))
    app.elemento_var.set(str(pg.get("elemento", "") or "Pyro")[:_MAX_LEN_FIELD])
    vals = [
        pg.get("hp_flat", ""),
        pg.get("atk_flat", ""),
        pg.get("def_flat", ""),
        pg.get("em_flat", ""),
        pg.get("cr", ""),
        pg.get("cd", ""),
        pg.get("er", ""),
    ]
    for e, v in zip(app._personaggio_entries, vals):
        app._set_entry(e, str(v)[:_MAX_LEN_FIELD])

    ar = state.get("arma") or {}
    app._set_entry(app.arma_nome_entry, str(ar.get("nome", ""))[:_MAX_LEN_NOME])
    app.tipo_var.set(str(ar.get("tipo", "") or "Spada")[:_MAX_LEN_FIELD])
    app._set_entry(app.arma_liv_entry, ar.get("livello", ""))
    app._set_entry(app.arma_stelle_entry, ar.get("stelle", ""))
    app._set_entry(app.arma_atk_entry, ar.get("atk_base", ""))
    app.arma_stat_var.set(str(ar.get("stat_secondaria", "") or "")[:_MAX_LEN_FIELD])
    app._set_entry(app.arma_val_entry, ar.get("valore_stat", ""))

    cost = state.get("costellazioni") or {}
    for i, cb in enumerate(app.cost_entries):
        key = f"c{i + 1}"
        v = cost.get(key, "0")
        cb.set("1" if str(v) == "1" else "0")

    tal = state.get("talenti") or {}
    keys: List[str] = ["aa", "skill", "burst", "pas1", "pas2", "pas3", "pas4"]
    for i, k in enumerate(keys):
        if i < len(app.talenti_entries):
            app._set_entry(app.talenti_entries[i], str(tal.get(k, "-"))[:_MAX_LEN_FIELD])

    equip = state.get("equipaggiamento") or {}
    lbls = state.get("artefatti_labels") or {}
    for slot_ui, slot_db in app.slot_map.items():
        w = app.artefatti_widgets[slot_ui]
        aid = equip.get(slot_db)
        if aid is not None:
            try:
                aid = int(aid)
            except (TypeError, ValueError):
                aid = None
        w["artefatto_id"] = aid
        w["label_art"].config(
            text=_truncate_safe(str(lbls.get(slot_ui, "—") or "—"), _MAX_LEN_LABEL)
        )


def load_and_apply_gui_checkpoint(app: Any) -> bool:
    if not _checkpoint_enabled():
        return False
    path = checkpoint_path()
    if not path.is_file():
        return False
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        logger.exception("load gui checkpoint read")
        _delete_corrupt_checkpoint_files(path)
        return False
    if not isinstance(state, dict):
        _delete_corrupt_checkpoint_files(path)
        return False

    ok, reason = validate_gui_checkpoint_state(state)
    if not ok:
        logger.warning("Checkpoint GUI non valido (%s), file eliminato.", reason)
        _delete_corrupt_checkpoint_files(path)
        return False

    try:
        apply_gui_state(app, state)
    except Exception:
        logger.exception("load gui checkpoint apply")
        _delete_corrupt_checkpoint_files(path)
        return False
    try:
        nomi = app.service.nomi_per_autocomplete()
        app.nome_combo["values"] = nomi
        app.nome_combo._values = nomi
    except Exception:
        logger.exception("refresh autocomplete after checkpoint")
    return True


def mark_gui_checkpoint_dirty(app: Any, delay_ms: int = 1600) -> None:
    """Debounced save (evita scrivere ad ogni tasto)."""
    if not _checkpoint_enabled():
        return
    job_id = getattr(app, "_gui_checkpoint_after_id", None)
    if job_id is not None:
        try:
            app.root.after_cancel(job_id)
        except Exception:
            pass

    def _flush() -> None:
        app._gui_checkpoint_after_id = None
        save_gui_checkpoint_safe(app)

    app._gui_checkpoint_after_id = app.root.after(delay_ms, _flush)

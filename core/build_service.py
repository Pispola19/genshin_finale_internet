"""
BuildService - logica analisi build attuale vs ottimale.
Tutta la business logic per /api/build passa da qui.
API → Service → Repository (mai salti).
"""
from typing import Optional, List, Dict, Any

from core.dps import DpsCalculator
from core.dps_types import build_full_combat_view
from config import SLOT_DB

_SLOT_LABEL_IT = {
    "fiore": "Fiore",
    "piuma": "Piuma",
    "sabbie": "Sabbie",
    "calice": "Calice",
    "corona": "Corona",
}


def _bonus_set_linee(set_counts: Dict[str, int]) -> List[str]:
    """Testi italiani su 2p/4p in base al conteggio pezzi per set."""
    linee = []
    for nome in sorted(set_counts.keys(), key=lambda x: (-set_counts[x], x.lower())):
        n = set_counts[nome]
        if not (nome or "").strip() or nome.strip() == "—":
            continue
        if n >= 4:
            linee.append(
                f"{nome}: {n} pezzi — bonus 4 pezzi del set attivo. "
                "Il «Proxy danno» sotto include un moltiplicatore 4p semplificato; in gioco i numeri reali possono differire."
            )
        elif n == 3:
            linee.append(
                f"{nome}: 3 pezzi — bonus 2 pezzi attivo; manca 1 pezzo per il bonus 4 pezzi."
            )
        elif n == 2:
            linee.append(
                f"{nome}: 2 pezzi — bonus 2 pezzi del set attivo. "
                "Il proxy danno applica un bonus 2p semplificato."
            )
        else:
            linee.append(
                f"{nome}: 1 pezzo — nessun bonus di set (servono almeno 2 pezzi dello stesso set)."
            )
    if not linee:
        return ["Nessun set conteggiato (slot vuoti o nome set mancante sui manufatti)."]
    return linee


def _riepilogo_build_slots(slot_to_art: Dict[str, Any]) -> dict:
    """
    slot_to_art: chiavi come SLOT_DB, valore dict artefatto completo o None.
    """
    slots_detail = []
    set_counts: Dict[str, int] = {}
    for slot in SLOT_DB:
        a = slot_to_art.get(slot)
        slabel = _SLOT_LABEL_IT.get(slot, slot)
        if not a:
            slots_detail.append({"slot": slabel, "slot_key": slot, "vuoto": True})
            continue
        sn = (a.get("set_nome") or "").strip() or "—"
        name = (a.get("nome") or "").strip() or "—"
        main = (a.get("main_stat") or "").strip() or "—"
        mv = a.get("main_val")
        try:
            mv_num = float(mv) if mv is not None and str(mv).strip() != "" else None
        except (TypeError, ValueError):
            mv_num = None
        if sn and sn != "—":
            set_counts[sn] = set_counts.get(sn, 0) + 1
        aid = a.get("id")
        slots_detail.append(
            {
                "slot": slabel,
                "slot_key": slot,
                "vuoto": False,
                "artefatto_id": int(aid) if aid is not None else None,
                "set": sn,
                "nome": name,
                "main": main,
                "main_val": mv_num,
            }
        )
    return {
        "slots": slots_detail,
        "conteggio_set": set_counts,
        "bonus_set": _bonus_set_linee(set_counts),
    }


def _sf(val) -> float:
    try:
        if val is None or (isinstance(val, str) and not str(val).strip()):
            return 0.0
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _somma_stats(artefatti: List[dict]) -> dict:
    """Aggrega ATK, CR, CD, ER, EM da lista artefatti."""
    atk, cr, cd, er, em = 0, 0, 0, 0, 0
    for a in artefatti:
        if not a:
            continue
        m = (a.get("main_stat") or "").upper()
        v = _sf(a.get("main_val"))
        # ATK% non è flat (allineato a combat_stats_from_artefatto_dict)
        if "ATK" in m and "%" not in m:
            atk += v
        elif "CR" in m or "CRIT RATE" in m:
            cr += v
        elif "CD" in m or "CRIT DMG" in m:
            cd += v
        elif "ER" in m:
            er += v
        elif "EM" in m:
            em += v
        for i in range(1, 5):
            s = (a.get(f"sub{i}_stat") or "").upper()
            val = _sf(a.get(f"sub{i}_val"))
            if "ATK" in s and "%" not in s:
                atk += val
            elif "CR" in s or "CRIT RATE" in s:
                cr += val
            elif "CD" in s or "CRIT DMG" in s:
                cd += val
            elif "ER" in s:
                er += val
            elif "EM" in s:
                em += val
    return {"atk": round(atk, 1), "cr": round(cr, 1), "cd": round(cd, 1), "er": round(er, 1), "em": round(em, 1)}


def _confronto_slot_attuale_ottimale(riep_curr: dict, riep_opt: dict) -> dict:
    """Per ogni slot: stesso pezzo o cambio (per UX confronto)."""
    by_curr = {s["slot_key"]: s for s in riep_curr.get("slots", []) if s.get("slot_key")}
    by_opt = {s["slot_key"]: s for s in riep_opt.get("slots", []) if s.get("slot_key")}
    out = []
    n_chg = 0
    for sk in SLOT_DB:
        c = by_curr.get(sk, {"slot_key": sk, "vuoto": True})
        o = by_opt.get(sk, {"slot_key": sk, "vuoto": True})
        vc, vo = bool(c.get("vuoto")), bool(o.get("vuoto"))
        idc, ido = c.get("artefatto_id"), o.get("artefatto_id")
        changed = False
        motivo = ""
        if vc != vo:
            changed = True
            motivo = "Vuoto ↔ equipaggiato"
        elif not vc and not vo:
            if idc is not None and ido is not None and idc != ido:
                changed = True
                motivo = "Manufatto diverso"
            else:
                fc = (c.get("set"), c.get("nome"), c.get("main"), c.get("main_val"))
                fo = (o.get("set"), o.get("nome"), o.get("main"), o.get("main_val"))
                if fc != fo:
                    changed = True
                    motivo = "Dettagli pezzo diversi"
        if changed:
            n_chg += 1
        out.append(
            {
                "slot_key": sk,
                "slot_label": _SLOT_LABEL_IT.get(sk, sk),
                "cambiato": changed,
                "motivo": motivo,
            }
        )
    return {"slots": out, "num_slot_cambiati": n_chg}


class BuildService:
    """Analisi build: attuale vs ottimale."""

    def __init__(self, personaggio_service, artefatto_service):
        self._pg = personaggio_service
        self._art = artefatto_service

    def analisi_build(self, personaggio_id: int) -> Optional[dict]:
        """
        Build attuale + ottimale per personaggio.
        Ritorna None se personaggio non esiste.
        """
        pg = self._pg.get_personaggio(personaggio_id)
        if not pg:
            return None

        eq_ids = self._pg.get_equipaggiamento_ids(personaggio_id)
        artefatti_attuali = [
            self._art.get_artefatto(aid)
            for slot, aid in eq_ids.items()
            if aid
        ]
        artefatti_attuali = [a for a in artefatti_attuali if a]

        stats_attuali = _somma_stats(artefatti_attuali)
        score_attuale = sum(
            DpsCalculator.score_artefatto_per_personaggio(a, pg)[0] for a in artefatti_attuali
        )

        ottimali = []
        for slot in SLOT_DB:
            liberi = self._art.lista_artefatti_liberi_completi(slot)
            if not liberi:
                continue
            migliore = max(
                liberi,
                key=lambda a, p=pg: DpsCalculator.score_artefatto_per_personaggio(a, p)[0],
            )
            ottimali.append(migliore)

        stats_ottimali = _somma_stats(ottimali)
        score_ottimale = sum(DpsCalculator.score_artefatto_per_personaggio(a, pg)[0] for a in ottimali)

        dps_attuale = round(score_attuale * 10, 0)
        dps_ottimale = round(score_ottimale * 10, 0)
        diff_dps = round(dps_ottimale - dps_attuale, 0)

        artefatti_tabella = self._art.lista_artefatti_inventario_per_tabella()

        slot_curr: Dict[str, Any] = {}
        for slot in SLOT_DB:
            aid = eq_ids.get(slot)
            slot_curr[slot] = self._art.get_artefatto(aid) if aid else None

        opt_by_slot: Dict[str, Any] = {}
        for a in ottimali:
            sl = a.get("slot")
            if sl:
                opt_by_slot[sl] = a
        slot_opt = {s: opt_by_slot.get(s) for s in SLOT_DB}

        riepilogo_attuale = _riepilogo_build_slots(slot_curr)
        riepilogo_ottimale = _riepilogo_build_slots(slot_opt)

        arma = self._pg.get_arma(personaggio_id)
        combat_att = build_full_combat_view(pg, arma, artefatti_attuali)
        combat_opt = build_full_combat_view(pg, arma, ottimali)

        confronto_slot = _confronto_slot_attuale_ottimale(riepilogo_attuale, riepilogo_ottimale)

        return {
            "personaggio": {"id": pg.id, "nome": pg.nome, "elemento": pg.elemento},
            "build_attuale": {
                **stats_attuali,
                "dps": dps_attuale,
                "artefatti": artefatti_attuali,
                "riepilogo": riepilogo_attuale,
                "damage_proxy": combat_att.damage_proxy,
            },
            "build_ottimale": {
                **stats_ottimali,
                "dps": dps_ottimale,
                "artefatti": ottimali,
                "riepilogo": riepilogo_ottimale,
                "damage_proxy": combat_opt.damage_proxy,
            },
            "combat_build": {
                "attuale": combat_att.to_dict(),
                "ottimale": combat_opt.to_dict(),
            },
            "dps_model_note_it": (
                "DPS mostrato = somma score manufatti contestualizzati (elemento, EM, CR) ×10. "
                "Proxy danno = foglio + arma + manufatti + moltiplicatori 2p/4p semplificati (combat_build)."
            ),
            "differenza": {
                "dps": diff_dps,
                "damage_proxy": round(combat_opt.damage_proxy - combat_att.damage_proxy, 1),
                "atk": round(stats_ottimali["atk"] - stats_attuali["atk"], 1),
                "cr": stats_ottimali["cr"] - stats_attuali["cr"],
                "cd": stats_ottimali["cd"] - stats_attuali["cd"],
                "er": round(stats_ottimali["er"] - stats_attuali["er"], 1),
                "em": round(stats_ottimali["em"] - stats_attuali["em"], 1),
            },
            "confronto": {
                "slot": confronto_slot,
                "set_proxy": {
                    "attuale": {
                        "moltiplicatore": combat_att.set_bonus_multiplier,
                        "linee": combat_att.set_bonus_lines,
                    },
                    "ottimale": {
                        "moltiplicatore": combat_opt.set_bonus_multiplier,
                        "linee": combat_opt.set_bonus_lines,
                    },
                    "delta_moltiplicatore": round(
                        combat_opt.set_bonus_multiplier - combat_att.set_bonus_multiplier, 4
                    ),
                },
            },
            "artefatti_disponibili": artefatti_tabella,
        }

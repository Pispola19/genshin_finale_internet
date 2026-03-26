/**
 * Magazzino manufatti — API path /api/artefatti (invariato).
 */
function apiBase() {
  const m = document.querySelector('meta[name="api-base"]');
  const b = (m && m.content && m.content.trim()) || "/api";
  return b.replace(/\/$/, "");
}
const API = apiBase();

const EQUIP_SLOTS = [
  { k: "fiore", label: "Fiore" },
  { k: "piuma", label: "Piuma" },
  { k: "sabbie", label: "Sabbie" },
  { k: "calice", label: "Calice" },
  { k: "corona", label: "Corona" },
];

/** Personaggio selezionato nel pannello Equip */
let equipPgId = null;
/** ID equipaggiato per slot (per «libera») */
const equipSlotCurrentId = {};

const COL_TAB_MAGAZZINO = 9;

/** Righe messaggio tabella magazzino (testo unificato, niente duplicati sparsi). */
function trMagazzinoMsg(htmlInner) {
  return `<tr><td colspan="${COL_TAB_MAGAZZINO}" class="td-magazzino-vuoto">${htmlInner}</td></tr>`;
}

const MSG_MAG_DB_VUOTO =
  "Nessun manufatto in elenco. Modulo <strong>Aggiungi o modifica</strong>: <strong>AGGIUNGI</strong>; riga → <strong>Carica nel modulo</strong> per modifiche e assegnazione.";
const MSG_MAG_FILTRI_VUOTI =
  "Nessun pezzo con questi filtri. Cambia criteri o <strong>Reset</strong> filtri.";

let catalogo = { set: [], main_stats: [], stats_subs: [] };
/** Modifica nel modulo unificato: null = nuovo pezzo. */
let editingId = null;
let editingAssigned = false;

async function populatePersonaggiSelect(sel, emptyLabel, emptyValue = "") {
  if (!sel) return;
  try {
    const r = await fetch(`${API}/personaggi`);
    const list = await r.json();
    sel.replaceChildren();
    const o0 = document.createElement("option");
    o0.value = emptyValue;
    o0.textContent = emptyLabel;
    sel.appendChild(o0);
    for (const p of Array.isArray(list) ? list : []) {
      const o = document.createElement("option");
      o.value = String(p.id);
      o.textContent = p.nome || `ID ${p.id}`;
      sel.appendChild(o);
    }
  } catch (e) {
    console.warn("Lista personaggi:", e);
  }
}

async function loadPersonaggiPerForm() {
  await populatePersonaggiSelect(
    document.getElementById("assegn_a_personaggio"),
    "— Solo magazzino (libero) —",
    ""
  );
}

async function loadEquipPersonaggiSelect() {
  await populatePersonaggiSelect(
    document.getElementById("equipPersonaggio"),
    "— Scegli personaggio —",
    ""
  );
}

function buildEquipGridHtml() {
  const grid = document.getElementById("equipSlotsGrid");
  if (!grid || grid.dataset.built === "1") return;
  grid.dataset.built = "1";
  grid.replaceChildren();
  for (const { k, label } of EQUIP_SLOTS) {
    const art = document.createElement("article");
    art.className = "equip-slot-card";
    art.dataset.slot = k;
    art.innerHTML = `
      <h3 class="equip-slot-title">${label}</h3>
      <div class="equip-slot-current" id="equipCur_${k}"><span class="equip-empty">—</span></div>
      <label class="equip-pick-label" for="equipPick_${k}">Sostituisci con</label>
      <select id="equipPick_${k}" class="equip-pick-select inv-set-select" aria-label="Pezzo per slot ${label}"></select>
      <button type="button" class="btn btn-primary equip-apply-btn" data-equip-slot="${k}">Applica slot</button>
    `;
    grid.appendChild(art);
  }
}

function formatEquipCurrentSummary(info) {
  if (!info || info.id == null || info.id === "") {
    return '<span class="equip-empty">Slot vuoto (magazzino)</span>';
  }
  const set = escapeHtml(info.set || "—");
  const nome = info.nome ? escapeHtml(String(info.nome)) : "";
  const mainLine = [info.main_stat, info.main_val != null && info.main_val !== "" ? info.main_val : ""]
    .filter(Boolean)
    .join(" ");
  const mainEsc = escapeHtml(mainLine || "—");
  const lv = info.livello != null && info.livello !== "" ? escapeHtml(info.livello) : "—";
  const st = info.stelle != null && info.stelle !== "" ? escapeHtml(info.stelle) : "—";
  return (
    `<div class="equip-cur-inner">` +
    `<strong class="equip-cur-set">${set}</strong>` +
    (nome ? `<span>${nome}</span>` : "") +
    `<span class="equip-cur-main">${mainEsc}</span>` +
    `<span class="equip-cur-id">#${escapeHtml(info.id)} · Lv.${lv} ★${st}</span>` +
    `</div>`
  );
}

async function populateEquipPickSelect(slot, personaggioId, currentInfo) {
  const sel = document.getElementById(`equipPick_${slot}`);
  if (!sel) return;
  sel.replaceChildren();
  const oKeep = document.createElement("option");
  oKeep.value = "__keep__";
  oKeep.textContent = "— Nessun cambio —";
  sel.appendChild(oKeep);
  if (currentInfo && currentInfo.id != null && currentInfo.id !== "") {
    const oClear = document.createElement("option");
    oClear.value = "__clear__";
    oClear.textContent = "Libera slot (magazzino)";
    sel.appendChild(oClear);
  }
  try {
    const r = await fetch(
      `${API}/artefatti/per-equip?slot=${encodeURIComponent(slot)}&personaggio_id=${encodeURIComponent(String(personaggioId))}`
    );
    let opts = [];
    try {
      opts = await r.json();
    } catch {
      opts = [];
    }
    if (!Array.isArray(opts)) opts = [];
    const seen = new Set();
    for (const op of opts) {
      if (!op || op.id == null) continue;
      const idn = Number(op.id);
      if (seen.has(idn)) continue;
      seen.add(idn);
      const o = document.createElement("option");
      o.value = String(op.id);
      o.textContent =
        op.label || `#${op.id} ${op.set || ""} ${op.main_stat || ""}`.trim() || `#${op.id}`;
      sel.appendChild(o);
    }
  } catch (e) {
    console.warn("per-equip", slot, e);
  }
}

async function refreshEquipPanel() {
  const selPg = document.getElementById("equipPersonaggio");
  const raw = selPg && selPg.value ? String(selPg.value).trim() : "";
  const pgId = raw ? parseInt(raw, 10) : NaN;
  equipPgId = Number.isFinite(pgId) ? pgId : null;

  for (const { k } of EQUIP_SLOTS) {
    equipSlotCurrentId[k] = null;
    const curEl = document.getElementById(`equipCur_${k}`);
    const pickEl = document.getElementById(`equipPick_${k}`);
    if (curEl) curEl.innerHTML = '<span class="equip-empty">—</span>';
    if (pickEl) {
      pickEl.replaceChildren();
      const ph = document.createElement("option");
      ph.value = "__keep__";
      ph.textContent = equipPgId ? "— Caricamento… —" : "— Scegli personaggio —";
      pickEl.appendChild(ph);
    }
  }

  if (!equipPgId) return;

  let d;
  try {
    const r = await fetch(`${API}/personaggio/${equipPgId}`);
    if (!r.ok) throw new Error("personaggio");
    d = await r.json();
  } catch (e) {
    console.warn("refreshEquipPanel", e);
    return;
  }

  for (const { k } of EQUIP_SLOTS) {
    const info = d.artefatti && d.artefatti[k];
    const curEl = document.getElementById(`equipCur_${k}`);
    if (curEl) curEl.innerHTML = formatEquipCurrentSummary(info);
    equipSlotCurrentId[k] = info && info.id != null && info.id !== "" ? Number(info.id) : null;
    await populateEquipPickSelect(k, equipPgId, info);
  }
}

async function applyEquipSlot(slot) {
  const pickEl = document.getElementById(`equipPick_${slot}`);
  if (!pickEl) return;
  const v = pickEl.value;
  if (v === "__keep__") {
    alert("Scegli un pezzo dal menu oppure «Libera slot».");
    return;
  }
  if (!equipPgId) {
    alert("Scegli un personaggio.");
    return;
  }
  try {
    if (v === "__clear__") {
      const cur = equipSlotCurrentId[slot];
      if (!cur) return;
      const r = await fetch(`${API}/artefatti/${cur}/utilizzatore`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ personaggio_id: null }),
      });
      let res = {};
      try {
        res = await r.json();
      } catch {
        /* ignore */
      }
      if (!r.ok || res.error) {
        alert("Errore: " + (res.error || r.status));
        return;
      }
    } else {
      const aid = parseInt(v, 10);
      if (!aid) return;
      const r = await fetch(`${API}/artefatti/${aid}/utilizzatore`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ personaggio_id: equipPgId }),
      });
      let res = {};
      try {
        res = await r.json();
      } catch {
        /* ignore */
      }
      if (!r.ok || res.error) {
        alert("Errore: " + (res.error || r.status));
        return;
      }
    }
    await loadMagazzino();
    await refreshEquipPanel();
  } catch (e) {
    alert("Errore: " + (e && e.message ? e.message : e));
  }
}

function maybeRefreshEquipIfVisible() {
  const pe = document.getElementById("invPanelEquip");
  if (pe && !pe.hidden) void refreshEquipPanel();
}

function wireInvTabs() {
  const ta = document.getElementById("invTabArchivio");
  const te = document.getElementById("invTabEquip");
  const pa = document.getElementById("invPanelArchivio");
  const pe = document.getElementById("invPanelEquip");
  if (!ta || !te || !pa || !pe) return;

  function focusTab(activeBtn, otherBtn) {
    activeBtn.classList.add("is-active");
    otherBtn.classList.remove("is-active");
    activeBtn.setAttribute("aria-selected", "true");
    otherBtn.setAttribute("aria-selected", "false");
    activeBtn.setAttribute("tabindex", "0");
    otherBtn.setAttribute("tabindex", "-1");
  }

  ta.addEventListener("click", () => {
    focusTab(ta, te);
    pa.hidden = false;
    pe.hidden = true;
  });
  te.addEventListener("click", () => {
    focusTab(te, ta);
    pa.hidden = true;
    pe.hidden = false;
    void refreshEquipPanel();
  });
}

function wireEquipPanel() {
  document.getElementById("equipPersonaggio")?.addEventListener("change", () => void refreshEquipPanel());
  document.getElementById("btnEquipRefresh")?.addEventListener("click", () => void refreshEquipPanel());
  document.getElementById("equipSlotsGrid")?.addEventListener("click", e => {
    const btn = e.target.closest(".equip-apply-btn");
    if (!btn) return;
    const slot = btn.getAttribute("data-equip-slot");
    if (slot) void applyEquipSlot(slot);
  });
}

function appOpenHint() {
  try {
    const o = window.location.origin;
    if (o && /^https?:\/\//i.test(o)) return o;
  } catch (_) {
    /* ignore */
  }
  return "";
}

function jsonServerHintArtefatti() {
  const o = appOpenHint();
  return o
    ? `Il server non ha restituito JSON. Avvia python3 run_web.py e apri ${o}/artefatti.html (non il file dal disco).`
    : "Il server non ha restituito JSON. Avvia python3 run_web.py e apri la pagina dall’URL del server.";
}

function escapeHtml(s) {
  if (s == null || s === "") return "—";
  const t = String(s);
  return t
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;");
}

function fillSelect(sel, items, emptyLabel) {
  if (!sel) return;
  sel.replaceChildren();
  const o0 = document.createElement("option");
  o0.value = "";
  o0.textContent = emptyLabel;
  sel.appendChild(o0);
  for (const text of items || []) {
    const o = document.createElement("option");
    o.value = text;
    o.textContent = text;
    sel.appendChild(o);
  }
}

function toggleCustomNome(show) {
  const w = document.getElementById("nome_custom_wrap");
  if (w) w.hidden = !show;
}

/** Set effettivo: campo «Set libero» ha priorità sul menu catalogo. */
function resolveSetNome() {
  const customEl = document.getElementById("set_nome_custom");
  const custom = customEl && customEl.value ? String(customEl.value).trim() : "";
  if (custom) return custom;
  const sel = document.getElementById("set_nome");
  return sel && sel.value ? String(sel.value).trim() : "";
}

function fillNomePezzoOptions(pezzi) {
  const sel = document.getElementById("nome_pezzo");
  if (!sel) return;
  sel.replaceChildren();
  const ph = document.createElement("option");
  ph.value = "";
  ph.textContent = pezzi.length ? "— Scegli pezzo —" : "— Nessun nome in catalogo —";
  sel.appendChild(ph);
  for (const text of pezzi) {
    const o = document.createElement("option");
    o.value = text;
    o.textContent = text;
    sel.appendChild(o);
  }
  const oc = document.createElement("option");
  oc.value = "__custom__";
  oc.textContent = "Altro (scrivi sotto)";
  sel.appendChild(oc);
  if (pezzi.length === 1) {
    sel.value = pezzi[0];
    toggleCustomNome(false);
    const c = document.getElementById("nome_custom");
    if (c) c.value = "";
  } else {
    toggleCustomNome(pezzi.length === 0);
  }
}

async function refreshPezzoSelect() {
  const setSel = document.getElementById("set_nome");
  const slotEl = document.getElementById("slot");
  const selPezzo = document.getElementById("nome_pezzo");
  if (!setSel || !slotEl || !selPezzo) return;
  const setNome = resolveSetNome();
  if (!setNome) {
    selPezzo.replaceChildren();
    const ph = document.createElement("option");
    ph.value = "";
    ph.textContent = "— Scegli prima il set —";
    selPezzo.appendChild(ph);
    toggleCustomNome(false);
    const c = document.getElementById("nome_custom");
    if (c) c.value = "";
    return;
  }
  try {
    const r = await fetch(
      `${API}/artefatti/catalogo-pezzo?slot=${encodeURIComponent(slotEl.value)}&set=${encodeURIComponent(setNome)}`
    );
    const j = await r.json();
    const pezzi = Array.isArray(j.pezzi) ? j.pezzi : [];
    fillNomePezzoOptions(pezzi);
  } catch {
    fillNomePezzoOptions([]);
  }
}

function resolveNomePezzo() {
  const pezzoSel = document.getElementById("nome_pezzo");
  const custom = document.getElementById("nome_custom");
  if (!pezzoSel) return "";
  const v = pezzoSel.value;
  if (v === "__custom__") return custom && custom.value ? custom.value.trim() : "";
  if (v) return v.trim();
  return custom && custom.value ? custom.value.trim() : "";
}

async function loadCatalogo(slot) {
  try {
    const r = await fetch(`${API}/artefatti/catalogo?slot=${encodeURIComponent(slot)}`);
    const raw = await r.text();
    let j;
    try {
      j = JSON.parse(raw);
    } catch {
      console.warn("Catalogo: risposta non JSON");
      return;
    }
    if (!r.ok || !j || typeof j !== "object") {
      if (j && j.error) console.warn("Catalogo:", j.error);
      return;
    }
    catalogo = j;
    const setSel = document.getElementById("set_nome");
    const mainSel = document.getElementById("main_stat");
    if (!setSel || !mainSel) return;
    const prevSet = setSel.value;
    fillSelect(setSel, catalogo.set || [], "— Scegli set —");
    if (prevSet) {
      for (const o of setSel.options) {
        if (o.value === prevSet) {
          setSel.value = prevSet;
          break;
        }
      }
    }
    fillSelect(mainSel, catalogo.main_stats || [], "—");
    document.querySelectorAll(".sub_stat").forEach(sel => {
      fillSelect(sel, catalogo.stats_subs || [], "—");
    });
    await refreshPezzoSelect();
  } catch (e) {
    console.warn("Catalogo artefatti:", e);
  }
}

function setSelectValue(sel, val) {
  if (!sel) return;
  const v = val == null ? "" : String(val);
  sel.value = v;
  if (v && sel.value !== v) {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = v;
    sel.appendChild(o);
    sel.value = v;
  }
}

function updateFormEditUI() {
  const banner = document.getElementById("formModuloBanner");
  const spanId = document.getElementById("formModuloId");
  const slotHint = document.getElementById("slotLockedHint");
  const btnMain = document.getElementById("btnAggiungi");
  const btnAnnulla = document.getElementById("btnAnnullaForm");
  const btnElimina = document.getElementById("btnEliminaForm");
  const slotEl = document.getElementById("slot");
  if (!btnMain) return;
  if (!editingId) {
    if (banner) banner.hidden = true;
    if (spanId) spanId.textContent = "";
    btnMain.textContent = "AGGIUNGI";
    if (btnAnnulla) btnAnnulla.hidden = true;
    if (btnElimina) btnElimina.hidden = true;
    if (slotEl) slotEl.disabled = false;
    if (slotHint) slotHint.hidden = true;
    return;
  }
  if (banner) banner.hidden = false;
  if (spanId) spanId.textContent = String(editingId);
  btnMain.textContent = "SALVA MODIFICHE";
  if (btnAnnulla) btnAnnulla.hidden = false;
  if (btnElimina) btnElimina.hidden = false;
  if (slotEl) slotEl.disabled = editingAssigned;
  if (slotHint) slotHint.hidden = !editingAssigned;
}

function resetForm() {
  editingId = null;
  editingAssigned = false;
  updateFormEditUI();
  document.getElementById("livello").value = "20";
  document.getElementById("stelle").value = "5";
  document.getElementById("main_val").value = "";
  document.getElementById("slot").value = "fiore";
  document.getElementById("set_nome").value = "";
  const setLib = document.getElementById("set_nome_custom");
  if (setLib) setLib.value = "";
  document.getElementById("nome_custom").value = "";
  document.getElementById("assegn_a_personaggio").value = "";
  toggleCustomNome(false);
  document.querySelectorAll(".sub_val").forEach(el => {
    el.value = "";
  });
  void loadCatalogo("fiore");
}

async function caricaNelModulo(aid) {
  modalInfoClose();
  await loadPersonaggiPerForm();
  const r = await fetch(`${API}/artefatti/${aid}`);
  const d = await r.json();
  if (!r.ok) {
    alert(d.error || "Errore");
    return;
  }
  editingId = aid;
  editingAssigned = !!d.personaggio_id;
  updateFormEditUI();
  const slot = d.slot || "fiore";
  document.getElementById("slot").value = slot;
  await loadCatalogo(slot);
  const rawSet = (d.set_nome || "").trim();
  const setSel = document.getElementById("set_nome");
  const setLib = document.getElementById("set_nome_custom");
  if (setLib) setLib.value = "";
  let inCatalog = false;
  if (setSel && rawSet) {
    for (const o of setSel.options) {
      if (o.value === rawSet) {
        setSel.value = rawSet;
        inCatalog = true;
        break;
      }
    }
  }
  if (!inCatalog && rawSet) {
    if (setSel) setSel.value = "";
    if (setLib) setLib.value = rawSet;
  } else if (setSel && !rawSet) {
    setSel.value = "";
  }
  await refreshPezzoSelect();
  const nomeSel = document.getElementById("nome_pezzo");
  const nomeVal = (d.nome || "").trim();
  let found = false;
  if (nomeSel) {
    for (const o of nomeSel.options) {
      if (o.value === nomeVal) {
        nomeSel.value = nomeVal;
        found = true;
        break;
      }
    }
    if (!found && nomeVal) {
      nomeSel.value = "__custom__";
      const c = document.getElementById("nome_custom");
      if (c) c.value = nomeVal;
      toggleCustomNome(true);
    } else {
      toggleCustomNome(false);
      const c = document.getElementById("nome_custom");
      if (c) c.value = "";
    }
  }
  setSelectValue(document.getElementById("main_stat"), d.main_stat);
  document.getElementById("main_val").value = d.main_val != null && d.main_val !== "" ? d.main_val : "";
  document.getElementById("livello").value = d.livello != null ? d.livello : 20;
  document.getElementById("stelle").value = d.stelle != null ? d.stelle : 5;
  const subStats = document.querySelectorAll(".sub_stat");
  const subVals = document.querySelectorAll(".sub_val");
  for (let i = 1; i <= 4; i++) {
    if (subStats[i - 1]) setSelectValue(subStats[i - 1], d[`sub${i}_stat`]);
    const vi = d[`sub${i}_val`];
    if (subVals[i - 1]) subVals[i - 1].value = vi != null && vi !== "" ? vi : "";
  }
  const pgSel = document.getElementById("assegn_a_personaggio");
  if (pgSel) pgSel.value = d.personaggio_id ? String(d.personaggio_id) : "";
  document.getElementById("section-form-manufatto")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

/** Dati grezzi ultimo GET /artefatti (filtri lato client). */
let magazzinoRows = [];

function buildRowHtml(a) {
  const subStr =
    (a.subs || [])
      .map(s => `${escapeHtml(s.stat)} ${s.val != null ? escapeHtml(s.val) : ""}`)
      .filter(Boolean)
      .join(", ") || "—";
  const util = a.utilizzatore ? escapeHtml(a.utilizzatore) : '<span style="color:#94a3b8">Magazzino</span>';
  const actions = `<button type="button" class="btn btn-secondary btn-carica-modulo" data-aid="${a.id}" style="padding:0.28rem 0.6rem;font-size:0.82rem;white-space:nowrap">Carica nel modulo</button>`;
  return `<tr class="row-manufatto" data-aid="${a.id}" tabindex="0" title="Carica nel modulo per modificare sopra; clic sulla riga per suggerimenti">
    <td>${escapeHtml(a.id)}</td><td>${escapeHtml(a.slot)}</td><td>${escapeHtml(a.set)}</td><td>${escapeHtml(a.nome)}</td>
    <td>${escapeHtml(a.main)}</td><td>${escapeHtml(a.main_val)}</td><td>${util}</td><td>${subStr}</td>
    <td class="magazzino-azioni" data-stop-row-click="1">${actions}</td></tr>`;
}

function rowContainsStatToken(a, token) {
  const t = (token || "").trim().toLowerCase();
  if (!t) return true;
  const main = String(a.main || "").toLowerCase();
  if (main.includes(t)) return true;
  for (const s of a.subs || []) {
    if (String(s.stat || "").toLowerCase().includes(t)) return true;
  }
  return false;
}

function rowMatchesTextBlob(a, q) {
  const t = (q || "").trim().toLowerCase();
  if (!t) return true;
  const parts = [a.id, a.slot, a.set, a.nome, a.main, a.main_val, a.utilizzatore];
  for (const s of a.subs || []) {
    parts.push(s.stat, s.val);
  }
  return parts.join(" ").toLowerCase().includes(t);
}

function rowMatchesFiltri(a) {
  const slotF = (document.getElementById("filtro_slot")?.value || "").trim();
  if (slotF && (a.slot || "") !== slotF) return false;
  const setF = (document.getElementById("filtro_set")?.value || "").trim().toLowerCase();
  if (setF && !String(a.set || "").toLowerCase().includes(setF)) return false;
  const mainF = (document.getElementById("filtro_main")?.value || "").trim();
  if (mainF && (a.main || "") !== mainF) return false;
  const statRaw = document.getElementById("filtro_stat_tokens")?.value || "";
  const tokens = statRaw.split(/[,;]/).map(s => s.trim().toLowerCase()).filter(Boolean);
  for (const tok of tokens) {
    if (!rowContainsStatToken(a, tok)) return false;
  }
  const utilF = document.getElementById("filtro_util")?.value || "";
  if (utilF === "__mag__") {
    if (a.personaggio_id) return false;
  } else if (utilF && utilF !== "__tutti__") {
    if (String(a.personaggio_id || "") !== utilF) return false;
  }
  const q = document.getElementById("filtro_testo")?.value || "";
  if (!rowMatchesTextBlob(a, q)) return false;
  return true;
}

function populateDatalistSet() {
  const dl = document.getElementById("datalist_set_magazzino");
  if (!dl) return;
  const sets = [...new Set(magazzinoRows.map(x => x.set).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "it")
  );
  dl.innerHTML = sets.map(s => `<option value="${escapeAttr(s)}"></option>`).join("");
}

function populateSelectMainFiltro() {
  const sel = document.getElementById("filtro_main");
  if (!sel) return;
  const cur = sel.value;
  const mains = [...new Set(magazzinoRows.map(x => x.main).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "it")
  );
  sel.replaceChildren();
  const o0 = document.createElement("option");
  o0.value = "";
  o0.textContent = "Tutte";
  sel.appendChild(o0);
  for (const m of mains) {
    const o = document.createElement("option");
    o.value = m;
    o.textContent = m;
    sel.appendChild(o);
  }
  if (mains.includes(cur)) sel.value = cur;
}

function populateSelectUtilFiltro() {
  const sel = document.getElementById("filtro_util");
  if (!sel) return;
  const cur = sel.value;
  sel.replaceChildren();
  const oAll = document.createElement("option");
  oAll.value = "__tutti__";
  oAll.textContent = "Tutti";
  sel.appendChild(oAll);
  const oMag = document.createElement("option");
  oMag.value = "__mag__";
  oMag.textContent = "Solo magazzino";
  sel.appendChild(oMag);
  const seen = new Map();
  for (const row of magazzinoRows) {
    if (row.personaggio_id && row.utilizzatore && !seen.has(row.personaggio_id)) {
      seen.set(row.personaggio_id, row.utilizzatore);
    }
  }
  for (const [pid, nome] of [...seen.entries()].sort((a, b) =>
    String(a[1]).localeCompare(String(b[1]), "it")
  )) {
    const o = document.createElement("option");
    o.value = String(pid);
    o.textContent = nome;
    sel.appendChild(o);
  }
  if ([...sel.options].some(o => o.value === cur)) sel.value = cur;
  else sel.value = "__tutti__";
}

function applyFiltriMagazzino() {
  const tbody = document.getElementById("tabellaInventario");
  if (!tbody) return;
  if (magazzinoRows.length === 0) {
    tbody.innerHTML = trMagazzinoMsg(MSG_MAG_DB_VUOTO);
    return;
  }
  const filtered = magazzinoRows.filter(rowMatchesFiltri);
  if (filtered.length === 0) {
    tbody.innerHTML = trMagazzinoMsg(MSG_MAG_FILTRI_VUOTI);
    return;
  }
  tbody.innerHTML = filtered.map(buildRowHtml).join("");
}

function resetFiltriMagazzino() {
  const ids = ["filtro_slot", "filtro_set", "filtro_main", "filtro_stat_tokens", "filtro_testo"];
  for (const id of ids) {
    const el = document.getElementById(id);
    if (el) el.value = "";
  }
  const u = document.getElementById("filtro_util");
  if (u) u.value = "__tutti__";
  applyFiltriMagazzino();
}

async function loadMagazzino() {
  const tbody = document.getElementById("tabellaInventario");
  if (!tbody) return;
  const col = COL_TAB_MAGAZZINO;
  try {
    const r = await fetch(`${API}/artefatti`);
    const raw = await r.text();
    let data;
    try {
      data = JSON.parse(raw);
    } catch {
      throw new Error(jsonServerHintArtefatti());
    }
    if (!r.ok) {
      const msg = data && typeof data === "object" && data.error ? String(data.error) : `HTTP ${r.status}`;
      throw new Error(msg);
    }
    const rowVuotoDb = trMagazzinoMsg(MSG_MAG_DB_VUOTO);
    if (!Array.isArray(data)) {
      if (data && typeof data === "object" && data.error) throw new Error(String(data.error));
      magazzinoRows = [];
      tbody.innerHTML = rowVuotoDb;
      populateDatalistSet();
      populateSelectMainFiltro();
      populateSelectUtilFiltro();
      return;
    }
    if (data.length === 0) {
      magazzinoRows = [];
      tbody.innerHTML = rowVuotoDb;
      populateDatalistSet();
      populateSelectMainFiltro();
      populateSelectUtilFiltro();
      return;
    }
    magazzinoRows = data;
    populateDatalistSet();
    populateSelectMainFiltro();
    populateSelectUtilFiltro();
    applyFiltriMagazzino();
  } catch (e) {
    magazzinoRows = [];
    const hint = e && e.message ? escapeHtml(e.message) : escapeHtml(jsonServerHintArtefatti());
    tbody.innerHTML = `<tr><td colspan="${col}" style="text-align:left;color:#ef4444;padding:0.75rem;line-height:1.4">${hint}</td></tr>`;
    console.error(e);
  }
}

function modalInfoOpen() {
  document.getElementById("modalInfoBackdrop").hidden = false;
}

function modalInfoClose() {
  document.getElementById("modalInfoBackdrop").hidden = true;
}

function buildInfoBody(d) {
  const rows = [
    ["Slot", d.slot],
    ["Set", d.set_nome],
    ["Pezzo", d.nome],
    ["Liv. / ★", `Lv.${d.livello ?? "—"} · ★${d.stelle ?? "—"}`],
    ["Main", `${d.main_stat || "—"} ${d.main_val != null && d.main_val !== "" ? d.main_val : ""}`.trim()],
    ["Utilizzatore", d.utilizzatore || "Magazzino"],
  ];
  for (let i = 1; i <= 4; i++) {
    const k = `sub${i}_stat`;
    const v = `sub${i}_val`;
    const line = [d[k], d[v]].filter(x => x != null && x !== "").join(" ");
    rows.push([`Sub ${i}`, line || "—"]);
  }
  rows.push(["ID", `#${d.id}`]);
  return rows
    .map(([k, v]) => `<div class="mi-row"><span class="mi-k">${escapeHtml(k)}</span><span>${escapeHtml(v)}</span></div>`)
    .join("");
}

async function openInfoModal(aid) {
  const bd = document.getElementById("modalInfoBackdrop");
  const title = document.getElementById("modalInfoTitle");
  const body = document.getElementById("modalInfoBody");
  const msgEl = document.getElementById("modalInfoMessaggio");
  const rankEl = document.getElementById("modalInfoRanking");
  title.textContent = "Manufatto #" + aid;
  body.innerHTML = "<p>Caricamento…</p>";
  msgEl.textContent = "";
  rankEl.innerHTML = "";
  modalInfoOpen();
  try {
    const [dr, sr] = await Promise.all([
      fetch(`${API}/artefatti/${aid}`),
      fetch(`${API}/artefatti/${aid}/suggerimenti-personaggi`),
    ]);
    const d = await dr.json();
    const s = await sr.json();
    if (!dr.ok) {
      body.innerHTML = "<p>" + escapeHtml(d.error || "Errore") + "</p>";
      return;
    }
    title.textContent = `Manufatto #${d.id}` + (d.set_nome ? ` — ${d.set_nome}` : "");
    body.innerHTML = buildInfoBody(d);
    msgEl.textContent = s.messaggio || "";
    const list = s.ranking || [];
    rankEl.innerHTML = list
      .map(
        (x, i) =>
          `<li><strong>${i + 1}.</strong> ${escapeHtml(x.nome)} <span style="opacity:0.8">(${escapeHtml(x.elemento)})</span> — punteggio ${escapeHtml(x.score)}</li>`
      )
      .join("");
    if (!list.length) rankEl.innerHTML = "<li style='color:var(--text-muted)'>—</li>";
  } catch (e) {
    body.innerHTML = "<p>Errore di rete.</p>";
    console.error(e);
  }
}

async function eliminaManufatto(aid) {
  if (!confirm("Eliminare definitivamente questo manufatto dal database? (es. usato come materiale per potenziarne un altro)")) return;
  const r = await fetch(`${API}/artefatti/${aid}`, { method: "DELETE" });
  let res = {};
  try {
    res = await r.json();
  } catch {
    /* ignore */
  }
  if (!r.ok || res.error) {
    alert("Errore: " + (res.error || r.status));
    return;
  }
  if (editingId === aid) resetForm();
  modalInfoClose();
  await loadMagazzino();
  maybeRefreshEquipIfVisible();
}

function collectFormPayload() {
  const subs = [];
  document.querySelectorAll(".sub_stat").forEach((sel, i) => {
    const valEl = document.querySelectorAll(".sub_val")[i];
    subs.push({ stat: sel.value, val: valEl.value ? parseFloat(valEl.value) : null });
  });
  const selPg = document.getElementById("assegn_a_personaggio");
  const rawPid = selPg && selPg.value ? String(selPg.value).trim() : "";
  return {
    slot: document.getElementById("slot").value,
    set_nome: resolveSetNome(),
    nome: resolveNomePezzo(),
    livello: parseInt(document.getElementById("livello").value, 10) || 20,
    stelle: parseInt(document.getElementById("stelle").value, 10) || 5,
    main_stat: document.getElementById("main_stat").value,
    main_val: document.getElementById("main_val").value ? parseFloat(document.getElementById("main_val").value) : null,
    sub1_stat: subs[0].stat,
    sub1_val: subs[0].val,
    sub2_stat: subs[1].stat,
    sub2_val: subs[1].val,
    sub3_stat: subs[2].stat,
    sub3_val: subs[2].val,
    sub4_stat: subs[3].stat,
    sub4_val: subs[3].val,
    _rawPersonaggio: rawPid,
  };
}

async function salvaModuloManufatto() {
  const base = collectFormPayload();
  const rawPid = base._rawPersonaggio;
  delete base._rawPersonaggio;

  if (editingId) {
    const payload = {
      ...base,
      personaggio_id: rawPid ? parseInt(rawPid, 10) : null,
    };
    const r = await fetch(`${API}/artefatti/${editingId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    let res = {};
    try {
      res = await r.json();
    } catch {
      /* ignore */
    }
    if (!r.ok || res.error) {
      alert("Errore: " + (res.error || r.status));
      return;
    }
    resetForm();
    await loadMagazzino();
    maybeRefreshEquipIfVisible();
    return;
  }

  const payload = { ...base };
  if (rawPid) payload.personaggio_id = parseInt(rawPid, 10);
  const r = await fetch(`${API}/artefatti`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  let res;
  try {
    res = await r.json();
  } catch {
    alert("Risposta non valida dal server.");
    return;
  }
  if (res.error) {
    alert("Errore: " + res.error);
    return;
  }
  alert(rawPid ? "Manufatto aggiunto ed equipaggiato al personaggio scelto." : "Manufatto aggiunto al magazzino (libero).");
  await loadMagazzino();
  maybeRefreshEquipIfVisible();
}

document.getElementById("slot").addEventListener("change", () => loadCatalogo(document.getElementById("slot").value));
document.getElementById("set_nome").addEventListener("change", () => refreshPezzoSelect());
document.getElementById("set_nome_custom")?.addEventListener("input", () => void refreshPezzoSelect());
document.getElementById("set_nome_custom")?.addEventListener("change", () => void refreshPezzoSelect());
const nomePezzoEl = document.getElementById("nome_pezzo");
if (nomePezzoEl) {
  nomePezzoEl.addEventListener("change", () => {
    const v = nomePezzoEl.value;
    toggleCustomNome(v === "__custom__");
    if (v !== "__custom__") {
      const c = document.getElementById("nome_custom");
      if (c) c.value = "";
    }
  });
}
document.getElementById("btnAggiungi").addEventListener("click", () => void salvaModuloManufatto());
document.getElementById("btnAnnullaForm")?.addEventListener("click", () => resetForm());
document.getElementById("btnEliminaForm")?.addEventListener("click", () => {
  if (!editingId) return;
  void eliminaManufatto(editingId);
});

document.getElementById("modalInfoClose").addEventListener("click", modalInfoClose);
document.getElementById("modalInfoBackdrop").addEventListener("click", e => {
  if (e.target.id === "modalInfoBackdrop") modalInfoClose();
});

const tbodyInv = document.getElementById("tabellaInventario");
if (tbodyInv) {
  tbodyInv.addEventListener("click", async e => {
    const t = e.target;
    const tr = t.closest("tr.row-manufatto");
    const btn = t.closest("button");
    if (btn) {
      const aid = parseInt(btn.getAttribute("data-aid"), 10);
      if (!aid) return;
      e.stopPropagation();
      if (btn.classList.contains("btn-carica-modulo")) {
        await caricaNelModulo(aid);
        return;
      }
      return;
    }
    if (!tr || t.closest("[data-stop-row-click]")) return;
    const aid = parseInt(tr.getAttribute("data-aid"), 10);
    if (aid) await openInfoModal(aid);
  });

  tbodyInv.addEventListener("keydown", e => {
    const tr = e.target.closest("tr.row-manufatto");
    if (!tr || (e.key !== "Enter" && e.key !== " ")) return;
    e.preventDefault();
    const aid = parseInt(tr.getAttribute("data-aid"), 10);
    if (aid) openInfoModal(aid);
  });
}

function wireFiltriMagazzino() {
  ["filtro_slot", "filtro_main", "filtro_util"].forEach(id => {
    document.getElementById(id)?.addEventListener("change", () => applyFiltriMagazzino());
  });
  ["filtro_set", "filtro_stat_tokens", "filtro_testo"].forEach(id => {
    document.getElementById(id)?.addEventListener("input", () => applyFiltriMagazzino());
  });
  document.getElementById("btnResetFiltri")?.addEventListener("click", () => resetFiltriMagazzino());
}

function wireFiltriToggle() {
  const btn = document.getElementById("btnToggleFiltriMagazzino");
  const panel = document.getElementById("magazzinoFiltriPanel");
  if (!btn || !panel) return;
  btn.addEventListener("click", () => {
    const willOpen = panel.hidden;
    panel.hidden = !willOpen;
    btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
    btn.textContent = willOpen ? "Nascondi filtri inventario" : "Mostra filtri inventario";
  });
}

async function initArtefattiPage() {
  buildEquipGridHtml();
  wireInvTabs();
  wireEquipPanel();
  wireFiltriMagazzino();
  wireFiltriToggle();
  await Promise.all([loadPersonaggiPerForm(), loadEquipPersonaggiSelect(), loadCatalogo("fiore")]);
  await loadMagazzino();
  if (location.hash === "#equip") {
    document.getElementById("invTabEquip")?.click();
    history.replaceState(null, "", location.pathname + location.search);
  }
}
initArtefattiPage();

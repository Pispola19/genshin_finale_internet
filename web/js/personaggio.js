/**
 * Scheda personaggio — manufatti solo lettura; assegnazione solo da pagina Manufatti.
 */
function apiBase() {
  const m = document.querySelector('meta[name="api-base"]');
  const b = (m && m.content && m.content.trim()) || "/api";
  return b.replace(/\/$/, "");
}
const API = apiBase();
const SLOTS = ["fiore", "piuma", "sabbie", "calice", "corona"];
const TALENT_IDS = ["aa", "skill", "burst", "pas1", "pas2", "pas3", "pas4"];
const COST_IDS = ["c1", "c2", "c3", "c4", "c5", "c6"];

let currentId = null;
let personaggiList = [];
let catalogoNomi = [];
let catalogoArmi = [];
let onlySavedPg = false;

const searchPersonaggio = document.getElementById("searchPersonaggio");
const autocompleteList = document.getElementById("autocompleteList");
const nome = document.getElementById("nome");
const datalistCatalogoPg = document.getElementById("datalist_catalogo_pg");
const datalistCatalogoArmi = document.getElementById("datalist_catalogo_armi");
const livello = document.getElementById("livello");
const elemento = document.getElementById("elemento");
const hp_flat = document.getElementById("hp_flat");
const atk_flat = document.getElementById("atk_flat");
const def_flat = document.getElementById("def_flat");
const em_flat = document.getElementById("em_flat");
const cr = document.getElementById("cr");
const cd = document.getElementById("cd");
const er = document.getElementById("er");
const arma_nome = document.getElementById("arma_nome");
const arma_tipo = document.getElementById("arma_tipo");
const arma_livello = document.getElementById("arma_livello");
const arma_stelle = document.getElementById("arma_stelle");
const arma_atk_base = document.getElementById("arma_atk_base");
const arma_stat = document.getElementById("arma_stat");
const arma_valore = document.getElementById("arma_valore");
const btnOnlySavedPg = document.getElementById("btnOnlySavedPg");

/** Allineato a config.STATS (suggerimenti stat secondaria arma). */
const ARMA_STAT_SUGGESTIONS = [
  "HP", "HP%", "ATK", "ATK%", "DEF", "DEF%",
  "EM", "ER", "CR", "CR%", "CD", "CD%",
  "Pyro DMG", "Hydro DMG", "Electro DMG", "Cryo DMG", "Anemo DMG", "Geo DMG",
  "Dendro DMG", "Physical DMG", "Healing Bonus", "Shield Strength",
];

function initArmaStatDatalist() {
  const dl = document.getElementById("datalist_arma_stats");
  if (!dl) return;
  dl.innerHTML = ARMA_STAT_SUGGESTIONS.map(s => `<option value="${String(s).replace(/"/g, "&quot;")}"></option>`).join("");
}
const artLabels = { fiore: "art_fiore", piuma: "art_piuma", sabbie: "art_sabbie", calice: "art_calice", corona: "art_corona" };

function escArtTxt(t) {
  return String(t == null || t === "" ? "" : t)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

/** Anteprima manufatto (payload scheda personaggio / GET /api/personaggio/:id). */
function formatArtefatto(info) {
  if (!info || info.id == null || info.id === "") {
    return '<span class="art-empty">Nessun manufatto. Vai in <a href="artefatti.html#equip">Manufatti → Equip personaggio</a> per assegnare i pezzi.</span>';
  }
  const rows = [];
  rows.push(`<div class="art-row"><span class="art-k">Set</span><span class="art-v"><strong>${escArtTxt(info.set) || "—"}</strong></span></div>`);
  const pezzo = (info.nome && String(info.nome).trim()) ? escArtTxt(info.nome) : "—";
  rows.push(`<div class="art-row"><span class="art-k">Pezzo</span><span class="art-v">${pezzo}</span></div>`);
  const liv = info.livello != null && info.livello !== "" ? info.livello : null;
  const st = info.stelle != null && info.stelle !== "" ? info.stelle : null;
  rows.push(
    `<div class="art-row"><span class="art-k">Liv. ★</span><span class="art-v art-lv-st">` +
      `Lv.${liv != null ? escArtTxt(liv) : "—"} · ★${st != null ? escArtTxt(st) : "—"}</span></div>`
  );
  const mainS = info.main_stat ? escArtTxt(info.main_stat) : "—";
  const mainV = info.main_val != null && info.main_val !== "" ? escArtTxt(info.main_val) : "";
  rows.push(`<div class="art-row"><span class="art-k">Main</span><span class="art-v">${mainS}${mainV ? ` ${mainV}` : ""}</span></div>`);
  const subs = Array.isArray(info.subs) ? info.subs : [];
  for (let i = 0; i < 4; i++) {
    const s = subs[i];
    if (s && (s.stat || s.val != null && s.val !== "")) {
      const line = `${escArtTxt(s.stat || "")}${s.val != null && s.val !== "" ? ` ${escArtTxt(s.val)}` : ""}`.trim() || "—";
      rows.push(`<div class="art-row art-sub"><span class="art-k">Sub ${i + 1}</span><span class="art-v">${line}</span></div>`);
    } else {
      rows.push(`<div class="art-row art-sub art-sub-empty"><span class="art-k">Sub ${i + 1}</span><span class="art-v">—</span></div>`);
    }
  }
  rows.push(`<div class="art-row art-id-ref"><span class="art-k">ID</span><span class="art-v">#${escArtTxt(info.id)}</span></div>`);
  return `<div class="art-detail" role="group" aria-label="Dettaglio manufatto">${rows.join("")}</div>`;
}

async function loadPersonaggi() {
  try {
    const r = await fetch(`${API}/personaggi`);
    const data = await r.json();
    personaggiList = Array.isArray(data) ? data : [];
  } catch {
    personaggiList = [];
  }
}

/** Allineato a core.nome_normalization.norm_key_nome */
function normKeyNome(s) {
  return String(s || "")
    .trim()
    .split(/\s+/)
    .join(" ")
    .toLowerCase();
}

function fillDatalist(dl, items) {
  if (!dl) return;
  const esc = (v) =>
    String(v)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  dl.innerHTML = (items || []).map((t) => `<option value="${esc(t)}"></option>`).join("");
}

function nomeInCatalogoEffettivo(n) {
  const k = normKeyNome(n);
  if (!k) return false;
  return catalogoNomi.some((x) => normKeyNome(x) === k);
}

function armaInCatalogoEffettivo(n) {
  const k = normKeyNome(n);
  if (!k) return true;
  return catalogoArmi.some((x) => normKeyNome(x) === k);
}

function updateOrigineBadges(d) {
  void d;
}

async function loadCatalogoNomi() {
  try {
    const r = await fetch(`${API}/personaggi/catalogo-nomi`);
    const raw = await r.text();
    const j = JSON.parse(raw);
    catalogoNomi = Array.isArray(j.nomi) ? j.nomi : [];
  } catch {
    try {
      const r2 = await fetch(`${API}/autocomplete`);
      const arr = await r2.json();
      catalogoNomi = Array.isArray(arr) ? arr : [];
    } catch {
      catalogoNomi = [];
    }
  }
  fillDatalist(datalistCatalogoPg, catalogoNomi);
}

async function loadCatalogoArmi() {
  try {
    const r = await fetch(`${API}/catalogo/armi`);
    const j = await r.json();
    catalogoArmi = Array.isArray(j.nomi) ? j.nomi : [];
  } catch {
    catalogoArmi = [];
  }
  fillDatalist(datalistCatalogoArmi, catalogoArmi);
}

function idSalvatoPerNome(nomeStr) {
  const k = normKeyNome(nomeStr);
  const p = personaggiList.find(x => normKeyNome(x.nome || "") === k);
  return p ? p.id : null;
}

function suggestionsNomePersonaggio(query) {
  const q = (query || "").toLowerCase().trim();
  let names;
  if (onlySavedPg) {
    names = [...new Set(personaggiList.map(p => p.nome).filter(Boolean))];
  } else {
    names = catalogoNomi.length ? catalogoNomi : [...new Set(personaggiList.map(p => p.nome).filter(Boolean))];
  }
  if (q) names = names.filter(n => (n || "").toLowerCase().includes(q));
  return names.map(nomeStr => {
    const id = idSalvatoPerNome(nomeStr);
    return { nome: nomeStr, id, salvato: id != null };
  });
}

function refreshAutocompleteCurrentQuery() {
  if (!searchPersonaggio || !autocompleteList) return;
  // Evita di aprire automaticamente il menu: aggiorniamo solo se l'input è in focus.
  if (document.activeElement !== searchPersonaggio) return;
  showAutocomplete(suggestionsNomePersonaggio(searchPersonaggio.value));
}

function showAutocomplete(suggestions) {
  autocompleteList.innerHTML = "";
  if (suggestions.length === 0) {
    autocompleteList.style.display = "none";
    return;
  }
  suggestions.forEach(s => {
    const li = document.createElement("li");
    li.className = "autocomplete-row";
    const nameSpan = document.createElement("span");
    nameSpan.className = "autocomplete-name";
    nameSpan.textContent = s.nome;
    li.appendChild(nameSpan);
    const tag = document.createElement("span");
    tag.className = "autocomplete-tag " + (s.salvato ? "autocomplete-tag-salvato" : "autocomplete-tag-nuovo");
    tag.textContent = s.salvato ? "Salvato" : "Nuovo";
    li.appendChild(tag);
    li.addEventListener("click", () => {
      searchPersonaggio.value = s.nome;
      autocompleteList.style.display = "none";
      if (s.id != null) loadPersonaggio(s.id);
      else {
        nuovo();
        nome.value = s.nome;
        searchPersonaggio.value = s.nome;
      }
    });
    autocompleteList.appendChild(li);
  });
  autocompleteList.style.display = "block";
}

function refreshNomeAutocomplete() {
  showAutocomplete(suggestionsNomePersonaggio(searchPersonaggio.value));
}

searchPersonaggio.addEventListener("input", refreshNomeAutocomplete);
searchPersonaggio.addEventListener("focus", refreshNomeAutocomplete);

document.addEventListener("click", e => {
  const inSearch = e.target === searchPersonaggio || autocompleteList.contains(e.target);
  if (!inSearch) autocompleteList.style.display = "none";
});

btnOnlySavedPg?.addEventListener("click", () => {
  onlySavedPg = !onlySavedPg;
  if (btnOnlySavedPg) btnOnlySavedPg.setAttribute("aria-pressed", onlySavedPg ? "true" : "false");
  refreshAutocompleteCurrentQuery();
});

/** Riempie il modulo scheda da oggetto come GET /api/personaggio/:id. */
function applySchedaToForm(d, idPg) {
  if (!d) return;
  if (idPg != null) currentId = idPg;

  const wantNome = (d.nome || "").trim();
  if (nome) nome.value = wantNome;
  livello.value = d.livello === "-" ? "" : d.livello;
  elemento.value = d.elemento || "Pyro";
  hp_flat.value = d.hp_flat === "-" ? "" : d.hp_flat;
  atk_flat.value = d.atk_flat === "-" ? "" : d.atk_flat;
  def_flat.value = d.def_flat === "-" ? "" : d.def_flat;
  em_flat.value = d.em_flat === "-" ? "" : d.em_flat;
  cr.value = d.cr === "-" ? "" : d.cr;
  cd.value = d.cd === "-" ? "" : d.cd;
  er.value = d.er === "-" ? "" : d.er;

  if (d.arma) {
    const an = (d.arma.nome || "").trim();
    if (arma_nome) arma_nome.value = an;
    arma_tipo.value = d.arma.tipo || "Spada";
    arma_livello.value = d.arma.livello === "-" ? "" : d.arma.livello;
    arma_stelle.value = d.arma.stelle === "-" ? "" : d.arma.stelle;
    if (arma_atk_base) arma_atk_base.value = d.arma.atk_base === "-" || d.arma.atk_base == null ? "" : d.arma.atk_base;
    arma_stat.value = d.arma.stat_secondaria || "";
    arma_valore.value = d.arma.valore_stat === "-" ? "" : d.arma.valore_stat;
  }

  if (d.costellazioni) {
    COST_IDS.forEach((k, i) => {
      const el = document.getElementById(k);
      if (el) el.value = d.costellazioni[i] ? "1" : "0";
    });
  }
  if (d.talenti && Array.isArray(d.talenti)) {
    TALENT_IDS.forEach((tid, i) => {
      const el = document.getElementById(tid);
      if (el) el.value = d.talenti[i] != null ? String(d.talenti[i]) : "-";
    });
  }

  if (d.artefatti) {
    for (const [slot, info] of Object.entries(d.artefatti)) {
      const contentEl = document.getElementById(artLabels[slot]);
      if (contentEl) contentEl.innerHTML = formatArtefatto(info);
    }
  }
  updateOrigineBadges(d);
}

async function loadPersonaggio(id) {
  const r = await fetch(`${API}/personaggio/${id}`);
  if (!r.ok) return false;
  const d = await r.json();
  applySchedaToForm(d, id);
  return true;
}

async function salva() {
  const pgNome = nome ? nome.value.trim() : "";
  const arNome = arma_nome ? arma_nome.value.trim() : "";
  const meta = {};

  const payload = {
    id: currentId,
    personaggio: {
      nome: pgNome,
      livello: livello.value || 1,
      elemento: elemento.value,
      hp_flat: hp_flat.value,
      atk_flat: atk_flat.value,
      def_flat: def_flat.value,
      em_flat: em_flat.value,
      cr: cr.value,
      cd: cd.value,
      er: er.value,
    },
    arma: {
      nome: arNome,
      tipo: arma_tipo.value,
      livello: arma_livello.value,
      stelle: arma_stelle.value,
      atk_base: arma_atk_base ? arma_atk_base.value : "",
      stat_secondaria: arma_stat.value,
      valore_stat: arma_valore.value,
    },
    costellazioni: Object.fromEntries(COST_IDS.map((k) => [k, document.getElementById(k).value])),
    talenti: Object.fromEntries(TALENT_IDS.map((tid) => [tid, document.getElementById(tid).value])),
    meta,
  };

  const r = await fetch(`${API}/personaggio`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  const res = await r.json();
  if (res.error) { alert("Errore: " + res.error); return; }
  currentId = res.id;
  searchPersonaggio.value = nome.value;
  await loadPersonaggi();
  await loadCatalogoNomi();
  await loadCatalogoArmi();
  await loadPersonaggio(currentId);
  alert("Salvato!");
}

function nuovo() {
  currentId = null;
  searchPersonaggio.value = "";
  nome.value = "";
  livello.value = "1";
  elemento.value = "Pyro";
  hp_flat.value = atk_flat.value = def_flat.value = em_flat.value = "";
  cr.value = cd.value = er.value = "";
  arma_nome.value = arma_stat.value = arma_valore.value = "";
  if (arma_atk_base) arma_atk_base.value = "";
  arma_tipo.value = "Spada";
  arma_livello.value = arma_stelle.value = "";
  COST_IDS.forEach(k => { const el = document.getElementById(k); if (el) el.value = "0"; });
  TALENT_IDS.forEach(id => { const el = document.getElementById(id); if (el) el.value = "-"; });
  SLOTS.forEach(slot => {
    const contentEl = document.getElementById(artLabels[slot]);
    if (contentEl) contentEl.innerHTML = '<span class="art-empty">Nessun manufatto</span>';
  });
  updateOrigineBadges({ origine_nome: "ufficiale", arma: { origine_nome: "ufficiale" } });
}

async function cancella() {
  if (!currentId || !confirm("Eliminare questo personaggio?")) return;
  try {
    const r = await fetch(`${API}/personaggio/${currentId}`, { method: "DELETE" });
    let data = {};
    try {
      data = await r.json();
    } catch {
      /* body vuoto */
    }
    if (!r.ok) {
      alert("Eliminazione non riuscita: " + (data.error || r.statusText || r.status));
      return;
    }
    nuovo();
    await loadPersonaggi();
    await loadCatalogoNomi();
    alert("Eliminato");
  } catch (e) {
    alert("Errore di rete: " + (e && e.message ? e.message : e));
  }
}

document.getElementById("btnNuovo").addEventListener("click", () => {
  nuovo();
});
document.getElementById("btnSalva").addEventListener("click", salva);
document.getElementById("btnCancella").addEventListener("click", cancella);

const listaPgBackdrop = document.getElementById("listaPgBackdrop");

function openListaModifica() {
  if (!listaPgBackdrop) return;
  if (!personaggiList.length) {
    alert("Nessun personaggio salvato. Premi NUOVO, compila la scheda e salva.");
    return;
  }
  const ul = document.getElementById("listaPgUl");
  if (!ul) return;
  ul.innerHTML = "";
  const sorted = [...personaggiList].sort((a, b) => String(a.nome || "").localeCompare(String(b.nome || ""), "it"));
  sorted.forEach((p) => {
    const li = document.createElement("li");
    li.className = "pick-pg";
    li.textContent = `${p.nome} — Lv.${p.livello} (${p.elemento || "—"})`;
    li.addEventListener("click", async () => {
      await loadPersonaggio(p.id);
      searchPersonaggio.value = p.nome;
      listaPgBackdrop.hidden = true;
    });
    ul.appendChild(li);
  });
  listaPgBackdrop.hidden = false;
}

document.getElementById("btnModifica")?.addEventListener("click", openListaModifica);
document.getElementById("listaPgClose")?.addEventListener("click", () => {
  if (listaPgBackdrop) listaPgBackdrop.hidden = true;
});
listaPgBackdrop?.addEventListener("click", (e) => {
  if (e.target === listaPgBackdrop) listaPgBackdrop.hidden = true;
});

async function initPersonaggioPage() {
  initArmaStatDatalist();
  await Promise.all([loadPersonaggi(), loadCatalogoNomi(), loadCatalogoArmi()]);
  if (btnOnlySavedPg) btnOnlySavedPg.setAttribute("aria-pressed", onlySavedPg ? "true" : "false");
}
initPersonaggioPage();

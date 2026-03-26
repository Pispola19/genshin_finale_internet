/**
 * Pagina Build Analysis - confronto build attuale vs ottimale (solo personaggi salvati).
 * UX: slot che cambiano evidenziati, delta stat manufatti, impatto set sul proxy.
 */
function apiBase() {
  const m = document.querySelector('meta[name="api-base"]');
  const b = (m && m.content && m.content.trim()) || "/api";
  return b.replace(/\/$/, "");
}
const API = apiBase();

let currentPersonaggioId = null;
let lastBuildData = null;
let personaggiList = [];
let catalogoNomi = [];

const searchPersonaggio = document.getElementById("searchPersonaggio");
const autocompleteList = document.getElementById("autocompleteList");
const buildSelectionHint = document.getElementById("buildSelectionHint");
const curr_atk = document.getElementById("curr_atk");
const curr_crcd = document.getElementById("curr_crcd");
const curr_er_em = document.getElementById("curr_er_em");
const curr_dps = document.getElementById("curr_dps");
const opt_atk = document.getElementById("opt_atk");
const opt_crcd = document.getElementById("opt_crcd");
const opt_er_em = document.getElementById("opt_er_em");
const opt_dps = document.getElementById("opt_dps");
const diff_dps = document.getElementById("diff_dps");
const diff_damage_proxy = document.getElementById("diff_damage_proxy");
const diff_set_mult = document.getElementById("diff_set_mult");
const diff_atk = document.getElementById("diff_atk");
const diff_crcd = document.getElementById("diff_crcd");
const diff_er_em = document.getElementById("diff_er_em");
const curr_damage_proxy = document.getElementById("curr_damage_proxy");
const opt_damage_proxy = document.getElementById("opt_damage_proxy");
const buildModelHint = document.getElementById("buildModelHint");
const curr_bonus_set = document.getElementById("curr_bonus_set");
const curr_riepilogo_slots = document.getElementById("curr_riepilogo_slots");
const opt_bonus_set = document.getElementById("opt_bonus_set");
const opt_riepilogo_slots = document.getElementById("opt_riepilogo_slots");
const buildSlotChangeLead = document.getElementById("buildSlotChangeLead");
const buildSlotDiffBody = document.getElementById("buildSlotDiffBody");
const buildSetImpactSummary = document.getElementById("buildSetImpactSummary");
const buildSetImpactLines = document.getElementById("buildSetImpactLines");
const tabella_artefatti = document.getElementById("tabellaArtefatti");
const btn_calcola = document.getElementById("btnCalcola");
const btn_applica = document.getElementById("btnApplica");
const btn_confronta = document.getElementById("btnConfronta");

async function load_personaggi() {
  try {
    const r = await fetch(`${API}/personaggi`);
    const data = await r.json();
    personaggiList = Array.isArray(data) ? data : [];
  } catch {
    personaggiList = [];
  }
}

async function load_catalogo_nomi() {
  try {
    const r = await fetch(`${API}/personaggi/catalogo-nomi`);
    const j = JSON.parse(await r.text());
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
}

function id_salvato_per_nome(nome_str) {
  const p = personaggiList.find(x => (x.nome || "") === nome_str);
  return p ? p.id : null;
}

function suggestions_nome_personaggio(query) {
  const q = (query || "").toLowerCase().trim();
  let names = catalogoNomi.length ? catalogoNomi : [...new Set(personaggiList.map(p => p.nome).filter(Boolean))];
  if (q) names = names.filter(n => (n || "").toLowerCase().includes(q));
  return names.map(nome_str => {
    const id = id_salvato_per_nome(nome_str);
    return { nome: nome_str, id, salvato: id != null };
  });
}

function escape_html(s) {
  if (s == null) return "";
  const d = document.createElement("div");
  d.textContent = String(s);
  return d.innerHTML;
}

/** Mappa slot_key → info confronto API */
function slot_change_by_key(confronto) {
  const o = {};
  const slots = (confronto && confronto.slot && confronto.slot.slots) || [];
  for (const row of slots) {
    if (row && row.slot_key) o[row.slot_key] = row;
  }
  return o;
}

function slot_line_icon_html(changed, vuoto) {
  if (vuoto) {
    return '<span class="build-ux-ico build-ux-ico-empty" title="Slot vuoto" aria-hidden="true">○</span>';
  }
  if (changed) {
    return '<span class="build-ux-ico build-ux-ico-change" title="Da cambiare rispetto all’ottimale" aria-hidden="true">⇄</span>';
  }
  return '<span class="build-ux-ico build-ux-ico-same" title="Stesso manufatto / dettagli" aria-hidden="true">✓</span>';
}

function render_riepilogo_build(ul_bonus, ul_slots, riepilogo, change_by_key) {
  if (!ul_bonus || !ul_slots) return;
  if (!riepilogo) {
    ul_bonus.innerHTML = "";
    ul_slots.innerHTML = "";
    return;
  }
  const bonus = riepilogo.bonus_set || [];
  ul_bonus.innerHTML = bonus.map(
    b => `<li><span class="build-ux-ico build-ux-ico-setmini" aria-hidden="true">◆</span>${escape_html(b)}</li>`
  ).join("");
  const slots = riepilogo.slots || [];
  ul_slots.innerHTML = slots.map(s => {
    const sk = s.slot_key || "";
    const ch = change_by_key[sk];
    const changed = ch && ch.cambiato;
    const row_cls = changed ? "slot-changed" : s.vuoto ? "slot-empty" : "slot-unchanged";
    const ico = slot_line_icon_html(changed, s.vuoto);
    if (s.vuoto) {
      return `<li class="${row_cls}">${ico}<span class="slot-tag">${escape_html(s.slot)}</span> Vuoto</li>`;
    }
    const mv =
      s.main_val != null && s.main_val !== ""
        ? ` ${escape_html(String(s.main_val))}`
        : "";
    return `<li class="${row_cls}">${ico}<span class="slot-tag">${escape_html(s.slot)}</span> ${escape_html(s.set)} — ${escape_html(s.nome)} · ${escape_html(s.main)}${mv}</li>`;
  }).join("");
}

function render_slot_diff_table(tbody, confronto) {
  if (!tbody) return;
  tbody.innerHTML = "";
  const slots = (confronto && confronto.slot && confronto.slot.slots) || [];
  const n = confronto && confronto.slot && confronto.slot.num_slot_cambiati;
  if (buildSlotChangeLead) {
    if (!slots.length) {
      buildSlotChangeLead.textContent = "Nessun dato confronto.";
    } else if (n === 0) {
      buildSlotChangeLead.textContent =
        "Nessuno slot diverso: stessi manufatti (o stessi dettagli) tra build attuale e ottimale proposta.";
    } else {
      buildSlotChangeLead.textContent = `${n} slot diversi rispetto alla build ottimale (libera in inventario).`;
    }
  }
  for (const r of slots) {
    const tr = document.createElement("tr");
    const changed = r.cambiato;
    tr.className = changed ? "row-changed" : "row-same";
    const label = escape_html(r.slot_label || r.slot_key || "—");
    const stato = changed
      ? '<span class="cell-status status-change"><span class="build-ux-ico build-ux-ico-change" aria-hidden="true">⇄</span>Cambia</span>'
      : '<span class="cell-status status-same"><span class="build-ux-ico build-ux-ico-same" aria-hidden="true">✓</span>Uguale</span>';
    const note = escape_html(r.motivo || (changed ? "—" : "Stesso pezzo"));
    tr.innerHTML = `<td>${label}</td><td>${stato}</td><td>${note}</td>`;
    tbody.appendChild(tr);
  }
}

function render_set_impact(summary_el, ul_el, confronto) {
  const sp = confronto && confronto.set_proxy;
  if (!summary_el || !ul_el) return;
  if (!sp) {
    summary_el.textContent = "";
    ul_el.innerHTML = "";
    return;
  }
  const a = sp.attuale && sp.attuale.moltiplicatore;
  const o = sp.ottimale && sp.ottimale.moltiplicatore;
  const d = sp.delta_moltiplicatore;
  const txt =
    `Moltiplicatore proxy per i set: attuale ×${a != null ? a : "—"} → ottimale ×${o != null ? o : "—"} ` +
    `(Δ ${d != null && d !== "" ? (d > 0 ? "+" : "") + String(d) : "—"}).`;
  summary_el.innerHTML = "";
  const ico = document.createElement("span");
  ico.className = "build-ux-ico build-ux-ico-set";
  ico.setAttribute("aria-hidden", "true");
  ico.textContent = "◇";
  ico.title = "Impatto bonus set (proxy)";
  const span = document.createElement("span");
  span.textContent = txt;
  summary_el.appendChild(ico);
  summary_el.appendChild(span);

  const la = (sp.attuale && sp.attuale.linee) || [];
  const lo = (sp.ottimale && sp.ottimale.linee) || [];
  const lines = [];
  lines.push({ text: "Attuale (proxy set)", section: true });
  la.forEach(x => lines.push({ text: String(x), section: false }));
  lines.push({ text: "Ottimale (proxy set)", section: true });
  lo.forEach(x => lines.push({ text: String(x), section: false }));
  ul_el.innerHTML = lines
    .map(item => {
      if (item.section) {
        return `<li class="build-set-impact-section"><span class="build-ux-ico build-ux-ico-setmini" aria-hidden="true">◆</span>${escape_html(item.text)}</li>`;
      }
      return `<li>${escape_html(item.text)}</li>`;
    })
    .join("");
}

function signed_str(n) {
  if (n == null || n === "") return "—";
  const x = Number(n);
  if (Number.isNaN(x)) return "—";
  return x > 0 ? `+${x}` : String(x);
}

function apply_signed_class(el, n) {
  if (!el) return;
  const x = Number(n);
  el.className = "";
  if (Number.isNaN(x) || x === 0) return;
  el.className = x > 0 ? "positive delta-typed" : "negative delta-typed";
}

function clear_build_results() {
  curr_atk.textContent = "—";
  curr_crcd.textContent = "—";
  if (curr_er_em) curr_er_em.textContent = "—";
  curr_dps.textContent = "—";
  if (curr_damage_proxy) curr_damage_proxy.textContent = "—";
  opt_atk.textContent = "—";
  opt_crcd.textContent = "—";
  if (opt_er_em) opt_er_em.textContent = "—";
  opt_dps.textContent = "—";
  if (opt_damage_proxy) opt_damage_proxy.textContent = "—";
  if (curr_bonus_set) curr_bonus_set.innerHTML = "";
  if (curr_riepilogo_slots) curr_riepilogo_slots.innerHTML = "";
  if (opt_bonus_set) opt_bonus_set.innerHTML = "";
  if (opt_riepilogo_slots) opt_riepilogo_slots.innerHTML = "";
  diff_dps.textContent = "—";
  diff_dps.className = "";
  if (diff_damage_proxy) {
    diff_damage_proxy.textContent = "—";
    diff_damage_proxy.className = "";
  }
  if (diff_set_mult) {
    diff_set_mult.textContent = "—";
    diff_set_mult.className = "";
  }
  if (diff_atk) {
    diff_atk.textContent = "—";
    diff_atk.className = "";
  }
  diff_crcd.textContent = "—";
  if (diff_er_em) {
    diff_er_em.textContent = "—";
    diff_er_em.className = "";
  }
  if (buildModelHint) buildModelHint.textContent = "";
  if (buildSlotChangeLead) buildSlotChangeLead.textContent = "Calcola la build per vedere quali slot cambiano.";
  if (buildSlotDiffBody) buildSlotDiffBody.innerHTML = "";
  if (buildSetImpactSummary) buildSetImpactSummary.textContent = "";
  if (buildSetImpactLines) buildSetImpactLines.innerHTML = "";
  lastBuildData = null;
  tabella_artefatti.innerHTML =
    '<tr><td colspan="5" style="text-align:center;color:#94a3b8">Seleziona un personaggio <strong>salvato</strong> e premi Calcola</td></tr>';
}

function show_autocomplete(suggestions) {
  autocompleteList.innerHTML = "";
  if (suggestions.length === 0) {
    autocompleteList.style.display = "none";
    return;
  }
  suggestions.forEach(s => {
    const li = document.createElement("li");
    li.className = "autocomplete-row";
    const name_span = document.createElement("span");
    name_span.className = "autocomplete-name";
    name_span.textContent = s.nome;
    li.appendChild(name_span);
    const tag = document.createElement("span");
    tag.className = "autocomplete-tag " + (s.salvato ? "autocomplete-tag-salvato" : "autocomplete-tag-nuovo");
    tag.textContent = s.salvato ? "Salvato" : "Da salvare";
    li.appendChild(tag);
    li.addEventListener("click", () => {
      searchPersonaggio.value = s.nome;
      autocompleteList.style.display = "none";
      if (s.id != null) {
        currentPersonaggioId = s.id;
        if (buildSelectionHint) {
          buildSelectionHint.textContent = `Scheda salvata: ${s.nome} — puoi usare «Calcola build».`;
        }
        calcola_build();
      } else {
        currentPersonaggioId = null;
        clear_build_results();
        if (buildSelectionHint) {
          buildSelectionHint.textContent =
            `«${s.nome}» non è ancora salvato. Vai su Personaggio & Inventario, scegli lo stesso nome (Nuovo), compila e Salva — poi torna qui per il calcolo.`;
        }
      }
    });
    autocompleteList.appendChild(li);
  });
  autocompleteList.style.display = "block";
}

function refresh_nome_autocomplete() {
  show_autocomplete(suggestions_nome_personaggio(searchPersonaggio.value));
}

searchPersonaggio.addEventListener("input", refresh_nome_autocomplete);
searchPersonaggio.addEventListener("focus", refresh_nome_autocomplete);

document.addEventListener("click", e => {
  const in_search = e.target === searchPersonaggio || autocompleteList.contains(e.target);
  if (!in_search) autocompleteList.style.display = "none";
});

async function calcola_build() {
  if (!currentPersonaggioId) {
    alert(
      "Serve un personaggio salvato in database. Cerca il nome: se compare «Salvato» puoi calcolare; se «Non in build» crea prima la scheda da Personaggio & Inventario."
    );
    return;
  }
  const r = await fetch(`${API}/build/${currentPersonaggioId}`);
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    alert(err.error || "Errore");
    return;
  }
  lastBuildData = await r.json();
  render_build(lastBuildData);
  if (buildSelectionHint) buildSelectionHint.textContent = "Build aggiornata.";
}

function render_build(data) {
  const curr = data.build_attuale;
  const opt = data.build_ottimale;
  const diff = data.differenza || {};
  const confronto = data.confronto || {};
  const ch_map = slot_change_by_key(confronto);

  curr_atk.textContent = curr.atk ?? "—";
  curr_crcd.textContent = `${curr.cr ?? 0}/${curr.cd ?? 0}`;
  if (curr_er_em) curr_er_em.textContent = `${curr.er ?? 0} / ${curr.em ?? 0}`;
  render_riepilogo_build(curr_bonus_set, curr_riepilogo_slots, curr.riepilogo, ch_map);
  curr_dps.textContent = curr.dps ?? "—";
  if (curr_damage_proxy) curr_damage_proxy.textContent = curr.damage_proxy != null ? String(curr.damage_proxy) : "—";

  opt_atk.textContent = opt.atk ?? "—";
  opt_crcd.textContent = `${opt.cr ?? 0}/${opt.cd ?? 0}`;
  if (opt_er_em) opt_er_em.textContent = `${opt.er ?? 0} / ${opt.em ?? 0}`;
  render_riepilogo_build(opt_bonus_set, opt_riepilogo_slots, opt.riepilogo, ch_map);
  opt_dps.textContent = opt.dps ?? "—";
  if (opt_damage_proxy) opt_damage_proxy.textContent = opt.damage_proxy != null ? String(opt.damage_proxy) : "—";

  if (buildModelHint) {
    buildModelHint.textContent = data.dps_model_note_it || "";
  }

  render_slot_diff_table(buildSlotDiffBody, confronto);
  render_set_impact(buildSetImpactSummary, buildSetImpactLines, confronto);

  const d_dps = diff.dps ?? 0;
  diff_dps.textContent = signed_str(d_dps);
  diff_dps.className =
    d_dps > 0 ? "positive delta-typed" : d_dps < 0 ? "negative delta-typed" : "";

  const dp = diff.damage_proxy ?? 0;
  if (diff_damage_proxy) {
    diff_damage_proxy.textContent = signed_str(dp);
    apply_signed_class(diff_damage_proxy, dp);
  }

  const dsm = confronto.set_proxy && confronto.set_proxy.delta_moltiplicatore;
  if (diff_set_mult) {
    diff_set_mult.textContent = dsm != null ? signed_str(dsm) : "—";
    apply_signed_class(diff_set_mult, dsm);
  }

  const da = diff.atk;
  if (diff_atk) {
    diff_atk.textContent = da != null ? signed_str(da) : "—";
    apply_signed_class(diff_atk, da);
  }

  diff_crcd.textContent = `CR ${signed_str(diff.cr ?? 0)} / CD ${signed_str(diff.cd ?? 0)}`;

  const der = diff.er;
  const dem = diff.em;
  if (diff_er_em) {
    diff_er_em.textContent = `ER ${signed_str(der)} / EM ${signed_str(dem)}`;
    const mx = Math.max(Math.abs(Number(der) || 0), Math.abs(Number(dem) || 0));
    diff_er_em.className = mx > 0 ? (Number(der) + Number(dem) >= 0 ? "positive" : "negative") : "";
  }

  const arts = data.artefatti_disponibili || [];
  if (arts.length === 0) {
    tabella_artefatti.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#94a3b8">Nessun artefatto</td></tr>';
  } else {
    tabella_artefatti.innerHTML = arts.map(a =>
      `<tr><td>${escape_html(a.slot || "—")}</td><td>${escape_html(a.set || "—")}</td><td>${escape_html(a.main || "—")}</td><td>${escape_html(a.val ?? "—")}</td><td>${escape_html(a.score ?? "—")}</td></tr>`
    ).join("");
  }
}

function applica() {
  alert(
    "L’equip ottimale non si applica in automatico: ogni pezzo va assegnato a mano in Manufatti " +
      "(Carica nel modulo sul pezzo libero, scegli il personaggio nel riquadro blu, SALVA MODIFICHE). " +
      "La Build serve solo a confrontare numeri."
  );
}

function confronta() {
  if (lastBuildData) {
    render_build(lastBuildData);
    alert("Confronto aggiornato.");
  } else {
    alert("Calcola prima la build.");
  }
}

btn_calcola.addEventListener("click", calcola_build);
btn_applica.addEventListener("click", applica);
btn_confronta.addEventListener("click", confronta);

async function init_build_page() {
  await Promise.all([load_personaggi(), load_catalogo_nomi()]);
}
init_build_page();

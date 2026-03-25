/**
 * Pagina Build Analysis - confronto build attuale vs ottimale (solo personaggi salvati).
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
const curr_er = document.getElementById("curr_er");
const curr_dps = document.getElementById("curr_dps");
const opt_atk = document.getElementById("opt_atk");
const opt_crcd = document.getElementById("opt_crcd");
const opt_er = document.getElementById("opt_er");
const opt_dps = document.getElementById("opt_dps");
const diff_dps = document.getElementById("diff_dps");
const diff_crcd = document.getElementById("diff_crcd");
const tabellaArtefatti = document.getElementById("tabellaArtefatti");
const btnCalcola = document.getElementById("btnCalcola");
const btnApplica = document.getElementById("btnApplica");
const btnConfronta = document.getElementById("btnConfronta");

async function loadPersonaggi() {
  try {
    const r = await fetch(`${API}/personaggi`);
    const data = await r.json();
    personaggiList = Array.isArray(data) ? data : [];
  } catch {
    personaggiList = [];
  }
}

async function loadCatalogoNomi() {
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

function idSalvatoPerNome(nomeStr) {
  const p = personaggiList.find(x => (x.nome || "") === nomeStr);
  return p ? p.id : null;
}

function suggestionsNomePersonaggio(query) {
  const q = (query || "").toLowerCase().trim();
  let names = catalogoNomi.length ? catalogoNomi : [...new Set(personaggiList.map(p => p.nome).filter(Boolean))];
  if (q) names = names.filter(n => (n || "").toLowerCase().includes(q));
  return names.map(nomeStr => {
    const id = idSalvatoPerNome(nomeStr);
    return { nome: nomeStr, id, salvato: id != null };
  });
}

function clearBuildResults() {
  curr_atk.textContent = "—";
  curr_crcd.textContent = "—";
  curr_er.textContent = "—";
  curr_dps.textContent = "—";
  opt_atk.textContent = "—";
  opt_crcd.textContent = "—";
  opt_er.textContent = "—";
  opt_dps.textContent = "—";
  diff_dps.textContent = "—";
  diff_dps.className = "";
  diff_crcd.textContent = "—";
  lastBuildData = null;
  tabellaArtefatti.innerHTML =
    '<tr><td colspan="5" style="text-align:center;color:#94a3b8">Seleziona un personaggio <strong>salvato</strong> e premi Calcola</td></tr>';
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
        calcolaBuild();
      } else {
        currentPersonaggioId = null;
        clearBuildResults();
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

function refreshNomeAutocomplete() {
  showAutocomplete(suggestionsNomePersonaggio(searchPersonaggio.value));
}

searchPersonaggio.addEventListener("input", refreshNomeAutocomplete);
searchPersonaggio.addEventListener("focus", refreshNomeAutocomplete);

document.addEventListener("click", e => {
  const inSearch = e.target === searchPersonaggio || autocompleteList.contains(e.target);
  if (!inSearch) autocompleteList.style.display = "none";
});

async function calcolaBuild() {
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
  renderBuild(lastBuildData);
  if (buildSelectionHint) {
    buildSelectionHint.textContent = "Build aggiornata.";
  }
}

function renderBuild(data) {
  const curr = data.build_attuale;
  const opt = data.build_ottimale;
  const diff = data.differenza || {};

  curr_atk.textContent = curr.atk ?? "—";
  curr_crcd.textContent = `${curr.cr ?? 0}/${curr.cd ?? 0}`;
  curr_er.textContent = curr.er ?? "—";
  curr_dps.textContent = curr.dps ?? "—";

  opt_atk.textContent = opt.atk ?? "—";
  opt_crcd.textContent = `${opt.cr ?? 0}/${opt.cd ?? 0}`;
  opt_er.textContent = opt.er ?? "—";
  opt_dps.textContent = opt.dps ?? "—";

  const d = diff.dps ?? 0;
  diff_dps.textContent = d >= 0 ? `+${d}` : String(d);
  diff_dps.className = d > 0 ? "positive" : d < 0 ? "negative" : "";
  diff_crcd.textContent = `CR +${diff.cr ?? 0} / CD +${diff.cd ?? 0}`;

  const arts = data.artefatti_disponibili || [];
  if (arts.length === 0) {
    tabellaArtefatti.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#94a3b8">Nessun artefatto</td></tr>';
  } else {
    tabellaArtefatti.innerHTML = arts.map(a =>
      `<tr><td>${a.slot || "—"}</td><td>${a.set || "—"}</td><td>${a.main || "—"}</td><td>${a.val ?? "—"}</td><td>${a.score ?? "—"}</td></tr>`
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
    renderBuild(lastBuildData);
    alert("Confronto aggiornato.");
  } else {
    alert("Calcola prima la build.");
  }
}

btnCalcola.addEventListener("click", calcolaBuild);
btnApplica.addEventListener("click", applica);
btnConfronta.addEventListener("click", confronta);

async function initBuildPage() {
  await Promise.all([loadPersonaggi(), loadCatalogoNomi()]);
}
initBuildPage();

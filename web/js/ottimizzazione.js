/**
 * Ottimizzazione manufatti — solo lettura, API /api/ottimizzazione-manufatti
 */
function apiBase() {
  const m = document.querySelector('meta[name="api-base"]');
  const b = (m && m.content && m.content.trim()) || "/api";
  return b.replace(/\/$/, "");
}
const API = apiBase();

const SLOT_ORDER = ["fiore", "piuma", "sabbie", "calice", "corona"];

function esc(t) {
  return String(t == null ? "" : t)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function manufattiEquipHref(personaggioId, slotKey) {
  const pg = encodeURIComponent(String(personaggioId));
  const sl = encodeURIComponent(String(slotKey || ""));
  return `artefatti.html?pg=${pg}&slot=${sl}#equip`;
}

function renderSlot(sl, personaggioId) {
  const imp = sl.migliorabile === true;
  const cur = sl.equipped;
  const alt = sl.best_alternative;
  const curLine = cur
    ? `<span class="opt-cur-label">${esc(cur.label)}</span> <span class="opt-score">Indice ${esc(cur.score)}</span>`
    : `<span class="opt-empty">Nessun pezzo equipaggiato</span>`;
  const altBlock = imp && alt
    ? `<div class="opt-alt"><span class="opt-alt-tag">Migliore in magazzino</span> <strong>${esc(alt.label)}</strong> <span class="opt-delta">+${esc(alt.delta)}</span></div>`
    : "";
  const action =
    imp && personaggioId != null
      ? `<p class="opt-action"><a class="btn btn-secondary opt-manufatti-link" href="${esc(manufattiEquipHref(personaggioId, sl.slot))}">Vai a Manufatti (equip)</a></p>`
      : "";
  return `
    <div class="opt-slot ${imp ? "opt-slot--improvable" : "opt-slot--ok"}" data-slot="${esc(sl.slot)}">
      <div class="opt-slot-h"><span class="opt-slot-name">${esc(sl.slot_label)}</span>${imp ? `<span class="opt-badge">Migliorabile</span>` : ""}</div>
      <div class="opt-slot-body">${curLine}${altBlock}<p class="opt-hint">${esc(sl.messaggio_breve || "")}</p>${action}</div>
    </div>
  `;
}

function renderCard(pg) {
  const slots = pg.slots || {};
  const pid = pg.personaggio_id;
  const rows = SLOT_ORDER.map((k) => slots[k])
    .filter(Boolean)
    .map((sl) => renderSlot(sl, pid))
    .join("");
  const headNote = pg.ha_suggerimenti
    ? `<p class="opt-pg-summary opt-pg-summary--yes">Alcuni slot hanno un’alternativa migliore in magazzino.</p>`
    : `<p class="opt-pg-summary opt-pg-summary--no">Nessun miglioramento disponibile in magazzino.</p>`;
  return `
    <article class="opt-pg-card section" data-pid="${esc(pg.personaggio_id)}">
      <h2 class="opt-pg-title">${esc(pg.nome)} <span class="opt-pg-el">${esc(pg.elemento || "")}</span></h2>
      ${headNote}
      <div class="opt-slots-grid">${rows}</div>
    </article>
  `;
}

async function carica() {
  const err = document.getElementById("optErrore");
  const vuoto = document.getElementById("optVuoto");
  const guida = document.getElementById("optGuida");
  const lista = document.getElementById("optLista");
  if (err) {
    err.hidden = true;
    err.textContent = "";
  }
  try {
    const r = await fetch(`${API}/ottimizzazione-manufatti`, { credentials: "same-origin" });
    if (!r.ok) {
      if (err) {
        err.hidden = false;
        err.textContent = "Errore durante il caricamento (" + r.status + ").";
      }
      return;
    }
    const data = await r.json();
    if (!Array.isArray(data) || data.length === 0) {
      vuoto.hidden = false;
      if (guida) guida.hidden = true;
      lista.innerHTML = "";
      return;
    }
    vuoto.hidden = true;
    if (guida) {
      const hasAnyEquipped = data.some((pg) =>
        Object.values(pg && pg.slots ? pg.slots : {}).some((sl) => !!(sl && sl.equipped))
      );
      guida.hidden = hasAnyEquipped;
    }
    lista.innerHTML = data.map(renderCard).join("");
  } catch (e) {
    if (err) {
      err.hidden = false;
      err.textContent = "Errore di rete. Riprova.";
    }
  }
}

document.getElementById("btnOptAggiorna")?.addEventListener("click", carica);
carica();

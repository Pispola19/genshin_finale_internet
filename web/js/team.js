/**
 * Pagina Team Builder - costruzione e ottimizzazione squadre
 */
const API = "/api";

let personaggiList = [];
let teamIds = [null, null, null, null];  // 4 slot

// Elements
const teamSlots = document.getElementById("teamSlots");
const teamPower = document.getElementById("teamPower");
const sinergie = document.getElementById("sinergie");
const topTeams = document.getElementById("topTeams");
const btnCalcola = document.getElementById("btnCalcola");
const btnOttimizza = document.getElementById("btnOttimizza");
const btnSalva = document.getElementById("btnSalva");
const modal = document.getElementById("modalPersonaggi");
const listaPersonaggiModal = document.getElementById("listaPersonaggiModal");
const btnChiudiModal = document.getElementById("btnChiudiModal");

let slotInModifica = null;

// Load personaggi
async function loadPersonaggi() {
  try {
    const r = await fetch(`${API}/teams`);
    personaggiList = await r.json();
    if (!Array.isArray(personaggiList)) personaggiList = [];
  } catch {
    personaggiList = [];
  }
}

function renderEmptyTeamState() {
  teamPower.textContent = "—";
  sinergie.innerHTML = "<li>Seleziona un personaggio per iniziare.</li>";
  topTeams.innerHTML =
    '<div class="top-team"><span class="chars">Nessuna build disponibile. Salva almeno un personaggio e riprova.</span></div>';
}

function apriModal(slotIndex) {
  if (!personaggiList.length) {
    renderEmptyTeamState();
    return;
  }
  slotInModifica = slotIndex;
  modal.style.display = "flex";
  listaPersonaggiModal.innerHTML = personaggiList.map(p => {
    const sel = teamIds[slotIndex] === p.id ? " ✓" : "";
    return `<div style="padding:0.5rem;cursor:pointer;border-radius:6px" class="pick-pg" data-id="${p.id}">${p.nome} (${p.elemento})${sel}</div>`;
  }).join("");

  document.querySelectorAll(".pick-pg").forEach(el => {
    el.addEventListener("click", () => {
      teamIds[slotIndex] = parseInt(el.dataset.id, 10);
      aggiornaSlot(slotIndex, personaggiList.find(x => x.id === teamIds[slotIndex]));
      modal.style.display = "none";
    });
  });
}

function aggiornaSlot(index, pg) {
  const slotEl = teamSlots.querySelector(`[data-slot="${index}"]`);
  if (!slotEl) return;
  const nameEl = slotEl.querySelector(".slot-name");
  if (pg) {
    slotEl.classList.add("filled");
    nameEl.textContent = pg.nome;
  } else {
    slotEl.classList.remove("filled");
    nameEl.textContent = "—";
  }
}

// Render slots
function renderSlots() {
  [0, 1, 2, 3].forEach(i => {
    const pg = teamIds[i] ? personaggiList.find(p => p.id === teamIds[i]) : null;
    aggiornaSlot(i, pg);
  });
}

teamSlots.querySelectorAll(".team-slot").forEach(slot => {
  slot.addEventListener("click", () => {
    apriModal(parseInt(slot.dataset.slot, 10));
  });
});

btnChiudiModal.addEventListener("click", () => {
  modal.style.display = "none";
});

// Calcola team power
function calcolaPower() {
  const ids = teamIds.filter(Boolean);
  if (ids.length === 0) {
    teamPower.textContent = "—";
    return 0;
  }
  let power = 0;
  ids.forEach(id => {
    const p = personaggiList.find(x => x.id === id);
    if (p) power += (p.livello || 1) * 100;
  });
  const elemUnici = new Set(ids.map(id => {
    const p = personaggiList.find(x => x.id === id);
    return p ? p.elemento : "";
  })).size;
  power += elemUnici * 50;
  teamPower.textContent = power;
  return power;
}

// Calcola top 4 team (usa slot se 4 pieni, altrimenti tutti i personaggi)
async function calcolaTeams() {
  const ids = teamIds.filter(Boolean);
  // Se abbiamo 4 slot pieni, usiamo quelli; altrimenti [] = API userà tutti i personaggi
  const payload = ids.length >= 4 ? { personaggi: ids } : { personaggi: [] };

  const r = await fetch(`${API}/teams/calcola`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await r.json();

  if (!data.teams || data.teams.length === 0) {
    topTeams.innerHTML = `<div class="top-team"><span class="chars">${data.message || "Nessun team disponibile"}</span></div>`;
    return;
  }

  topTeams.innerHTML = data.teams.map((t, i) => {
    const cls = i === 0 ? "top-team best" : "top-team";
    const chars = (t.personaggi || []).join(", ");
    const dps = t.dps || "—";
    return `<div class="${cls}"><span class="chars">${chars}</span><span class="dps">DPS: ${dps}</span></div>`;
  }).join("");
}

// Ottimizza: mette i top 4 nel primo team
function ottimizza() {
  const firstTeam = topTeams.querySelector(".top-team");
  if (!firstTeam) {
    alert("Calcola prima il team.");
    return;
  }
  const chars = firstTeam.querySelector(".chars").textContent;
  if (!chars || chars === "—") return;
  // Parsing semplificato: i nomi sono separati da ", "
  const nomi = chars.split(", ");
  const nuoviIds = nomi.slice(0, 4).map(n => {
    const p = personaggiList.find(x => x.nome === n.trim());
    return p ? p.id : null;
  }).filter(Boolean);
  for (let i = 0; i < 4; i++) teamIds[i] = nuoviIds[i] || null;
  renderSlots();
  calcolaPower();
  alert("Team ottimizzato applicato!");
}

function salva() {
  const ids = teamIds.filter(Boolean);
  if (ids.length < 4) {
    alert("Completa i 4 slot prima di salvare.");
    return;
  }
  // Salvataggio team: per ora solo alert (non c'è tabella teams nel DB)
  alert("Salvataggio team non ancora disponibile.");
}

btnCalcola.addEventListener("click", () => {
  calcolaPower();
  calcolaTeams();
});

btnOttimizza.addEventListener("click", ottimizza);
btnSalva.addEventListener("click", salva);

// Init
loadPersonaggi().then(() => {
  if (!personaggiList.length) {
    renderEmptyTeamState();
    return;
  }
  renderSlots();
});

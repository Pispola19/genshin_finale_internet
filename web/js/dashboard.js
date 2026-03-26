/**
 * Dashboard - solo lettura, nessun calcolo frontend.
 * Chiama API, mostra dati.
 */
const API = "/api";

function renderVuoto() {
  document.getElementById("topNome").textContent = "—";
  document.getElementById("topDps").textContent = "DPS: —";
  document.getElementById("dpsMedio").textContent = "—";
  const slots = document.querySelectorAll("#teamMigliore .slot");
  slots.forEach(el => {
    el.textContent = "—";
    el.classList.remove("filled");
  });
  document.getElementById("teamPower").textContent = "—";
  document.getElementById("top5").innerHTML = "<li>—</li>";
  document.getElementById("buildMigliorabili").innerHTML = "<li>—</li>";
  const dq = document.getElementById("dashboardDpsQuality");
  if (dq) {
    dq.hidden = true;
    dq.replaceChildren();
    dq.className = "dashboard-dps-quality";
  }
}

function render(dati) {
  const vuoto = dati.vuoto === true;
  const msg = document.getElementById("dashboardVuotoMsg");
  if (msg) msg.hidden = !vuoto;

  const top = dati.top_personaggio || {};
  document.getElementById("topNome").textContent = top.nome || "—";
  document.getElementById("topDps").textContent = top.dps != null ? `DPS: ${top.dps}` : "DPS: —";

  document.getElementById("dpsMedio").textContent = dati.dps_medio != null ? dati.dps_medio : "—";

  const tm = dati.team_migliore || {};
  const personaggi = tm.personaggi || [];
  const slots = document.querySelectorAll("#teamMigliore .slot");
  slots.forEach((el, i) => {
    el.textContent = personaggi[i] || "—";
    el.classList.toggle("filled", !!personaggi[i]);
  });
  document.getElementById("teamPower").textContent = tm.power ?? "—";

  const top5 = dati.top_5 || [];
  const top5El = document.getElementById("top5");
  if (top5.length === 0) {
    top5El.innerHTML = "<li>—</li>";
  } else {
    top5El.innerHTML = top5.map((p, i) =>
      `<li>${i + 1}. ${p.nome} → DPS ${p.dps ?? "—"}</li>`
    ).join("");
  }

  const migliorabili = dati.build_migliorabili || [];
  const migliorabiliEl = document.getElementById("buildMigliorabili");
  if (migliorabili.length === 0) {
    migliorabiliEl.innerHTML = vuoto
      ? "<li>—</li>"
      : "<li>Nessuna build da migliorare</li>";
  } else {
    migliorabiliEl.innerHTML = migliorabili.map(p =>
      `<li>${p.nome} → attuale ${p.dps_attuale ?? "—"} vs ottimale ${p.dps_ottimale ?? "—"} (+${p.diff ?? 0})</li>`
    ).join("");
  }

  const dq = document.getElementById("dashboardDpsQuality");
  const q = dati.dps_quality;
  if (dq && q && typeof q === "object") {
    dq.hidden = false;
    const ready = Number(q.ready) || 0;
    const partial = Number(q.partial) || 0;
    dq.className = "dashboard-dps-quality";
    dq.classList.add(
      vuoto
        ? "dashboard-dps-quality--neutral"
        : partial > 0
          ? "dashboard-dps-quality--warn"
          : "dashboard-dps-quality--ok"
    );
    dq.replaceChildren();
    const title = document.createElement("span");
    title.className = "dashboard-dps-quality__title";
    title.textContent = "Affidabilità DPS (tutte le schede)";
    const line1 = document.createElement("div");
    line1.className = "dashboard-dps-quality__stats";
    line1.textContent = String(q.summary_it || "");
    const line2 = document.createElement("div");
    line2.className = "dashboard-dps-quality__stats";
    line2.style.marginTop = "0.35rem";
    line2.textContent = `Pronti: ${ready} · Non affidabili: ${partial}`;
    dq.append(title, line1, line2);
  } else if (dq) {
    dq.hidden = true;
    dq.replaceChildren();
    dq.className = "dashboard-dps-quality";
  }
}

async function carica() {
  const errEl = document.getElementById("dashboardErroreMsg");
  if (errEl) errEl.hidden = true;
  try {
    const r = await fetch(`${API}/dashboard`);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const dati = await r.json();
    render(dati);
  } catch (e) {
    console.error(e);
    renderVuoto();
    const msg = document.getElementById("dashboardVuotoMsg");
    if (msg) msg.hidden = true;
    if (errEl) {
      errEl.hidden = false;
      errEl.textContent =
        "Impossibile caricare la dashboard (server non raggiungibile o errore). Avvia python3 run_web.py e premi AGGIORNA.";
    }
  }
}

document.getElementById("btnAggiorna").addEventListener("click", carica);

carica();

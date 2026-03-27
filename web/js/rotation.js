(function () {
  const apiBase = (document.querySelector('meta[name="api-base"]') || {}).content || "/api";
  const sel = document.getElementById("rotPgSelect");
  const presetEl = document.getElementById("rotPreset");
  const btn = document.getElementById("rotCalcBtn");
  const err = document.getElementById("rotationErr");
  const outSec = document.getElementById("rotationResult");
  const summary = document.getElementById("rotationSummary");
  const detail = document.getElementById("rotationDetail");

  function showErr(msg) {
    err.textContent = msg || "";
    err.hidden = !msg;
  }

  async function loadPeople() {
    const r = await fetch(apiBase + "/teams");
    if (!r.ok) throw new Error("Impossibile caricare i personaggi salvati.");
    const list = await r.json();
    sel.innerHTML = "";
    const ph = document.createElement("option");
    ph.value = "";
    ph.textContent = "— Seleziona un personaggio per iniziare —";
    sel.appendChild(ph);
    for (const p of list) {
      const o = document.createElement("option");
      o.value = String(p.id);
      o.textContent = (p.nome || "—") + " (lv " + (p.livello ?? "?") + ")";
      sel.appendChild(o);
    }
    if (!Array.isArray(list) || list.length === 0) {
      showErr("Nessuna build disponibile. Salva un personaggio e assegna i manufatti.");
    } else {
      showErr("");
    }
  }

  btn.addEventListener("click", async () => {
    showErr("");
    outSec.hidden = true;
    const id = sel.value;
    if (!id) {
      showErr("Seleziona un personaggio per iniziare.");
      return;
    }
    const preset = (presetEl && presetEl.value) || "equilibrato";
    let r;
    try {
      r = await fetch(
        apiBase + "/build/" + encodeURIComponent(id) + "/rotation?preset=" + encodeURIComponent(preset)
      );
    } catch (e) {
      showErr("Server non raggiungibile. Riprova tra poco.");
      return;
    }
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      showErr(data.message_it || data.error || "Errore " + r.status);
      return;
    }
    const nome = data.personaggio_nome || "—";
    const idx = data.rotation_index != null ? data.rotation_index : "—";
    const proxy = data.damage_proxy != null ? data.damage_proxy : "—";
    const mult = data.rotation_multiplier != null ? data.rotation_multiplier : "—";
    summary.innerHTML =
      "<strong>" +
      nome +
      "</strong> — indice rotazione: <strong>" +
      idx +
      "</strong> " +
      "(proxy build: " +
      proxy +
      " × moltiplicatore " +
      mult +
      ") · modello v" +
      (data.model_version || "?") +
      ")";
    const lines = [];
    lines.push(data.note_it || "");
    lines.push("");
    if (Array.isArray(data.warnings)) data.warnings.forEach((w) => lines.push("⚠ " + w));
    lines.push("");
    lines.push("Proxy — nota: " + (data.damage_proxy_note_it || "—"));
    lines.push("");
    lines.push("Pesi (NA / E / Q): " + JSON.stringify(data.weights || {}, null, 2));
    lines.push("Talenti (AA, skill, burst): " + JSON.stringify(data.talent_levels || {}, null, 2));
    lines.push("Moltiplicatori talento: " + JSON.stringify(data.talent_multipliers || {}, null, 2));
    detail.textContent = lines.join("\n");
    outSec.hidden = false;
  });

  loadPeople().catch((e) => showErr(e.message || String(e)));
})();

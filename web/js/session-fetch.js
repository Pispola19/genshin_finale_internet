/**
 * Cookie di sessione sempre inviati (same-origin).
 * Redirect a login solo se il backend segnala gate attivo (write_auth_required) e l'API risponde auth_required.
 */
(function () {
  const orig = window.fetch.bind(window);

  /** null = non ancora letto; true/false da /api/auth/status */
  let writeAuthRequired = null;

  function apiStatusUrl() {
    const m = document.querySelector('meta[name="api-base"]');
    const c = m && m.getAttribute("content");
    const base = (c || "/api").replace(/\/$/, "");
    return base + "/auth/status";
  }

  async function syncWriteAuthFlag() {
    try {
      const r = await orig(apiStatusUrl(), { credentials: "same-origin" });
      if (!r.ok) {
        writeAuthRequired = false;
        return;
      }
      const j = await r.json();
      writeAuthRequired = !!j.write_auth_required;
    } catch (e) {
      writeAuthRequired = false;
    }
  }

  syncWriteAuthFlag();

  window.fetch = async function (input, init) {
    const url = typeof input === "string" ? input : input && input.url ? String(input.url) : "";
    const opts = Object.assign({}, init, {
      credentials: (init && init.credentials) || "same-origin",
    });
    const res = await orig(input, opts);
    if (res.status !== 401) return res;
    if (url.indexOf("/api/auth/login") !== -1) return res;
    if (url.indexOf("/api/auth/status") !== -1) return res;
    if (window.location.pathname.indexOf("login.html") !== -1) return res;
    try {
      const ct = (res.headers.get("content-type") || "").toLowerCase();
      if (!ct.includes("application/json")) return res;
      const j = await res.clone().json();
      if (j && j.code === "auth_required") {
        if (writeAuthRequired === null) {
          await syncWriteAuthFlag();
        }
        if (writeAuthRequired === false) {
          return res;
        }
        const next = encodeURIComponent(
          window.location.pathname + window.location.search + window.location.hash
        );
        window.location.href = "/login.html?next=" + next;
      }
    } catch (e) {
      /* ignore */
    }
    return res;
  };
})();

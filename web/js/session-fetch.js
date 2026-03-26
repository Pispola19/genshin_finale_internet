/**
 * Invia sempre i cookie di sessione (login web) e reindirizza al login se l'API risponde auth_required.
 */
(function () {
  const orig = window.fetch.bind(window);
  window.fetch = async function (input, init) {
    const url = typeof input === "string" ? input : input && input.url ? String(input.url) : "";
    const opts = Object.assign({}, init, {
      credentials: (init && init.credentials) || "same-origin",
    });
    const res = await orig(input, opts);
    if (res.status !== 401) return res;
    if (url.indexOf("/api/auth/login") !== -1) return res;
    if (window.location.pathname.indexOf("login.html") !== -1) return res;
    try {
      const ct = (res.headers.get("content-type") || "").toLowerCase();
      if (!ct.includes("application/json")) return res;
      const j = await res.clone().json();
      if (j && j.code === "auth_required") {
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

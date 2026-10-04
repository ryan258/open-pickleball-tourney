"use strict";
(() => {
  const connection = document.querySelector("#connection-status");
  const updateConnection = () => { if (connection) connection.hidden = navigator.onLine; };
  window.addEventListener("online", updateConnection);
  window.addEventListener("offline", updateConnection);
  updateConnection();
  const announce = (button, text) => {
    let status = button.parentElement.querySelector("[data-action-status]");
    if (!status) { status = document.createElement("span"); status.dataset.actionStatus = ""; status.setAttribute("role", "status"); button.after(status); }
    status.textContent = text;
  };
  document.addEventListener("click", async event => {
    const button = event.target.closest("[data-copy],[data-copy-target],[data-print],[data-back],[data-confirm]");
    if (!button) return;
    if (button.dataset.confirm && !window.confirm(button.dataset.confirm)) { event.preventDefault(); return; }
    if (button.hasAttribute("data-print")) { window.print(); return; }
    if (button.hasAttribute("data-back")) { history.back(); return; }
    if (button.hasAttribute("data-copy") || button.dataset.copyTarget) {
      const target = document.getElementById(button.dataset.copyTarget);
      const value = button.dataset.copy || (target && (target.value || target.textContent));
      try { await navigator.clipboard.writeText(value || ""); announce(button, "Copied."); }
      catch { announce(button, "Copy unavailable. Select the displayed text to copy it."); if (target && target.select) target.select(); }
    }
  });
  let dirty = false;
  document.querySelectorAll("form[method=post]").forEach(form => {
    form.addEventListener("input", () => {
      dirty = true;
      const status = form.querySelector(".draft-status");
      if (status) status.textContent = "Unsaved changes. Keep this tab open until the server confirms your save.";
    });
    form.addEventListener("submit", event => {
      if (!navigator.onLine) { event.preventDefault(); updateConnection(); return; }
      dirty = false;
    });
  });
  window.addEventListener("beforeunload", event => { if (dirty) { event.preventDefault(); event.returnValue = ""; } });
  document.querySelectorAll("[data-live-url]").forEach(board => {
    let paused = false;
    const status = board.querySelector("[data-live-status]");
    const toggle = board.querySelector("[data-pause-live]");
    const changes = board.querySelector("[data-live-changes]");
    toggle?.addEventListener("click", () => {
      paused = !paused; toggle.textContent = paused ? "Resume updates" : "Pause updates";
      status.textContent = paused ? "Updates paused. This view may be stale." : "Checking for updates…";
      if (!paused) poll();
    });
    async function poll() {
      if (paused || document.hidden) return;
      if (!navigator.onLine) { status.textContent = "Offline. Showing the last loaded view."; return; }
      try {
        const response = await fetch(board.dataset.liveUrl, { headers: { Accept: "application/json" }, cache: "no-store", signal: AbortSignal.timeout(8000) });
        if (!response.ok) throw new Error("Unavailable");
        const data = await response.json();
        const changed = String(data.revision) !== board.dataset.revision;
        changes.hidden = !changed;
        status.textContent = changed ? "New event revision available. Refresh when ready." : "View current · checked " + new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
      } catch { status.textContent = "Updates unavailable. This view may be stale; retrying shortly."; }
    }
    poll(); setInterval(poll, 10000);
  });
})();

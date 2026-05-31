(function () {
  const $ = (id) => document.getElementById(id);

  const els = {
    statusPill: $("status-pill"),
    statusLine: $("status-line"),
    healthList: $("health-list"),
    greeterHint: $("greeter-hint"),
    activityLog: $("activity-log"),
    activityCount: $("activity-count"),
    boardLog: $("board-log"),
    boardProcs: $("board-procs"),
    toast: $("toast"),
    overlay: $("overlay"),
    overlayText: $("overlay-text"),
    btnDriver: $("btn-driver"),
  };

  let busy = false;
  let toastTimer = null;

  function showToast(message, kind = "info") {
    els.toast.textContent = message;
    els.toast.className = `toast ${kind}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => els.toast.classList.add("hidden"), 3200);
  }

  function setBusy(on, text = "Working…") {
    busy = on;
    els.overlay.classList.toggle("hidden", !on);
    els.overlay.setAttribute("aria-hidden", on ? "false" : "true");
    els.overlayText.textContent = text;
    document.querySelectorAll(".btn").forEach((b) => {
      b.disabled = on;
    });
  }

  async function api(path, options = {}) {
    const opts = {
      method: options.method || "GET",
      headers: { Accept: "application/json" },
      ...options,
    };
    if (options.body) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(options.body);
    }
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok && !data.error) {
      throw new Error(data.message || `Request failed (${res.status})`);
    }
    if (data.error) throw new Error(data.error);
    return data;
  }

  function renderHealth(health) {
    if (!health) return;

    const pillMap = {
      ready: ["pill-ready", "Ready"],
      offline: ["pill-offline", "Offline"],
      setup: ["pill-setup", "Setup needed"],
    };
    const [pillClass, pillText] = pillMap[health.status] || ["pill-muted", "Unknown"];
    els.statusPill.className = `pill ${pillClass}`;
    els.statusPill.textContent = pillText;
    els.statusLine.textContent = health.statusText || "";

    els.healthList.innerHTML = "";
    (health.checks || []).forEach((c) => {
      const li = document.createElement("li");
      li.className = "health-item";
      const dotClass = c.ok ? "ok" : c.detail.match(/not connected|Connect board/i) ? "off" : "warn";
      li.innerHTML = `
        <span class="health-dot ${dotClass}" aria-hidden="true"></span>
        <span class="health-label">${escapeHtml(c.label)}</span>
        <span class="health-detail">${escapeHtml(c.detail)}</span>
      `;
      els.healthList.appendChild(li);
    });

    if (health.boardConnected && !health.ncmDriver) {
      els.btnDriver.classList.remove("hidden");
    } else {
      els.btnDriver.classList.add("hidden");
    }
  }

  function renderActivity(entries) {
    if (!entries || !entries.length) {
      els.activityLog.innerHTML = '<p class="log-entry"><span class="m">No activity yet.</span></p>';
      els.activityCount.textContent = "";
      return;
    }
    els.activityCount.textContent = `${entries.length} lines`;
    els.activityLog.innerHTML = entries
      .map(
        (e) =>
          `<p class="log-entry ${e.level}"><span class="t">[${escapeHtml(e.time)}]</span><span class="m">${escapeHtml(e.message)}</span></p>`
      )
      .join("");
    els.activityLog.scrollTop = els.activityLog.scrollHeight;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function loadHealth() {
    const data = await api("/api/health");
    renderHealth(data.health);
    renderActivity(data.activity);
    return data;
  }

  async function refreshAll() {
    setBusy(true, "Checking board and syncing scripts…");
    try {
      const data = await api("/api/refresh", { method: "POST" });
      renderHealth(data.health);
      renderActivity(data.activity);
      showToast(data.health?.boardConnected ? "Board status updated" : "Refresh done — board offline", data.ok ? "ok" : "err");
      await loadBoardLog();
      await loadProcesses();
    } catch (e) {
      showToast(e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  async function loadBoardLog() {
    try {
      const data = await api("/api/board-log?lines=100");
      if (!data.ok) {
        els.boardLog.textContent = data.message || "Could not read log.";
        return;
      }
      els.boardLog.textContent = (data.lines || []).join("\n") || "(empty)";
    } catch (e) {
      els.boardLog.textContent = e.message;
    }
  }

  async function loadProcesses() {
    try {
      const data = await api("/api/board-processes");
      if (!data.ok) {
        els.boardProcs.textContent = data.message || "";
        els.greeterHint.classList.add("hidden");
        return;
      }
      const lines = data.processes || [];
      els.boardProcs.textContent = lines.join("\n") || "(none)";
      const greeterUp = lines.some((l) => /greeter\.py/.test(l));
      if (greeterUp) {
        els.greeterHint.textContent = "greeter.py is running on the board.";
        els.greeterHint.classList.remove("hidden");
      } else {
        els.greeterHint.classList.add("hidden");
      }
    } catch (e) {
      els.boardProcs.textContent = e.message;
      els.greeterHint.classList.add("hidden");
    }
  }

  async function postAction(path, body, busyText, okMsg) {
    if (busy) return;
    setBusy(true, busyText);
    try {
      const data = await api(path, { method: "POST", body });
      if (data.health) renderHealth(data.health);
      if (data.activity) renderActivity(data.activity);
      showToast(data.message || okMsg, data.ok !== false ? "ok" : "err");
      if (path.includes("start-gemy") || path.includes("cleanup")) {
        await loadBoardLog();
        await loadProcesses();
      }
    } catch (e) {
      showToast(e.message, "err");
    } finally {
      setBusy(false);
    }
  }

  $("btn-refresh").addEventListener("click", () => refreshAll());
  $("btn-start-voice").addEventListener("click", () =>
    postAction("/api/start-gemy", { noVision: true }, "Launching…", "Launched Gemy (voice)")
  );
  $("btn-start-cam").addEventListener("click", () =>
    postAction("/api/start-gemy", { noVision: false }, "Launching…", "Launched Gemy (camera + voice)")
  );
  $("btn-hat").addEventListener("click", () =>
    postAction("/api/hat-panel", null, "Opening HAT panel…", "HAT panel opened")
  );
  $("btn-cleanup").addEventListener("click", () => {
    if (!confirm("Stop greeter, demos, and turn the buzzer off?")) return;
    postAction("/api/cleanup", null, "Cleaning up board…", "Board reset");
  });
  $("btn-driver").addEventListener("click", () => {
    if (
      !confirm(
        "Install the Coralboard USB network driver?\n\nWindows will ask for admin approval once."
      )
    )
      return;
    postAction("/api/install-driver", null, "Installing driver…", "Driver install finished");
  });
  $("btn-tail-log").addEventListener("click", () => {
    loadBoardLog();
    loadProcesses();
    showToast("Board log reloaded", "info");
  });

  async function init() {
    try {
      const snap = await api("/api/health");
      renderHealth(snap.health);
      renderActivity(snap.activity);
      loadBoardLog();
      loadProcesses();
      refreshAll().catch((e) => showToast(e.message, "err"));
      setInterval(() => {
        if (!busy) {
          loadHealth().catch(() => {});
          loadBoardLog().catch(() => {});
          loadProcesses().catch(() => {});
        }
      }, 20000);
    } catch (e) {
      showToast("Cannot reach Control Center server. Is the PowerShell window still open?", "err");
      els.statusLine.textContent = e.message;
    }
  }

  init();
})();

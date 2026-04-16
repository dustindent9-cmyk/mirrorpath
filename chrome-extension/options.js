"use strict";

const DEFAULT_BASE = "http://localhost:8000";

const baseUrlEl  = document.getElementById("base-url");
const saveBtn    = document.getElementById("btn-save");
const testBtn    = document.getElementById("btn-test");
const statusMsg  = document.getElementById("status-msg");
const versionEl  = document.getElementById("version-line");

// ── Load saved settings ────────────────────────────────────────────────────
(async () => {
  const { dallasBases } = await chrome.storage.sync.get("dallasBases");
  baseUrlEl.value = dallasBases ?? DEFAULT_BASE;

  const manifest = chrome.runtime.getManifest();
  versionEl.textContent = `Dallas Copilot v${manifest.version}`;
})();

// ── Save ───────────────────────────────────────────────────────────────────
saveBtn.addEventListener("click", async () => {
  const url = baseUrlEl.value.trim().replace(/\/$/, "");
  if (!url) {
    showStatus("error", "URL cannot be empty.");
    return;
  }
  await chrome.storage.sync.set({ dallasBases: url });
  showStatus("ok", "Saved!");
});

// ── Test connection ────────────────────────────────────────────────────────
testBtn.addEventListener("click", async () => {
  const url = baseUrlEl.value.trim().replace(/\/$/, "");
  showStatus("", "Testing…");
  testBtn.disabled = true;

  try {
    const res = await fetch(`${url}/api/health`, {
      signal: AbortSignal.timeout(6000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data.status === "ok") {
      showStatus("ok", "Connected! Anthropic key is active.");
    } else {
      showStatus("ok", `Reached Dallas (status: ${data.status}).`);
    }
  } catch (err) {
    showStatus("error", `Could not connect: ${err.message}`);
  } finally {
    testBtn.disabled = false;
  }
});

// ── Helper ────────────────────────────────────────────────────────────────
function showStatus(cls, text) {
  statusMsg.textContent = text;
  statusMsg.className   = `status-msg ${cls}`;
}

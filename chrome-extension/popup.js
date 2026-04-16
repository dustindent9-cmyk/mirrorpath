"use strict";

// ── Constants ──────────────────────────────────────────────────────────────
const DEFAULT_BASE = "http://localhost:8000";
const STORAGE_KEY  = "dallas_ext_sessions";
const MAX_SESSIONS = 20;

// ── State ──────────────────────────────────────────────────────────────────
let baseUrl   = DEFAULT_BASE;
let sending   = false;
let sessions  = [];   // [{ id, preview, messages: [{role, text}] }]
let sessionId = String(Date.now());

// ── DOM refs ───────────────────────────────────────────────────────────────
const messagesEl  = document.getElementById("messages");
const inputEl     = document.getElementById("input");
const sendBtn     = document.getElementById("btn-send");
const routeBadge  = document.getElementById("route-badge");
const statusDot   = document.getElementById("status-dot");
const statusText  = document.getElementById("status-text");
const welcomeEl   = document.getElementById("welcome");

// ── Init ───────────────────────────────────────────────────────────────────
(async () => {
  const stored = await chrome.storage.sync.get(["dallasBases", "dallas_sessions"]);
  baseUrl  = stored.dallasBases ?? DEFAULT_BASE;
  sessions = stored.dallas_sessions ?? [];

  checkHealth();
  inputEl.focus();
})();

// ── Health check ───────────────────────────────────────────────────────────
async function checkHealth() {
  setStatus("loading", "Connecting…");
  try {
    const r = await fetch(`${baseUrl}/api/health`, { signal: AbortSignal.timeout(5000) });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    if (d.status === "ok") {
      setStatus("ok", "Connected");
    } else {
      setStatus("ok", "Connected (no API key)");
    }
  } catch {
    setStatus("error", "Cannot reach Dallas — check Settings");
  }
}

function setStatus(cls, text) {
  statusDot.className  = `status-dot ${cls}`;
  statusText.textContent = text;
}

// ── Send message ───────────────────────────────────────────────────────────
async function sendMessage() {
  if (sending) return;
  const text = inputEl.value.trim();
  if (!text) return;

  hideWelcome();
  appendMessage("user", text);
  inputEl.value = "";
  autoResize(inputEl);
  setSending(true);

  const typingId = showTyping();

  try {
    const res = await fetch(`${baseUrl}/api/chat`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ message: text }),
      signal:  AbortSignal.timeout(60000),
    });

    removeTyping(typingId);

    if (!res.ok) {
      const err = await res.text().catch(() => res.statusText);
      appendMessage("ai", `Error ${res.status}: ${err}`);
      setStatus("error", `Server error ${res.status}`);
      return;
    }

    const data = await res.json();
    appendMessage("ai", data.output ?? "(no response)");
    setStatus("ok", "Connected");
    showRouteBadge(data);
    saveSession(text, data.output ?? "");

  } catch (err) {
    removeTyping(typingId);
    if (err.name === "TimeoutError") {
      appendMessage("ai", "Request timed out. Dallas may be processing — try again.");
      setStatus("error", "Timeout");
    } else {
      appendMessage("ai", "Could not reach Dallas. Check your connection and Settings.");
      setStatus("error", "Disconnected");
    }
  } finally {
    setSending(false);
    inputEl.focus();
  }
}

// ── UI helpers ─────────────────────────────────────────────────────────────
function appendMessage(role, text) {
  const row    = document.createElement("div");
  row.className = `msg-row ${role}`;

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerHTML  = role === "ai" ? renderMarkdown(text) : escapeHtml(text);
  row.appendChild(bubble);

  if (role === "ai") {
    const meta = document.createElement("div");
    meta.className   = "msg-meta";
    meta.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    row.appendChild(meta);
  }

  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function showTyping() {
  const id  = "typing-" + Date.now();
  const row = document.createElement("div");
  row.className = "msg-row ai";
  row.id = id;

  const ind = document.createElement("div");
  ind.className = "typing-indicator";
  for (let i = 0; i < 3; i++) {
    const d = document.createElement("div");
    d.className = "typing-dot";
    ind.appendChild(d);
  }
  row.appendChild(ind);
  messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return id;
}

function removeTyping(id) {
  document.getElementById(id)?.remove();
}

function hideWelcome() {
  welcomeEl?.remove();
}

function setSending(val) {
  sending        = val;
  sendBtn.disabled = val;
  inputEl.disabled = val;
}

function showRouteBadge(data) {
  if (!data.route_provider) { routeBadge.classList.add("hidden"); return; }
  routeBadge.textContent = `${data.route_provider} · ${data.route_model} · ${data.route_agent} · ${data.elapsed_ms}ms`;
  routeBadge.classList.remove("hidden");
}

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 100) + "px";
}

// ── Markdown renderer (basic, XSS-safe) ────────────────────────────────────
function renderMarkdown(raw) {
  let s = escapeHtml(raw);

  // Fenced code blocks
  s = s.replace(/```[\w]*\n?([\s\S]*?)```/g, (_, code) =>
    `<pre><code>${code.trimEnd()}</code></pre>`);

  // Inline code
  s = s.replace(/`([^`\n]+)`/g, (_, c) => `<code>${c}</code>`);

  // Bold
  s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Paragraphs (split on blank lines)
  const blocks = s.split(/\n\n+/);
  s = blocks.map(b => {
    if (b.startsWith("<pre>") || b.startsWith("<code>")) return b;
    return `<p>${b.replace(/\n/g, "<br>")}</p>`;
  }).join("");

  return s;
}

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ── Session persistence ────────────────────────────────────────────────────
function saveSession(userMsg, aiMsg) {
  const preview = userMsg.slice(0, 60);
  const idx = sessions.findIndex(s => s.id === sessionId);
  if (idx >= 0) {
    sessions[idx].preview = preview;
    sessions[idx].ts = Date.now();
  } else {
    sessions.unshift({ id: sessionId, preview, ts: Date.now() });
  }
  if (sessions.length > MAX_SESSIONS) sessions.splice(MAX_SESSIONS);
  chrome.storage.sync.set({ dallas_sessions: sessions });
}

// ── New chat ───────────────────────────────────────────────────────────────
function newChat() {
  sessionId = String(Date.now());
  messagesEl.innerHTML = "";

  const w = document.createElement("div");
  w.id        = "welcome";
  w.className = "welcome";
  w.innerHTML = `
    <div class="welcome-icon">✦</div>
    <div class="welcome-title">How can I help?</div>
    <div class="welcome-sub">Ask anything. Press <kbd>Alt+D</kbd> to open me anytime.</div>
  `;
  messagesEl.appendChild(w);

  routeBadge.classList.add("hidden");
  inputEl.value = "";
  autoResize(inputEl);
  inputEl.focus();
}

// ── Event listeners ────────────────────────────────────────────────────────
sendBtn.addEventListener("click", sendMessage);

inputEl.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

inputEl.addEventListener("input", () => autoResize(inputEl));

document.getElementById("btn-new-chat").addEventListener("click", newChat);

document.getElementById("btn-settings").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

// Handle the "new-chat" command fired from the background service worker
chrome.runtime.onMessage.addListener(msg => {
  if (msg.type === "new-chat") newChat();
});

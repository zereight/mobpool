"""Self-contained HTML, CSS, and JS assets for the mobpool local web GUI."""

from __future__ import annotations

import html


def render_index_html(csrf_token: str, default_owner: str) -> str:
    escaped_token = html.escape(csrf_token, quote=True)
    escaped_owner = html.escape(default_owner, quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="mobpool-token" content="{escaped_token}">
  <meta name="mobpool-default-owner" content="{escaped_owner}">
  <title>mobpool — Unified iOS &amp; Android Manager</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">mp</div>
        <div>
          <h1>mobpool</h1>
          <p class="subtitle">Unified iOS Simulator &amp; Android Emulator Pool</p>
        </div>
      </div>
      <div class="topbar-actions">
        <span id="last-updated" class="meta-pill">Loading...</span>
        <label class="toggle-pill" title="Auto-refresh every 8s while this tab is visible">
          <input id="auto-refresh-toggle" type="checkbox" checked>
          <span>Auto 8s</span>
        </label>
        <button id="btn-refresh" class="btn btn-secondary" type="button">Refresh</button>
        <button id="btn-init-pool" class="btn btn-secondary" type="button">Init Pool</button>
      </div>
    </header>

    <section id="summary-grid" class="summary-grid" aria-label="System summary"></section>

    <section class="acquire-bar" aria-label="Quick acquire">
      <div class="acquire-inputs">
        <label class="field">
          <span>Owner</span>
          <input id="input-owner" type="text" value="{escaped_owner}" placeholder="mobpool-gui" maxlength="80">
        </label>
        <label class="field field-sm">
          <span>TTL (min)</span>
          <input id="input-ttl-min" type="number" min="1" max="1440" value="60">
        </label>
        <label class="toggle-pill" title="Preserve installed apps when clicking Release">
          <input id="keep-apps-toggle" type="checkbox">
          <span>Keep apps on release</span>
        </label>
      </div>
      <div class="acquire-buttons">
        <button id="btn-acquire-ios" class="btn btn-ios" type="button">+ Acquire iOS</button>
        <button id="btn-acquire-android" class="btn btn-android" type="button">+ Acquire Android</button>
      </div>
    </section>

    <section id="inflight-banner" class="inflight-banner hidden" aria-live="polite"></section>
    <section id="error-banner" class="error-banner hidden" role="alert"></section>

    <section class="panel">
      <div class="toolbar">
        <div id="platform-tabs" class="segmented" role="tablist" aria-label="Platform filter"></div>
        <div id="state-filters" class="filter-pills" role="group" aria-label="State filter"></div>
        <div class="search-wrap">
          <input id="search-input" type="search" placeholder="Search name, UDID, AVD, serial, owner...">
        </div>
      </div>

      <div class="table-wrap">
        <table class="device-table">
          <thead>
            <tr>
              <th>Device</th>
              <th>Status</th>
              <th>Ownership / Lease</th>
              <th>Resources &amp; Slim</th>
              <th class="col-actions">Actions</th>
            </tr>
          </thead>
          <tbody id="device-tbody"></tbody>
        </table>
        <div id="empty-state" class="empty-state hidden">No matching devices.</div>
      </div>
    </section>

    <section class="panel activity-panel">
      <div class="panel-header">
        <h2>Activity Log</h2>
        <span id="activity-count" class="meta-pill">0 events</span>
      </div>
      <div id="activity-list" class="activity-list"></div>
    </section>
  </div>

  <div id="toast-container" class="toast-container" aria-live="polite"></div>

  <div id="modal-backdrop" class="modal-backdrop hidden" role="dialog" aria-modal="true" aria-labelledby="modal-title">
    <div class="modal-card">
      <h3 id="modal-title"></h3>
      <p id="modal-body" class="modal-body"></p>
      <div id="modal-extra" class="modal-extra"></div>
      <div class="modal-footer">
        <button id="modal-cancel" class="btn btn-secondary" type="button">Cancel</button>
        <button id="modal-confirm" class="btn btn-danger" type="button">Confirm</button>
      </div>
    </div>
  </div>

  <script src="/app.js" defer></script>
</body>
</html>
"""


STYLES_CSS = """\
:root {
  --bg: #0c1017;
  --surface: #141a24;
  --surface-2: #1b2331;
  --border: #273244;
  --text: #e6edf7;
  --muted: #93a4bc;
  --ios: #4da3ff;
  --ios-bg: rgba(77, 163, 255, 0.14);
  --android: #34d399;
  --android-bg: rgba(52, 211, 153, 0.14);
  --ok: #34d399;
  --warn: #fbbf24;
  --danger: #f87171;
  --danger-bg: rgba(248, 113, 113, 0.14);
  --radius: 12px;
  --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  --sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  font-size: 14px;
  line-height: 1.45;
  -webkit-font-smoothing: antialiased;
}

.app-shell {
  max-width: 1320px;
  margin: 0 auto;
  padding: 20px 24px 40px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--ios), var(--android));
  color: #081018;
  font-weight: 800;
  font-family: var(--mono);
  display: grid;
  place-items: center;
  font-size: 15px;
}

.brand h1 {
  margin: 0;
  font-size: 20px;
  letter-spacing: -0.02em;
}

.subtitle {
  margin: 0;
  color: var(--muted);
  font-size: 12.5px;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-pill {
  font-size: 12px;
  color: var(--muted);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 5px 10px;
  font-variant-numeric: tabular-nums;
}

.toggle-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--text);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
  user-select: none;
}

.toggle-pill input {
  accent-color: var(--ios);
  margin: 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

@media (max-width: 980px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 600px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}

.metric-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-label {
  font-size: 12px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}

.metric-sub {
  font-size: 12px;
  color: var(--muted);
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.progress-bar {
  width: 100%;
  height: 6px;
  appearance: none;
  -webkit-appearance: none;
  border: none;
  border-radius: 999px;
  overflow: hidden;
  background: var(--surface-2);
}

.progress-bar::-webkit-progress-bar {
  background: var(--surface-2);
  border-radius: 999px;
}

.progress-bar::-webkit-progress-value {
  background: var(--ok);
  border-radius: 999px;
  transition: width 0.25s ease;
}

.progress-bar.warn::-webkit-progress-value {
  background: var(--warn);
}

.progress-bar.danger::-webkit-progress-value {
  background: var(--danger);
}

.progress-bar::-moz-progress-bar {
  background: var(--ok);
  border-radius: 999px;
}

.progress-bar.warn::-moz-progress-bar {
  background: var(--warn);
}

.progress-bar.danger::-moz-progress-bar {
  background: var(--danger);
}

.acquire-bar {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.acquire-inputs {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--muted);
}

.field input,
.search-wrap input,
.modal-select {
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
}

.field input {
  width: 150px;
}

.field-sm input {
  width: 76px;
}

.acquire-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn {
  appearance: none;
  border: 1px solid var(--border);
  background: var(--surface-2);
  color: var(--text);
  border-radius: 8px;
  padding: 7px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, opacity 0.15s ease;
  white-space: nowrap;
}

.btn:hover:not(:disabled) {
  background: #243044;
  border-color: #3a4a63;
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-sm {
  padding: 4px 9px;
  font-size: 12px;
}

.btn-ios {
  background: var(--ios-bg);
  border-color: rgba(77, 163, 255, 0.45);
  color: var(--ios);
}

.btn-ios:hover:not(:disabled) {
  background: rgba(77, 163, 255, 0.24);
}

.btn-android {
  background: var(--android-bg);
  border-color: rgba(52, 211, 153, 0.45);
  color: var(--android);
}

.btn-android:hover:not(:disabled) {
  background: rgba(52, 211, 153, 0.24);
}

.btn-primary {
  background: #2563eb;
  border-color: #3b82f6;
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-danger {
  background: var(--danger-bg);
  border-color: rgba(248, 113, 113, 0.45);
  color: var(--danger);
}

.btn-danger:hover:not(:disabled) {
  background: rgba(248, 113, 113, 0.24);
}

.btn-ghost {
  background: transparent;
  border-color: transparent;
  color: var(--muted);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--surface-2);
  color: var(--text);
}

.inflight-banner,
.error-banner {
  border-radius: var(--radius);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
}

.inflight-banner {
  background: rgba(77, 163, 255, 0.1);
  border: 1px solid rgba(77, 163, 255, 0.35);
}

.inflight-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  border: 2px solid rgba(77, 163, 255, 0.3);
  border-top-color: var(--ios);
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-banner {
  background: var(--danger-bg);
  border: 1px solid rgba(248, 113, 113, 0.45);
  color: #fecaca;
}

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.toolbar {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.segmented {
  display: inline-flex;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 2px;
  gap: 2px;
}

.seg-btn {
  border: none;
  background: transparent;
  color: var(--muted);
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}

.seg-btn.active {
  background: var(--surface);
  color: var(--text);
}

.filter-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.pill-btn {
  border: 1px solid var(--border);
  background: transparent;
  color: var(--muted);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;
}

.pill-btn.active {
  background: var(--surface-2);
  color: var(--text);
  border-color: #4a5d7c;
}

.search-wrap input {
  width: 260px;
  max-width: 100%;
}

.table-wrap {
  overflow-x: auto;
}

.device-table {
  width: 100%;
  border-collapse: collapse;
}

.device-table th {
  text-align: left;
  font-size: 11.5px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.015);
}

.device-table td {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(39, 50, 68, 0.7);
  vertical-align: middle;
}

.device-table tr:last-child td {
  border-bottom: none;
}

.device-table tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}

.col-actions {
  text-align: right !important;
}

.device-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.device-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.device-name {
  font-weight: 650;
  color: var(--text);
}

.device-os {
  font-size: 12px;
  color: var(--muted);
}

.device-id-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.mono-id {
  font-family: var(--mono);
  font-size: 11.5px;
  color: var(--muted);
}

.target-chip {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--android);
  background: var(--android-bg);
  border: 1px solid rgba(52, 211, 153, 0.35);
  border-radius: 6px;
  padding: 1px 6px;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
}

.badge-ios {
  background: var(--ios-bg);
  color: var(--ios);
}

.badge-android {
  background: var(--android-bg);
  color: var(--android);
}

.badge-booted {
  background: rgba(52, 211, 153, 0.16);
  color: var(--ok);
}

.badge-shutdown {
  background: rgba(147, 164, 188, 0.14);
  color: var(--muted);
}

.badge-pool {
  background: rgba(99, 102, 241, 0.18);
  color: #a5b4fc;
}

.badge-self {
  background: rgba(77, 163, 255, 0.16);
  color: var(--ios);
}

.badge-other {
  background: var(--danger-bg);
  color: var(--danger);
}

.badge-orphan {
  background: rgba(251, 191, 36, 0.18);
  color: var(--warn);
}

.badge-muted {
  background: rgba(147, 164, 188, 0.12);
  color: var(--muted);
}

.stack {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}

.row-inline {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.metrics-text {
  font-variant-numeric: tabular-nums;
  font-size: 12.5px;
  color: var(--text);
}

.sub-text {
  font-size: 11.5px;
  color: var(--muted);
}

.actions-cell {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: wrap;
}

.empty-state {
  padding: 28px;
  text-align: center;
  color: var(--muted);
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-header h2 {
  margin: 0;
  font-size: 14px;
}

.activity-list {
  max-height: 220px;
  overflow-y: auto;
  padding: 8px 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 12.5px;
  padding: 6px 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.02);
}

.activity-time {
  font-family: var(--mono);
  font-size: 11.5px;
  color: var(--muted);
  flex-shrink: 0;
}

.activity-msg {
  white-space: pre-wrap;
  word-break: break-word;
}

.toast-container {
  position: fixed;
  right: 20px;
  bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 50;
  max-width: 380px;
}

.toast {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
  white-space: pre-wrap;
}

.toast-ok {
  border-color: rgba(52, 211, 153, 0.5);
}

.toast-err {
  border-color: rgba(248, 113, 113, 0.55);
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(5, 8, 13, 0.72);
  display: grid;
  place-items: center;
  padding: 16px;
  z-index: 100;
}

.modal-card {
  width: 100%;
  max-width: 460px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.55);
}

.modal-card h3 {
  margin: 0;
  font-size: 16px;
}

.modal-body {
  margin: 0;
  color: var(--muted);
  font-size: 13.5px;
  white-space: pre-wrap;
}

.modal-extra {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}

.hidden {
  display: none !important;
}
"""


APP_JS = r"""
(function () {
  "use strict";

  const tokenMeta = document.querySelector('meta[name="mobpool-token"]');
  const CSRF_TOKEN = tokenMeta ? tokenMeta.getAttribute("content") || "" : "";
  const POLL_INTERVAL_MS = 8000;
  const JOB_POLL_MS = 700;

  const uiState = {
    snapshot: null,
    platformFilter: "all",
    stateFilter: "all",
    search: "",
    autoRefresh: true,
    pollTimer: null,
    jobTimer: null,
    loading: false,
    seenCompletedJobs: new Set(),
    ttlInitialized: false,
  };

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [key, val] of Object.entries(attrs)) {
        if (val === null || val === undefined || val === false) continue;
        if (key === "class") {
          node.className = String(val);
        } else if (key === "text") {
          node.textContent = String(val);
        } else if (key.startsWith("on") && typeof val === "function") {
          node.addEventListener(key.slice(2).toLowerCase(), val);
        } else if (val === true) {
          node.setAttribute(key, "");
        } else {
          node.setAttribute(key, String(val));
        }
      }
    }
    if (Array.isArray(children)) {
      for (const child of children) {
        if (child === null || child === undefined || child === false) continue;
        if (typeof child === "string") {
          node.appendChild(document.createTextNode(child));
        } else {
          node.appendChild(child);
        }
      }
    }
    return node;
  }

  function clearNode(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function formatGb(bytes) {
    const num = Number(bytes || 0);
    if (!num) return "0.00 GB";
    return (num / 1e9).toFixed(2) + " GB";
  }

  function formatTime(epochSec) {
    if (!epochSec) return "";
    const date = new Date(epochSec * 1000);
    return date.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function showToast(message, isError) {
    const container = document.getElementById("toast-container");
    const toast = el("div", {
      class: "toast " + (isError ? "toast-err" : "toast-ok"),
      text: message,
    });
    container.appendChild(toast);
    window.setTimeout(() => {
      toast.remove();
    }, isError ? 5500 : 3500);
  }

  function showErrorBanner(message) {
    const banner = document.getElementById("error-banner");
    if (!message) {
      banner.classList.add("hidden");
      banner.textContent = "";
      return;
    }
    banner.textContent = message;
    banner.classList.remove("hidden");
  }

  async function apiGet(path) {
    const resp = await fetch(path, {
      method: "GET",
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      throw new Error(data.error || data.message || "Request failed (" + resp.status + ")");
    }
    return data;
  }

  async function apiPost(path, payload) {
    const resp = await fetch(path, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Mobpool-Token": CSRF_TOKEN,
        Accept: "application/json",
      },
      body: JSON.stringify(payload || {}),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const err = new Error(data.error || data.message || "Request failed (" + resp.status + ")");
      err.status = resp.status;
      err.payload = data;
      throw err;
    }
    return data;
  }

  function getOwnerInput() {
    const input = document.getElementById("input-owner");
    return (input ? input.value : "").trim();
  }

  function getTtlSecInput() {
    const input = document.getElementById("input-ttl-min");
    const mins = parseInt(input ? input.value : "60", 10);
    if (!Number.isFinite(mins) || mins < 1) return 3600;
    return Math.max(60, mins * 60);
  }

  function getKeepAppsPref() {
    const toggle = document.getElementById("keep-apps-toggle");
    return Boolean(toggle && toggle.checked);
  }

  function activeJobs() {
    if (!uiState.snapshot || !Array.isArray(uiState.snapshot.in_flight)) {
      return [];
    }
    return uiState.snapshot.in_flight;
  }

  function isDeviceBusy(deviceId) {
    return activeJobs().some((job) => job.device_id === deviceId || job.action === "init");
  }

  function isAcquireBusy(platform) {
    return activeJobs().some(
      (job) =>
        (job.action === "acquire" && job.platform === platform) ||
        job.action === "init"
    );
  }

  function openModal(options) {
    const backdrop = document.getElementById("modal-backdrop");
    const title = document.getElementById("modal-title");
    const body = document.getElementById("modal-body");
    const extra = document.getElementById("modal-extra");
    const confirmBtn = document.getElementById("modal-confirm");
    const cancelBtn = document.getElementById("modal-cancel");

    title.textContent = options.title || "Confirm";
    body.textContent = options.body || "";
    clearNode(extra);
    if (options.extraNode) {
      extra.appendChild(options.extraNode);
    }
    confirmBtn.textContent = options.confirmLabel || "Confirm";
    confirmBtn.className = "btn " + (options.confirmClass || "btn-danger");

    const cleanup = () => {
      backdrop.classList.add("hidden");
      confirmBtn.onclick = null;
      cancelBtn.onclick = null;
      backdrop.onclick = null;
      document.removeEventListener("keydown", onKey);
    };

    const onKey = (ev) => {
      if (ev.key === "Escape") cleanup();
    };

    cancelBtn.onclick = cleanup;
    backdrop.onclick = (ev) => {
      if (ev.target === backdrop) cleanup();
    };
    confirmBtn.onclick = async () => {
      cleanup();
      if (options.onConfirm) {
        await options.onConfirm();
      }
    };
    document.addEventListener("keydown", onKey);
    backdrop.classList.remove("hidden");
    confirmBtn.focus();
  }

  async function submitAction(path, payload) {
    try {
      const data = await apiPost(path, payload);
      if (data.job) {
        showToast(data.job.label + " started...", false);
        await fetchState(true);
        scheduleJobPoll();
      } else if (data.message) {
        showToast(data.message, false);
        await fetchState(true);
      }
    } catch (err) {
      showToast(err.message || String(err), true);
      await fetchState(true);
    }
  }

  function scheduleJobPoll() {
    if (uiState.jobTimer) {
      window.clearTimeout(uiState.jobTimer);
      uiState.jobTimer = null;
    }
    if (activeJobs().length === 0) return;
    uiState.jobTimer = window.setTimeout(async () => {
      uiState.jobTimer = null;
      await fetchState(false);
      if (activeJobs().length > 0) {
        scheduleJobPoll();
      }
    }, JOB_POLL_MS);
  }

  function scheduleNextPoll() {
    if (uiState.pollTimer) {
      window.clearTimeout(uiState.pollTimer);
      uiState.pollTimer = null;
    }
    if (!uiState.autoRefresh || document.visibilityState === "hidden") {
      return;
    }
    uiState.pollTimer = window.setTimeout(async () => {
      uiState.pollTimer = null;
      await fetchState(false);
    }, POLL_INTERVAL_MS);
  }

  function notifyNewCompletedJobs(recentJobs) {
    if (!Array.isArray(recentJobs)) return;
    const firstLoad = uiState.snapshot === null;
    for (const job of recentJobs) {
      if (job.status === "running") continue;
      if (uiState.seenCompletedJobs.has(job.id)) continue;
      uiState.seenCompletedJobs.add(job.id);
      if (!firstLoad) {
        const isErr = job.status !== "succeeded";
        showToast(job.message || (job.label + " " + job.status), isErr);
      }
    }
  }

  async function fetchState(forceRefresh) {
    if (uiState.loading) return;
    uiState.loading = true;
    try {
      const url = forceRefresh ? "/api/state?refresh=1" : "/api/state";
      const data = await apiGet(url);
      notifyNewCompletedJobs(data.recent_jobs);
      uiState.snapshot = data;
      showErrorBanner("");
      if (!uiState.ttlInitialized && data.config && data.config.default_ttl_sec) {
        const ttlInput = document.getElementById("input-ttl-min");
        if (ttlInput) {
          ttlInput.value = String(Math.max(1, Math.round(data.config.default_ttl_sec / 60)));
        }
        uiState.ttlInitialized = true;
      }
      renderAll();
      if (activeJobs().length > 0) {
        scheduleJobPoll();
      }
    } catch (err) {
      showErrorBanner("Failed to fetch mobpool state: " + (err.message || String(err)));
    } finally {
      uiState.loading = false;
      scheduleNextPoll();
    }
  }

  function renderSummary(state) {
    const grid = document.getElementById("summary-grid");
    clearNode(grid);

    const totalBooted = Number(state.total_booted || 0);
    const totalCap = Number((state.caps && state.caps.total) || 2);
    const iosCount = Number((state.counts && state.counts.ios) || 0);
    const iosCap = Number((state.caps && state.caps.ios) || 2);
    const androidCount = Number((state.counts && state.counts.android) || 0);
    const androidCap = Number((state.caps && state.caps.android) || 1);
    const totalPct = totalCap > 0 ? Math.min(100, Math.round((totalBooted / totalCap) * 100)) : 0;
    const capClass = totalBooted >= totalCap ? "danger" : totalPct >= 75 ? "warn" : "";

    const freePct = state.free_memory_pct;
    const minFree = Number(state.min_free_pct || 25);
    const memText = typeof freePct === "number" ? freePct + "%" : "n/a";
    const memBarWidth = typeof freePct === "number" ? Math.max(0, Math.min(100, freePct)) : 0;
    const memClass =
      typeof freePct === "number"
        ? freePct < minFree
          ? "danger"
          : freePct < minFree + 10
            ? "warn"
            : ""
        : "";

    const iosMeta = (state.platforms && state.platforms.ios) || {};
    const androidMeta = (state.platforms && state.platforms.android) || {};

    const cards = [
      el("div", { class: "metric-card" }, [
        el("div", { class: "metric-label", text: "Booted Devices" }),
        el("div", { class: "metric-value", text: totalBooted + " / " + totalCap }),
        el("progress", {
          class: "progress-bar " + capClass,
          max: "100",
          value: String(totalPct),
        }),
        el("div", { class: "metric-sub" }, [
          el("span", { text: "iOS " + iosCount + "/" + iosCap }),
          el("span", { text: "·" }),
          el("span", { text: "Android " + androidCount + "/" + androidCap }),
        ]),
      ]),
      el("div", { class: "metric-card" }, [
        el("div", { class: "metric-label", text: "Mac Free Memory" }),
        el("div", { class: "metric-value", text: memText }),
        el("progress", {
          class: "progress-bar " + memClass,
          max: "100",
          value: String(memBarWidth),
        }),
        el("div", { class: "metric-sub" }, [
          el("span", { text: "Safety floor: " + minFree + "%" }),
        ]),
      ]),
      el("div", { class: "metric-card" }, [
        el("div", { class: "metric-label", text: "Active Virtual RAM" }),
        el("div", { class: "metric-value", text: formatGb(state.total_ram_bytes) }),
        el("div", { class: "metric-sub" }, [
          el("span", {
            text:
              "Pool: iOS " +
              (iosMeta.pool_count || 0) +
              " · Android " +
              (androidMeta.pool_count || 0),
          }),
        ]),
      ]),
      el("div", { class: "metric-card" }, [
        el("div", { class: "metric-label", text: "Backends & Guardrails" }),
        el("div", { class: "row-inline" }, [
          el("span", {
            class: "badge " + (iosMeta.available ? "badge-ios" : "badge-other"),
            text: iosMeta.available
              ? "iOS ok (" + (iosMeta.installed_count || 0) + ")"
              : "iOS unavailable",
            title: iosMeta.reason || "",
          }),
          el("span", {
            class: "badge " + (androidMeta.available ? "badge-android" : "badge-other"),
            text: androidMeta.available
              ? "Android ok (" + (androidMeta.installed_count || 0) + ")"
              : "Android unavailable",
            title: androidMeta.reason || "",
          }),
        ]),
        el("div", { class: "metric-sub" }, [
          el("span", {
            text:
              "TTL " +
              Math.round(((state.config && state.config.default_ttl_sec) || 3600) / 60) +
              "m" +
              (state.config && state.config.app_id ? " · App guard on" : ""),
            title: state.config ? state.config.pool_file : "",
          }),
        ]),
      ]),
    ];

    for (const card of cards) {
      grid.appendChild(card);
    }

    const btnIos = document.getElementById("btn-acquire-ios");
    const btnAndroid = document.getElementById("btn-acquire-android");
    if (btnIos) {
      btnIos.disabled = !iosMeta.available || isAcquireBusy("ios");
      btnIos.title = iosMeta.available ? "Boot next free iOS pool simulator" : (iosMeta.reason || "");
    }
    if (btnAndroid) {
      btnAndroid.disabled = !androidMeta.available || isAcquireBusy("android");
      btnAndroid.title = androidMeta.available
        ? "Boot next free Android pool emulator"
        : (androidMeta.reason || "");
    }

    const updated = document.getElementById("last-updated");
    if (updated) {
      updated.textContent = "Updated " + formatTime(state.timestamp);
    }
  }

  function renderInFlight() {
    const banner = document.getElementById("inflight-banner");
    clearNode(banner);
    const jobs = activeJobs();
    if (jobs.length === 0) {
      banner.classList.add("hidden");
      return;
    }
    banner.classList.remove("hidden");
    for (const job of jobs) {
      const elapsed = Math.max(0, Math.round(Date.now() / 1000 - (job.started_at || 0)));
      banner.appendChild(
        el("div", { class: "inflight-row" }, [
          el("span", { class: "spinner", "aria-hidden": "true" }),
          el("strong", { text: job.label }),
          el("span", { class: "sub-text", text: "(" + elapsed + "s)" }),
        ])
      );
    }
  }

  function renderFilters(devices) {
    const platformTabs = document.getElementById("platform-tabs");
    clearNode(platformTabs);
    const iosTotal = devices.filter((d) => d.platform === "ios").length;
    const androidTotal = devices.filter((d) => d.platform === "android").length;
    const tabDefs = [
      { id: "all", label: "All (" + devices.length + ")" },
      { id: "ios", label: "iOS (" + iosTotal + ")" },
      { id: "android", label: "Android (" + androidTotal + ")" },
    ];
    for (const tab of tabDefs) {
      platformTabs.appendChild(
        el("button", {
          type: "button",
          class: "seg-btn" + (uiState.platformFilter === tab.id ? " active" : ""),
          text: tab.label,
          onClick: () => {
            uiState.platformFilter = tab.id;
            renderAll();
          },
        })
      );
    }

    const stateFilters = document.getElementById("state-filters");
    clearNode(stateFilters);
    const pillDefs = [
      { id: "all", label: "All" },
      { id: "booted", label: "Booted" },
      { id: "shutdown", label: "Shutdown" },
      { id: "pool", label: "In Pool" },
      { id: "claimed", label: "Claimed" },
      { id: "orphan", label: "Orphan" },
    ];
    for (const pill of pillDefs) {
      stateFilters.appendChild(
        el("button", {
          type: "button",
          class: "pill-btn" + (uiState.stateFilter === pill.id ? " active" : ""),
          text: pill.label,
          onClick: () => {
            uiState.stateFilter = pill.id;
            renderAll();
          },
        })
      );
    }
  }

  function matchesFilters(dev) {
    if (uiState.platformFilter !== "all" && dev.platform !== uiState.platformFilter) {
      return false;
    }
    if (uiState.stateFilter === "booted" && dev.state !== "Booted") return false;
    if (uiState.stateFilter === "shutdown" && dev.state === "Booted") return false;
    if (uiState.stateFilter === "pool" && !dev.in_pool) return false;
    if (uiState.stateFilter === "claimed" && !dev.owner) return false;
    if (uiState.stateFilter === "orphan" && !dev.is_orphan) return false;
    if (uiState.search) {
      const q = uiState.search.toLowerCase();
      const hay = [
        dev.name,
        dev.device_id,
        dev.target_id,
        dev.os_version,
        dev.platform,
        dev.tag,
        dev.owner ? dev.owner.label : "",
      ]
        .join(" ")
        .toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  }

  async function copyTargetId(targetId, btn) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(targetId);
      } else {
        const ta = el("textarea", { value: targetId });
        ta.value = targetId;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
      }
      const prev = btn.textContent;
      btn.textContent = "Copied";
      window.setTimeout(() => {
        btn.textContent = prev;
      }, 1200);
    } catch (_err) {
      showToast("Copy failed for " + targetId, true);
    }
  }

  function confirmForceRelease(dev) {
    const keepCheck = el("input", { type: "checkbox" });
    keepCheck.checked = getKeepAppsPref();
    const extra = el("label", { class: "toggle-pill" }, [
      keepCheck,
      el("span", { text: "Keep installed apps on device" }),
    ]);
    const ownerDesc = dev.owner ? dev.owner.display : "another session";
    openModal({
      title: "Force Release Protected Device?",
      body:
        dev.name +
        " (" +
        dev.target_id +
        ") is currently owned by " +
        ownerDesc +
        ".\n\nForcing release will shut down this device and interrupt that session.",
      extraNode: extra,
      confirmLabel: "Force Release",
      confirmClass: "btn-danger",
      onConfirm: () =>
        submitAction("/api/release", {
          device_id: dev.device_id,
          keep_apps: keepCheck.checked,
          force: true,
        }),
    });
  }

  function confirmForceSlim(dev) {
    const ownerDesc = dev.owner ? dev.owner.display : "another session";
    openModal({
      title: "Force Slim Booted Device?",
      body:
        dev.name +
        " (" +
        dev.device_id +
        ") is booted and owned by " +
        ownerDesc +
        ".\n\nRunning slim may reboot this device and disrupt that session.",
      confirmLabel: "Force Slim",
      confirmClass: "btn-danger",
      onConfirm: () =>
        submitAction("/api/slim", {
          device_id: dev.device_id,
          platform: dev.platform,
          force: true,
        }),
    });
  }

  function confirmNonPoolBoot(dev) {
    openModal({
      title: "Boot Non-Pool Device?",
      body:
        dev.name +
        " (" +
        dev.device_id +
        ") is not in the " +
        dev.platform +
        " pool.\n\nBooting it consumes a cap slot and marks it as an orphan once its TTL lease expires. Adding it to the pool first is recommended.",
      confirmLabel: "Prepare & Boot Anyway",
      confirmClass: "btn-primary",
      onConfirm: () =>
        submitAction("/api/acquire", {
          platform: dev.platform,
          device_id: dev.device_id,
          allow_non_pool: true,
          owner: getOwnerInput(),
          ttl_sec: getTtlSecInput(),
        }),
    });
  }

  function openInitPoolModal() {
    const platSelect = el("select", { class: "modal-select" }, [
      el("option", { value: "all", text: "All platforms (iOS + Android)" }),
      el("option", { value: "ios", text: "iOS only" }),
      el("option", { value: "android", text: "Android only" }),
    ]);
    const countInput = el("input", {
      type: "number",
      min: "1",
      max: "10",
      placeholder: "Default (platform cap)",
      class: "modal-select",
    });
    const extra = el("div", { class: "stack" }, [
      el("label", { class: "sub-text", text: "Target platform" }),
      platSelect,
      el("label", { class: "sub-text", text: "Pool count per platform (optional)" }),
      countInput,
    ]);
    openModal({
      title: "Initialize Device Pool?",
      body:
        "This replaces the saved pool list for the selected platform(s) with unowned devices and runs slim preparation (simslim / avdslim).",
      extraNode: extra,
      confirmLabel: "Run Init Pool",
      confirmClass: "btn-primary",
      onConfirm: () => {
        const rawCount = countInput.value.trim();
        const payload = { platform: platSelect.value };
        if (rawCount) {
          payload.count = parseInt(rawCount, 10);
        }
        return submitAction("/api/init", payload);
      },
    });
  }

  function renderOwnerCell(dev) {
    const wrap = el("div", { class: "stack" });
    if (dev.owner) {
      const cls = dev.owner.is_self ? "badge-self" : "badge-other";
      const prefix = dev.owner.is_self ? "Self · " : "Locked · ";
      wrap.appendChild(
        el("span", {
          class: "badge " + cls,
          text: prefix + dev.owner.source + ":" + dev.owner.label,
        })
      );
      if (typeof dev.owner.expires_in_sec === "number") {
        const mins = Math.max(0, Math.round(dev.owner.expires_in_sec / 60));
        wrap.appendChild(
          el("span", { class: "sub-text", text: "TTL: " + mins + "m remaining" })
        );
      } else {
        wrap.appendChild(
          el("span", { class: "sub-text", text: "External session owner" })
        );
      }
    } else if (dev.is_orphan) {
      wrap.appendChild(el("span", { class: "badge badge-orphan", text: "Orphan (unclaimed)" }));
      wrap.appendChild(el("span", { class: "sub-text", text: "Booted outside pool" }));
    } else if (dev.in_pool) {
      wrap.appendChild(el("span", { class: "badge badge-muted", text: "Pool (free)" }));
    } else {
      wrap.appendChild(el("span", { class: "sub-text", text: "Unclaimed" }));
    }
    return wrap;
  }

  function renderMetricsCell(dev) {
    const wrap = el("div", { class: "stack" });
    if (dev.state === "Booted") {
      const cpu = Number(dev.cpu_pct || 0).toFixed(1);
      wrap.appendChild(
        el("span", {
          class: "metrics-text",
          text: formatGb(dev.ram_bytes) + " · CPU " + cpu + "%",
        })
      );
      if (dev.slim_status) {
        const notSlim = dev.slim_status.includes("NOT slim");
        wrap.appendChild(
          el("span", {
            class: "badge " + (notSlim ? "badge-orphan" : "badge-muted"),
            text: dev.slim_status,
          })
        );
      }
    } else {
      wrap.appendChild(el("span", { class: "sub-text", text: "Shutdown" }));
      if (!dev.can_slim) {
        wrap.appendChild(
          el("span", { class: "sub-text", text: "Flags-slim on boot", title: dev.slim_note || "" })
        );
      }
    }
    return wrap;
  }

  function renderActionsCell(dev) {
    const cell = el("div", { class: "actions-cell" });
    const busy = isDeviceBusy(dev.device_id);
    const isBooted = dev.state === "Booted";
    const ownedByOther = Boolean(dev.owner && !dev.owner.is_self);

    if (isBooted) {
      if (dev.owner && dev.owner.source === "mobpool") {
        cell.appendChild(
          el("button", {
            type: "button",
            class: "btn btn-sm",
            text: "Renew",
            disabled: busy,
            title: "Extend TTL lease to " + Math.round(getTtlSecInput() / 60) + "m",
            onClick: () =>
              submitAction("/api/renew", {
                device_id: dev.device_id,
                ttl_sec: getTtlSecInput(),
              }),
          })
        );
      }

      cell.appendChild(
        el("button", {
          type: "button",
          class: "btn btn-sm",
          text: "Slim",
          disabled: busy || !dev.can_slim,
          title: dev.can_slim ? "Apply slimming profile" : dev.slim_note || "Slim unavailable",
          onClick: () => {
            if (ownedByOther) {
              confirmForceSlim(dev);
            } else {
              submitAction("/api/slim", {
                device_id: dev.device_id,
                platform: dev.platform,
                force: false,
              });
            }
          },
        })
      );

      if (ownedByOther) {
        cell.appendChild(
          el("button", {
            type: "button",
            class: "btn btn-sm btn-danger",
            text: "Force Release",
            disabled: busy,
            onClick: () => confirmForceRelease(dev),
          })
        );
      } else {
        cell.appendChild(
          el("button", {
            type: "button",
            class: "btn btn-sm btn-danger",
            text: dev.is_orphan ? "Shut down" : "Release",
            disabled: busy,
            onClick: () =>
              submitAction("/api/release", {
                device_id: dev.device_id,
                keep_apps: getKeepAppsPref(),
                force: false,
              }),
          })
        );
      }
    } else {
      if (dev.in_pool) {
        cell.appendChild(
          el("button", {
            type: "button",
            class: "btn btn-sm " + (dev.platform === "ios" ? "btn-ios" : "btn-android"),
            text: "Boot & Claim",
            disabled: busy || isAcquireBusy(dev.platform),
            onClick: () =>
              submitAction("/api/acquire", {
                platform: dev.platform,
                device_id: dev.device_id,
                allow_non_pool: false,
                owner: getOwnerInput(),
                ttl_sec: getTtlSecInput(),
              }),
          })
        );
        if (dev.can_slim) {
          cell.appendChild(
            el("button", {
              type: "button",
              class: "btn btn-sm",
              text: "Slim",
              disabled: busy,
              title: "Persist slim profile while keeping device shut down",
              onClick: () =>
                submitAction("/api/slim", {
                  device_id: dev.device_id,
                  platform: dev.platform,
                  force: false,
                }),
            })
          );
        }
        cell.appendChild(
          el("button", {
            type: "button",
            class: "btn btn-sm btn-ghost",
            text: "− Pool",
            disabled: busy,
            title: "Remove from pool",
            onClick: () =>
              submitAction("/api/pool", {
                platform: dev.platform,
                device_id: dev.device_id,
                in_pool: false,
              }),
          })
        );
      } else {
        cell.appendChild(
          el("button", {
            type: "button",
            class: "btn btn-sm btn-primary",
            text: "+ Add to Pool",
            disabled: busy,
            title: "Prepare slim profile and add to pool",
            onClick: () =>
              submitAction("/api/pool", {
                platform: dev.platform,
                device_id: dev.device_id,
                in_pool: true,
                prepare: true,
              }),
          })
        );
        cell.appendChild(
          el("button", {
            type: "button",
            class: "btn btn-sm",
            text: "Boot",
            disabled: busy || isAcquireBusy(dev.platform),
            title: "Boot outside pool (requires confirmation)",
            onClick: () => confirmNonPoolBoot(dev),
          })
        );
      }
    }

    return cell;
  }

  function renderDevices(devices) {
    const tbody = document.getElementById("device-tbody");
    const empty = document.getElementById("empty-state");
    clearNode(tbody);

    const filtered = devices.filter(matchesFilters);
    if (filtered.length === 0) {
      empty.classList.remove("hidden");
      return;
    }
    empty.classList.add("hidden");

    for (const dev of filtered) {
      const copyBtn = el("button", {
        type: "button",
        class: "btn btn-sm btn-ghost",
        text: "Copy ID",
        title: "Copy target ID: " + dev.target_id,
      });
      copyBtn.addEventListener("click", () => copyTargetId(dev.target_id, copyBtn));

      const idRowChildren = [
        el("span", { class: "mono-id", text: dev.device_id }),
      ];
      if (dev.target_id && dev.target_id !== dev.device_id) {
        idRowChildren.push(
          el("span", {
            class: "target-chip",
            text: dev.target_id,
            title: "Runtime target ID for adb / Argent",
          })
        );
      }
      idRowChildren.push(copyBtn);

      const tr = el("tr", null, [
        el("td", null, [
          el("div", { class: "device-cell" }, [
            el("div", { class: "device-title-row" }, [
              el("span", {
                class: "badge " + (dev.platform === "ios" ? "badge-ios" : "badge-android"),
                text: dev.platform === "ios" ? "iOS" : "Android",
              }),
              el("span", { class: "device-name", text: dev.name }),
              dev.os_version
                ? el("span", { class: "device-os", text: dev.os_version })
                : null,
            ]),
            el("div", { class: "device-id-row" }, idRowChildren),
          ]),
        ]),
        el("td", null, [
          el("div", { class: "stack" }, [
            el("span", {
              class: "badge " + (dev.state === "Booted" ? "badge-booted" : "badge-shutdown"),
              text: dev.state,
            }),
            dev.in_pool
              ? el("span", { class: "badge badge-pool", text: "In Pool" })
              : el("span", { class: "sub-text", text: "Non-Pool" }),
          ]),
        ]),
        el("td", null, [renderOwnerCell(dev)]),
        el("td", null, [renderMetricsCell(dev)]),
        el("td", null, [renderActionsCell(dev)]),
      ]);
      tbody.appendChild(tr);
    }
  }

  function renderActivity(recentJobs) {
    const list = document.getElementById("activity-list");
    const count = document.getElementById("activity-count");
    clearNode(list);
    const jobs = Array.isArray(recentJobs) ? recentJobs : [];
    count.textContent = jobs.length + (jobs.length === 1 ? " event" : " events");
    if (jobs.length === 0) {
      list.appendChild(el("div", { class: "sub-text", text: "No actions yet in this session." }));
      return;
    }
    for (const job of jobs) {
      const badgeCls =
        job.status === "succeeded"
          ? "badge-booted"
          : job.status === "running"
            ? "badge-self"
            : "badge-other";
      list.appendChild(
        el("div", { class: "activity-item" }, [
          el("span", { class: "activity-time", text: formatTime(job.finished_at || job.started_at) }),
          el("span", { class: "badge " + badgeCls, text: job.status }),
          el("div", { class: "activity-msg", text: job.label + (job.message ? " — " + job.message : "") }),
        ])
      );
    }
  }

  function renderAll() {
    const state = uiState.snapshot;
    if (!state) return;
    renderSummary(state);
    renderInFlight();
    const devices = Array.isArray(state.devices) ? state.devices : [];
    renderFilters(devices);
    renderDevices(devices);
    renderActivity(state.recent_jobs);
  }

  function bindEvents() {
    document.getElementById("btn-refresh").addEventListener("click", () => fetchState(true));
    document.getElementById("btn-init-pool").addEventListener("click", openInitPoolModal);
    document.getElementById("btn-acquire-ios").addEventListener("click", () =>
      submitAction("/api/acquire", {
        platform: "ios",
        owner: getOwnerInput(),
        ttl_sec: getTtlSecInput(),
      })
    );
    document.getElementById("btn-acquire-android").addEventListener("click", () =>
      submitAction("/api/acquire", {
        platform: "android",
        owner: getOwnerInput(),
        ttl_sec: getTtlSecInput(),
      })
    );
    document.getElementById("auto-refresh-toggle").addEventListener("change", (ev) => {
      uiState.autoRefresh = Boolean(ev.target.checked);
      if (uiState.autoRefresh) {
        scheduleNextPoll();
      } else if (uiState.pollTimer) {
        window.clearTimeout(uiState.pollTimer);
        uiState.pollTimer = null;
      }
    });
    document.getElementById("search-input").addEventListener("input", (ev) => {
      uiState.search = String(ev.target.value || "").trim();
      renderAll();
    });
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") {
        if (uiState.pollTimer) {
          window.clearTimeout(uiState.pollTimer);
          uiState.pollTimer = null;
        }
      } else if (uiState.autoRefresh) {
        fetchState(false);
      }
    });
  }

  bindEvents();
  fetchState(true);
})();
"""

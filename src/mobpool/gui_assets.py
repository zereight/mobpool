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
  <title>mobpool — iOS &amp; Android Device Pool</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <div class="app">
    <header class="header">
      <div class="title-group">
        <h1>mobpool</h1>
        <span class="subtitle">iOS &amp; Android device pool</span>
      </div>
      <div class="header-controls">
        <span id="last-updated" class="timestamp">Loading...</span>
        <label class="check-label" title="Auto-refresh every 8s while this tab is visible">
          <input id="auto-refresh-toggle" type="checkbox" checked>
          <span>Auto 8s</span>
        </label>
        <button id="btn-refresh" class="btn" type="button">Refresh</button>
        <button id="btn-init-pool" class="btn" type="button">Init pool</button>
      </div>
    </header>

    <section id="summary-grid" class="metrics-strip" aria-label="System summary"></section>

    <section class="lease-bar" aria-label="Quick acquire">
      <div class="lease-inputs">
        <label class="field">
          <span>Owner</span>
          <input id="input-owner" type="text" value="{escaped_owner}" placeholder="mobpool-gui" maxlength="80">
        </label>
        <label class="field field-ttl">
          <span>TTL (min)</span>
          <input id="input-ttl-min" type="number" min="1" max="1440" value="60">
        </label>
        <label class="check-label" title="Preserve installed apps when clicking Release">
          <input id="keep-apps-toggle" type="checkbox">
          <span>Keep apps on release</span>
        </label>
      </div>
      <div class="lease-actions">
        <button id="btn-acquire-ios" class="btn btn-primary" type="button">Acquire iOS</button>
        <button id="btn-acquire-android" class="btn btn-primary" type="button">Acquire Android</button>
      </div>
    </section>

    <section id="inflight-banner" class="notice notice-info hidden" aria-live="polite"></section>
    <section id="error-banner" class="notice notice-error hidden" role="alert"></section>

    <main class="surface">
      <div class="toolbar">
        <div class="toolbar-filters">
          <div id="platform-tabs" class="segmented" role="tablist" aria-label="Platform filter"></div>
          <div id="state-filters" class="state-tabs" role="group" aria-label="State filter"></div>
        </div>
        <div class="search-wrap">
          <input id="search-input" type="search" placeholder="Filter by name, UDID, AVD, owner...">
        </div>
      </div>

      <div class="table-wrap">
        <table class="device-table">
          <thead>
            <tr>
              <th class="col-device">Device</th>
              <th class="col-status">Status</th>
              <th class="col-owner">Ownership</th>
              <th class="col-metrics">Resources</th>
              <th class="col-actions">Actions</th>
            </tr>
          </thead>
          <tbody id="device-tbody"></tbody>
        </table>
        <div id="empty-state" class="empty-state hidden">No matching devices.</div>
      </div>
    </main>

    <footer id="activity-panel" class="activity-footer is-empty">
      <div class="activity-head">
        <h2>Activity</h2>
        <span id="activity-count" class="activity-count">0 events</span>
      </div>
      <div id="activity-list" class="activity-list"></div>
    </footer>
  </div>

  <div id="toast-container" class="toast-container" aria-live="polite"></div>

  <div id="modal-backdrop" class="modal-backdrop hidden" role="dialog" aria-modal="true" aria-labelledby="modal-title">
    <div class="modal-card">
      <h3 id="modal-title"></h3>
      <p id="modal-body" class="modal-body"></p>
      <div id="modal-extra" class="modal-extra"></div>
      <div class="modal-footer">
        <button id="modal-cancel" class="btn" type="button">Cancel</button>
        <button id="modal-confirm" class="btn btn-danger-solid" type="button">Confirm</button>
      </div>
    </div>
  </div>

  <script src="/app.js" defer></script>
</body>
</html>
"""


STYLES_CSS = r"""
:root {
  color-scheme: light dark;
  --bg: #f6f6f7;
  --surface: #ffffff;
  --surface-subtle: #f1f1f3;
  --surface-hover: #f5f5f7;
  --border: #e4e4e7;
  --border-strong: #d1d1d6;
  --text: #141416;
  --text-secondary: #52525b;
  --text-muted: #71717a;
  --ink-bg: #18181b;
  --ink-bg-hover: #27272a;
  --ink-text: #ffffff;
  --focus: #2563eb;
  --green: #16a34a;
  --amber: #b45309;
  --red: #dc2626;
  --red-subtle: #fef2f2;
  --red-border: #fecaca;
  --radius: 6px;
  --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", "Segoe UI", sans-serif;
  --font-mono: ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0e0e10;
    --surface: #151518;
    --surface-subtle: #1c1c20;
    --surface-hover: #1d1d22;
    --border: #26262b;
    --border-strong: #36363d;
    --text: #f1f1f4;
    --text-secondary: #a1a1aa;
    --text-muted: #7c7c86;
    --ink-bg: #f4f4f5;
    --ink-bg-hover: #e4e4e7;
    --ink-text: #111113;
    --focus: #60a5fa;
    --green: #22c55e;
    --amber: #f59e0b;
    --red: #f87171;
    --red-subtle: rgba(239, 68, 68, 0.1);
    --red-border: rgba(239, 68, 68, 0.3);
  }
}

* {
  box-sizing: border-box;
}

html, body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  font-size: 13px;
  line-height: 1.45;
  -webkit-font-smoothing: antialiased;
}

button, input, select {
  font: inherit;
  color: inherit;
}

:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: 1px;
}

.hidden {
  display: none !important;
}

.app {
  max-width: 1240px;
  margin: 0 auto;
  padding: 20px 24px 36px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding-bottom: 4px;
}

.title-group {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.title-group h1 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.subtitle {
  font-size: 12px;
  color: var(--text-muted);
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.timestamp {
  font-size: 12px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.check-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  user-select: none;
}

.check-label input[type="checkbox"] {
  margin: 0;
  width: 14px;
  height: 14px;
  accent-color: var(--ink-bg);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  padding: 0 10px;
  border-radius: var(--radius);
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--text);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  transition: background-color 180ms ease, border-color 180ms ease;
}

.btn:hover:not(:disabled) {
  background: var(--surface-subtle);
  border-color: var(--text-muted);
  transition-duration: 120ms;
}

.btn:active:not(:disabled) {
  background: var(--border);
  transition-duration: 0ms;
}

.btn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--ink-bg);
  border-color: var(--ink-bg);
  color: var(--ink-text);
}

.btn-primary:hover:not(:disabled) {
  background: var(--ink-bg-hover);
  border-color: var(--ink-bg-hover);
}

.btn-primary:active:not(:disabled) {
  opacity: 0.85;
  transition-duration: 0ms;
}

.btn-emphasis {
  background: var(--surface-subtle);
  border-color: var(--border-strong);
  color: var(--text);
}

.btn-ghost {
  background: transparent;
  border-color: transparent;
  color: var(--text-secondary);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--surface-subtle);
  border-color: var(--border);
  color: var(--text);
}

.btn-danger {
  background: transparent;
  border-color: var(--red-border);
  color: var(--red);
}

.btn-danger:hover:not(:disabled) {
  background: var(--red-subtle);
  border-color: var(--red);
}

.btn-danger-solid {
  background: var(--red);
  border-color: var(--red);
  color: #ffffff;
}

.btn-danger-solid:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-sm {
  height: 26px;
  padding: 0 9px;
  font-size: 12px;
}

.btn-copy {
  height: 20px;
  min-width: 48px;
  padding: 0 6px;
  font-size: 11px;
  font-weight: 500;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-muted);
}

.btn-copy:hover:not(:disabled) {
  background: var(--surface-subtle);
  border-color: var(--border-strong);
  color: var(--text);
}

.metrics-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.metric-cell {
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-right: 1px solid var(--border);
}

.metric-cell:last-child {
  border-right: none;
}

.metric-label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
}

.metric-main {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-variant-numeric: tabular-nums;
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.metric-value.is-warn {
  color: var(--amber);
}

.metric-value.is-danger {
  color: var(--red);
}

.metric-detail {
  font-size: 12px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lease-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 8px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.lease-inputs {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.field input {
  height: 28px;
  padding: 0 8px;
  border-radius: var(--radius);
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--text);
  font-size: 12px;
  width: 148px;
}

.field-ttl input {
  width: 66px;
  font-variant-numeric: tabular-nums;
}

.lease-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.notice {
  padding: 8px 12px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--surface);
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.notice-error {
  border-color: var(--red-border);
  background: var(--red-subtle);
  color: var(--red);
}

.inflight-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.spinner {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1.5px solid var(--border-strong);
  border-top-color: var(--text);
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.surface {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
}

.toolbar-filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.segmented {
  display: inline-flex;
  background: var(--surface-subtle);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2px;
  gap: 2px;
}

.seg-btn {
  height: 24px;
  padding: 0 9px;
  border-radius: 4px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.seg-btn:hover:not(.active) {
  color: var(--text);
}

.seg-btn.active {
  background: var(--surface);
  border-color: var(--border);
  color: var(--text);
}

.state-tabs {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  flex-wrap: wrap;
}

.filter-btn {
  height: 26px;
  padding: 0 8px;
  border-radius: 4px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.filter-btn:hover:not(.active) {
  background: var(--surface-subtle);
  color: var(--text);
}

.filter-btn.active {
  background: var(--surface-subtle);
  border-color: var(--border-strong);
  color: var(--text);
}

.search-wrap {
  flex: 0 1 240px;
  min-width: 180px;
}

.search-wrap input {
  width: 100%;
  height: 28px;
  padding: 0 10px;
  border-radius: var(--radius);
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--text);
  font-size: 12px;
}

.table-wrap {
  overflow-x: auto;
}

.device-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: auto;
}

.device-table th {
  text-align: left;
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

.device-table td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}

.device-table tbody tr:last-child td {
  border-bottom: none;
}

.device-table tbody tr:hover {
  background: var(--surface-hover);
}

.device-table tbody tr.is-booted {
  background: var(--surface);
}

.col-actions {
  text-align: right;
  width: 1%;
  white-space: nowrap;
}

.device-table th.col-actions {
  text-align: right;
}

.device-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 260px;
}

.device-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.plat-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 50px;
  height: 18px;
  flex-shrink: 0;
  border-radius: 4px;
  border: 1px solid var(--border-strong);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--text-secondary);
}

.device-name {
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 240px;
}

.device-os {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.device-id-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 58px;
}

.mono-id {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

.status-cell,
.owner-cell,
.metrics-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.status-line {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  white-space: nowrap;
}

.status-line.is-muted {
  color: var(--text-muted);
  font-weight: 400;
}

.status-line.is-danger {
  color: var(--red);
}

.status-line.is-warn {
  color: var(--amber);
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--border-strong);
}

.dot-booted {
  background: var(--green);
}

.dot-locked {
  background: var(--red);
}

.dot-self {
  background: var(--focus);
}

.dot-warn {
  background: var(--amber);
}

.pool-flag {
  display: inline-block;
  width: fit-content;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  padding-left: 12px;
}

.sub-text {
  font-size: 11px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.metrics-text {
  font-size: 12px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.actions-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  white-space: nowrap;
}

.empty-state {
  padding: 28px 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
}

.activity-footer {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 8px 12px;
}

.activity-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.activity-head h2 {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.activity-count {
  font-size: 11px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.activity-footer.is-empty .activity-list {
  display: none;
}

.activity-list {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 200px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 12px;
}

.activity-time {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.activity-status {
  font-size: 11px;
  font-weight: 500;
  flex-shrink: 0;
  min-width: 66px;
}

.activity-status.is-ok {
  color: var(--green);
}

.activity-status.is-err {
  color: var(--red);
}

.activity-msg {
  color: var(--text-secondary);
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
  max-width: 360px;
}

.toast {
  padding: 9px 12px;
  border-radius: var(--radius);
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--text);
  font-size: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.toast-err {
  border-color: var(--red-border);
  color: var(--red);
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 60;
}

.modal-card {
  width: 100%;
  max-width: 440px;
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-card h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  text-wrap: balance;
}

.modal-body {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
  white-space: pre-line;
  text-wrap: pretty;
}

.modal-extra {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.modal-select {
  height: 30px;
  padding: 0 8px;
  border-radius: var(--radius);
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--text);
  font-size: 12px;
  width: 100%;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 4px;
}

@media (max-width: 860px) {
  .app {
    padding: 14px;
  }
  .metrics-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .metric-cell:nth-child(2) {
    border-right: none;
  }
  .metric-cell:nth-child(1),
  .metric-cell:nth-child(2) {
    border-bottom: 1px solid var(--border);
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
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
        node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
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
    return new Date(epochSec * 1000).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function showToast(message, isError) {
    const container = document.getElementById("toast-container");
    const toast = el("div", {
      class: "toast" + (isError ? " toast-err" : ""),
      text: message,
    });
    container.appendChild(toast);
    window.setTimeout(() => toast.remove(), isError ? 5500 : 3200);
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
      (job) => (job.action === "acquire" && job.platform === platform) || job.action === "init"
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
    confirmBtn.className = "btn " + (options.confirmClass || "btn-danger-solid");

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
        showToast(data.job.label + " started", false);
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
        showToast(job.message || (job.label + " " + job.status), job.status !== "succeeded");
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
    const capTone = totalBooted >= totalCap ? " is-danger" : "";

    const freePct = state.free_memory_pct;
    const minFree = Number(state.min_free_pct || 25);
    const memText = typeof freePct === "number" ? freePct + "%" : "n/a";
    const memTone =
      typeof freePct === "number"
        ? freePct < minFree
          ? " is-danger"
          : freePct < minFree + 10
            ? " is-warn"
            : ""
        : "";

    const iosMeta = (state.platforms && state.platforms.ios) || {};
    const androidMeta = (state.platforms && state.platforms.android) || {};
    const ttlMins = Math.round(((state.config && state.config.default_ttl_sec) || 3600) / 60);

    const backendValue =
      (iosMeta.available ? "iOS " + (iosMeta.installed_count || 0) : "iOS off") +
      " · " +
      (androidMeta.available ? "Android " + (androidMeta.installed_count || 0) : "Android off");
    const backendDetail =
      "TTL " + ttlMins + "m" + (state.config && state.config.app_id ? " · App guard on" : "");

    const cells = [
      {
        label: "Booted",
        value: totalBooted + " / " + totalCap,
        tone: capTone,
        detail: "iOS " + iosCount + "/" + iosCap + " · Android " + androidCount + "/" + androidCap,
      },
      {
        label: "Mac free memory",
        value: memText,
        tone: memTone,
        detail: "Floor " + minFree + "%",
      },
      {
        label: "Virtual RAM",
        value: formatGb(state.total_ram_bytes),
        tone: "",
        detail: "Pool: iOS " + (iosMeta.pool_count || 0) + " · Android " + (androidMeta.pool_count || 0),
      },
      {
        label: "Backends",
        value: backendValue,
        tone: !iosMeta.available && !androidMeta.available ? " is-danger" : "",
        detail: backendDetail,
        title: [iosMeta.reason, androidMeta.reason].filter((r) => r && r !== "ok").join(" | "),
      },
    ];

    for (const item of cells) {
      grid.appendChild(
        el("div", { class: "metric-cell", title: item.title || null }, [
          el("span", { class: "metric-label", text: item.label }),
          el("div", { class: "metric-main" }, [
            el("span", { class: "metric-value" + item.tone, text: item.value }),
          ]),
          el("span", { class: "metric-detail", text: item.detail }),
        ])
      );
    }

    const btnIos = document.getElementById("btn-acquire-ios");
    const btnAndroid = document.getElementById("btn-acquire-android");
    if (btnIos) {
      btnIos.disabled = !iosMeta.available || isAcquireBusy("ios");
      btnIos.title = iosMeta.available ? "Boot next free iOS pool simulator" : iosMeta.reason || "";
    }
    if (btnAndroid) {
      btnAndroid.disabled = !androidMeta.available || isAcquireBusy("android");
      btnAndroid.title = androidMeta.available
        ? "Boot next free Android pool emulator"
        : androidMeta.reason || "";
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
          el("span", { class: "sub-text", text: elapsed + "s" }),
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
          role: "tab",
          "aria-selected": String(uiState.platformFilter === tab.id),
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
    const defs = [
      { id: "all", label: "All" },
      { id: "booted", label: "Booted" },
      { id: "shutdown", label: "Shutdown" },
      { id: "pool", label: "In Pool" },
      { id: "claimed", label: "Claimed" },
      { id: "orphan", label: "Orphan" },
    ];
    for (const item of defs) {
      stateFilters.appendChild(
        el("button", {
          type: "button",
          class: "filter-btn" + (uiState.stateFilter === item.id ? " active" : ""),
          text: item.label,
          onClick: () => {
            uiState.stateFilter = item.id;
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
    const extra = el("label", { class: "check-label" }, [
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
        ".\n\nForcing release shuts down this device and interrupts that session.",
      extraNode: extra,
      confirmLabel: "Force Release",
      confirmClass: "btn-danger-solid",
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
      confirmClass: "btn-danger-solid",
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
        " pool.\n\nBooting it consumes a cap slot and marks it as an orphan once its lease expires. Adding it to the pool first is recommended.",
      confirmLabel: "Prepare & Boot",
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
    const extra = el("div", { class: "modal-extra" }, [
      el("label", { class: "sub-text", text: "Target platform" }),
      platSelect,
      el("label", { class: "sub-text", text: "Pool count per platform (optional)" }),
      countInput,
    ]);
    openModal({
      title: "Initialize Device Pool?",
      body:
        "Replaces the saved pool for the selected platform(s) with unowned devices and runs slim preparation.",
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
    const wrap = el("div", { class: "owner-cell" });
    if (dev.owner) {
      const isSelf = Boolean(dev.owner.is_self);
      wrap.appendChild(
        el("span", { class: "status-line" + (isSelf ? "" : " is-danger") }, [
          el("span", { class: "dot " + (isSelf ? "dot-self" : "dot-locked") }),
          el("span", {
            text: (isSelf ? "Self · " : "Locked · ") + dev.owner.source + ":" + dev.owner.label,
          }),
        ])
      );
      if (typeof dev.owner.expires_in_sec === "number") {
        const mins = Math.max(0, Math.round(dev.owner.expires_in_sec / 60));
        wrap.appendChild(el("span", { class: "sub-text", text: mins + "m left" }));
      } else {
        wrap.appendChild(el("span", { class: "sub-text", text: "External session" }));
      }
    } else if (dev.is_orphan) {
      wrap.appendChild(
        el("span", { class: "status-line is-warn" }, [
          el("span", { class: "dot dot-warn" }),
          el("span", { text: "Orphan" }),
        ])
      );
      wrap.appendChild(el("span", { class: "sub-text", text: "Booted outside pool" }));
    } else if (dev.in_pool) {
      wrap.appendChild(el("span", { class: "sub-text", text: "Free (pool)" }));
    } else {
      wrap.appendChild(el("span", { class: "sub-text", text: "—" }));
    }
    return wrap;
  }

  function renderMetricsCell(dev) {
    const wrap = el("div", { class: "metrics-cell" });
    if (dev.state === "Booted") {
      const cpu = Number(dev.cpu_pct || 0).toFixed(1);
      wrap.appendChild(
        el("span", {
          class: "metrics-text",
          text: formatGb(dev.ram_bytes) + " · " + cpu + "% CPU",
        })
      );
      if (dev.slim_status) {
        const notSlim = dev.slim_status.includes("NOT slim");
        wrap.appendChild(
          el("span", {
            class: "sub-text" + (notSlim ? " is-warn" : ""),
            text: dev.slim_status,
          })
        );
      }
    } else if (!dev.can_slim) {
      wrap.appendChild(
        el("span", {
          class: "sub-text",
          text: "Flags-slim on boot",
          title: dev.slim_note || "",
        })
      );
    } else {
      wrap.appendChild(el("span", { class: "sub-text", text: "—" }));
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
            title: "Extend lease TTL",
            onClick: () =>
              submitAction("/api/renew", {
                device_id: dev.device_id,
                ttl_sec: getTtlSecInput(),
              }),
          })
        );
      }
      if (dev.can_slim) {
        cell.appendChild(
          el("button", {
            type: "button",
            class: "btn btn-sm",
            text: "Slim",
            disabled: busy,
            title: "Apply slimming profile",
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
      }
      cell.appendChild(
        el("button", {
          type: "button",
          class: "btn btn-sm btn-danger",
          text: ownedByOther ? "Force Release" : dev.is_orphan ? "Shut down" : "Release",
          disabled: busy,
          onClick: () => {
            if (ownedByOther) {
              confirmForceRelease(dev);
            } else {
              submitAction("/api/release", {
                device_id: dev.device_id,
                keep_apps: getKeepAppsPref(),
                force: false,
              });
            }
          },
        })
      );
      return cell;
    }

    if (dev.in_pool) {
      cell.appendChild(
        el("button", {
          type: "button",
          class: "btn btn-sm btn-emphasis",
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
            title: "Persist slim profile while shut down",
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
          text: "Remove",
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
          class: "btn btn-sm",
          text: "Add to pool",
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
          class: "btn btn-sm btn-ghost",
          text: "Boot",
          disabled: busy || isAcquireBusy(dev.platform),
          title: "Boot outside pool (requires confirmation)",
          onClick: () => confirmNonPoolBoot(dev),
        })
      );
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
      const idLabel =
        dev.runtime_id && dev.runtime_id !== dev.device_id
          ? dev.device_id + " · " + dev.runtime_id
          : dev.device_id;
      const copyBtn = el("button", {
        type: "button",
        class: "btn-copy",
        text: "Copy",
        title: "Copy target ID (" + dev.target_id + ")",
      });
      copyBtn.addEventListener("click", () => copyTargetId(dev.target_id, copyBtn));

      const isBooted = dev.state === "Booted";
      const tr = el("tr", { class: isBooted ? "is-booted" : "" }, [
        el("td", null, [
          el("div", { class: "device-cell" }, [
            el("div", { class: "device-head" }, [
              el("span", {
                class: "plat-tag",
                text: dev.platform === "ios" ? "iOS" : "Android",
              }),
              el("span", { class: "device-name", text: dev.name, title: dev.name }),
              dev.os_version
                ? el("span", { class: "device-os", text: dev.os_version })
                : null,
            ]),
            el("div", { class: "device-id-row" }, [
              el("span", { class: "mono-id", text: idLabel }),
              copyBtn,
            ]),
          ]),
        ]),
        el("td", null, [
          el("div", { class: "status-cell" }, [
            el("span", { class: "status-line" + (isBooted ? "" : " is-muted") }, [
              el("span", { class: "dot" + (isBooted ? " dot-booted" : "") }),
              el("span", { text: dev.state }),
            ]),
            dev.in_pool ? el("span", { class: "pool-flag", text: "In pool" }) : null,
          ]),
        ]),
        el("td", null, [renderOwnerCell(dev)]),
        el("td", null, [renderMetricsCell(dev)]),
        el("td", { class: "col-actions" }, [renderActionsCell(dev)]),
      ]);
      tbody.appendChild(tr);
    }
  }

  function renderActivity(recentJobs) {
    const panel = document.getElementById("activity-panel");
    const list = document.getElementById("activity-list");
    const count = document.getElementById("activity-count");
    clearNode(list);
    const jobs = Array.isArray(recentJobs) ? recentJobs : [];
    count.textContent = jobs.length + (jobs.length === 1 ? " event" : " events");
    panel.classList.toggle("is-empty", jobs.length === 0);
    if (jobs.length === 0) return;

    for (const job of jobs) {
      const cls =
        job.status === "succeeded"
          ? " is-ok"
          : job.status === "running"
            ? ""
            : " is-err";
      list.appendChild(
        el("div", { class: "activity-item" }, [
          el("span", { class: "activity-time", text: formatTime(job.finished_at || job.started_at) }),
          el("span", { class: "activity-status" + cls, text: job.status }),
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

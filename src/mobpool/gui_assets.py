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
  <title>mobpool — Virtual Devices</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <h1>mobpool</h1>
        <span id="status-pill" class="status-pill">Loading...</span>
      </div>
      <div class="topbar-actions">
        <button id="btn-refresh" class="btn btn-quiet" type="button" title="Refresh device list">Refresh</button>
        <button id="btn-settings" class="btn btn-quiet" type="button" aria-expanded="false" aria-controls="settings-panel">Settings</button>
      </div>
    </header>

    <section id="settings-panel" class="settings-panel hidden" aria-label="Settings">
      <div class="settings-grid">
        <label class="setting-field">
          <span class="setting-label">Your name</span>
          <input id="input-owner" type="text" value="{escaped_owner}" placeholder="mobpool-gui" maxlength="80">
          <span class="setting-help">Shown on devices you start</span>
        </label>
        <label class="setting-field">
          <span class="setting-label">Lock duration (minutes)</span>
          <input id="input-ttl-min" type="number" min="1" max="1440" value="60">
          <span class="setting-help">Reserves the device for you (does not auto-shut down)</span>
        </label>
      </div>
      <div class="settings-checks">
        <label class="check-row">
          <input id="keep-apps-toggle" type="checkbox">
          <span>
            <strong>Keep installed apps when stopping</strong>
            <small>When off, Stop cleans apps and resets iOS keychain.</small>
          </span>
        </label>
        <label class="check-row">
          <input id="auto-refresh-toggle" type="checkbox" checked>
          <span>
            <strong>Auto-refresh every 8 seconds</strong>
            <small id="last-updated">Updating...</small>
          </span>
        </label>
      </div>
      <div class="settings-footer">
        <button id="btn-init-pool" class="btn" type="button">Auto-pick Quick-start devices...</button>
      </div>
    </section>

    <section class="hero" aria-label="Quick start">
      <button id="btn-acquire-ios" class="start-card" type="button">
        <span class="start-card-main">
          <span class="start-card-title">Start iOS</span>
          <span id="sub-acquire-ios" class="start-card-sub">Checking simulators...</span>
        </span>
        <span class="start-card-arrow" aria-hidden="true">+</span>
      </button>
      <button id="btn-acquire-android" class="start-card" type="button">
        <span class="start-card-main">
          <span class="start-card-title">Start Android</span>
          <span id="sub-acquire-android" class="start-card-sub">Checking emulators...</span>
        </span>
        <span class="start-card-arrow" aria-hidden="true">+</span>
      </button>
    </section>

    <section id="guard-banner" class="notice notice-warn hidden" aria-live="polite"></section>
    <section id="inflight-banner" class="notice notice-info hidden" aria-live="polite"></section>
    <section id="error-banner" class="notice notice-error hidden" role="alert"></section>

    <main class="sections">
      <section class="panel" aria-labelledby="heading-running">
        <div class="panel-head">
          <div class="panel-title-wrap">
            <h2 id="heading-running">Running</h2>
            <span id="running-count" class="count-pill">0</span>
          </div>
          <span id="running-ram" class="panel-hint"></span>
        </div>
        <div id="running-list" class="device-list"></div>
      </section>

      <section class="panel" aria-labelledby="heading-quickstart">
        <div class="panel-head panel-head-wrap">
          <div class="panel-title-block">
            <div class="panel-title-wrap">
              <h2 id="heading-quickstart">Quick-start</h2>
              <span id="quickstart-count" class="count-pill">0</span>
            </div>
            <p class="panel-sub">Devices picked by Start iOS and Start Android</p>
          </div>
          <div id="platform-tabs" class="segmented" role="tablist" aria-label="Platform filter"></div>
        </div>
        <div id="quickstart-list" class="device-list"></div>
      </section>

      <section class="panel" aria-labelledby="heading-other">
        <div class="other-bar">
          <button id="btn-toggle-other" class="collapse-toggle" type="button" aria-expanded="false" aria-controls="other-body">
            <span id="other-chevron" class="chevron" aria-hidden="true">&#9656;</span>
            <span id="heading-other" class="collapse-title">Other installed devices</span>
            <span id="other-count" class="count-pill">0</span>
          </button>
          <input id="search-input" class="search-input" type="search" placeholder="Search devices...">
        </div>
        <div id="other-body" class="other-body hidden">
          <div id="other-list" class="device-list"></div>
        </div>
      </section>
    </main>

    <footer class="activity-footer">
      <button id="btn-toggle-activity" class="collapse-toggle collapse-toggle-sm" type="button" aria-expanded="false" aria-controls="activity-body">
        <span id="activity-chevron" class="chevron" aria-hidden="true">&#9656;</span>
        <span>Recent activity</span>
        <span id="activity-count" class="count-pill">0</span>
      </button>
      <div id="activity-body" class="activity-body hidden">
        <div id="activity-list" class="activity-list"></div>
      </div>
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
  --bg: #f5f5f7;
  --surface: #ffffff;
  --surface-subtle: #f8f8fa;
  --surface-hover: #f0f1f4;
  --border: #e4e4e9;
  --border-strong: #d1d1da;
  --text: #16161a;
  --text-secondary: #585866;
  --text-muted: #7e7e8f;
  --primary: #18181c;
  --primary-hover: #2d2d35;
  --primary-text: #ffffff;
  --accent: #2563eb;
  --accent-bg: rgba(37, 99, 235, 0.09);
  --green: #16803d;
  --green-bg: rgba(22, 128, 61, 0.11);
  --amber: #a86108;
  --amber-bg: rgba(168, 97, 8, 0.11);
  --red: #c62828;
  --red-bg: rgba(198, 40, 40, 0.1);
  --radius-lg: 14px;
  --radius-md: 10px;
  --radius-sm: 8px;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-pop: 0 12px 32px rgba(0, 0, 0, 0.14);
  --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", system-ui, sans-serif;
  --font-mono: ui-monospace, "SF Mono", Menlo, Monaco, monospace;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111114;
    --surface: #18181c;
    --surface-subtle: #1e1e24;
    --surface-hover: #25252d;
    --border: #2a2a33;
    --border-strong: #3a3a46;
    --text: #f3f3f6;
    --text-secondary: #a7a7b5;
    --text-muted: #7c7c8c;
    --primary: #f3f3f6;
    --primary-hover: #dcdce3;
    --primary-text: #111114;
    --accent: #60a5fa;
    --accent-bg: rgba(96, 165, 250, 0.14);
    --green: #4ade80;
    --green-bg: rgba(74, 222, 128, 0.13);
    --amber: #fbbf24;
    --amber-bg: rgba(251, 191, 36, 0.13);
    --red: #f87171;
    --red-bg: rgba(248, 113, 113, 0.14);
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.25);
    --shadow-pop: 0 14px 36px rgba(0, 0, 0, 0.55);
  }
}

*, *::before, *::after {
  box-sizing: border-box;
}

html, body {
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.45;
  -webkit-font-smoothing: antialiased;
}

.hidden {
  display: none !important;
}

.app {
  max-width: 860px;
  margin: 0 auto;
  padding: 24px 20px 44px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.brand h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.025em;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--surface);
  border: 1px solid var(--border);
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.status-pill.is-warn {
  color: var(--amber);
  background: var(--amber-bg);
  border-color: transparent;
}

.status-pill.is-danger {
  color: var(--red);
  background: var(--red-bg);
  border-color: transparent;
}

.topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn {
  appearance: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
  padding: 0 13px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.12s ease, border-color 0.12s ease, opacity 0.12s ease;
}

.btn:hover:not(:disabled) {
  background: var(--surface-hover);
}

.btn:focus-visible,
.start-card:focus-visible,
.collapse-toggle:focus-visible,
.seg-btn:focus-visible,
.menu-item:focus-visible,
input:focus-visible,
select:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.btn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.btn-quiet {
  border-color: var(--border);
  color: var(--text-secondary);
}

.btn-quiet.is-active {
  background: var(--surface-hover);
  border-color: var(--border-strong);
  color: var(--text);
}

.btn-primary {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--primary-text);
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
}

.btn-danger {
  color: var(--red);
  border-color: var(--border-strong);
}

.btn-danger:hover:not(:disabled) {
  background: var(--red-bg);
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
  height: 30px;
  padding: 0 11px;
  font-size: 12.5px;
}

.btn-icon {
  width: 30px;
  height: 30px;
  padding: 0;
  font-size: 15px;
  line-height: 1;
}

.btn-copy {
  height: 22px;
  padding: 0 7px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
  cursor: pointer;
  transition: background-color 0.12s ease, color 0.12s ease;
}

.btn-copy:hover {
  background: var(--surface-hover);
  color: var(--text);
}

.btn-copy.copied {
  color: var(--green);
  background: var(--green-bg);
}

.settings-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px 18px;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.settings-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.setting-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.setting-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
}

.setting-field input,
.modal-select,
.modal-input {
  height: 34px;
  padding: 0 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--text);
  font-family: inherit;
  font-size: 13px;
}

.setting-help {
  font-size: 11.5px;
  color: var(--text-muted);
}

.settings-checks {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 2px;
}

.check-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  cursor: pointer;
  font-size: 13px;
}

.check-row input[type="checkbox"] {
  margin-top: 3px;
  accent-color: var(--accent);
  cursor: pointer;
}

.check-row span {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.check-row strong {
  font-weight: 500;
  color: var(--text);
}

.check-row small {
  font-size: 12px;
  color: var(--text-muted);
}

.settings-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}

.hero {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.start-card {
  appearance: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 18px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: border-color 0.14s ease, background-color 0.14s ease, transform 0.1s ease;
}

.start-card:hover:not(:disabled) {
  border-color: var(--border-strong);
  background: var(--surface-subtle);
}

.start-card:active:not(:disabled) {
  transform: translateY(1px);
}

.start-card:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.start-card-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.start-card-title {
  font-size: 16px;
  font-weight: 650;
  letter-spacing: -0.015em;
}

.start-card-sub {
  font-size: 12.5px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.start-card-arrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  background: var(--primary);
  color: var(--primary-text);
  font-size: 18px;
  font-weight: 500;
  flex-shrink: 0;
}

.start-card:disabled .start-card-arrow {
  background: var(--border-strong);
  color: var(--text-muted);
}

.notice {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 13px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.notice-info {
  background: var(--accent-bg);
  color: var(--text);
  border: 1px solid var(--border);
}

.notice-warn {
  background: var(--amber-bg);
  color: var(--amber);
}

.notice-error {
  background: var(--red-bg);
  color: var(--red);
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.inflight-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--border-strong);
  border-top-color: var(--accent);
  animation: spin 0.75s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
}

.panel-head-wrap {
  flex-wrap: wrap;
}

.panel-title-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.panel-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-head h2 {
  margin: 0;
  font-size: 14.5px;
  font-weight: 650;
  letter-spacing: -0.01em;
}

.panel-sub {
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
}

.panel-hint {
  font-size: 12px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.count-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  background: var(--surface-subtle);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  font-size: 11.5px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.segmented {
  display: inline-flex;
  padding: 2px;
  border-radius: var(--radius-sm);
  background: var(--surface-subtle);
  border: 1px solid var(--border);
}

.seg-btn {
  appearance: none;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
}

.seg-btn:hover {
  color: var(--text);
}

.seg-btn.active {
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow-sm);
}

.device-list {
  display: flex;
  flex-direction: column;
}

.device-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 13px 16px;
  border-bottom: 1px solid var(--border);
}

.device-row:last-child {
  border-bottom: none;
}

.device-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.device-title-line {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.plat-badge {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 7px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--surface-subtle);
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.device-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.device-os {
  font-size: 12px;
  color: var(--text-muted);
}

.device-meta-line {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12.5px;
  color: var(--text-secondary);
}

.state-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
  flex-shrink: 0;
}

.state-tag.is-green {
  color: var(--green);
}

.state-tag.is-green .dot {
  background: var(--green);
}

.state-tag.is-amber {
  color: var(--amber);
}

.state-tag.is-amber .dot {
  background: var(--amber);
}

.state-tag.is-red {
  color: var(--red);
}

.state-tag.is-red .dot {
  background: var(--red);
}

.meta-pill {
  font-size: 11.5px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.slim-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 5px;
  background: var(--green-bg);
  color: var(--green);
  font-weight: 500;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.menu-wrap {
  position: relative;
}

.menu-pop {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  min-width: 196px;
  padding: 5px;
  border-radius: var(--radius-md);
  background: var(--surface);
  border: 1px solid var(--border-strong);
  box-shadow: var(--shadow-pop);
  z-index: 30;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.menu-item {
  appearance: none;
  width: 100%;
  text-align: left;
  padding: 7px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text);
  font-family: inherit;
  font-size: 12.5px;
  cursor: pointer;
}

.menu-item:hover:not(:disabled) {
  background: var(--surface-hover);
}

.menu-item:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.menu-item.is-danger {
  color: var(--red);
}

.empty-box {
  padding: 20px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  color: var(--text-muted);
  font-size: 13px;
}

.other-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  flex-wrap: wrap;
}

.collapse-toggle {
  appearance: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: none;
  background: transparent;
  color: var(--text);
  font-family: inherit;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  padding: 4px 2px;
}

.collapse-toggle-sm {
  font-size: 12.5px;
  font-weight: 500;
  color: var(--text-secondary);
}

.chevron {
  display: inline-block;
  font-size: 11px;
  color: var(--text-muted);
  transition: transform 0.14s ease;
}

.chevron.is-open {
  transform: rotate(90deg);
}

.search-input {
  height: 32px;
  width: 220px;
  max-width: 100%;
  padding: 0 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface-subtle);
  color: var(--text);
  font-family: inherit;
  font-size: 12.5px;
}

.other-body {
  border-top: 1px solid var(--border);
}

.activity-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 2px 2px;
}

.activity-body {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 8px 12px;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 220px;
  overflow-y: auto;
}

.activity-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  font-size: 12px;
  color: var(--text-secondary);
}

.activity-time {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.activity-status {
  font-weight: 600;
  flex-shrink: 0;
}

.activity-status.is-ok {
  color: var(--green);
}

.activity-status.is-fail {
  color: var(--red);
}

.activity-msg {
  word-break: break-word;
}

.toast-container {
  position: fixed;
  right: 18px;
  bottom: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 60;
  max-width: 380px;
}

.toast {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--primary);
  color: var(--primary-text);
  font-size: 13px;
  box-shadow: var(--shadow-pop);
}

.toast.is-error {
  background: var(--red);
  color: #ffffff;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 80;
}

.modal-card {
  width: 100%;
  max-width: 420px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-pop);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-card h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 650;
}

.modal-body {
  margin: 0;
  font-size: 13.5px;
  color: var(--text-secondary);
  white-space: pre-line;
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

@media (max-width: 640px) {
  .hero,
  .settings-grid {
    grid-template-columns: 1fr;
  }
  .device-row {
    flex-direction: column;
    align-items: flex-start;
  }
  .row-actions {
    width: 100%;
    justify-content: flex-end;
  }
  .search-input {
    width: 100%;
  }
}
"""


APP_JS = r"""
(function () {
  "use strict";

  const tokenMeta = document.querySelector('meta[name="mobpool-token"]');
  const defaultOwnerMeta = document.querySelector('meta[name="mobpool-default-owner"]');
  const CSRF_TOKEN = tokenMeta ? tokenMeta.content : "";
  const DEFAULT_OWNER = defaultOwnerMeta ? defaultOwnerMeta.content : "mobpool-gui";

  const uiState = {
    state: null,
    platformFilter: "all",
    search: "",
    allDevicesOpen: false,
    activityOpen: false,
    settingsOpen: false,
    openMenuId: null,
    autoRefresh: true,
    pollTimer: null,
    jobPollTimer: null,
    inFlight: false,
    seenFinishedJobs: new Set(),
    modalConfirmHandler: null,
  };

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [key, val] of Object.entries(attrs)) {
        if (val === null || val === undefined || val === false) continue;
        if (key === "class") {
          node.className = val;
        } else if (key === "text") {
          node.textContent = String(val);
        } else if (key.startsWith("on") && typeof val === "function") {
          node.addEventListener(key.slice(2).toLowerCase(), val);
        } else if (key === "disabled" || key === "checked") {
          node[key] = Boolean(val);
        } else {
          node.setAttribute(key, String(val));
        }
      }
    }
    if (children) {
      for (const child of children) {
        if (child === null || child === undefined || child === false) continue;
        node.appendChild(typeof child === "string" ? document.createTextNode(child) : child);
      }
    }
    return node;
  }

  function clearNode(node) {
    while (node && node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function formatGb(bytes) {
    const val = Number(bytes || 0);
    if (!Number.isFinite(val) || val <= 0) return "";
    return (val / (1024 ** 3)).toFixed(1) + " GB";
  }

  function formatTime(epochSec) {
    if (!epochSec) return "";
    try {
      return new Date(epochSec * 1000).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch (_) {
      return "";
    }
  }

  function shortId(id) {
    const raw = String(id || "");
    if (raw.length <= 12) return raw;
    return raw.slice(0, 8);
  }

  function showToast(message, isError) {
    const container = document.getElementById("toast-container");
    const toast = el("div", {
      class: "toast" + (isError ? " is-error" : ""),
      text: message,
    });
    container.appendChild(toast);
    window.setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, isError ? 5200 : 3200);
  }

  function showErrorBanner(message) {
    const banner = document.getElementById("error-banner");
    clearNode(banner);
    if (!message) {
      banner.classList.add("hidden");
      return;
    }
    banner.classList.remove("hidden");
    banner.appendChild(el("span", { text: message }));
    banner.appendChild(
      el("button", {
        type: "button",
        class: "btn btn-sm",
        text: "Dismiss",
        onClick: () => showErrorBanner(""),
      })
    );
  }

  async function apiGet(path) {
    const resp = await fetch(path, {
      method: "GET",
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      throw new Error(data.error || "Request failed (" + resp.status + ")");
    }
    return data;
  }

  async function apiPost(path, payload) {
    const resp = await fetch(path, {
      method: "POST",
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-Mobpool-Token": CSRF_TOKEN,
      },
      body: JSON.stringify(payload || {}),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const err = new Error(data.error || data.message || "Request failed (" + resp.status + ")");
      err.status = resp.status;
      throw err;
    }
    return data;
  }

  function getOwnerInput() {
    const input = document.getElementById("input-owner");
    return (input && input.value.trim()) || DEFAULT_OWNER;
  }

  function getTtlSecInput() {
    const input = document.getElementById("input-ttl-min");
    const mins = input ? parseInt(input.value, 10) : 60;
    if (!Number.isFinite(mins) || mins < 1) return 3600;
    return Math.min(86400, mins * 60);
  }

  function getKeepAppsPref() {
    const box = document.getElementById("keep-apps-toggle");
    return Boolean(box && box.checked);
  }

  function activeJobs() {
    const jobs = (uiState.state && uiState.state.jobs && uiState.state.jobs.active) || [];
    return Array.isArray(jobs) ? jobs : [];
  }

  function isDeviceBusy(deviceId) {
    return activeJobs().some((job) => job.device_id === deviceId || job.action === "init");
  }

  function isAcquireBusy(platform) {
    return activeJobs().some(
      (job) =>
        (job.action === "acquire" && job.platform === platform) ||
        (job.action === "pool" && job.platform === platform) ||
        job.action === "init"
    );
  }

  function getStartBlocker(state, platform) {
    if (!state) return "Loading...";
    const meta = (state.platforms && state.platforms[platform]) || {};
    const platName = platform === "ios" ? "iOS" : "Android";
    if (!meta.available) {
      return meta.reason ? platName + " unavailable (" + meta.reason + ")" : platName + " unavailable";
    }
    const totalBooted = Number(state.total_booted || 0);
    const totalCap = Number((state.caps && state.caps.total) || 2);
    if (totalBooted >= totalCap) {
      return totalBooted + " of " + totalCap + " devices running — stop one first";
    }
    const platBooted = Number((state.counts && state.counts[platform]) || 0);
    const platCap = Number((state.caps && state.caps[platform]) || 1);
    if (platBooted >= platCap) {
      return platName + " limit reached (" + platBooted + "/" + platCap + ") — stop one first";
    }
    const freePct = state.free_memory_pct;
    const minFree = Number(state.min_free_pct || 25);
    if (typeof freePct === "number" && freePct < minFree) {
      return "Mac memory is low (" + freePct + "% free, needs " + minFree + "%)";
    }
    return "";
  }

  function openModal(options) {
    const backdrop = document.getElementById("modal-backdrop");
    const title = document.getElementById("modal-title");
    const body = document.getElementById("modal-body");
    const extra = document.getElementById("modal-extra");
    const confirmBtn = document.getElementById("modal-confirm");

    title.textContent = options.title || "Confirm";
    body.textContent = options.body || "";
    clearNode(extra);
    if (options.extraNode) {
      extra.appendChild(options.extraNode);
    }
    confirmBtn.textContent = options.confirmLabel || "Confirm";
    confirmBtn.className = options.danger ? "btn btn-danger-solid" : "btn btn-primary";
    uiState.modalConfirmHandler = options.onConfirm || null;
    backdrop.classList.remove("hidden");
  }

  function closeModal() {
    const backdrop = document.getElementById("modal-backdrop");
    backdrop.classList.add("hidden");
    uiState.modalConfirmHandler = null;
  }

  async function submitAction(path, payload) {
    uiState.openMenuId = null;
    showErrorBanner("");
    try {
      const res = await apiPost(path, payload);
      if (res.job) {
        showToast(res.job.label + "...", false);
        await fetchState(true);
        scheduleJobPoll();
      } else if (res.message) {
        showToast(res.message, !res.ok);
        await fetchState(true);
      }
    } catch (err) {
      showToast(err.message, true);
      showErrorBanner(err.message);
      await fetchState(true);
    }
  }

  function scheduleJobPoll() {
    if (uiState.jobPollTimer) {
      window.clearTimeout(uiState.jobPollTimer);
      uiState.jobPollTimer = null;
    }
    if (activeJobs().length > 0) {
      uiState.jobPollTimer = window.setTimeout(async () => {
        await fetchState(false);
        if (activeJobs().length > 0) {
          scheduleJobPoll();
        }
      }, 700);
    }
  }

  function scheduleNextPoll() {
    if (uiState.pollTimer) {
      window.clearTimeout(uiState.pollTimer);
      uiState.pollTimer = null;
    }
    if (!uiState.autoRefresh || document.hidden) return;
    uiState.pollTimer = window.setTimeout(async () => {
      await fetchState(false);
      scheduleNextPoll();
    }, 8000);
  }

  function notifyNewCompletedJobs(recentJobs) {
    if (!Array.isArray(recentJobs)) return;
    for (const job of recentJobs) {
      if (!job || !job.id || job.status === "running") continue;
      if (uiState.seenFinishedJobs.has(job.id)) continue;
      uiState.seenFinishedJobs.add(job.id);
      if (uiState.state !== null) {
        const ok = job.status === "succeeded";
        showToast((ok ? "Done: " : "Failed: ") + (job.message || job.label), !ok);
      }
    }
  }

  async function fetchState(forceRefresh) {
    if (uiState.inFlight && !forceRefresh) return;
    uiState.inFlight = true;
    try {
      const url = forceRefresh ? "/api/state?refresh=1" : "/api/state";
      const data = await apiGet(url);
      const hadState = uiState.state !== null;
      if (!hadState && data.jobs && Array.isArray(data.jobs.recent)) {
        for (const job of data.jobs.recent) {
          if (job && job.id && job.status !== "running") {
            uiState.seenFinishedJobs.add(job.id);
          }
        }
      } else if (data.jobs && Array.isArray(data.jobs.recent)) {
        notifyNewCompletedJobs(data.jobs.recent);
      }
      uiState.state = data;
      renderAll();
      if (activeJobs().length > 0) {
        scheduleJobPoll();
      }
    } catch (err) {
      showErrorBanner("Cannot reach mobpool: " + err.message);
    } finally {
      uiState.inFlight = false;
    }
  }

  async function copyTargetId(targetId, btn) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(targetId);
      } else {
        const area = el("textarea", { text: targetId });
        document.body.appendChild(area);
        area.select();
        document.execCommand("copy");
        document.body.removeChild(area);
      }
      const prev = btn.textContent;
      btn.textContent = "Copied!";
      btn.classList.add("copied");
      window.setTimeout(() => {
        btn.textContent = prev;
        btn.classList.remove("copied");
      }, 1200);
    } catch (_) {
      showToast("Copy failed", true);
    }
  }

  function confirmForceStop(dev) {
    const keepBox = el("input", { type: "checkbox", checked: getKeepAppsPref() });
    const extra = el("label", { class: "check-row" }, [
      keepBox,
      el("span", {}, [
        el("strong", { text: "Keep installed apps on device" }),
        el("small", { text: "Turn on to avoid deleting their app data." }),
      ]),
    ]);
    openModal({
      title: "Stop someone else's device?",
      body:
        dev.name +
        " is currently in use by " +
        dev.owner.label +
        ".\nStopping it may interrupt their work.",
      extraNode: extra,
      confirmLabel: "Force stop",
      danger: true,
      onConfirm: () => {
        submitAction("/api/release", {
          device_id: dev.device_id,
          keep_apps: keepBox.checked,
          force: true,
        });
      },
    });
  }

  function confirmForceSlim(dev) {
    openModal({
      title: "Optimize someone else's device?",
      body:
        dev.name +
        " is currently in use by " +
        dev.owner.label +
        ".\nOptimizing RAM (Slim) may boot or reboot the device.",
      confirmLabel: "Optimize anyway",
      danger: true,
      onConfirm: () => {
        submitAction("/api/slim", {
          device_id: dev.device_id,
          platform: dev.platform,
          force: true,
        });
      },
    });
  }

  function openInitPoolModal(defaultPlatform) {
    const platSelect = el("select", { class: "modal-select" }, [
      el("option", { value: "all", text: "Both iOS and Android" }),
      el("option", { value: "ios", text: "iOS only" }),
      el("option", { value: "android", text: "Android only" }),
    ]);
    if (defaultPlatform && ["all", "ios", "android"].includes(defaultPlatform)) {
      platSelect.value = defaultPlatform;
    }
    const countInput = el("input", {
      type: "number",
      min: "1",
      max: "8",
      placeholder: "Automatic (recommended)",
      class: "modal-input",
    });
    const wrap = el("div", { class: "setting-field" }, [
      el("label", { class: "setting-label", text: "Platform" }),
      platSelect,
      el("label", { class: "setting-label", text: "Devices per platform (optional)" }),
      countInput,
    ]);
    openModal({
      title: "Auto-pick Quick-start devices",
      body:
        "Picks available shut-down devices, optimizes them for low RAM, and saves them to your Quick-start list.\nDevices currently running or in use are skipped.",
      extraNode: wrap,
      confirmLabel: "Auto-pick",
      danger: false,
      onConfirm: () => {
        const payload = { platform: platSelect.value };
        const parsed = parseInt(countInput.value, 10);
        if (Number.isFinite(parsed) && parsed >= 1) {
          payload.count = parsed;
        }
        submitAction("/api/init", payload);
      },
    });
  }

  function renderTopStatus(state) {
    const pill = document.getElementById("status-pill");
    const totalBooted = Number(state.total_booted || 0);
    const totalCap = Number((state.caps && state.caps.total) || 2);
    const iosCount = Number((state.counts && state.counts.ios) || 0);
    const iosCap = Number((state.caps && state.caps.ios) || 2);
    const androidCount = Number((state.counts && state.counts.android) || 0);
    const androidCap = Number((state.caps && state.caps.android) || 1);
    const freePct = state.free_memory_pct;
    const minFree = Number(state.min_free_pct || 25);

    const memPart = typeof freePct === "number" ? " · " + freePct + "% RAM free" : "";
    pill.textContent = totalBooted + " / " + totalCap + " running" + memPart;
    pill.title =
      "iOS " +
      iosCount +
      "/" +
      iosCap +
      " · Android " +
      androidCount +
      "/" +
      androidCap +
      (typeof freePct === "number" ? " · min " + minFree + "% free RAM" : "");

    pill.className = "status-pill";
    if (totalBooted >= totalCap || (typeof freePct === "number" && freePct < minFree)) {
      pill.classList.add("is-danger");
    } else if (typeof freePct === "number" && freePct < minFree + 10) {
      pill.classList.add("is-warn");
    }

    const updated = document.getElementById("last-updated");
    if (updated) {
      updated.textContent = "Last updated " + formatTime(state.timestamp);
    }
  }

  function renderHero(state) {
    const guardBanner = document.getElementById("guard-banner");
    const totalBooted = Number(state.total_booted || 0);
    const totalCap = Number((state.caps && state.caps.total) || 2);
    const freePct = state.free_memory_pct;
    const minFree = Number(state.min_free_pct || 25);

    let globalWarn = "";
    if (typeof freePct === "number" && freePct < minFree) {
      globalWarn =
        "Mac memory is low (" +
        freePct +
        "% free, needs at least " +
        minFree +
        "%) — close apps or stop a device before starting another.";
    } else if (totalBooted >= totalCap) {
      globalWarn =
        totalBooted +
        " of " +
        totalCap +
        " devices are running — stop a running device below to start another.";
    }
    if (globalWarn) {
      guardBanner.textContent = globalWarn;
      guardBanner.classList.remove("hidden");
    } else {
      guardBanner.textContent = "";
      guardBanner.classList.add("hidden");
    }

    for (const plat of ["ios", "android"]) {
      const btn = document.getElementById("btn-acquire-" + plat);
      const sub = document.getElementById("sub-acquire-" + plat);
      if (!btn || !sub) continue;
      const meta = (state.platforms && state.platforms[plat]) || {};
      const count = Number((state.counts && state.counts[plat]) || 0);
      const cap = Number((state.caps && state.caps[plat]) || 1);
      const poolCount = Number(meta.pool_count || 0);
      const busy = isAcquireBusy(plat);
      const blocker = getStartBlocker(state, plat);

      if (!meta.available) {
        btn.disabled = true;
        sub.textContent = meta.reason ? "Unavailable (" + meta.reason + ")" : "Not installed";
      } else if (busy) {
        btn.disabled = true;
        sub.textContent = "Starting...";
      } else if (blocker) {
        btn.disabled = true;
        sub.textContent = blocker;
      } else if (poolCount === 0) {
        btn.disabled = true;
        sub.textContent = "Pick a Quick-start device below first";
      } else {
        btn.disabled = false;
        sub.textContent = count + " / " + cap + " running · " + poolCount + " in Quick-start";
      }
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
          el("span", { class: "meta-pill", text: elapsed + "s" }),
        ])
      );
    }
  }

  function renderPlatformTabs(devices) {
    const tabs = document.getElementById("platform-tabs");
    clearNode(tabs);
    const defs = [
      { id: "all", label: "All" },
      { id: "ios", label: "iOS" },
      { id: "android", label: "Android" },
    ];
    for (const item of defs) {
      tabs.appendChild(
        el("button", {
          type: "button",
          role: "tab",
          "aria-selected": String(uiState.platformFilter === item.id),
          class: "seg-btn" + (uiState.platformFilter === item.id ? " active" : ""),
          text: item.label,
          onClick: () => {
            uiState.platformFilter = item.id;
            uiState.openMenuId = null;
            renderAll();
          },
        })
      );
    }
  }

  function makeCopyButton(dev) {
    const targetId = dev.target_id || dev.device_id;
    const btn = el("button", {
      type: "button",
      class: "btn-copy",
      text: shortId(targetId) + " · Copy",
      title: "Copy ID: " + targetId,
    });
    btn.addEventListener("click", () => copyTargetId(targetId, btn));
    return btn;
  }

  function makeMoreMenu(menuKey, items) {
    if (!items || items.length === 0) return null;
    const isOpen = uiState.openMenuId === menuKey;
    const wrap = el("div", { class: "menu-wrap" });
    const trigger = el("button", {
      type: "button",
      class: "btn btn-icon btn-quiet" + (isOpen ? " is-active" : ""),
      text: "⋯",
      title: "More actions",
      "aria-expanded": String(isOpen),
      onClick: (ev) => {
        ev.stopPropagation();
        uiState.openMenuId = isOpen ? null : menuKey;
        renderAll();
      },
    });
    wrap.appendChild(trigger);
    if (isOpen) {
      const pop = el("div", { class: "menu-pop", role: "menu" });
      for (const item of items) {
        pop.appendChild(
          el("button", {
            type: "button",
            role: "menuitem",
            class: "menu-item" + (item.danger ? " is-danger" : ""),
            text: item.label,
            disabled: Boolean(item.disabled),
            title: item.title || null,
            onClick: (ev) => {
              ev.stopPropagation();
              uiState.openMenuId = null;
              item.onClick();
            },
          })
        );
      }
      wrap.appendChild(pop);
    }
    return wrap;
  }

  function renderRunningSection(state, devices) {
    const list = document.getElementById("running-list");
    const countEl = document.getElementById("running-count");
    const ramEl = document.getElementById("running-ram");
    clearNode(list);

    const running = devices.filter((d) => d.state === "Booted");
    countEl.textContent = String(running.length);
    const ramText = formatGb(state.total_ram_bytes);
    ramEl.textContent = running.length > 0 && ramText ? ramText + " total RAM" : "";

    if (running.length === 0) {
      list.appendChild(
        el("div", { class: "empty-box" }, [
          el("span", { text: "No devices running right now. Click Start iOS or Start Android above." }),
        ])
      );
      return;
    }

    const keepApps = getKeepAppsPref();
    for (const dev of running) {
      const busy = isDeviceBusy(dev.device_id);
      const ownedByOther = Boolean(dev.owner && !dev.owner.is_self);
      const isSelfMobpool = Boolean(dev.owner && dev.owner.is_self && dev.owner.source === "mobpool");

      let statusClass = "is-green";
      let statusText = "Running";
      if (dev.owner) {
        if (dev.owner.is_self) {
          statusClass = "is-green";
          if (typeof dev.owner.remaining_sec === "number") {
            const mins = Math.max(0, Math.round(dev.owner.remaining_sec / 60));
            statusText = "Yours · " + mins + "m left";
          } else {
            statusText = "Yours";
          }
        } else {
          statusClass = "is-red";
          statusText = "In use by " + dev.owner.label;
        }
      } else if (dev.is_orphan) {
        statusClass = "is-amber";
        statusText = "Started outside mobpool";
      }

      const metaChildren = [
        el("span", { class: "state-tag " + statusClass }, [
          el("span", { class: "dot", "aria-hidden": "true" }),
          el("span", { text: statusText }),
        ]),
      ];
      const devRam = formatGb(dev.ram_bytes);
      if (devRam) {
        metaChildren.push(el("span", { class: "meta-pill", text: devRam + " RAM" }));
      }
      if (dev.slim_status && dev.slim_status.startsWith("slim")) {
        metaChildren.push(el("span", { class: "slim-tag", text: "Slim" }));
      }
      metaChildren.push(makeCopyButton(dev));

      const actions = [];
      if (isSelfMobpool) {
        actions.push(
          el("button", {
            type: "button",
            class: "btn btn-sm btn-quiet",
            text: "+1h",
            disabled: busy,
            title: "Add 1 hour to your reservation",
            onClick: () => {
              const remaining = Math.max(0, Number(dev.owner.remaining_sec || 0));
              const nextTtl = Math.min(86400, remaining + 3600);
              submitAction("/api/renew", {
                device_id: dev.device_id,
                ttl_sec: nextTtl,
              });
            },
          })
        );
      }

      if (ownedByOther) {
        actions.push(
          el("button", {
            type: "button",
            class: "btn btn-sm btn-danger",
            text: "Force stop",
            disabled: busy,
            onClick: () => confirmForceStop(dev),
          })
        );
      } else {
        actions.push(
          el("button", {
            type: "button",
            class: "btn btn-sm btn-danger",
            text: keepApps ? "Stop (keep apps)" : "Stop & clean",
            disabled: busy,
            title: keepApps
              ? "Shut down while keeping installed apps"
              : "Clean installed apps and shut down",
            onClick: () =>
              submitAction("/api/release", {
                device_id: dev.device_id,
                keep_apps: keepApps,
                force: false,
              }),
          })
        );
      }

      const menuItems = [];
      if (!ownedByOther) {
        menuItems.push({
          label: keepApps ? "Stop & clean apps" : "Stop (keep apps)",
          disabled: busy,
          onClick: () =>
            submitAction("/api/release", {
              device_id: dev.device_id,
              keep_apps: !keepApps,
              force: false,
            }),
        });
      }
      if (dev.can_slim) {
        menuItems.push({
          label: "Optimize RAM (Slim)",
          disabled: busy,
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
        });
      }
      if (!ownedByOther) {
        menuItems.push({
          label: dev.in_pool ? "Remove from Quick-start" : "Pin to Quick-start",
          disabled: busy,
          onClick: () =>
            submitAction("/api/pool", {
              platform: dev.platform,
              device_id: dev.device_id,
              in_pool: !dev.in_pool,
              prepare: false,
            }),
        });
      }
      const menu = makeMoreMenu("run:" + dev.device_id, menuItems);
      if (menu) actions.push(menu);

      list.appendChild(
        el("div", { class: "device-row" }, [
          el("div", { class: "device-info" }, [
            el("div", { class: "device-title-line" }, [
              el("span", { class: "plat-badge", text: dev.platform === "ios" ? "iOS" : "Android" }),
              el("span", { class: "device-name", text: dev.name }),
              dev.os_version ? el("span", { class: "device-os", text: dev.os_version }) : null,
            ]),
            el("div", { class: "device-meta-line" }, metaChildren),
          ]),
          el("div", { class: "row-actions" }, actions),
        ])
      );
    }
  }

  function matchesPlatform(dev) {
    return uiState.platformFilter === "all" || dev.platform === uiState.platformFilter;
  }

  function matchesSearch(dev) {
    if (!uiState.search) return true;
    const q = uiState.search.toLowerCase();
    const hay = [
      dev.name,
      dev.device_id,
      dev.target_id,
      dev.os_version,
      dev.platform,
      dev.owner ? dev.owner.label : "",
    ]
      .join(" ")
      .toLowerCase();
    return hay.includes(q);
  }

  function totalPoolCountForFilter(state) {
    const pools = (state && state.pools) || {};
    const iosLen = Array.isArray(pools.ios) ? pools.ios.length : 0;
    const androidLen = Array.isArray(pools.android) ? pools.android.length : 0;
    if (uiState.platformFilter === "ios") return iosLen;
    if (uiState.platformFilter === "android") return androidLen;
    return iosLen + androidLen;
  }

  function renderQuickStartSection(state, devices) {
    const list = document.getElementById("quickstart-list");
    const countEl = document.getElementById("quickstart-count");
    clearNode(list);

    const poolStopped = devices.filter(
      (d) => d.state !== "Booted" && d.in_pool && matchesPlatform(d)
    );
    countEl.textContent = String(poolStopped.length);

    if (poolStopped.length === 0) {
      const configuredPoolCount = totalPoolCountForFilter(state);
      if (configuredPoolCount === 0) {
        list.appendChild(
          el("div", { class: "empty-box" }, [
            el("span", { text: "No Quick-start devices picked yet." }),
            el("button", {
              type: "button",
              class: "btn btn-primary btn-sm",
              text: "Auto-pick best devices",
              onClick: () => openInitPoolModal(uiState.platformFilter),
            }),
          ])
        );
      } else {
        list.appendChild(
          el("div", { class: "empty-box" }, [
            el("span", { text: "All Quick-start devices are currently running above." }),
          ])
        );
      }
      return;
    }

    for (const dev of poolStopped) {
      const busy = isDeviceBusy(dev.device_id);
      const ownedByOther = Boolean(dev.owner && !dev.owner.is_self);
      const blocker = getStartBlocker(state, dev.platform);
      const startDisabled = busy || isAcquireBusy(dev.platform) || ownedByOther || Boolean(blocker);
      const startTitle = ownedByOther
        ? "In use by " + dev.owner.label
        : blocker || "Start this device";

      const metaChildren = [];
      if (ownedByOther) {
        metaChildren.push(
          el("span", { class: "state-tag is-red" }, [
            el("span", { class: "dot", "aria-hidden": "true" }),
            el("span", { text: "In use by " + dev.owner.label }),
          ])
        );
      } else if (dev.owner && dev.owner.is_self) {
        metaChildren.push(
          el("span", { class: "state-tag is-green" }, [
            el("span", { class: "dot", "aria-hidden": "true" }),
            el("span", { text: "Reserved by you" }),
          ])
        );
      } else {
        metaChildren.push(el("span", { class: "meta-pill", text: "Ready" }));
      }
      metaChildren.push(makeCopyButton(dev));

      const menuItems = [];
      if (dev.can_slim) {
        menuItems.push({
          label: "Optimize RAM (Slim)",
          disabled: busy || ownedByOther,
          title: ownedByOther ? "In use by " + dev.owner.label : "Apply low-RAM profile",
          onClick: () =>
            submitAction("/api/slim", {
              device_id: dev.device_id,
              platform: dev.platform,
              force: false,
            }),
        });
      }
      menuItems.push({
        label: "Remove from Quick-start",
        disabled: busy,
        onClick: () =>
          submitAction("/api/pool", {
            platform: dev.platform,
            device_id: dev.device_id,
            in_pool: false,
          }),
      });

      const actions = [
        el("button", {
          type: "button",
          class: "btn btn-primary btn-sm",
          text: "Start",
          disabled: startDisabled,
          title: startTitle,
          onClick: () =>
            submitAction("/api/acquire", {
              platform: dev.platform,
              device_id: dev.device_id,
              allow_non_pool: false,
              owner: getOwnerInput(),
              ttl_sec: getTtlSecInput(),
            }),
        }),
        makeMoreMenu("qs:" + dev.device_id, menuItems),
      ];

      list.appendChild(
        el("div", { class: "device-row" }, [
          el("div", { class: "device-info" }, [
            el("div", { class: "device-title-line" }, [
              el("span", { class: "plat-badge", text: dev.platform === "ios" ? "iOS" : "Android" }),
              el("span", { class: "device-name", text: dev.name }),
              dev.os_version ? el("span", { class: "device-os", text: dev.os_version }) : null,
            ]),
            el("div", { class: "device-meta-line" }, metaChildren),
          ]),
          el("div", { class: "row-actions" }, actions),
        ])
      );
    }
  }

  function renderOtherSection(state, devices) {
    const list = document.getElementById("other-list");
    const countEl = document.getElementById("other-count");
    const body = document.getElementById("other-body");
    const chevron = document.getElementById("other-chevron");
    const toggleBtn = document.getElementById("btn-toggle-other");
    clearNode(list);

    const others = devices.filter(
      (d) => d.state !== "Booted" && !d.in_pool && matchesPlatform(d) && matchesSearch(d)
    );
    countEl.textContent = String(others.length);

    const isOpen = uiState.allDevicesOpen || Boolean(uiState.search);
    body.classList.toggle("hidden", !isOpen);
    chevron.classList.toggle("is-open", isOpen);
    toggleBtn.setAttribute("aria-expanded", String(isOpen));

    if (!isOpen) return;

    if (others.length === 0) {
      list.appendChild(
        el("div", { class: "empty-box" }, [
          el("span", {
            text: uiState.search ? "No matching devices found." : "No other devices installed.",
          }),
        ])
      );
      return;
    }

    for (const dev of others) {
      const busy = isDeviceBusy(dev.device_id);
      const ownedByOther = Boolean(dev.owner && !dev.owner.is_self);
      const blocker = getStartBlocker(state, dev.platform);
      const startDisabled = busy || isAcquireBusy(dev.platform) || ownedByOther || Boolean(blocker);
      const startTitle = ownedByOther
        ? "In use by " + dev.owner.label
        : blocker || "Start this device (applies low-RAM slim setup on first start)";
      const pinDisabled = busy || isAcquireBusy(dev.platform) || ownedByOther;
      const pinTitle = ownedByOther
        ? "In use by " + dev.owner.label
        : "Add to Quick-start list and optimize RAM";

      const metaChildren = [];
      if (ownedByOther) {
        metaChildren.push(
          el("span", { class: "state-tag is-red" }, [
            el("span", { class: "dot", "aria-hidden": "true" }),
            el("span", { text: "In use by " + dev.owner.label }),
          ])
        );
      } else if (dev.owner && dev.owner.is_self) {
        metaChildren.push(
          el("span", { class: "state-tag is-green" }, [
            el("span", { class: "dot", "aria-hidden": "true" }),
            el("span", { text: "Reserved by you" }),
          ])
        );
      }
      metaChildren.push(makeCopyButton(dev));

      const actions = [
        el("button", {
          type: "button",
          class: "btn btn-sm",
          text: "Start",
          disabled: startDisabled,
          title: startTitle,
          onClick: () =>
            submitAction("/api/acquire", {
              platform: dev.platform,
              device_id: dev.device_id,
              allow_non_pool: true,
              owner: getOwnerInput(),
              ttl_sec: getTtlSecInput(),
            }),
        }),
        el("button", {
          type: "button",
          class: "btn btn-sm btn-quiet",
          text: "Pin",
          disabled: pinDisabled,
          title: pinTitle,
          onClick: () =>
            submitAction("/api/pool", {
              platform: dev.platform,
              device_id: dev.device_id,
              in_pool: true,
              prepare: true,
            }),
        }),
      ];

      list.appendChild(
        el("div", { class: "device-row" }, [
          el("div", { class: "device-info" }, [
            el("div", { class: "device-title-line" }, [
              el("span", { class: "plat-badge", text: dev.platform === "ios" ? "iOS" : "Android" }),
              el("span", { class: "device-name", text: dev.name }),
              dev.os_version ? el("span", { class: "device-os", text: dev.os_version }) : null,
            ]),
            el("div", { class: "device-meta-line" }, metaChildren),
          ]),
          el("div", { class: "row-actions" }, actions),
        ])
      );
    }
  }

  function renderActivity(recentJobs) {
    const list = document.getElementById("activity-list");
    const count = document.getElementById("activity-count");
    const body = document.getElementById("activity-body");
    const chevron = document.getElementById("activity-chevron");
    const toggleBtn = document.getElementById("btn-toggle-activity");
    clearNode(list);

    const items = Array.isArray(recentJobs) ? recentJobs : [];
    count.textContent = String(items.length);
    body.classList.toggle("hidden", !uiState.activityOpen);
    chevron.classList.toggle("is-open", uiState.activityOpen);
    toggleBtn.setAttribute("aria-expanded", String(uiState.activityOpen));

    if (!uiState.activityOpen) return;

    if (items.length === 0) {
      list.appendChild(el("div", { class: "meta-pill", text: "No actions yet." }));
      return;
    }
    for (const job of items.slice(0, 20)) {
      const cls =
        job.status === "succeeded" ? " is-ok" : job.status === "failed" ? " is-fail" : "";
      list.appendChild(
        el("div", { class: "activity-row" }, [
          el("span", { class: "activity-time", text: formatTime(job.finished_at || job.started_at) }),
          el("span", { class: "activity-status" + cls, text: job.status }),
          el("div", {
            class: "activity-msg",
            text: job.label + (job.message ? " — " + job.message : ""),
          }),
        ])
      );
    }
  }

  function renderAll() {
    if (!uiState.state) return;
    const devices = Array.isArray(uiState.state.devices) ? uiState.state.devices : [];
    renderTopStatus(uiState.state);
    renderHero(uiState.state);
    renderInFlight();
    renderPlatformTabs(devices);
    renderRunningSection(uiState.state, devices);
    renderQuickStartSection(uiState.state, devices);
    renderOtherSection(uiState.state, devices);
    renderActivity(uiState.state.jobs && uiState.state.jobs.recent);
  }

  function bindEvents() {
    document.getElementById("btn-refresh").addEventListener("click", () => fetchState(true));

    const settingsBtn = document.getElementById("btn-settings");
    const settingsPanel = document.getElementById("settings-panel");
    settingsBtn.addEventListener("click", () => {
      uiState.settingsOpen = !uiState.settingsOpen;
      settingsPanel.classList.toggle("hidden", !uiState.settingsOpen);
      settingsBtn.classList.toggle("is-active", uiState.settingsOpen);
      settingsBtn.setAttribute("aria-expanded", String(uiState.settingsOpen));
    });

    document.getElementById("btn-init-pool").addEventListener("click", () => openInitPoolModal("all"));

    document.getElementById("btn-acquire-ios").addEventListener("click", () => {
      submitAction("/api/acquire", {
        platform: "ios",
        owner: getOwnerInput(),
        ttl_sec: getTtlSecInput(),
      });
    });

    document.getElementById("btn-acquire-android").addEventListener("click", () => {
      submitAction("/api/acquire", {
        platform: "android",
        owner: getOwnerInput(),
        ttl_sec: getTtlSecInput(),
      });
    });

    document.getElementById("btn-toggle-other").addEventListener("click", () => {
      uiState.allDevicesOpen = !uiState.allDevicesOpen;
      renderAll();
    });

    document.getElementById("btn-toggle-activity").addEventListener("click", () => {
      uiState.activityOpen = !uiState.activityOpen;
      renderAll();
    });

    document.getElementById("search-input").addEventListener("input", (ev) => {
      uiState.search = ev.target.value.trim();
      if (uiState.search && !uiState.allDevicesOpen) {
        uiState.allDevicesOpen = true;
      }
      renderAll();
    });

    document.getElementById("keep-apps-toggle").addEventListener("change", () => {
      renderAll();
    });

    document.getElementById("auto-refresh-toggle").addEventListener("change", (ev) => {
      uiState.autoRefresh = Boolean(ev.target.checked);
      scheduleNextPoll();
    });

    document.getElementById("modal-cancel").addEventListener("click", closeModal);
    document.getElementById("modal-confirm").addEventListener("click", () => {
      const handler = uiState.modalConfirmHandler;
      closeModal();
      if (typeof handler === "function") handler();
    });

    document.getElementById("modal-backdrop").addEventListener("click", (ev) => {
      if (ev.target.id === "modal-backdrop") closeModal();
    });

    document.addEventListener("click", () => {
      if (uiState.openMenuId !== null) {
        uiState.openMenuId = null;
        renderAll();
      }
    });

    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") {
        closeModal();
        if (uiState.openMenuId !== null) {
          uiState.openMenuId = null;
          renderAll();
        }
      }
    });

    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) {
        fetchState(false).then(scheduleNextPoll);
      } else if (uiState.pollTimer) {
        window.clearTimeout(uiState.pollTimer);
        uiState.pollTimer = null;
      }
    });
  }

  bindEvents();
  fetchState(true).then(scheduleNextPoll);
})();
"""

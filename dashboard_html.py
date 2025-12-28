"""
HTML template generator for the Bandcamp release dashboard.
This module isolates the large HTML/JS/CSS document so the main logic in
dashboard.py remains focused on data normalization and file I/O.
"""

from __future__ import annotations

import html
import json


def render_dashboard_html(*, title: str, data_json: str, embed_proxy_url: str | None = None, default_theme: str | None = None) -> str:
    """
    Build the full dashboard HTML document.
    """
    escaped_title = html.escape(title)
    proxy_literal = json.dumps(embed_proxy_url)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escaped_title}</title>
  <style>
    :root {{
      --bg: #0f1116;
      --surface: #181b22;
      --panel: #0b0d11;
      --accent: #52d0ff;
      --text: #f4f6fb;
      --muted: #a8b0c2;
      --border: #222735;
      --shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
      --radius: 10px;
      --row-bg: #181b22;
      --row-unseen-bg: #1f2430;
    }}
    .theme-light {{
      --bg: #f5f7fb;
      --surface: #ffffff;
      --panel: #f1f3f7;
      --accent: #1f7aff;
      --text: #0a0f1a;
      --muted: #5a6375;
      --border: #d9e2ef;
      --shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
      --row-bg: #f6f7fb;
      --row-unseen-bg: #e8ecf4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: radial-gradient(circle at 20% 20%, rgba(82, 208, 255, 0.08), transparent 25%),
                  radial-gradient(circle at 80% 0%, rgba(255, 105, 180, 0.08), transparent 20%),
                  var(--bg);
      color: var(--text);
      font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
      display: flex;
    }}
    body.theme-light {{
      background: radial-gradient(circle at 20% 20%, rgba(31, 122, 255, 0.08), transparent 25%),
                  radial-gradient(circle at 80% 0%, rgba(255, 171, 64, 0.1), transparent 25%),
                  var(--bg);
    }}
    a.link {{
      color: var(--text);
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: color 0.12s ease, border-color 0.12s ease;
    }}
    a.link:hover {{
      color: var(--accent);
      border-color: rgba(82, 208, 255, 0.6);
    }}
    header {{
      padding: 18px 24px;
      border-bottom: 1px solid var(--border);
      background: var(--header-bg);
      backdrop-filter: blur(12px);
      position: sticky;
      top: 0;
      z-index: 20;
    }}
    .button {{
      padding: 8px 12px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: rgba(255, 255, 255, 0.04);
      color: var(--text);
      cursor: pointer;
      transition: all 0.12s ease;
      font-weight: 600;
      letter-spacing: 0.2px;
    }}
    .button:hover {{
      transform: translateY(-1px);
      box-shadow: 0 6px 12px rgba(0,0,0,0.2);
    }}
    h1 {{
      margin: 0;
      font-size: 22px;
      letter-spacing: 0.3px;
    }}
    .row-dot {{
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--muted);
      opacity: 0.7;
      cursor: pointer;
      transition: opacity 0.12s ease;
    }}
    .row-dot.read {{
      opacity: 0;
    }}
    .cached-badge {{
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 6px;
      border-radius: 999px;
      background: rgba(82, 208, 255, 0.14);
      color: var(--accent);
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.3px;
      margin-left: 6px;
      border: 1px solid rgba(82, 208, 255, 0.25);
      white-space: nowrap;
    }}
    .header-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 260px 1fr;
      gap: 0;
      width: 100%;
    }}
    aside {{
      background: var(--panel);
      border-right: 1px solid var(--border);
      padding: 20px;
      position: sticky;
      top: 0;
      align-self: start;
      height: 100vh;
      overflow-y: auto;
    }}
    .filter-title {{
      font-size: 14px;
      letter-spacing: 0.5px;
      color: var(--muted);
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    .filter-list {{
      display: grid;
      gap: 4px;
    }}
    .filter-item {{
      display: grid;
      grid-template-columns: auto auto 1fr auto;
      align-items: center;
      gap: 6px;
      padding: 2px 0;
      background: none;
      border: none;
      border-radius: 0;
      line-height: 1.05;
      font-size: 13px;
    }}
    .filter-checkbox {{
      width: 16px;
      height: 16px;
      cursor: pointer;
    }}
    .filter-checkbox.show {{
      accent-color: var(--accent);
    }}
    .filter-checkbox.show-only {{
      accent-color: #ff6b6b;
    }}
    .filter-checkbox:disabled {{
      opacity: 0.5;
      cursor: not-allowed;
    }}
    .filter-item.show-only-active .filter-checkbox.show {{
      opacity: 0.5;
    }}
    .filter-count {{
      margin-left: auto;
      justify-self: end;
      color: var(--muted);
      font-size: 12px;
    }}
    main {{
      padding: 0 16px 32px 16px;
    }}
    .wireframe-panel {{
      margin: 16px 0;
      padding: 14px 16px;
      background: var(--surface);
      border: 1px dashed var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }}
    .wireframe-panel.open {{
      border-style: solid;
      box-shadow: 0 12px 30px rgba(0,0,0,0.35);
    }}
    .wireframe-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 4px 0;
    }}
    .wireframe-title {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .wireframe-title strong {{
      font-size: 15px;
      letter-spacing: 0.2px;
    }}
    .wireframe-title span {{
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.4px;
      text-transform: uppercase;
    }}
    .wireframe-body {{
      margin-top: 12px;
      border: 1px dashed var(--border);
      border-radius: calc(var(--radius) - 2px);
      min-height: 140px;
      background: repeating-linear-gradient(
        45deg,
        rgba(255,255,255,0.04),
        rgba(255,255,255,0.04) 12px,
        rgba(255,255,255,0.02) 12px,
        rgba(255,255,255,0.02) 24px
      );
    }}
    .date-range-panel {{
      display: grid;
      gap: 8px;
    }}
    .calendar-row {{
      display: grid;
      grid-template-columns: 270px 1fr;
      gap: 12px;
      align-items: start;
    }}
    .calendar-card {{
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--surface);
      padding: 10px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
      width: 270px;
      height: 460px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .calendar-label {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
      font-weight: 600;
      letter-spacing: 0.3px;
    }}
    .calendar-meta {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .calendar-nav {{
      display: flex;
      gap: 6px;
      align-items: center;
    }}
    .calendar-nav button {{
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.04);
      color: var(--text);
      border-radius: 6px;
      padding: 4px 8px;
      cursor: pointer;
    }}
    .calendar-month {{
      font-size: 12px;
      color: var(--muted);
      width: 120px;
      min-width: 120px;
      display: inline-block;
      text-align: center;
      letter-spacing: 0.4px;
      text-transform: uppercase;
    }}
    .calendar-today-btn {{
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.06);
      color: var(--text);
      border-radius: 6px;
      padding: 4px 8px;
      cursor: pointer;
      font-size: 12px;
      letter-spacing: 0.3px;
    }}
    .calendar-grid {{
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 4px;
      font-size: 12px;
      flex: 1;
      min-height: 340px;
    }}
    .calendar-log {{
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--surface);
      padding: 10px;
      height: 460px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
    }}
    .scrollbox {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px;
      background: rgba(255,255,255,0.02);
      flex: 1;
      overflow-y: auto;
      font-size: 12px;
      color: var(--muted);
      white-space: pre-line;
    }}
    .calendar-day {{
      position: relative;
      border: 1px solid var(--border);
      border-radius: 8px;
      text-align: center;
      padding: 8px 0;
      min-height: 40px;
      cursor: pointer;
      background: rgba(255,255,255,0.02);
      transition: transform 0.1s ease, border-color 0.12s ease, box-shadow 0.12s ease;
    }}
    .calendar-day.in-range {{
      background: linear-gradient(180deg, rgba(82,208,255,0.14), rgba(82,208,255,0.05));
      border-color: rgba(82,208,255,0.5);
    }}
    .calendar-day .dot-strip {{
      display: flex;
      justify-content: center;
      gap: 4px;
      margin-top: 4px;
      min-height: 8px;
    }}
    .calendar-day .dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      border: 1px solid rgba(0,0,0,0.25);
      box-shadow: 0 0 0 1px rgba(255,255,255,0.1);
      background: transparent;
    }}
    .calendar-day.scraped {{
      background: rgba(255,255,255,0.12);
      border-color: rgba(255,255,255,0.28);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.05);
    }}
    body.theme-light .calendar-day.scraped {{
      background: rgba(0,0,0,0.08);
      border-color: rgba(0,0,0,0.16);
      box-shadow: inset 0 0 0 1px rgba(0,0,0,0.04);
    }}
    .calendar-day.scraped.in-range,
    .calendar-day.scraped.selected {{
      background: linear-gradient(180deg, rgba(255,255,255,0.36), rgba(255,255,255,0.22));
      border-color: rgba(82,208,255,0.7);
      box-shadow: 0 0 0 1px rgba(82,208,255,0.4), 0 8px 18px rgba(0,0,0,0.2);
    }}
    body.theme-light .calendar-day.scraped.in-range,
    body.theme-light .calendar-day.scraped.selected {{
      background: linear-gradient(180deg, rgba(0,0,0,0.18), rgba(0,0,0,0.12));
      border-color: rgba(64,150,210,0.65);
      box-shadow: 0 0 0 1px rgba(64,150,210,0.35), 0 6px 12px rgba(0,0,0,0.1);
    }}
    .calendar-day .dot.scraped {{
      display: none;
    }}
    .calendar-day .dot.unseen {{
      background: #64a8ff;
      border-color: rgba(50,120,200,0.6);
      box-shadow: 0 0 0 1px rgba(100,168,255,0.35);
    }}
    .calendar-day:hover {{
      transform: translateY(-1px);
      border-color: rgba(82,208,255,0.6);
      box-shadow: 0 6px 14px rgba(0,0,0,0.18);
    }}
    .calendar-day.other-month {{
      visibility: hidden;
      pointer-events: none;
    }}
    .calendar-day.disabled {{
      opacity: 0.35;
      cursor: not-allowed;
      background: rgba(255,255,255,0.02);
      border-style: dashed;
      pointer-events: none;
    }}
    .calendar-day.selected {{
      background: linear-gradient(180deg, rgba(82,208,255,0.14), rgba(82,208,255,0.05));
      border-color: rgba(82,208,255,0.5);
      box-shadow: none;
    }}
    .max-results-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.75);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 9999;
    }}
    .max-results-modal {{
      background: var(--surface);
      color: var(--text);
      padding: 22px 26px;
      border-radius: 12px;
      border: 1px solid var(--border);
      box-shadow: 0 24px 48px rgba(0,0,0,0.5);
      max-width: 460px;
      text-align: center;
      font-size: 15px;
      line-height: 1.5;
    }}
    .calendar-weekday {{
      text-align: center;
      font-size: 11px;
      color: var(--muted);
      padding: 4px 0;
      letter-spacing: 0.4px;
    }}
    .table-wrapper {{
      margin-top: 12px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    thead {{
      background: var(--panel);
      position: sticky;
      top: 0;
      z-index: 5;
    }}
    th, td {{
      padding: 6px 8px;
      text-align: left;
      border-bottom: 1px solid var(--border);
      line-height: 1.05;
    }}
    th {{
      user-select: none;
      cursor: pointer;
      text-transform: uppercase;
      font-size: 12px;
      letter-spacing: 0.6px;
      color: var(--muted);
      position: sticky;
      top: 0;
      background: var(--panel);
      z-index: 6;
    }}
    th .sort-indicator {{
      position: absolute;
      right: 10px;
      opacity: 0.7;
      font-size: 10px;
    }}
    tr.data-row {{
      transition: background 0.15s ease;
      background: var(--row-bg);
    }}
    tr.data-row.unseen {{
      background: var(--row-unseen-bg);
    }}
    tr.data-row:hover {{
      background: rgba(82, 208, 255, 0.02);
    }}
    tr.expanded {{
      background: var(--row-bg);
    }}
    .pill {{
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(82, 208, 255, 0.12);
      color: var(--text);
      border: 1px solid rgba(82, 208, 255, 0.25);
      font-size: 12px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .pill small {{
      color: var(--muted);
      font-weight: 600;
      letter-spacing: 0.3px;
    }}
    .detail-row td {{
      padding: 0;
      border: none;
      background: var(--surface);
    }}
    .detail-card {{
      padding: 16px;
      display: grid;
      grid-template-columns: 1fr;
      gap: 12px;
      background: var(--surface);
    }}
    .detail-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }}
    .detail-meta {{
      color: var(--muted);
      font-size: 13px;
    }}
    .settings-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.45);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 50;
    }}
    .settings-panel {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      min-width: 280px;
      box-shadow: var(--shadow);
      display: grid;
      gap: 12px;
    }}
    .settings-panel h2 {{
      margin: 0;
      font-size: 16px;
    }}
    .settings-row {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .embed-wrapper {{
      width: 100%;
      max-width: 550px;
      border-radius: var(--radius);
      overflow: hidden;
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
    }}
    .empty-state {{
      padding: 30px;
      text-align: center;
      color: var(--muted);
    }}
    .server-down-backdrop {{
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.75);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 9999;
    }}
    .server-down-modal {{
      background: var(--surface);
      color: var(--text);
      padding: 24px 28px;
      border-radius: 12px;
      border: 1px solid var(--border);
      box-shadow: 0 20px 50px rgba(0,0,0,0.45);
      max-width: 420px;
      text-align: center;
      font-size: 15px;
      line-height: 1.5;
    }}
    @media (max-width: 900px) {{
      body {{ display: block; }}
      .layout {{ grid-template-columns: 1fr; }}
      aside {{
        position: static;
        height: auto;
        border-right: none;
        border-bottom: 1px solid var(--border);
      }}
      header {{ position: static; }}
      .detail-card {{ padding: 12px; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside>
      <div class="filter-title">Filter by Label/Page</div>
      <div id="label-filters" class="filter-list"></div>
    </aside>
    <main>
      <header>
        <div class="header-bar">
          <div style="display:flex; flex-direction:column; gap:4px;">
            <h1>{escaped_title}</h1>
          </div>
          <div style="display:flex; gap:8px;">
            <label style="display:flex; align-items:center; gap:4px; font-size:12px;">
              <input type="checkbox" id="hide-viewed-toggle" />
              <span>Hide already seen releases</span>
            </label>
            <button id="mark-seen" class="button" style="padding:6px 10px; font-size:12px;">Mark all as seen</button>
            <button id="mark-unseen" class="button" style="padding:6px 10px; font-size:12px;">Mark all as unseen</button>
            <button id="settings-btn" class="button">Settings</button>
          </div>
        </div>
      </header>
      <section class="wireframe-panel" id="scrape-wireframe">
        <div class="wireframe-header">
          <div class="wireframe-title" style="display:flex; align-items:center; gap:6px; white-space:nowrap;">
            <span id="header-range-label" class="detail-meta" style="font-size:12px; white-space:nowrap;"></span>
            <span id="header-count-label" class="detail-meta" style="font-size:12px; white-space:nowrap;"></span>
          </div>
          <button id="scrape-wireframe-toggle" class="button" aria-expanded="false" aria-controls="scrape-wireframe-body">Expand</button>
        </div>
        <div class="wireframe-body" id="scrape-wireframe-body">
          <div class="date-range-panel">
            <div class="calendar-row">
              <div class="calendar-card">
                <div class="calendar-label">
                  <div class="calendar-meta">
                    <button type="button" class="calendar-today-btn" data-cal-today="range">Today</button>
                    <div class="calendar-nav">
                      <button type="button" data-cal-nav="range-prev" aria-label="Previous month">‹</button>
                      <span class="calendar-month" id="calendar-range-month"></span>
                      <button type="button" data-cal-nav="range-next" aria-label="Next month">›</button>
                    </div>
                  </div>
                </div>
                <div class="calendar-grid" id="calendar-range"></div>
              </div>
              <div class="calendar-log">
                <div class="calendar-label" style="justify-content:flex-start; gap:8px;">
                  <span style="font-weight:600;">Status</span>
                </div>
                <div id="populate-log" class="scrollbox"></div>
              </div>
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <button id="select-month-btn" class="button" style="background:var(--panel); border:1px solid var(--border); color:var(--text);">Select this month</button>
              <button id="populate-range" class="button">Populate</button>
            </div>
            <div style="display:none;">
              <input type="text" id="date-filter-from" />
              <input type="text" id="date-filter-to" />
            </div>
          </div>
        </div>
      </section>
      <div class="table-wrapper">
        <table aria-label="Bandcamp releases">
          <thead>
            <tr>
              <th style="width:24px;"></th>
              <th data-sort="page_name" style="min-width:100px; max-width:180px;">Label/Page <span class="sort-indicator"></span></th>
              <th data-sort="artist" style="min-width:120px; max-width:180px;">Artist <span class="sort-indicator"></span></th>
              <th data-sort="title" style="min-width:280px; max-width:560px;">Title <span class="sort-indicator"></span></th>
              <th data-sort="date" style="width:120px; min-width:120px; max-width:120px;">Date <span class="sort-indicator"></span></th>
            </tr>
          </thead>
          <tbody id="release-rows"></tbody>
        </table>
        <div id="empty-state" class="empty-state" style="display: none;">No releases match the current filter.</div>
      </div>
    </main>
  </div>
  <div id="settings-backdrop" class="settings-backdrop">
    <div class="settings-panel">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
        <h2>Settings</h2>
        <button id="settings-close" class="button">Close</button>
      </div>
      <div class="settings-row">
        <input type="checkbox" id="theme-toggle" />
        <label for="theme-toggle">Dark mode</label>
      </div>
      <div class="settings-row">
        <input type="checkbox" id="show-cached-toggle" checked />
        <label for="show-cached-toggle">Show cached badges</label>
      </div>
      <div class="settings-row">
        <input type="checkbox" id="preload-embeds-toggle" />
        <label for="preload-embeds-toggle">Preload Bandcamp players (faster browsing, slower generation)</label>
      </div>
      <div style="height:12px;"></div>
      <div style="display:flex; justify-content:flex-start;">
        <button id="settings-reset" class="button" style="width:auto; padding:6px 10px;">Clear cache</button>
      </div>
    </div>
  </div>
  <div id="server-down-backdrop" class="server-down-backdrop">
    <div class="server-down-modal">Please restart the app to use bcfeed.</div>
  </div>
  <div id="max-results-backdrop" class="max-results-backdrop">
    <div class="max-results-modal">Maximum number of results reached. Try again with a shorter date range.</div>
  </div>
  <script id="release-data" type="application/json">{data_json}</script>
  <script>
    const EMBED_PROXY_URL = {proxy_literal};
  </script>
  <script>
    const releases = JSON.parse(document.getElementById("release-data").textContent);
    const releaseMap = new Map();
    releases.forEach(r => releaseMap.set(releaseKey(r), r));
    const VIEWED_KEY = "bc_viewed_releases_v1";
    const API_ROOT = EMBED_PROXY_URL ? EMBED_PROXY_URL.replace(/\/embed-meta.*$/, "") : null;
    const HEALTH_URL = API_ROOT ? `${{API_ROOT}}/health` : null;
    const serverDownBackdrop = document.getElementById("server-down-backdrop");
    const maxResultsBackdrop = document.getElementById("max-results-backdrop");
    const preloadEmbedsToggle = document.getElementById("preload-embeds-toggle");
    let serverDownShown = false;
    let maxNoticeShown = false;
    const DEFAULT_THEME = {json.dumps(default_theme or "light")};
    const PRELOAD_KEY = "bc_preload_embeds_v1";
    function releaseKey(release) {{
      return release.url || [release.page_name, release.artist, release.title, release.date].filter(Boolean).join("|");
    }}
    function renderDateRangeLabel() {{
      const el = document.getElementById("date-range");
      if (!el || !releases.length) return;
      const dates = releases
        .map(r => r.date)
        .filter(Boolean)
        .map(d => new Date(d))
        .filter(d => !isNaN(d.getTime()))
        .sort((a, b) => a - b);
      if (!dates.length) {{
        el.textContent = "";
        return;
      }}
      const fmt = d => {{
        const y = d.getFullYear();
        const m = `${{d.getMonth() + 1}}`.padStart(2, "0");
        const day = `${{d.getDate()}}`.padStart(2, "0");
        return `${{y}}-${{m}}-${{day}}`;
      }};
      const first = dates[0];
      const last = dates[dates.length - 1];
      el.textContent = `Date range: ${{fmt(first)}} to ${{fmt(last)}}`;
    }}
    async function loadViewedSet() {{
      if (API_ROOT) {{
        try {{
          const resp = await fetch(`${{API_ROOT}}/viewed-state`);
          if (resp.ok) {{
            const data = await resp.json();
            if (data && Array.isArray(data.viewed)) {{
              return new Set(data.viewed);
            }}
          }}
        }} catch (err) {{
          console.warn("Failed to load viewed state from API; falling back to localStorage", err);
        }}
      }}
      try {{
        const raw = localStorage.getItem(VIEWED_KEY);
        if (!raw) return new Set();
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? new Set(parsed) : new Set();
      }} catch (err) {{
        return new Set();
      }}
    }}
    function showServerDownModal() {{
      if (serverDownShown) return;
      serverDownShown = true;
      if (serverDownBackdrop) {{
        serverDownBackdrop.style.display = "flex";
      }}
    }}
    function showMaxResultsModal() {{
      if (maxResultsBackdrop) {{
        maxResultsBackdrop.style.display = "flex";
      }}
    }}
    function hideMaxResultsModal() {{
      if (maxResultsBackdrop) {{
        maxResultsBackdrop.style.display = "none";
      }}
    }}
    function appendPopulateLogLine(msg) {{
      if (!populateLog) return;
      const current = populateLog.textContent || "";
      const next = current ? `${{current}}\\n${{msg}}` : msg;
      populateLog.textContent = next;
      try {{ localStorage.setItem(POPULATE_LOG_KEY, next); }} catch (e) {{}}
    }}
    async function checkServerAlive() {{
      if (!HEALTH_URL || serverDownShown) return;
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 4000);
      try {{
        const resp = await fetch(HEALTH_URL, {{
          method: "GET",
          cache: "no-store",
          signal: controller.signal,
        }});
        clearTimeout(timer);
        if (!resp.ok) throw new Error(`HTTP ${{resp.status}}`);
      }} catch (err) {{
        clearTimeout(timer);
        showServerDownModal();
      }}
    }}
    function persistViewedLocal(set) {{
      try {{
        localStorage.setItem(VIEWED_KEY, JSON.stringify(Array.from(set)));
      }} catch (err) {{}}
    }}
    async function persistViewedRemote(url, isRead) {{
      if (!API_ROOT || !url) return;
      try {{
        await fetch(`${{API_ROOT}}/viewed-state`, {{
          method: "POST",
          headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify({{url, read: isRead}}),
        }});
      }} catch (err) {{
        console.warn("Failed to persist viewed state to API", err);
      }}
    }}
    function setViewed(release, isRead) {{
      const key = releaseKey(release);
      if (!key) return;
      if (isRead) {{
        state.viewed.add(key);
      }} else {{
        state.viewed.delete(key);
      }}
      persistViewedLocal(state.viewed);
      persistViewedRemote(release.url || key, isRead);
      renderCalendar("range");
    }}
    const state = {{
      sortKey: "date",
      direction: "desc",
      showLabels: new Set(),
      showOnlyLabels: new Set(),
      viewed: new Set(),
      hideViewed: false,
      hideViewedSnapshot: new Set(),
      expandedKey: null,
      dateFilterFrom: "",
      dateFilterTo: "",
      showCachedBadges: true,
      preloadEmbeds: false,
    }};
    const THEME_KEY = "bc_dashboard_theme";
    const SHOW_CACHED_KEY = "bc_show_cached_badges";
    const themeToggleBtn = document.getElementById("theme-toggle");
    function applyTheme(theme) {{
      const isLight = theme === "light";
      document.body.classList.toggle("theme-light", isLight);
      if (themeToggleBtn) {{
        themeToggleBtn.checked = !isLight;
      }}
      localStorage.setItem(THEME_KEY, isLight ? "light" : "dark");
    }}
    const savedTheme = localStorage.getItem(THEME_KEY) || DEFAULT_THEME || "light";
    applyTheme(savedTheme);
    if (themeToggleBtn) {{
      themeToggleBtn.checked = savedTheme !== "light";
      themeToggleBtn.addEventListener("change", () => {{
        const next = themeToggleBtn.checked ? "dark" : "light";
        applyTheme(next);
      }});
    }}
    if (maxResultsBackdrop) {{
      maxResultsBackdrop.addEventListener("click", hideMaxResultsModal);
    }}
    if (preloadEmbedsToggle) {{
      const stored = localStorage.getItem(PRELOAD_KEY);
      state.preloadEmbeds = stored === null ? false : stored === "true";
      preloadEmbedsToggle.checked = state.preloadEmbeds;
      preloadEmbedsToggle.addEventListener("change", () => {{
        state.preloadEmbeds = !!preloadEmbedsToggle.checked;
        try {{ localStorage.setItem(PRELOAD_KEY, String(state.preloadEmbeds)); }} catch (e) {{}}
      }});
    }}

    function formatDate(value) {{
      if (!value) return "";
      const parsed = new Date(value);
      if (isNaN(parsed.getTime())) return value;
      const y = parsed.getFullYear();
      const m = `${{parsed.getMonth() + 1}}`.padStart(2, "0");
      const d = `${{parsed.getDate()}}`.padStart(2, "0");
      return `${{y}}-${{m}}-${{d}}`;
    }}

    function pageUrlFor(release) {{
      const url = release.url || "";
      if (!url) return "#";
      if (url.includes("/album/")) return url.split("/album/")[0];
      if (url.includes("/track/")) return url.split("/track/")[0];
      return url;
    }}

    const HIGHLIGHT_PALETTE = ["#52d0ff", "#ff8b52", "#7cde8c", "#ff6b9f", "#c18fff", "#f2d45c", "#8fd8ff", "#ffa34f"];
    const labelColorMap = new Map();
    function colorForLabel(label) {{
      const key = label || "default";
      if (labelColorMap.has(key)) return labelColorMap.get(key);
      const color = HIGHLIGHT_PALETTE[labelColorMap.size % HIGHLIGHT_PALETTE.length];
      labelColorMap.set(key, color);
      return color;
    }}

    function buildHighlightMap(items) {{
      const map = new Map();
      items.forEach(entry => {{
        if (!entry.date) return;
        const dateKey = formatDate(entry.date);
        if (!dateKey) return;
        const color = colorForLabel(entry.page_name || entry.artist || "");
        if (!map.has(dateKey)) map.set(dateKey, new Set());
        map.get(dateKey).add(color);
      }});
      return map;
    }}

    const highlightMap = buildHighlightMap(releases);
    let scrapeStatus = {{ scraped: new Set(), notScraped: new Set() }};

    function buildEmbedUrl(id, isTrack) {{
      if (!id) return null;
      const kind = isTrack ? "track" : "album";
      return `https://bandcamp.com/EmbeddedPlayer/${{kind}}=${{id}}/size=large/bgcol=ffffff/linkcol=0687f5/tracklist=true/artwork=small/transparent=true/`;
    }}

    function parseEmbedMeta(htmlText) {{
      const parser = new DOMParser();
      const doc = parser.parseFromString(htmlText, "text/html");
      const meta = doc.querySelector('meta[name="bc-page-properties"]');
      if (!meta || !meta.content) return null;
      try {{
        return JSON.parse(meta.content);
      }} catch (err) {{
        try {{
          return eval(`(${{meta.content}})`);
        }} catch (e) {{
          return null;
        }}
      }}
    }}

    async function ensureEmbed(release) {{
      if (release.embed_url) {{
        return release.embed_url;
      }}
      if (!release.url) return null;

      const tryDirect = async () => {{
        const response = await fetch(release.url, {{ method: "GET" }});
        const text = await response.text();
        const meta = parseEmbedMeta(text);
        if (!meta) return null;
        const embedUrl = buildEmbedUrl(meta.item_id, meta.item_type === "track");
        release.embed_url = embedUrl;
        if (meta.item_id) release.release_id = meta.item_id;
        release.is_track = meta.item_type === "track";
        return embedUrl;
      }};

      try {{
        if (EMBED_PROXY_URL) {{
          try {{
            const response = await fetch(`${{EMBED_PROXY_URL}}?url=${{encodeURIComponent(release.url)}}`);
            if (!response.ok) throw new Error(`Proxy fetch failed: ${{response.status}}`);
            const data = await response.json();
            const embedUrl = data.embed_url || buildEmbedUrl(data.release_id, data.is_track);
            release.embed_url = embedUrl;
            if (data.release_id) release.release_id = data.release_id;
            if (typeof data.is_track === "boolean") {{
              release.is_track = data.is_track;
            }}
            if (embedUrl) return embedUrl;
          }} catch (proxyErr) {{
            console.warn("Proxy embed fetch failed, falling back to direct fetch", proxyErr);
          }}
        }}
        return await tryDirect();
      }} catch (err) {{
        console.warn("Failed to fetch embed info", err);
        return null;
      }}
    }}

    function renderFilters(sourceList = releases) {{
      const counts = sourceList.reduce((acc, r) => {{
        if (!r.page_name) return acc;
        acc[r.page_name] = (acc[r.page_name] || 0) + 1;
        return acc;
      }}, {{}});
      const labels = Object.keys(counts)
        .sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
      const container = document.getElementById("label-filters");
      container.innerHTML = "";

      if (labels.length === 0) {{
        container.innerHTML = "<div class='detail-meta'>No label/page data available.</div>";
        return;
      }}

      if (state.showLabels.size === 0) {{
        labels.forEach(label => state.showLabels.add(label));
      }}

      const showOnlyMode = state.showOnlyLabels.size > 0;

      labels.forEach(label => {{
        const wrapper = document.createElement("div");
        wrapper.className = "filter-item";
        if (showOnlyMode) wrapper.classList.add("show-only-active");

        const showCheckbox = document.createElement("input");
        showCheckbox.type = "checkbox";
        showCheckbox.className = "filter-checkbox show";
        showCheckbox.dataset.filterRole = "show";
        showCheckbox.checked = state.showLabels.has(label);
        showCheckbox.disabled = showOnlyMode;
        showCheckbox.addEventListener("change", () => {{
          if (showCheckbox.checked) {{
            state.showLabels.add(label);
          }} else {{
            state.showLabels.delete(label);
          }}
          renderTable();
        }});

        const showOnlyCheckbox = document.createElement("input");
        showOnlyCheckbox.type = "checkbox";
        showOnlyCheckbox.className = "filter-checkbox show-only";
        showOnlyCheckbox.dataset.filterRole = "show-only";
        showOnlyCheckbox.checked = state.showOnlyLabels.has(label);
        showOnlyCheckbox.addEventListener("change", () => {{
          if (showOnlyCheckbox.checked) {{
            state.showOnlyLabels.add(label);
          }} else {{
            state.showOnlyLabels.delete(label);
          }}
          syncShowCheckboxAvailability();
          renderTable();
        }});

        const text = document.createElement("span");
        text.textContent = label;
        const count = document.createElement("span");
        count.className = "filter-count";
        count.textContent = `(${{counts[label]}})`;
        wrapper.appendChild(showCheckbox);
        wrapper.appendChild(showOnlyCheckbox);
        wrapper.appendChild(text);
        wrapper.appendChild(count);
        container.appendChild(wrapper);
      }});

      syncShowCheckboxAvailability();
    }}

    function updateRangePreview() {{}}

    function updateHeaderRange(count = null) {{
      const fromVal = state.dateFilterFrom || "";
      const toVal = state.dateFilterTo || "";
      const start = fromVal || toVal;
      const end = toVal || fromVal;
      if (headerRangeLabel) {{
        if (!start && !end) {{
          headerRangeLabel.textContent = "";
        }} else if (start === end) {{
          headerRangeLabel.textContent = `Date range: ${{start}}`;
        }} else {{
          headerRangeLabel.textContent = `Date range: ${{start}} to ${{end}}`;
        }}
      }}
      if (headerCountLabel) {{
        const label = count == null ? "" : `${{count}} release${{count === 1 ? "" : "s"}} shown`;
        headerCountLabel.textContent = label;
      }}
    }}

    function syncShowCheckboxAvailability() {{
      const disableShow = state.showOnlyLabels.size > 0;
      document.querySelectorAll("#label-filters .filter-item").forEach(item => {{
        const show = item.querySelector('input[data-filter-role="show"]');
        if (show) {{
          show.disabled = disableShow;
        }}
        item.classList.toggle("show-only-active", disableShow);
      }});
    }}

    function sortData(items) {{
      const {{sortKey, direction}} = state;
      const dir = direction === "asc" ? 1 : -1;
      return items.slice().sort((a, b) => {{
        if (sortKey === "date") {{
          const da = new Date(a.date);
          const db = new Date(b.date);
          const aTime = isNaN(da) ? 0 : da.getTime();
          const bTime = isNaN(db) ? 0 : db.getTime();
          return (aTime - bTime) * dir;
        }}
        const av = (a[sortKey] || "").toLowerCase();
        const bv = (b[sortKey] || "").toLowerCase();
        if (av === bv) return 0;
        return av > bv ? dir : -dir;
      }});
    }}

    function closeOpenDetailRows() {{
      document.querySelectorAll(".detail-row").forEach(node => {{
        const iframe = node.querySelector("iframe");
        if (iframe) iframe.remove();
        node.remove();
      }});
      document.querySelectorAll("tr.data-row").forEach(row => row.classList.remove("expanded"));
    }}

    function attachRowActions(row, release) {{
      // no-op; buttons removed
    }}

    function createDetailRow(release) {{
      const tr = document.createElement("tr");
      tr.className = "detail-row";
      const td = document.createElement("td");
      td.colSpan = 5;

      td.innerHTML = `
        <div class="detail-card">
          <div class="embed-wrapper" data-embed-target>
            <div class="detail-meta">Loading player…</div>
          </div>
        </div>`;
      tr.appendChild(td);
      td.addEventListener("click", (evt) => {{
        // Ignore clicks directly on the iframe
        if (evt.target.tagName.toLowerCase() === "iframe") return;
        // Focus the parent data row without toggling collapse
        const dataRow = tr.previousElementSibling;
        if (dataRow && dataRow.classList.contains("data-row")) {{
          dataRow.focus();
        }}
      }});
      return tr;
    }}

    function renderTable() {{
      const tbody = document.getElementById("release-rows");
      tbody.innerHTML = "";
      closeOpenDetailRows();

      const dateFiltered = releases.filter(r => withinSelectedRange(r));
      const filtered = dateFiltered.filter(r => {{
        const useShowOnly = state.showOnlyLabels.size > 0;
        const activeSet = useShowOnly ? state.showOnlyLabels : state.showLabels;
        if (activeSet.size > 0) {{
          if (r.page_name && !activeSet.has(r.page_name)) return false;
        }}

        if (state.hideViewed && state.hideViewedSnapshot.size > 0) {{
          const key = releaseKey(r);
          if (state.expandedKey && key === state.expandedKey) return true;
          return !state.hideViewedSnapshot.has(key);
        }}
        return true;
      }});

      const sorted = sortData(filtered);
      document.getElementById("empty-state").style.display = sorted.length ? "none" : "block";

      sorted.forEach(release => {{
        const tr = document.createElement("tr");
        tr.className = "data-row";
        tr.dataset.key = releaseKey(release);
        tr.dataset.page = release.page_name || "";
        tr.tabIndex = 0;
        tr.innerHTML = `
          <td style="width:24px;"><span class="row-dot"></span></td>
          <td><a class="link" href="${{pageUrlFor(release)}}" target="_blank" rel="noopener">${{release.page_name || "Unknown"}}</a></td>
          <td><a class="link" href="${{pageUrlFor(release)}}" target="_blank" rel="noopener">${{release.artist || "—"}}</a></td>
          <td><a class="link" href="${{release.url || "#"}}" target="_blank" rel="noopener">${{release.title || "—"}}</a>${{state.showCachedBadges && release.embed_url ? ' <span class="cached-badge">cached</span>' : ''}}</td>
          <td>${{formatDate(release.date)}}</td>
        `;
        const existingRead = state.viewed.has(releaseKey(release));
        const initialDot = tr.querySelector(".row-dot");
        if (initialDot) initialDot.classList.toggle("read", existingRead);
        tr.classList.toggle("unseen", !existingRead);

        tr.addEventListener("click", () => {{
          tr.focus();
          const existingDetail = tr.nextElementSibling;
          const hasDetail = existingDetail && existingDetail.classList.contains("detail-row");
          const wasVisible = hasDetail && existingDetail.style.display !== "none";

          // If already visible, toggle closed.
          if (wasVisible) {{
            closeOpenDetailRows();
            state.expandedKey = null;
            return;
          }}

          // Hide others
          closeOpenDetailRows();

          let detail = existingDetail;
          if (!hasDetail) {{
            detail = createDetailRow(release);
            tr.after(detail);
          }} else {{
            // ensure adjacency and show
            tr.after(detail);
            detail.style.display = "";
          }}
          tr.classList.add("expanded");
          state.expandedKey = releaseKey(release);

          const embedTarget = detail.querySelector("[data-embed-target]");
          const dot = tr.querySelector(".row-dot");
          if (dot) dot.classList.add("read");
          tr.classList.remove("unseen");
          const cachedUrl = releaseKey(release);
          if (cachedUrl) {{
            state.viewed.add(cachedUrl);
          }}
          setViewed(release, true);
          ensureEmbed(release).then(embedUrl => {{
              if (!embedUrl) {{
                embedTarget.innerHTML = `<div class="detail-meta">No embed available. Is the app still running? <br><a class="link" href="${{release.url || "#"}}" target="_blank" rel="noopener">Open on Bandcamp</a>.</div>`;
                return;
              }}
            const height = release.is_track ? 320 : 480;
            embedTarget.innerHTML = `<iframe title="Bandcamp player" style="border:0; width:100%; height:${{height}}px;" src="${{embedUrl}}" seamless></iframe>`;
            const titleCell = tr.children[3];
            if (titleCell && embedUrl && state.showCachedBadges && !titleCell.querySelector(".cached-badge")) {{
              titleCell.insertAdjacentHTML("beforeend", ' <span class="cached-badge">cached</span>');
            }}
          }});
        }});

        tr.addEventListener("keydown", (evt) => {{
          if (evt.key === "Escape") {{
            evt.preventDefault();
            closeOpenDetailRows();
            return;
          }}
          if (evt.key === " " || evt.key === "Spacebar" || evt.key === "Space") {{
            evt.preventDefault();
            tr.click();
            return;
          }}
          if (evt.key === "Enter") {{
            evt.preventDefault();
            tr.click();
            return;
          }}
          if (evt.key === "ArrowDown" || evt.key === "ArrowUp") {{
            evt.preventDefault();
            const rows = Array.from(document.querySelectorAll("tr.data-row"));
            const idx = rows.indexOf(tr);
            const nextIdx = evt.key === "ArrowDown" ? idx + 1 : idx - 1;
            if (nextIdx >= 0 && nextIdx < rows.length) {{
              rows[nextIdx].focus();
            }}
            return;
          }}
          if (evt.key.toLowerCase() === "u") {{
            evt.preventDefault();
            const markerCell = tr.querySelector("td:first-child");
            if (markerCell) {{
              const dot = markerCell.querySelector(".row-dot");
              if (dot) dot.classList.toggle("read", false);
              else {{
                const newDot = document.createElement("span");
                newDot.className = "row-dot";
                markerCell.appendChild(newDot);
              }}
              setViewed(release, false);
            }}
          }}
        }});

        const markerCell = tr.querySelector("td:first-child");
        if (markerCell) {{
          markerCell.addEventListener("click", (evt) => {{
            evt.stopPropagation();
            const dot = markerCell.querySelector(".row-dot");
            if (dot) {{
              const willBeRead = !dot.classList.contains("read");
              dot.classList.toggle("read");
              tr.classList.toggle("unseen", !willBeRead);
              setViewed(release, willBeRead);
            }}
          }});
        }}

        // Hover/focus-based preload with debounce (0.2s)
        let preloadTimer;
        const schedulePreload = () => {{
          preloadTimer = setTimeout(() => ensureEmbed(release), 200);
        }};
        const cancelPreload = () => {{
          if (preloadTimer) {{
            clearTimeout(preloadTimer);
            preloadTimer = null;
          }}
        }};
        tr.addEventListener("mouseenter", schedulePreload);
        tr.addEventListener("mouseleave", cancelPreload);
        tr.addEventListener("focus", schedulePreload);
        tr.addEventListener("blur", cancelPreload);

        attachRowActions(tr, release);
        tbody.appendChild(tr);
      }});
      refreshSortIndicators();
      renderFilters(dateFiltered);
      updateHeaderRange(sorted.length);
    }}

    function refreshSortIndicators() {{
      document.querySelectorAll("th[data-sort]").forEach(th => {{
        const indicator = th.querySelector(".sort-indicator");
        const key = th.dataset.sort;
        if (state.sortKey === key) {{
          indicator.textContent = state.direction === "asc" ? "▲" : "▼";
          th.style.color = "var(--text)";
        }} else {{
          indicator.textContent = "";
          th.style.color = "var(--muted)";
        }}
      }});
    }}

    function attachHeaderSorting() {{
      document.querySelectorAll("th[data-sort]").forEach(th => {{
        th.addEventListener("click", () => {{
          const key = th.dataset.sort;
          if (state.sortKey === key) {{
            state.direction = state.direction === "asc" ? "desc" : "asc";
          }} else {{
            state.sortKey = key;
            state.direction = key === "date" ? "desc" : "asc";
          }}
          renderTable();
        }});
      }});
    }}

    renderFilters();
    attachHeaderSorting();
    const settingsBackdrop = document.getElementById("settings-backdrop");
    const settingsBtn = document.getElementById("settings-btn");
    const settingsClose = document.getElementById("settings-close");
    const settingsReset = document.getElementById("settings-reset");
    const resetClearCache = null;
    const resetClearViewed = null;
    const hideViewedToggle = document.getElementById("hide-viewed-toggle");
    const markSeenBtn = document.getElementById("mark-seen");
    const markUnseenBtn = document.getElementById("mark-unseen");
    const dateFilterFrom = document.getElementById("date-filter-from");
    const dateFilterTo = document.getElementById("date-filter-to");
    const showCachedToggle = document.getElementById("show-cached-toggle");
    const wireframePanel = document.getElementById("scrape-wireframe");
    const wireframeToggle = document.getElementById("scrape-wireframe-toggle");
    const wireframeBody = document.getElementById("scrape-wireframe-body");
    const calendarRange = document.getElementById("calendar-range");
    const calendarRangeMonth = document.getElementById("calendar-range-month");
    const populateBtn = document.getElementById("populate-range");
    const selectMonthBtn = document.getElementById("select-month-btn");
    const populateStatus = document.createElement("div");
    const POPULATE_LOG_KEY = "bc_populate_log_v1";
    const populateLog = document.getElementById("populate-log");
    const CALENDAR_STATE_KEY = "bc_calendar_state_v1";
    const headerRangeLabel = document.getElementById("header-range-label");
    const headerCountLabel = document.getElementById("header-count-label");
    const SCRAPE_STATUS_URL = API_ROOT ? `${{API_ROOT}}/scrape-status` : null;

    function toggleSettings(open) {{
      if (!settingsBackdrop) return;
      settingsBackdrop.style.display = open ? "flex" : "none";
    }}
    if (settingsBtn) settingsBtn.addEventListener("click", () => toggleSettings(true));
    if (settingsClose) settingsClose.addEventListener("click", () => toggleSettings(false));
    if (settingsBackdrop) settingsBackdrop.addEventListener("click", (e) => {{
      if (e.target === settingsBackdrop) toggleSettings(false);
    }});

    async function performReset() {{
      const clearCache = true;
      const clearViewed = true;
      let hadError = false;
      if (API_ROOT) {{
        try {{
          const resp = await fetch(`${{API_ROOT}}/reset-caches`, {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{clear_cache: clearCache, clear_viewed: clearViewed}}),
          }});
          if (!resp.ok) throw new Error(`HTTP ${{resp.status}}`);
        }} catch (err) {{
          console.warn("Failed to reset via API", err);
          hadError = true;
        }}
      }} else {{
        hadError = true; // cannot clear disk cache without API
      }}
      state.viewed = new Set();
      persistViewedLocal(state.viewed);
      releases.forEach(r => {{
        delete r.embed_url;
        delete r.release_id;
        delete r.is_track;
      }});
      renderTable();
      toggleSettings(false);
      if (hadError && clearCache) {{
        alert("Could not clear disk cache (proxy not reachable). Run the app/proxy and try again.");
      }} else {{
        window.location.reload();
      }}
    }}
    if (settingsReset) settingsReset.addEventListener("click", performReset);

    function applyHideViewed(checked) {{
      const expandedRow = document.querySelector("tr.data-row.expanded");
      if (expandedRow && expandedRow.dataset.key) {{
        state.expandedKey = expandedRow.dataset.key;
      }}
      state.hideViewed = checked;
      if (checked) {{
        state.hideViewedSnapshot = new Set(state.viewed);
      }} else {{
        state.hideViewedSnapshot = new Set();
      }}
      renderTable();
    }}
    if (hideViewedToggle) {{
      hideViewedToggle.addEventListener("change", () => applyHideViewed(hideViewedToggle.checked));
    }}

    function markVisibleRows(seen) {{
      const rows = Array.from(document.querySelectorAll("#release-rows tr.data-row"));
      rows.forEach(row => {{
        const key = row.dataset.key;
        const release = key ? releaseMap.get(key) : null;
        if (!release) return;
        setViewed(release, seen);
        const dot = row.querySelector(".row-dot");
        if (dot) {{
          dot.classList.toggle("read", seen);
        }}
        row.classList.toggle("unseen", !seen);
      }});
      if (state.hideViewed) {{
        state.hideViewedSnapshot = new Set(state.viewed);
      }}
      renderTable();
      renderCalendar("range");
    }}
    if (markSeenBtn) markSeenBtn.addEventListener("click", () => markVisibleRows(true));
    if (markUnseenBtn) markUnseenBtn.addEventListener("click", () => markVisibleRows(false));

    if (showCachedToggle) {{
      const savedShowCached = localStorage.getItem(SHOW_CACHED_KEY);
      if (savedShowCached !== null) {{
        state.showCachedBadges = savedShowCached === "true";
      }}
      showCachedToggle.checked = state.showCachedBadges;
      showCachedToggle.addEventListener("change", () => {{
        state.showCachedBadges = !!showCachedToggle.checked;
        localStorage.setItem(SHOW_CACHED_KEY, String(state.showCachedBadges));
        renderTable();
      }});
    }}

    const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const calendars = {{
      range: {{ container: calendarRange, current: new Date(), startKey: null, endKey: null }},
    }};

    function isoKeyFromDate(dateObj) {{
      if (!(dateObj instanceof Date) || isNaN(dateObj.getTime())) return "";
      const y = dateObj.getFullYear();
      const m = String(dateObj.getMonth() + 1).padStart(2, "0");
      const d = String(dateObj.getDate()).padStart(2, "0");
      return `${{y}}-${{m}}-${{d}}`;
    }}

    function parseDateString(value) {{
      if (!value) return null;
      const parts = value.split("-");
      if (parts.length !== 3) return null;
      const [y, m, d] = parts.map(Number);
      const parsed = new Date(y, m - 1, d);
      if (isNaN(parsed.getTime())) return null;
      if (parsed.getFullYear() !== y || parsed.getMonth() !== m - 1 || parsed.getDate() !== d) return null;
      return parsed;
    }}

    function withinSelectedRange(release) {{
      let fromVal = state.dateFilterFrom || "";
      let toVal = state.dateFilterTo || "";
      if (fromVal && !toVal) toVal = fromVal;
      if (toVal && !fromVal) fromVal = toVal;
      const rowTs = Date.parse(release.date);
      if (fromVal) {{
        const fromTs = Date.parse(fromVal);
        if (!isNaN(fromTs) && !isNaN(rowTs) && rowTs < fromTs) return false;
      }}
      if (toVal) {{
        const toTs = Date.parse(toVal);
        if (!isNaN(toTs) && !isNaN(rowTs) && rowTs > toTs) return false;
      }}
      return true;
    }}

    function renderCalendar(type) {{
      const cal = calendars[type];
      if (!cal || !cal.container) return;
      const grid = cal.container;
      grid.innerHTML = "";

      const monthLabel = calendarRangeMonth;
      if (monthLabel) {{
        const monthName = cal.current.toLocaleString("en-US", {{ month: "short", year: "numeric" }});
        monthLabel.textContent = monthName;
      }}

      WEEKDAYS.forEach(day => {{
        const label = document.createElement("div");
        label.className = "calendar-weekday";
        label.textContent = day;
        grid.appendChild(label);
      }});

      const monthStart = new Date(cal.current.getFullYear(), cal.current.getMonth(), 1);
      const startOffset = monthStart.getDay();
      const totalCells = 42; // 6 weeks
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const startSelectedDate = cal.startKey ? parseDateString(cal.startKey) : null;
      const endSelectedDate = cal.endKey ? parseDateString(cal.endKey) : null;

      for (let idx = 0; idx < totalCells; idx++) {{
        const dayNumber = idx - startOffset + 1;
        const cellDate = new Date(cal.current.getFullYear(), cal.current.getMonth(), dayNumber);
        const isOtherMonth = cellDate.getMonth() !== cal.current.getMonth();
        const key = isoKeyFromDate(cellDate);
        const cell = document.createElement("div");
        cell.className = "calendar-day";
        let isDisabled = cellDate > today;
        if (isOtherMonth) cell.classList.add("other-month");
        if (isDisabled) cell.classList.add("disabled");
        if (cal.startKey === key || cal.endKey === key) cell.classList.add("selected");
        if (startSelectedDate && endSelectedDate && cellDate >= startSelectedDate && cellDate <= endSelectedDate) {{
          cell.classList.add("in-range");
        }}
        cell.textContent = String(cellDate.getDate());
        const dots = document.createElement("div");
        dots.className = "dot-strip";
        const scraped = scrapeStatus.scraped.has(key);
        if (scraped) {{
          cell.classList.add("scraped");
        }}
        const hasUnseen = releases.some(rel => {{
          const relDate = formatDate(rel.date);
          const relKey = releaseKey(rel);
          if (!relDate || relDate !== key) return false;
          return !state.viewed.has(relKey);
        }});
        if (hasUnseen) {{
          const unseenDot = document.createElement("span");
          unseenDot.className = "dot unseen";
          dots.appendChild(unseenDot);
        }}
        cell.appendChild(dots);

        cell.addEventListener("click", () => {{
          if (isDisabled) return;
          const startKey = cal.startKey;
          const endKey = cal.endKey;
          const clickedKey = key;
          if (!startKey || (startKey && endKey)) {{
            // Start a new selection
            cal.startKey = clickedKey;
            cal.endKey = null;
          }} else if (startKey && !endKey) {{
            const startDate = parseDateString(startKey);
            const clickedDate = cellDate;
            if (startDate && clickedDate < startDate) {{
              cal.endKey = startKey;
              cal.startKey = clickedKey;
            }} else {{
              cal.endKey = clickedKey;
            }}
          }}
          renderCalendar("range");
          applyCalendarFiltersFromSelection();
        }});
        grid.appendChild(cell);
      }}
    }}

    function shiftCalendarMonth(type, delta) {{
      const cal = calendars[type];
      if (!cal) return;
      const next = new Date(cal.current.getFullYear(), cal.current.getMonth() + delta, 1);
      const now = new Date();
      const maxMonth = new Date(now.getFullYear(), now.getMonth(), 1);
      cal.current = next > maxMonth ? maxMonth : next;
      renderCalendar(type);
    }}

    function initializeCalendars() {{
      const dateValues = releases
        .map(entry => parseDateString(entry.date))
        .filter(Boolean)
        .sort((a, b) => a - b);
      const today = new Date();
      if (dateValues.length) {{
        calendars.range.current = new Date(dateValues[0].getFullYear(), dateValues[0].getMonth(), 1);
      }} else {{
        calendars.range.current = new Date(today.getFullYear(), today.getMonth(), 1);
      }}
      syncCalendarsFromInputs();
      renderCalendar("range");
    }}

    function syncCalendarsFromInputs() {{
      const fromVal = dateFilterFrom ? dateFilterFrom.value.trim() : "";
      const toVal = dateFilterTo ? dateFilterTo.value.trim() : "";
      const parsedFrom = parseDateString(fromVal);
      const parsedTo = parseDateString(toVal);
      calendars.range.startKey = parsedFrom ? isoKeyFromDate(parsedFrom) : null;
      calendars.range.endKey = parsedTo ? isoKeyFromDate(parsedTo) : null;
      const target = parsedTo || parsedFrom;
      if (target) {{
        calendars.range.current = new Date(target.getFullYear(), target.getMonth(), 1);
      }}
    }}

    document.querySelectorAll("[data-cal-nav]").forEach(btn => {{
      btn.addEventListener("click", () => {{
        const role = btn.getAttribute("data-cal-nav") || "";
        if (role.startsWith("range")) shiftCalendarMonth("range", role.endsWith("prev") ? -1 : 1);
      }});
    }});

    document.querySelectorAll("[data-cal-today]").forEach(btn => {{
      btn.addEventListener("click", () => {{
        const cal = calendars.range;
        if (!cal) return;
        const today = new Date();
        const todayKey = isoKeyFromDate(today);
        cal.current = new Date(today.getFullYear(), today.getMonth(), 1);
        if (!cal.startKey || (cal.startKey && cal.endKey)) {{
          cal.startKey = todayKey;
          cal.endKey = null;
        }} else {{
          cal.endKey = todayKey;
        }}
        renderCalendar("range");
        applyCalendarFiltersFromSelection();
      }});
    }});

    function selectVisibleMonthRange() {{
      const cal = calendars.range;
      if (!cal) return;
      const current = cal.current || new Date();
      const year = current.getFullYear();
      const month = current.getMonth();
      const startDate = new Date(year, month, 1);
      const endDate = new Date(year, month + 1, 0);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (today.getFullYear() === year && today.getMonth() === month) {{
        endDate.setTime(today.getTime());
      }}
      cal.startKey = isoKeyFromDate(startDate);
      cal.endKey = isoKeyFromDate(endDate);
      renderCalendar("range");
      applyCalendarFiltersFromSelection();
    }}
    if (selectMonthBtn) {{
      selectMonthBtn.addEventListener("click", selectVisibleMonthRange);
    }}

    function populateRangeFromCalendars() {{
      checkServerAlive();
      applyCalendarFiltersFromSelection();
      let startVal = dateFilterFrom ? dateFilterFrom.value.trim() : "";
      let endVal = dateFilterTo ? dateFilterTo.value.trim() : "";
      if (startVal && !endVal) endVal = startVal;
      if (endVal && !startVal) startVal = endVal;
      const preloadEmbeds = !!(preloadEmbedsToggle && preloadEmbedsToggle.checked);
      if (!API_ROOT || !startVal || !endVal) return;
      const btn = populateBtn;
      const original = btn ? btn.textContent : "";
      if (btn) {{
        btn.disabled = true;
        btn.textContent = "Populating…";
      }}
      populateStatus.textContent = "";

      async function runPopulate() {{
        if (window.EventSource) {{
          if (populateLog) populateLog.textContent = "";
          try {{ localStorage.setItem(POPULATE_LOG_KEY, ""); }} catch (e) {{}}
          const url = `${{API_ROOT}}/populate-range-stream?start=${{encodeURIComponent(startVal)}}&end=${{encodeURIComponent(endVal)}}&preload_embeds=${{preloadEmbeds ? "true" : "false"}}`;
          const es = new EventSource(url);
          es.onmessage = (ev) => {{
            if (!ev || !ev.data) return;
            if (!maxNoticeShown && ev.data.includes("Maximum results")) {{
              maxNoticeShown = true;
              showMaxResultsModal();
              appendPopulateLogLine("Maximum number of results reached. Stopping download.");
            }}
            const current = populateLog ? populateLog.textContent : "";
            const next = current ? `${{current}}\\n${{ev.data}}` : ev.data;
            if (populateLog) populateLog.textContent = next;
            try {{ localStorage.setItem(POPULATE_LOG_KEY, next); }} catch (e) {{}}
          }};
          es.addEventListener("done", () => {{
            populateStatus.textContent = "Done. Reloading…";
            es.close();
            window.location.reload();
          }});
          es.onerror = () => {{
            es.close();
            populateStatus.textContent = "";
            alert("Populate failed (stream error)");
            if (btn) {{
              btn.disabled = false;
              btn.textContent = original || "Populate";
            }}
          }};
          return;
        }}

        try {{
          const resp = await fetch(`${{API_ROOT}}/populate-range`, {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{start: startVal, end: endVal, preload_embeds: preloadEmbeds}}),
          }});
          const data = await resp.json().catch(() => ({{}}));
          const joinedLogs = Array.isArray(data.logs) ? data.logs.join("\\n") : "";
          if (!resp.ok) {{
            if (populateLog && joinedLogs) {{
              populateLog.textContent = joinedLogs;
            }}
            if (joinedLogs) {{
              try {{ localStorage.setItem(POPULATE_LOG_KEY, joinedLogs); }} catch (e) {{}}
            }}
            throw new Error(data.error || `HTTP ${{resp.status}}`);
          }}
          if (populateLog && joinedLogs) {{
            populateLog.textContent = joinedLogs;
          }}
          if (joinedLogs) {{
            try {{ localStorage.setItem(POPULATE_LOG_KEY, joinedLogs); }} catch (e) {{}}
          }}
          if (!maxNoticeShown && joinedLogs.includes("Maximum results")) {{
            maxNoticeShown = true;
            showMaxResultsModal();
            appendPopulateLogLine("Maximum number of results reached. Stopping download.");
          }}
          populateStatus.textContent = "Done. Reloading…";
          window.location.reload();
        }} catch (err) {{
          populateStatus.textContent = "";
          if (populateLog) populateLog.textContent = String(err || "Error");
          try {{ localStorage.setItem(POPULATE_LOG_KEY, String(err || "Error")); }} catch (e) {{}}
          alert(`Populate failed: ${{err.message || err}}`);
        }} finally {{
          if (btn) {{
            btn.disabled = false;
            btn.textContent = original || "Populate";
          }}
        }}
      }}
      runPopulate();
    }}
    if (populateBtn) populateBtn.addEventListener("click", populateRangeFromCalendars);

    function setDefaultDateFilters() {{
      if ((dateFilterFrom && dateFilterFrom.value) || (dateFilterTo && dateFilterTo.value)) return;
      if (!releases.length) return;
      const dates = releases
        .map(entry => parseDateString(entry.date))
        .filter(Boolean)
        .sort((a, b) => a - b);
      if (!dates.length) return;
      const first = isoKeyFromDate(dates[0]);
      const last = isoKeyFromDate(dates[dates.length - 1]);
      if (dateFilterFrom && !dateFilterFrom.value) dateFilterFrom.value = first;
      if (dateFilterTo && !dateFilterTo.value) dateFilterTo.value = last;
      onDateFilterChange();
    }}

    function applyCalendarFiltersFromSelection() {{
      const cal = calendars.range;
      const fromKey = cal.startKey;
      const toKey = cal.endKey || "";
      if (dateFilterFrom && fromKey) {{
        dateFilterFrom.value = fromKey;
      }}
      if (dateFilterTo) {{
        dateFilterTo.value = toKey;
      }}
      onDateFilterChange();
      updateRangePreview();
    }}

    async function fetchScrapeStatus() {{
      if (!SCRAPE_STATUS_URL) return;
      try {{
        const params = new URLSearchParams();
        const firstDate = releases[0]?.date;
        const lastDate = releases[releases.length - 1]?.date;
        if (firstDate) params.set("start", formatDate(firstDate));
        if (lastDate) params.set("end", formatDate(lastDate));
        const resp = await fetch(`${{SCRAPE_STATUS_URL}}?${{params.toString()}}`);
        if (!resp.ok) throw new Error(`HTTP ${{resp.status}}`);
        const data = await resp.json();
        scrapeStatus.scraped = new Set(data.scraped || []);
        const notScraped = data.not_scraped || data["not_scraped"] || [];
        scrapeStatus.notScraped = new Set(notScraped || []);
        renderCalendar("range");
      }} catch (err) {{
        console.warn("Failed to load scrape status", err);
      }}
    }}

    function loadCalendarState() {{
      if (!dateFilterFrom || !dateFilterTo) return;
      try {{
        const raw = localStorage.getItem(CALENDAR_STATE_KEY);
        if (!raw) return;
        const data = JSON.parse(raw);
        if (data && typeof data === "object") {{
          if (typeof data.from === "string") dateFilterFrom.value = data.from;
          if (typeof data.to === "string") dateFilterTo.value = data.to;
          if (populateLog && typeof data.populateLog === "string") {{
            populateLog.textContent = data.populateLog;
          }}
        }}
      }} catch (err) {{}}
      try {{
        const savedLog = localStorage.getItem(POPULATE_LOG_KEY);
        if (populateLog && savedLog) {{
          populateLog.textContent = savedLog;
        }}
      }} catch (e) {{}}
      onDateFilterChange();
    }}

    function persistCalendarState() {{
      if (!dateFilterFrom || !dateFilterTo) return;
      const payload = {{
        from: (dateFilterFrom.value || "").trim(),
        to: (dateFilterTo.value || "").trim(),
        populateLog: (() => {{
          try {{ return localStorage.getItem(POPULATE_LOG_KEY) || ""; }} catch (e) {{ return ""; }}
        }})(),
      }};
      try {{
        localStorage.setItem(CALENDAR_STATE_KEY, JSON.stringify(payload));
      }} catch (err) {{}}
    }}

    function setWireframeOpen(open) {{
      if (!wireframePanel || !wireframeBody || !wireframeToggle) return;
      wireframePanel.classList.toggle("open", open);
      wireframeBody.hidden = !open;
      wireframeToggle.setAttribute("aria-expanded", open ? "true" : "false");
      wireframeToggle.textContent = open ? "Collapse" : "Expand";
    }}
    setWireframeOpen(true);
    if (wireframeToggle) {{
      wireframeToggle.addEventListener("click", () => {{
        const isOpen = wireframePanel && wireframePanel.classList.contains("open");
        setWireframeOpen(!isOpen);
      }});
    }}

    function onDateFilterChange() {{
      state.dateFilterFrom = dateFilterFrom ? dateFilterFrom.value.trim() : "";
      state.dateFilterTo = dateFilterTo ? dateFilterTo.value.trim() : "";
      syncCalendarsFromInputs();
      renderCalendar("range");
      updateRangePreview();
      updateHeaderRange();
      persistCalendarState();
      renderTable();
    }}
    if (dateFilterFrom) dateFilterFrom.addEventListener("input", onDateFilterChange);
    if (dateFilterTo) dateFilterTo.addEventListener("input", onDateFilterChange);

    initializeCalendars();
    loadCalendarState();
    setDefaultDateFilters();
    fetchScrapeStatus();
    setTimeout(() => checkServerAlive(), 500);
    setInterval(() => checkServerAlive(), 5000);

    // Render after viewed state loads to keep persisted read dots and show date range
    loadViewedSet().then(set => {{
      state.viewed = set;
      renderDateRangeLabel();
      renderTable();
      renderCalendar("range");
    }}).catch(() => {{
      renderDateRangeLabel();
      renderTable();
      renderCalendar("range");
    }});
  </script>
</body>
</html>
"""

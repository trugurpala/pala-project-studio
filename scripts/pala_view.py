#!/usr/bin/env python3
"""HTML view layer for the Pala control / status page.

Server-free, no external assets. One optional inline script may persist UI
prefs (theme + display toggles) in localStorage only — no network calls.
"""

from __future__ import annotations

import html
from typing import Any

_PURPOSE_LABELS = {
    "instructions": "AGENTS / talimat",
    "status": "guncel durum",
    "progress": "ilerleme",
    "plan": "plan",
    "tooling": "arac kararlari",
    "debugging": "debug gunlugu",
    "git": "git durumu",
}

_KIND_LABELS = {
    "register": "kayit",
    "begin": "basla",
    "checkpoint": "checkpoint",
    "debug_attempt": "debug denemesi",
    "provision": "provision",
    "mismatch": "uyumsuzluk",
}

_SECTION_NAV = (
    ("overview", "Genel bakis"),
    ("install", "Kurulum / Doctor"),
    ("hooks", "Hooks trust"),
    ("quality", "Quality engine"),
    ("memory", "Hafiza / store"),
    ("tickets", "Ticket / sonraki is"),
    ("features", "Yetki / ozellik"),
)


def _e(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _freshness_badge(level: str) -> str:
    labels = {"fresh": "taze", "aging": "eskiyor", "stale": "bayat"}
    return f'<span class="badge {level}">{labels.get(level, level)}</span>'


def _update_banner(
    update: dict[str, object] | None, cache_checked_at: str | None = None
) -> str:
    if not update:
        return '<div class="warnline">Pala guncellik: bilinmiyor</div>'
    status = str(update.get("status") or "unavailable")
    installed = _e(update.get("installed_version") or "?")
    available = _e(update.get("available_version") or "")
    url = update.get("url")
    checked = ""
    if isinstance(cache_checked_at, str) and cache_checked_at:
        checked = f' <span class="muted-inline">(son bakis: {_e(cache_checked_at)})</span>'
    if status == "update-available":
        link = ""
        if isinstance(url, str) and url.startswith("https://"):
            link = f' <a href="{_e(url)}">indir</a>'
        return (
            f'<div class="alert">Guncelleme var: {installed} &rarr; {available}'
            f"{link}{checked}</div>"
        )
    if status == "current":
        return f'<div class="okline">Pala guncel ({installed}){checked}</div>'
    return f'<div class="warnline">Pala guncellik: cevrimdisi / bilinmiyor{checked}</div>'


def _now_text(next_action: object, active_ticket: object = None) -> str:
    ticket = str(active_ticket).strip() if active_ticket else ""
    text = str(next_action).strip() if next_action else ""
    if ticket and text:
        if ticket not in text:
            text = f"{ticket} — {text}"
    elif ticket:
        text = ticket
    elif not text:
        text = "Henüz sonraki iş yok — register veya begin çalıştır."
    return text


def _now_line(next_action: object, active_ticket: object = None) -> str:
    text = _now_text(next_action, active_ticket)
    return (
        f'<div class="nowline" role="status"><span class="now-k">Şimdi:</span> '
        f"<span>{_e(text)}</span></div>"
    )


def _decision_strip(
    *,
    next_action: object,
    coherence: dict[str, object],
    brain: object,
    last_gate: object,
    freshness_level: object,
    quality: object,
) -> str:
    """Top decision strip: five shipping signals from the quality engine."""
    coherence = coherence if isinstance(coherence, dict) else {}
    quality = quality if isinstance(quality, dict) else {}
    risk = quality.get("risk") if isinstance(quality.get("risk"), dict) else {}
    coverage = quality.get("coverage") if isinstance(quality.get("coverage"), dict) else {}
    ticket = str(quality.get("ticket") or coherence.get("active") or "yok")
    risk_level = str(risk.get("level") or "unknown")
    reasons = ", ".join(str(item) for item in list(risk.get("reasons") or [])[:3])
    risk_label = f"{risk_level} — {reasons}" if reasons else risk_level
    quality_status = str(quality.get("status") or "not-run")
    quality_tone = (
        "ok" if quality_status == "passed" else "alert"
        if quality_status in {"blocked", "failed"} else "warn"
    )
    risk_tone = (
        "alert" if risk_level == "high"
        else "warn" if risk_level in {"medium", "unknown"} else "ok"
    )
    coverage_label = (
        f"{int(coverage.get('passed') or 0)}/{int(coverage.get('required') or 0)} passed"
    )
    cells = [
        ("Aktif ticket", ticket[:72], "now"),
        ("Risk seviyesi", risk_label[:72], risk_tone),
        ("Quality coverage", coverage_label, quality_tone),
        (
            "Son eksik gate",
            str(quality.get("last_problem") or "quality ledger not initialized")[:72],
            quality_tone,
        ),
        (
            "Tek sonraki eylem",
            str(quality.get("next_action") or next_action or "yok")[:120],
            "now",
        ),
    ]
    _ = (brain, last_gate, freshness_level)
    parts: list[str] = []
    for key, value, tone in cells:
        parts.append(
            f'<div class="signal tone-{tone}">'
            f'<div class="signal-k">{_e(key)}</div>'
            f'<div class="signal-v">{_e(value)}</div>'
            f"</div>"
        )
    return (
        '<div class="decision-strip" role="region" aria-label="Karar sinyalleri">'
        f'{"".join(parts)}</div>'
    )


def _brain_line(brain: object) -> str:
    if not isinstance(brain, dict) or not brain.get("ok"):
        detail = ""
        if isinstance(brain, dict) and brain.get("detail"):
            detail = f" ({_e(brain.get('detail'))})"
        return (
            f'<div class="warnline">Hata beyni: okunamadı{detail} — '
            "DEBUGGING.md Format / INC alanlarını kontrol et.</div>"
        )
    open_count = int(brain.get("open") or 0)
    fixed_count = int(brain.get("fixed") or 0)
    total = int(brain.get("total") or 0)
    path = _e(brain.get("path") or "DEBUGGING.md")
    soft_note = (
        '<span class="soft-closed-note muted-inline"> '
        f"(kapalı {fixed_count} — soft-fail kapalı hatırlatma açık)</span>"
    )
    if open_count:
        cls = "alert"
        note = f"{open_count} açık / {fixed_count} kapalı (toplam {total})"
    else:
        cls = "okline"
        note = f"açık yok; {fixed_count} kapalı (toplam {total})"
    return (
        f'<div class="{cls}">Hata beyni: {note} — önce <span class="mono">{path}</span> '
        f"oku.{soft_note}</div>"
    )


def _progress_block(progress: dict[str, object]) -> str:
    ready = int(progress.get("ready") or 0)
    total = int(progress.get("total") or 0)
    missing = progress.get("missing")
    missing_list = missing if isinstance(missing, list) else []
    if missing_list:
        items = "".join(f"<li>{_e(item)}</li>" for item in missing_list[:7])
        missing_html = f'<p class="gap-note">Eksik:</p><ul class="gap-list">{items}</ul>'
    else:
        missing_html = '<p class="ok-note">Okuma sirasi tamam.</p>'
    return (
        f'<div class="progress-block">'
        f'<div class="progress-head">{ready}/{total} hazir</div>'
        f"{missing_html}"
        f"</div>"
    )


def _read_order_rows(read_order: list[object]) -> str:
    rows: list[str] = []
    for index, item in enumerate(read_order, start=1):
        if not isinstance(item, dict):
            continue
        purpose = str(item.get("purpose") or "")
        label = _PURPOSE_LABELS.get(purpose, purpose)
        path = item.get("path") or "(yok)"
        exists = bool(item.get("exists"))
        badge = "var" if exists else "eksik"
        cls = "ok" if exists else "gap"
        rows.append(
            f'<tr><td class="num">{index}</td><td>{_e(label)}</td>'
            f'<td class="mono">{_e(path)}</td>'
            f'<td><span class="badge {cls}">{badge}</span></td></tr>'
        )
    return "\n".join(rows)


def _timeline_html(events: list[object]) -> str:
    if not events:
        return (
            '<p class="muted">Henuz olay yok. register, begin, checkpoint, '
            "debug_attempt veya provision calisinca burada gorunur.</p>"
        )
    items: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        kind = str(event.get("kind") or "")
        label = _KIND_LABELS.get(kind, kind or "olay")
        stamp = str(event.get("created_at") or "")[:19].replace("T", " ")
        name = event.get("project_name") or ""
        detail = event.get("detail") or ""
        kind_class = f"kind-{kind}" if kind else "kind-unknown"
        items.append(
            f'<li class="timeline-item {kind_class}" data-kind="{_e(kind)}">'
            f'<span class="badge kind {kind_class}">{_e(label)}</span>'
            f'<span><span class="mono">{_e(stamp)}</span> '
            f"{_e(name)} — {_e(detail)}</span>"
            "</li>"
        )
    return f'<ol class="timeline">{"".join(items)}</ol>'


def _provisions_html(provisions: list[object]) -> str:
    if not provisions:
        return (
            '<p class="muted">Henuz URL kurulumu yok. '
            "pala_provision.py ile HTTPS repo ekle.</p>"
        )
    rows: list[str] = []
    for item in provisions:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f'<td class="mono">{_e(item.get("source_url"))}</td>'
            f'<td class="mono">{_e(item.get("install_path"))}</td>'
            f'<td>{_e(item.get("status") or "?")}</td>'
            f'<td>{_e(item.get("created_at") or "")[:19]}</td>'
            "</tr>"
        )
    return (
        "<table><thead><tr><th>URL</th><th>Hedef</th><th>Durum</th><th>Zaman</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


def _project_detail_html(item: dict[str, object], freshness_fn: Any) -> str:
    tech = item.get("tech")
    tech_text = ", ".join(tech) if isinstance(tech, list) else ""
    blockers = item.get("blockers")
    blocker_list = blockers if isinstance(blockers, list) else []
    level = freshness_fn(item.get("updated_at"))
    github = item.get("github")
    github_html = ""
    if isinstance(github, str) and github.startswith("https://"):
        github_html = f'<p>GitHub: <a href="{_e(github)}">{_e(github)}</a></p>'
    blocker_html = ""
    if blocker_list:
        items = "".join(f"<li>{_e(b)}</li>" for b in blocker_list[:8])
        blocker_html = f"<p>Blokajlar:</p><ul>{items}</ul>"
    return (
        f'<div class="grid">'
        f'<div class="card"><div class="k">Faz</div>'
        f'<div class="v">{_e(item.get("phase") or "belirsiz")}</div></div>'
        f'<div class="card"><div class="k">Sonraki is</div>'
        f'<div class="v">{_e(item.get("next_action") or "yok")}</div></div>'
        f'<div class="card"><div class="k">Kalite</div>'
        f'<div class="v">{_e(item.get("quality_result") or "yok")}</div></div>'
        f'<div class="card"><div class="k">Tazelik</div>'
        f'<div class="v">{_freshness_badge(level)}</div></div>'
        f"</div>"
        f'<p class="mono">Yol: {_e(item.get("path"))}</p>'
        f'<p>Teknoloji: {_e(tech_text or "?")}</p>'
        f"{github_html}{blocker_html}"
    )


def _theme_script() -> str:
    """Inline prefs only: theme + display toggles via localStorage (no network)."""
    return """
<script>
(function () {
  var KEYS = {
    theme: "pala.ui.theme",
    experts: "pala.ui.showExperts",
    softFail: "pala.ui.softFailClosed",
    qualityTier: "pala.ui.showQualityTier"
  };
  function read(key, fallback) {
    try {
      var v = localStorage.getItem(key);
      return v == null ? fallback : v;
    } catch (e) {
      return fallback;
    }
  }
  function write(key, value) {
    try { localStorage.setItem(key, value); } catch (e) {}
  }
  function apply() {
    var root = document.documentElement;
    var theme = read(KEYS.theme, "dark");
    if (theme !== "light" && theme !== "dark") theme = "dark";
    root.setAttribute("data-theme", theme);
    root.setAttribute("data-show-experts", read(KEYS.experts, "1") === "0" ? "0" : "1");
    root.setAttribute("data-soft-fail-closed", read(KEYS.softFail, "0") === "1" ? "1" : "0");
    root.setAttribute("data-show-quality-tier", read(KEYS.qualityTier, "1") === "0" ? "0" : "1");
    var themeBtn = document.getElementById("pala-theme-toggle");
    if (themeBtn) {
      themeBtn.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
      themeBtn.textContent = theme === "dark" ? "Acik tema" : "Koyu tema";
    }
    var map = [
      ["pref-show-experts", KEYS.experts, "1"],
      ["pref-soft-fail-closed", KEYS.softFail, "0"],
      ["pref-show-quality-tier", KEYS.qualityTier, "1"]
    ];
    for (var i = 0; i < map.length; i++) {
      var el = document.getElementById(map[i][0]);
      if (!el) continue;
      var on = read(map[i][1], map[i][2]) === "1";
      el.checked = on;
    }
  }
  function bind() {
    var themeBtn = document.getElementById("pala-theme-toggle");
    if (themeBtn) {
      themeBtn.addEventListener("click", function () {
        var next = document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light";
        write(KEYS.theme, next);
        apply();
      });
    }
    function wire(id, key) {
      var el = document.getElementById(id);
      if (!el) return;
      el.addEventListener("change", function () {
        write(key, el.checked ? "1" : "0");
        apply();
      });
    }
    wire("pref-show-experts", KEYS.experts);
    wire("pref-soft-fail-closed", KEYS.softFail);
    wire("pref-show-quality-tier", KEYS.qualityTier);
  }
  apply();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
</script>
"""


def _css(checked_label_css: str, show_css: str) -> str:
    return f"""
  :root, html[data-theme="dark"] {{
    color-scheme: dark;
    --bg: #12151c;
    --bg-accent: #181c26;
    --fg: #e8eaef;
    --muted: #9aa3b5;
    --panel: #1a1f2a;
    --line: #2c3446;
    --brand: #e8dcc8;
    --accent: #c4a574;
    --focus: #e6c35c;
    --ok-bg: #14261c;
    --ok-fg: #8fcea8;
    --warn-bg: #2a2e38;
    --warn-fg: #d0d5e0;
    --alert-bg: #3a2320;
    --alert-fg: #f0a898;
    --now-bg: #1a2434;
    --now-bd: #3d5678;
    --sidebar: #151922;
    --nav-hover: #1e2430;
    --nav-active: #243044;
  }}
  html[data-theme="light"] {{
    color-scheme: light;
    --bg: #f3f5f7;
    --bg-accent: #e8ecf1;
    --fg: #1c1f26;
    --muted: #5c6575;
    --panel: #ffffff;
    --line: #cfd5de;
    --brand: #1c1f26;
    --accent: #3d6a8a;
    --focus: #3d6a8a;
    --ok-bg: #e5f2ea;
    --ok-fg: #1f5c3a;
    --warn-bg: #eef0f3;
    --warn-fg: #5c5340;
    --alert-bg: #f7e6e2;
    --alert-fg: #8a3a2e;
    --now-bg: #e8eef5;
    --now-bd: #b8c4d6;
    --sidebar: #e7ebf0;
    --nav-hover: #dce2ea;
    --nav-active: #d0d8e2;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    margin: 0; background: var(--bg); color: var(--fg); line-height: 1.45;
  }}
  .skip-link {{
    position: absolute; left: -9999px; top: 0; z-index: 100;
    background: #fff; color: #111; padding: .6rem 1rem; border-radius: 6px;
    font-weight: 600; text-decoration: none;
  }}
  .skip-link:focus {{ left: 1rem; top: 1rem; outline: 3px solid var(--focus); outline-offset: 2px; }}
  input[type="radio"] {{ position: absolute; opacity: 0; width: 1px; height: 1px; }}
  .shell {{ display: grid; grid-template-columns: minmax(12rem, 15rem) 1fr; min-height: 100vh; }}
  .sidebar {{
    background: var(--sidebar); border-right: 1px solid var(--line);
    padding: 16px 12px; display: flex; flex-direction: column; gap: 4px;
  }}
  .brand-block {{
    padding: 8px 10px 14px; margin-bottom: 8px; border-bottom: 1px solid var(--line);
  }}
  .brand-name {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.55rem; letter-spacing: .02em; color: var(--brand); margin: 0;
  }}
  .brand-tag {{ color: var(--muted); font-size: 12px; margin: 4px 0 0; }}
  .sidebar .nav-title {{
    font-size: 11px; margin: 12px 0 6px; color: var(--muted);
    text-transform: uppercase; letter-spacing: .06em;
  }}
  .nav-item {{
    display: flex; justify-content: space-between; align-items: center;
    gap: 8px; padding: 9px 12px; border-radius: 8px; cursor: pointer;
    border: 1px solid transparent; color: var(--fg);
  }}
  .nav-item:hover {{ background: var(--nav-hover); }}
  .nav-item:focus-within, .nav-item:focus {{
    outline: 3px solid var(--focus); outline-offset: 2px;
  }}
  .nav-name {{ font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  {checked_label_css}
  .main {{ padding: 20px 24px 32px; max-width: 74rem; }}
  .topbar {{
    display: flex; flex-wrap: wrap; align-items: flex-start;
    justify-content: space-between; gap: 12px; margin-bottom: 8px;
  }}
  .panel {{ display: none; }}
  {show_css}
  h1.title {{ font-size: 1.45rem; margin: 0 0 4px; color: var(--brand); }}
  h2 {{
    font-size: 13px; margin: 22px 0 8px; color: var(--muted);
    text-transform: uppercase; letter-spacing: .05em;
  }}
  .sub {{ color: var(--muted); font-size: 13px; margin-bottom: 12px; }}
  .hero {{
    background: var(--bg-accent); border: 1px solid var(--line);
    border-radius: 12px; padding: 18px 20px; margin: 0 0 14px;
  }}
  .hero-brand {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1.75rem; margin: 0 0 6px; color: var(--brand);
  }}
  .hero-lead {{ margin: 0; color: var(--muted); font-size: 14px; max-width: 42rem; }}
  .nowline {{
    background: var(--now-bg); border: 1px solid var(--now-bd); color: var(--fg);
    padding: 14px 16px; border-radius: 10px; margin: 8px 0 16px; font-size: 1.05rem;
    display: flex; flex-wrap: wrap; gap: .35rem .6rem; align-items: baseline;
  }}
  .now-k {{ color: var(--accent); font-weight: 600; }}
  .decision-strip {{
    display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px;
    margin: 8px 0 16px;
  }}
  .signal {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
    padding: 10px 12px; min-width: 0;
  }}
  .signal-k {{
    color: var(--muted); font-size: 11px; text-transform: uppercase;
    letter-spacing: .04em; margin-bottom: 4px;
  }}
  .signal-v {{ font-size: 13px; word-break: break-word; line-height: 1.35; }}
  .signal.tone-now {{ background: var(--now-bg); border-color: var(--now-bd); }}
  .signal.tone-ok {{ border-color: #1f4a34; }}
  .signal.tone-ok .signal-v {{ color: var(--ok-fg); }}
  .signal.tone-warn {{ border-color: #5a4e28; }}
  .signal.tone-warn .signal-v {{ color: #c9a84a; }}
  html[data-theme="light"] .signal.tone-warn .signal-v {{ color: #7a6220; }}
  .signal.tone-alert {{ border-color: #5a2f2a; }}
  .signal.tone-alert .signal-v {{ color: var(--alert-fg); }}
  .progress-block {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
    padding: 14px; margin: 8px 0 16px;
  }}
  .progress-head {{ font-size: 18px; margin-bottom: 8px; }}
  .gap-note {{ color: var(--alert-fg); margin: 0; }}
  .ok-note {{ color: var(--ok-fg); margin: 0; }}
  .gap-list {{ margin: 6px 0 0; padding-left: 18px; color: var(--alert-fg); }}
  .timeline {{ list-style: none; margin: 0; padding: 0; }}
  .timeline li {{
    padding: 10px 0; border-bottom: 1px solid var(--line); font-size: 13px;
    display: grid; grid-template-columns: auto 1fr; gap: .35rem .75rem;
  }}
  .timeline li:last-child {{ border-bottom: none; }}
  .badge.kind {{ background: var(--nav-active); color: var(--fg); }}
  .badge.kind-checkpoint {{ background: var(--ok-bg); color: var(--ok-fg); }}
  .badge.kind-debug_attempt {{ background: #3a3218; color: #e8c56a; }}
  html[data-theme="light"] .badge.kind-debug_attempt {{ background: #f3e8c8; color: #6a5418; }}
  .timeline-item.kind-debug_attempt {{ border-left: 3px solid #c9a84a; padding-left: 8px; }}
  .timeline-item.kind-checkpoint {{ border-left: 3px solid var(--ok-fg); padding-left: 8px; }}
  .grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 12px; margin: 12px 0;
  }}
  .card {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px;
  }}
  .card .k {{ color: var(--muted); font-size: 12px; }}
  .card .v {{ font-size: 16px; margin-top: 4px; word-break: break-word; }}
  table {{
    width: 100%; border-collapse: collapse; background: var(--panel);
    border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
  }}
  th, td {{
    text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); font-size: 13px;
  }}
  th {{ color: var(--muted); font-weight: 600; background: var(--sidebar); }}
  tr:last-child td {{ border-bottom: none; }}
  td.num {{ color: var(--muted); width: 34px; }}
  .mono {{
    font-family: ui-monospace, "Cascadia Code", Consolas, monospace; color: var(--muted);
  }}
  .muted {{ color: var(--muted); text-align: center; }}
  .muted-inline {{ color: var(--muted); font-size: 12px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 12px; }}
  .badge.ok {{ background: var(--ok-bg); color: var(--ok-fg); }}
  .badge.gap {{ background: var(--alert-bg); color: var(--alert-fg); }}
  .badge.fresh {{ background: var(--ok-bg); color: var(--ok-fg); }}
  .badge.aging {{ background: #3a3218; color: #e8c56a; }}
  .badge.stale {{ background: var(--alert-bg); color: var(--alert-fg); }}
  .alert {{
    background: var(--alert-bg); color: var(--alert-fg); padding: 10px 14px;
    border-radius: 8px; margin: 8px 0;
  }}
  .okline {{
    background: var(--ok-bg); color: var(--ok-fg); padding: 10px 14px;
    border-radius: 8px; margin: 8px 0;
  }}
  .warnline {{
    background: var(--warn-bg); color: var(--warn-fg); padding: 10px 14px;
    border-radius: 8px; margin: 8px 0;
  }}
  a {{ color: var(--accent); }}
  a:focus-visible, button:focus-visible, .nav-item:focus-visible {{
    outline: 3px solid var(--focus); outline-offset: 2px;
  }}
  .theme-toggle, .pref-row input {{ cursor: pointer; }}
  .theme-toggle {{
    background: var(--panel); color: var(--fg); border: 1px solid var(--line);
    border-radius: 8px; padding: 8px 12px; font-size: 13px;
  }}
  .pref-list {{ list-style: none; margin: 0; padding: 0; }}
  .pref-row {{
    display: flex; align-items: flex-start; gap: 12px;
    padding: 14px 12px; border: 1px solid var(--line); border-radius: 10px;
    background: var(--panel); margin-bottom: 8px;
  }}
  .pref-row label {{ flex: 1; cursor: pointer; }}
  .pref-title {{ font-weight: 600; display: block; margin-bottom: 2px; }}
  .pref-desc {{ color: var(--muted); font-size: 13px; }}
  .cmd {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 8px;
    padding: 10px 12px; font-size: 12px; overflow-x: auto; margin: 8px 0;
  }}
  .section-note {{ color: var(--muted); font-size: 13px; margin: 0 0 10px; }}
  html[data-show-experts="0"] .experts-panel {{ display: none; }}
  html[data-soft-fail-closed="0"] .soft-closed-note {{ display: none; }}
  html[data-show-quality-tier="0"] .quality-tier-panel {{ display: none; }}
  footer {{ color: var(--muted); font-size: 12px; margin-top: 24px; }}
  .catalog-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
  @media (max-width: 720px) {{
    .shell {{ grid-template-columns: 1fr; }}
    .sidebar {{
      border-right: none; border-bottom: 1px solid var(--line);
      flex-direction: row; flex-wrap: wrap; gap: 8px;
      max-height: 46vh; overflow-y: auto;
    }}
    .brand-block, .sidebar .nav-title {{ width: 100%; }}
    .nav-item {{ flex: 1 1 42%; min-width: 8rem; }}
    .main {{ padding: 16px; }}
    .nowline {{ font-size: 1rem; }}
    .decision-strip {{ grid-template-columns: 1fr 1fr; }}
    .decision-strip .signal:first-child {{ grid-column: 1 / -1; }}
    .timeline li {{ grid-template-columns: 1fr; }}
    table {{ font-size: 12px; }}
  }}
"""


def _section_overview(
    *,
    root_name: str,
    decision: str,
    now_line: str,
    brain_line: str,
    mismatch_banner: str,
    progress_html: str,
    coherence: dict[str, object],
    git: dict[str, object],
    next_action: object,
) -> str:
    return (
        '<section id="panel-overview" class="panel" data-admin-section="overview">'
        '<div class="hero" id="pala-admin-hero">'
        '<p class="hero-brand">Pala</p>'
        '<p class="hero-lead">Yerel kontrol merkezi — hafıza, ticket, kalite ve '
        "kurulum. Bağlam penceresi büyütmez; yalnız gerekli sinyali gösterir.</p>"
        "</div>"
        f"{decision}"
        f"{now_line}"
        f"{brain_line}"
        f"{mismatch_banner}"
        f"{progress_html}"
        '<div class="grid">'
        '<div class="card"><div class="k">Aktif ticket</div>'
        f'<div class="v">{_e(coherence.get("active") or "yok")}</div></div>'
        '<div class="card"><div class="k">Sonraki is</div>'
        f'<div class="v">{_e(coherence.get("inferred_next") or next_action or "yok")}</div></div>'
        '<div class="card"><div class="k">Git</div>'
        f'<div class="v mono">{_e(git.get("branch") or "?")}</div></div>'
        '<div class="card"><div class="k">Degisen dosya</div>'
        f'<div class="v">{_e(git.get("dirty_count", 0))}</div></div>'
        "</div>"
        f'<p class="muted-inline">Proje: {_e(root_name)}</p>'
        "</section>"
    )


def _section_install() -> str:
    return (
        '<section id="panel-install" class="panel" data-admin-section="install">'
        "<h2>Kurulum / Doctor</h2>"
        '<p class="section-note">Hook icinde Install/Doctor calismaz. '
        "Asagidaki komutlar agent veya Status yolunda elle calistirilir.</p>"
        '<div class="cmd mono">codex plugin marketplace add trugurpala/pala-project-studio</div>'
        '<div class="cmd mono">codex plugin add pala-project-studio@pala-project-studio</div>'
        '<div class="cmd mono">powershell -NoProfile -ExecutionPolicy Bypass '
        "-File .\\Install-Pala.ps1 -Mode Doctor</div>"
        '<div class="cmd mono">powershell -NoProfile -ExecutionPolicy Bypass '
        "-File .\\Install-Pala.ps1 -Mode Repair</div>"
        '<div class="warnline">Doctor <span class="mono">healthy</span> / '
        '<span class="mono">plugin_ready</span> dosya kanitidir; '
        "/hooks trust degildir.</div>"
        "</section>"
    )


def _section_hooks() -> str:
    return (
        '<section id="panel-hooks" class="panel" data-admin-section="hooks">'
        "<h2>Hooks trust</h2>"
        '<div class="warnline" id="pala-hooks-trust" data-evidence="configured-not-verified">'
        "Kanit: <strong>configured-not-verified</strong> — Codex Work &rarr; "
        '<span class="mono">/hooks</span> icinde Pala\'ya guven insan tiklamasidir. '
        "Bu sayfa trust'i gecemez.</div>"
        '<p class="section-note">hook_safety=passed yalniz dosya/sozlesme kontroludur; '
        "UI trust ile karistirma.</p>"
        "</section>"
    )


def _section_quality(quality: object, verification_tier: object) -> str:
    quality = quality if isinstance(quality, dict) else {}
    risk = quality.get("risk") if isinstance(quality.get("risk"), dict) else {}
    coverage = quality.get("coverage") if isinstance(quality.get("coverage"), dict) else {}
    tier = str(verification_tier or "not-run")
    return (
        '<section id="panel-quality" class="panel" data-admin-section="quality">'
        "<h2>Quality engine (0.9)</h2>"
        '<p class="section-note">Delivery Quality Engine: proje-yerel kapilar, '
        "ledger kaniti, soft % yok.</p>"
        '<div class="grid">'
        '<div class="card"><div class="k">Durum</div>'
        f'<div class="v">{_e(quality.get("status") or "not-run")}</div></div>'
        '<div class="card"><div class="k">Ticket</div>'
        f'<div class="v">{_e(quality.get("ticket") or "yok")}</div></div>'
        '<div class="card"><div class="k">Risk</div>'
        f'<div class="v">{_e(risk.get("level") or "unknown")}</div></div>'
        '<div class="card"><div class="k">Coverage</div>'
        f'<div class="v">{_e(int(coverage.get("passed") or 0))}/'
        f'{_e(int(coverage.get("required") or 0))}</div></div>'
        "</div>"
        f'<div class="warnline">Son eksik: {_e(quality.get("last_problem") or "yok")}</div>'
        f'<div class="okline">Sonraki: {_e(quality.get("next_action") or "yok")}</div>'
        '<div class="quality-tier-panel card" id="pala-quality-tier">'
        '<div class="k">Verification tier (gorunum)</div>'
        f'<div class="v mono">{_e(tier)}</div>'
        '<p class="pref-desc">Bu satir «quality tier goster» tercihiyle gizlenebilir; '
        "workflow gercegini degistirmez.</p>"
        "</div>"
        "</section>"
    )


def _section_memory(store_path: object, events: list[object], provisions: list[object]) -> str:
    return (
        '<section id="panel-memory" class="panel" data-admin-section="memory">'
        "<h2>Hafiza / store</h2>"
        f'<p class="section-note">SQLite: <span class="mono">{_e(store_path or "?")}</span></p>'
        '<div class="experts-panel card" id="pala-experts-panel">'
        '<div class="k">Experts (istege bagli)</div>'
        '<div class="v">Node/uv ile hazir olabilir; hook otomatik kurmaz/calistirmaz.</div>'
        '<p class="pref-desc">«Uzmanlari goster» kapaliysa bu panel gizlenir.</p>'
        "</div>"
        "<h2>Son olaylar</h2>"
        f"{_timeline_html(events)}"
        "<h2>Son URL kurulumlari</h2>"
        f"{_provisions_html(provisions)}"
        "</section>"
    )


def _section_tickets(
    *,
    coherence: dict[str, object],
    next_action: object,
    read_order: list[object],
) -> str:
    return (
        '<section id="panel-tickets" class="panel" data-admin-section="tickets">'
        "<h2>Ticket / sonraki is</h2>"
        f"{_now_line(next_action, coherence.get('active'))}"
        '<div class="grid">'
        '<div class="card"><div class="k">Aktif</div>'
        f'<div class="v">{_e(coherence.get("active") or "yok")}</div></div>'
        '<div class="card"><div class="k">Cikarilan sonraki</div>'
        f'<div class="v">{_e(coherence.get("inferred_next") or next_action or "yok")}</div></div>'
        "</div>"
        "<h2>Okuma sirasi (zorunlu)</h2>"
        "<table><thead><tr><th>#</th><th>Amac</th><th>Dosya</th><th>Durum</th>"
        f"</tr></thead><tbody>{_read_order_rows(read_order)}</tbody></table>"
        "</section>"
    )


def _section_features() -> str:
    return (
        '<section id="panel-features" class="panel" data-admin-section="features">'
        "<h2>Yetki / ozellik</h2>"
        '<p class="section-note">Yalniz gercek Pala gorunum tercihleri. '
        "Ucretli kilit yok; ag ozeligi hook yolunda iddia edilmez. "
        "Tercihler tarayici localStorage'da kalir.</p>"
        '<ul class="pref-list" id="pala-feature-toggles">'
        '<li class="pref-row">'
        '<input type="checkbox" id="pref-show-experts" checked>'
        '<label for="pref-show-experts">'
        '<span class="pref-title">Uzmanlari goster</span>'
        '<span class="pref-desc">Hafiza bolumunde experts panelini goster/gizle '
        "(kurulum otomatik baslatmaz).</span></label></li>"
        '<li class="pref-row">'
        '<input type="checkbox" id="pref-soft-fail-closed">'
        '<label for="pref-soft-fail-closed">'
        '<span class="pref-title">Kapali INC soft-fail hatirlatma</span>'
        '<span class="pref-desc">Hata beyni satirinda kapali kayit sayisini '
        "ek hatirlatma olarak goster.</span></label></li>"
        '<li class="pref-row">'
        '<input type="checkbox" id="pref-show-quality-tier" checked>'
        '<label for="pref-show-quality-tier">'
        '<span class="pref-title">Quality tier goster</span>'
        '<span class="pref-desc">Quality bolumunde verification_tier gorunumunu ac.</span>'
        "</label></li>"
        "</ul>"
        "</section>"
    )


def render(model: dict[str, object], *, freshness_fn: Any) -> str:
    """Render a status / control-center model into a single static HTML document."""
    root_name = str(model.get("root_name") or "project")
    root_path = str(model.get("root_path") or "")
    stamp = str(model.get("stamp") or "")
    coherence = model.get("coherence")
    coherence = coherence if isinstance(coherence, dict) else {}
    git = model.get("git")
    git = git if isinstance(git, dict) else {}
    read_order = model.get("read_order")
    read_order = read_order if isinstance(read_order, list) else []
    progress = model.get("progress")
    progress = progress if isinstance(progress, dict) else {"ready": 0, "total": 7, "missing": []}
    projects = model.get("projects")
    projects = projects if isinstance(projects, list) else []
    events = model.get("events")
    events = events if isinstance(events, list) else []
    provisions = model.get("provisions")
    provisions = provisions if isinstance(provisions, list) else []
    update = model.get("update")
    update = update if isinstance(update, dict) else None
    update_checked_at = model.get("update_checked_at")
    next_action = model.get("next_action")
    brain = model.get("debugging_brain")
    last_gate = model.get("last_gate")
    freshness_level = model.get("freshness_level")
    if not isinstance(freshness_level, str) or not freshness_level:
        freshness_level = "stale"
    quality = model.get("quality")
    store_path = model.get("store_path") or ""
    verification_tier = model.get("verification_tier") or "not-run"

    mismatch = bool(coherence.get("mismatch"))
    mismatch_banner = (
        f'<div class="alert">Ticket uyumsuzlugu: {_e(coherence.get("note"))}</div>'
        if mismatch
        else '<div class="okline">Ticket uyumu: tamam</div>'
    )
    decision = _decision_strip(
        next_action=next_action,
        coherence=coherence,
        brain=brain,
        last_gate=last_gate,
        freshness_level=freshness_level,
        quality=quality,
    )

    radios: list[str] = [
        '<input type="radio" name="pala-nav" id="nav-overview" checked>'
    ]
    for sec_id, _label in _SECTION_NAV[1:]:
        radios.append(f'<input type="radio" name="pala-nav" id="nav-{sec_id}">')

    labels: list[str] = []
    for sec_id, label in _SECTION_NAV:
        labels.append(
            f'<label for="nav-{sec_id}" class="nav-item">'
            f'<span class="nav-name">{_e(label)}</span></label>'
        )

    panels: list[str] = [
        _section_overview(
            root_name=root_name,
            decision=decision,
            now_line=_now_line(next_action, coherence.get("active")),
            brain_line=_brain_line(brain),
            mismatch_banner=mismatch_banner,
            progress_html=_progress_block(progress),
            coherence=coherence,
            git=git,
            next_action=next_action,
        ),
        _section_install(),
        _section_hooks(),
        _section_quality(quality, verification_tier),
        _section_memory(store_path, events, provisions),
        _section_tickets(
            coherence=coherence,
            next_action=next_action,
            read_order=read_order,
        ),
        _section_features(),
    ]

    ordered = sorted(
        [p for p in projects if isinstance(p, dict)],
        key=lambda item: str(item.get("updated_at", "")),
        reverse=True,
    )
    project_labels: list[str] = []
    for index, item in enumerate(ordered):
        pid = f"nav-project-{index}"
        radios.append(f'<input type="radio" name="pala-nav" id="{pid}">')
        level = freshness_fn(item.get("updated_at"))
        project_labels.append(
            f'<label for="{pid}" class="nav-item">'
            f'<span class="nav-name">{_e(item.get("name"))}</span>'
            f"{_freshness_badge(level)}</label>"
        )
        panels.append(
            f'<section id="panel-project-{index}" class="panel">'
            f'<h2>{_e(item.get("name"))}</h2>'
            f"{_project_detail_html(item, freshness_fn)}"
            f"</section>"
        )

    show_rules = [
        f"#nav-{sec_id}:checked ~ .shell #panel-{sec_id} {{ display: block; }}"
        for sec_id, _ in _SECTION_NAV
    ]
    for index in range(len(ordered)):
        show_rules.append(
            f"#nav-project-{index}:checked ~ .shell #panel-project-{index} {{ display: block; }}"
        )
    show_css = "\n  ".join(show_rules)

    checked_labels = [
        f'#nav-{sec_id}:checked ~ .shell label[for="nav-{sec_id}"]'
        for sec_id, _ in _SECTION_NAV
    ]
    for i in range(len(ordered)):
        checked_labels.append(
            f'#nav-project-{i}:checked ~ .shell label[for="nav-project-{i}"]'
        )
    checked_label_css = (
        ",\n  ".join(checked_labels)
        + " { background: var(--nav-active); border-color: var(--line); }"
    )

    catalog_rows: list[str] = []
    if not ordered:
        catalog_rows.append(
            '<tr><td colspan="6" class="muted">Henuz kayitli proje yok. '
            "Bir projede register calistir.</td></tr>"
        )
    else:
        for item in ordered:
            level = freshness_fn(item.get("updated_at"))
            tech = item.get("tech")
            tech_text = ", ".join(tech) if isinstance(tech, list) else ""
            catalog_rows.append(
                "<tr>"
                f'<td>{_e(item.get("name"))}</td>'
                f'<td>{_e(item.get("phase") or "belirsiz")}</td>'
                f'<td>{_e(item.get("next_action") or "yok")}</td>'
                f'<td>{_e(item.get("quality_result") or "yok")}</td>'
                f"<td>{_freshness_badge(level)}</td>"
                f'<td class="mono">{_e(tech_text or "?")}</td>'
                "</tr>"
            )

    project_nav = (
        "".join(project_labels) if project_labels else '<p class="muted-inline">Kayit yok</p>'
    )
    return f"""<!doctype html>
<html lang="tr" data-theme="dark" data-show-experts="1" data-soft-fail-closed="0" data-show-quality-tier="1">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pala kontrol - {_e(root_name)}</title>
<style>{_css(checked_label_css, show_css)}</style>
</head>
<body>
  <a class="skip-link" href="#pala-main">İçeriğe geç</a>
  {"".join(radios)}
  <div class="shell">
    <nav class="sidebar" aria-label="Pala kontrol menusu" id="pala-admin-nav">
      <div class="brand-block">
        <p class="brand-name">Pala</p>
        <p class="brand-tag">kontrol merkezi</p>
      </div>
      <p class="nav-title">Bolumler</p>
      {"".join(labels)}
      <p class="nav-title">Projeler</p>
      {project_nav}
    </nav>
    <main id="pala-main" class="main">
      <div class="topbar">
        <div>
          <h1 class="title">Pala kontrol — {_e(root_name)}</h1>
          <div class="sub">{_e(root_path)} &middot; {stamp}</div>
        </div>
        <button type="button" class="theme-toggle" id="pala-theme-toggle" aria-pressed="true">Acik tema</button>
      </div>
      {_update_banner(update, update_checked_at if isinstance(update_checked_at, str) else None)}
      {"".join(panels)}
      <h2>Proje katalogu</h2>
      <div class="catalog-wrap">
      <table>
        <thead><tr><th>Proje</th><th>Faz</th><th>Sonraki is</th><th>Kalite</th><th>Tazelik</th><th>Teknoloji</th></tr></thead>
        <tbody>
          {"".join(catalog_rows)}
        </tbody>
      </table>
      </div>
      <footer>Sohbet gecmisine guvenme; yukaridaki dosyalari sirayla oku. Bu sayfa yerel kayitlardan uretildi; guncellik 24 saat onbelleklidir (hook icinde ag yok). Tema/tercihler localStorage.</footer>
    </main>
  </div>
  {_theme_script()}
</body>
</html>
"""

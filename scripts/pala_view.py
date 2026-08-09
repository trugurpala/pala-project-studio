#!/usr/bin/env python3
"""HTML view layer for the Pala status page (no scripts, no external assets)."""

from __future__ import annotations

import html
from datetime import datetime, timezone
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
    """Top decision strip: max 5 signals (Şimdi | INC | ticket | gate | tazelik)."""
    now_text = _now_text(next_action, coherence.get("active"))
    open_inc = 0
    if isinstance(brain, dict) and brain.get("ok"):
        open_inc = int(brain.get("open") or 0)
    elif isinstance(brain, dict) and brain.get("open") is not None:
        try:
            open_inc = int(brain.get("open") or 0)
        except (TypeError, ValueError):
            open_inc = 0
    mismatch = bool(coherence.get("mismatch"))
    if mismatch:
        ticket_label = "uyumsuz"
        ticket_tone = "alert"
        ticket_detail = str(coherence.get("note") or "ticket uyumsuz")
    else:
        ticket_label = "tamam"
        ticket_tone = "ok"
        ticket_detail = str(coherence.get("active") or "uyum tamam")

    gate = last_gate if isinstance(last_gate, dict) else {}
    gate_status = str(gate.get("status") or "not-run")
    gate_label = str(gate.get("label") or gate_status or "not-run")
    if gate_status == "passed":
        gate_tone = "ok"
    elif gate_status in {"blocked", "failed"}:
        gate_tone = "alert"
    else:
        gate_tone = "warn"

    fresh = str(freshness_level or "stale")
    fresh_labels = {"fresh": "taze", "aging": "eskiyor", "stale": "bayat"}
    fresh_tone = {
        "fresh": "ok",
        "aging": "warn",
        "stale": "alert",
    }.get(fresh, "warn")

    inc_tone = "alert" if open_inc else "ok"
    inc_label = f"{open_inc} açık" if open_inc else "açık yok"

    cells = [
        ("Şimdi", now_text, "now"),
        ("açık INC", inc_label, inc_tone),
        ("ticket uyumu", f"{ticket_label} — {ticket_detail}"[:72], ticket_tone),
        ("son gate", gate_label[:72], gate_tone),
        ("tazelik", fresh_labels.get(fresh, fresh), fresh_tone),
    ]
    # Delivery Quality Engine replaces generic status hints with the five
    # concrete shipping signals. It intentionally carries no command output.
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
    risk_tone = "alert" if risk_level == "high" else "warn" if risk_level in {"medium", "unknown"} else "ok"
    coverage_label = f"{int(coverage.get('passed') or 0)}/{int(coverage.get('required') or 0)} passed"
    cells = [
        ("Aktif ticket", ticket[:72], "now"),
        ("Risk seviyesi", risk_label[:72], risk_tone),
        ("Quality coverage", coverage_label, quality_tone),
        ("Son eksik gate", str(quality.get("last_problem") or "quality ledger not initialized")[:72], quality_tone),
        ("Tek sonraki eylem", str(quality.get("next_action") or next_action or "yok")[:120], "now"),
    ]
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
    if open_count:
        cls = "alert"
        note = f"{open_count} açık / {fixed_count} kapalı (toplam {total})"
    else:
        cls = "okline"
        note = f"açık yok; {fixed_count} kapalı (toplam {total})"
    return (
        f'<div class="{cls}">Hata beyni: {note} — önce <span class="mono">{path}</span> '
        "oku.</div>"
    )

def _progress_block(progress: dict[str, object]) -> str:
    ready = int(progress.get("ready") or 0)
    total = int(progress.get("total") or 0)
    missing = progress.get("missing")
    missing_list = missing if isinstance(missing, list) else []
    missing_html = ""
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


def _css(checked_label_css: str, show_css: str) -> str:
    return f"""
  :root {{
    color-scheme: light dark;
    --bg: #0f1117;
    --fg: #e8eaef;
    --muted: #a8b0bf;
    --panel: #171a22;
    --line: #2a3142;
    --accent: #9ec5ff;
    --focus: #f5d76e;
    --ok-bg: #0f2a1c;
    --ok-fg: #7ddea8;
    --warn-bg: #2a2e3a;
    --warn-fg: #d0d5e0;
    --alert-bg: #3a2320;
    --alert-fg: #f3a796;
    --now-bg: #152238;
    --now-bd: #3a5f96;
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
         margin: 0; background: var(--bg); color: var(--fg); line-height: 1.45; }}
  .skip-link {{
    position: absolute; left: -9999px; top: 0; z-index: 100;
    background: #fff; color: #111; padding: .6rem 1rem; border-radius: 6px;
    font-weight: 600; text-decoration: none;
  }}
  .skip-link:focus {{ left: 1rem; top: 1rem; outline: 3px solid var(--focus); outline-offset: 2px; }}
  input[type="radio"] {{ position: absolute; opacity: 0; width: 1px; height: 1px; }}
  .shell {{ display: grid; grid-template-columns: minmax(12rem, 15rem) 1fr; min-height: 100vh; }}
  .sidebar {{ background: #14171f; border-right: 1px solid var(--line); padding: 16px 12px;
             display: flex; flex-direction: column; gap: 6px; }}
  .sidebar .nav-title {{ font-size: 14px; margin: 0 0 10px; color: var(--muted);
                 text-transform: uppercase; letter-spacing: .04em; }}
  .nav-item {{ display: flex; justify-content: space-between; align-items: center;
              gap: 8px; padding: 10px 12px; border-radius: 8px; cursor: pointer;
              border: 1px solid transparent; color: var(--fg); }}
  .nav-item:hover {{ background: #1b2030; }}
  .nav-item:focus-within, .nav-item:focus {{
    outline: 3px solid var(--focus); outline-offset: 2px;
  }}
  .nav-name {{ font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  {checked_label_css}
  .main {{ padding: 24px; max-width: 72rem; }}
  .panel {{ display: none; }}
  {show_css}
  h1.title {{ font-size: 1.35rem; margin: 0 0 4px; }}
  h2 {{ font-size: 15px; margin: 24px 0 8px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }}
  .sub {{ color: var(--muted); font-size: 13px; margin-bottom: 16px; }}
  .nowline {{ background: var(--now-bg); border: 1px solid var(--now-bd); color: #e7f0ff;
             padding: 14px 16px; border-radius: 10px; margin: 8px 0 16px; font-size: 1.05rem;
             display: flex; flex-wrap: wrap; gap: .35rem .6rem; align-items: baseline; }}
  .now-k {{ color: var(--accent); font-weight: 600; }}
  .decision-strip {{
    display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px;
    margin: 8px 0 16px;
  }}
  .signal {{
    background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
    padding: 10px 12px; min-width: 0;
  }}
  .signal-k {{ color: var(--muted); font-size: 11px; text-transform: uppercase;
              letter-spacing: .04em; margin-bottom: 4px; }}
  .signal-v {{ font-size: 13px; word-break: break-word; line-height: 1.35; }}
  .signal.tone-now {{ background: var(--now-bg); border-color: var(--now-bd); }}
  .signal.tone-ok {{ border-color: #1f4a34; }}
  .signal.tone-ok .signal-v {{ color: var(--ok-fg); }}
  .signal.tone-warn {{ border-color: #4a4020; }}
  .signal.tone-warn .signal-v {{ color: #e8c56a; }}
  .signal.tone-alert {{ border-color: #5a2f2a; }}
  .signal.tone-alert .signal-v {{ color: var(--alert-fg); }}
  .progress-block {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px;
                    padding: 14px; margin: 8px 0 16px; }}
  .progress-head {{ font-size: 18px; margin-bottom: 8px; }}
  .gap-note {{ color: var(--alert-fg); margin: 0; }}
  .ok-note {{ color: var(--ok-fg); margin: 0; }}
  .gap-list {{ margin: 6px 0 0; padding-left: 18px; color: var(--alert-fg); }}
  .timeline {{ list-style: none; margin: 0; padding: 0; }}
  .timeline li {{ padding: 10px 0; border-bottom: 1px solid var(--line); font-size: 13px;
                  display: grid; grid-template-columns: auto 1fr; gap: .35rem .75rem; }}
  .timeline li:last-child {{ border-bottom: none; }}
  .badge.kind {{ background: #1e2638; color: #c5cddc; }}
  .badge.kind-checkpoint {{ background: #1a2e24; color: var(--ok-fg); }}
  .badge.kind-debug_attempt {{ background: #3a3218; color: #e8c56a; }}
  .timeline-item.kind-debug_attempt {{ border-left: 3px solid #e8c56a; padding-left: 8px; }}
  .timeline-item.kind-checkpoint {{ border-left: 3px solid #7ddea8; padding-left: 8px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 12px 0; }}
  .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px; }}
  .card .k {{ color: var(--muted); font-size: 12px; }}
  .card .v {{ font-size: 16px; margin-top: 4px; word-break: break-word; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--panel);
          border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); font-size: 13px; }}
  th {{ color: var(--muted); font-weight: 600; background: #14171f; }}
  tr:last-child td {{ border-bottom: none; }}
  td.num {{ color: var(--muted); width: 34px; }}
  .mono {{ font-family: ui-monospace, "Cascadia Code", Consolas, monospace; color: #c5cddc; }}
  .muted {{ color: var(--muted); text-align: center; }}
  .muted-inline {{ color: var(--muted); font-size: 12px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 12px; }}
  .badge.ok {{ background: var(--ok-bg); color: var(--ok-fg); }}
  .badge.gap {{ background: var(--alert-bg); color: var(--alert-fg); }}
  .badge.fresh {{ background: var(--ok-bg); color: var(--ok-fg); }}
  .badge.aging {{ background: #3a3218; color: #e8c56a; }}
  .badge.stale {{ background: var(--alert-bg); color: var(--alert-fg); }}
  .alert {{ background: var(--alert-bg); color: var(--alert-fg); padding: 10px 14px; border-radius: 8px; margin: 8px 0; }}
  .okline {{ background: var(--ok-bg); color: var(--ok-fg); padding: 10px 14px; border-radius: 8px; margin: 8px 0; }}
  .warnline {{ background: var(--warn-bg); color: var(--warn-fg); padding: 10px 14px; border-radius: 8px; margin: 8px 0; }}
  a {{ color: var(--accent); }}
  a:focus-visible, button:focus-visible, .nav-item:focus-visible {{
    outline: 3px solid var(--focus); outline-offset: 2px;
  }}
  footer {{ color: var(--muted); font-size: 12px; margin-top: 24px; }}
  .catalog-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
  @media (max-width: 720px) {{
    .shell {{ grid-template-columns: 1fr; }}
    .sidebar {{ border-right: none; border-bottom: 1px solid var(--line);
               flex-direction: row; flex-wrap: wrap; gap: 8px;
               max-height: 40vh; overflow-y: auto; }}
    .sidebar .nav-title {{ width: 100%; margin-bottom: 4px; }}
    .nav-item {{ flex: 1 1 42%; min-width: 8rem; }}
    .main {{ padding: 16px; }}
    .nowline {{ font-size: 1rem; }}
    .decision-strip {{ grid-template-columns: 1fr 1fr; }}
    .decision-strip .signal:first-child {{ grid-column: 1 / -1; }}
    .timeline li {{ grid-template-columns: 1fr; }}
    table {{ font-size: 12px; }}
  }}
"""


def render(model: dict[str, object], *, freshness_fn: Any) -> str:
    """Render a status model dict into a single static HTML document."""
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
        '<input type="radio" name="pala-nav" id="nav-current" checked>'
    ]
    labels: list[str] = [
        '<label for="nav-current" class="nav-item">'
        f'<span class="nav-name">{_e(root_name)}</span>'
        '<span class="badge ok">aktif</span></label>'
    ]
    current_panel = (
        '<section id="panel-current" class="panel">'
        "<h2>Aktif proje</h2>"
        f"{decision}"
        f"{_now_line(next_action, coherence.get('active'))}"
        f"{_brain_line(brain)}"
        f"{mismatch_banner}"
        f"{_progress_block(progress)}"
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
        "<h2>Okuma sirasi (zorunlu)</h2>"
        "<table><thead><tr><th>#</th><th>Amac</th><th>Dosya</th><th>Durum</th>"
        f"</tr></thead><tbody>{_read_order_rows(read_order)}</tbody></table>"
        "<h2>Son olaylar</h2>"
        f"{_timeline_html(events)}"
        "<h2>Son URL kurulumlari</h2>"
        f"{_provisions_html(provisions)}"
        "</section>"
    )
    panels: list[str] = [current_panel]

    ordered = sorted(
        [p for p in projects if isinstance(p, dict)],
        key=lambda item: str(item.get("updated_at", "")),
        reverse=True,
    )
    for index, item in enumerate(ordered):
        pid = f"nav-{index}"
        radios.append(f'<input type="radio" name="pala-nav" id="{pid}">')
        level = freshness_fn(item.get("updated_at"))
        labels.append(
            f'<label for="{pid}" class="nav-item">'
            f'<span class="nav-name">{_e(item.get("name"))}</span>'
            f"{_freshness_badge(level)}</label>"
        )
        panels.append(
            f'<section id="panel-{index}" class="panel">'
            f'<h2>{_e(item.get("name"))}</h2>'
            f"{_project_detail_html(item, freshness_fn)}"
            f"</section>"
        )

    show_rules = ["#nav-current:checked ~ .shell #panel-current { display: block; }"]
    for index in range(len(ordered)):
        show_rules.append(
            f"#nav-{index}:checked ~ .shell #panel-{index} {{ display: block; }}"
        )
    show_css = "\n  ".join(show_rules)
    checked_labels = ['#nav-current:checked ~ .shell label[for="nav-current"]']
    for i in range(len(ordered)):
        checked_labels.append(f'#nav-{i}:checked ~ .shell label[for="nav-{i}"]')
    checked_label_css = (
        ",\n  ".join(checked_labels)
        + " { background: #1e2638; border-color: #2f3a55; }"
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

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pala durum - {_e(root_name)}</title>
<style>{_css(checked_label_css, show_css)}</style>
</head>
<body>
  <a class="skip-link" href="#pala-main">İçeriğe geç</a>
  {"".join(radios)}
  <div class="shell">
    <nav class="sidebar" aria-label="Kayıtlı projeler">
      <p class="nav-title">Projeler</p>
      {"".join(labels)}
    </nav>
    <main id="pala-main" class="main">
      <h1 class="title">Pala durum - {_e(root_name)}</h1>
      <div class="sub">{_e(root_path)} &middot; {stamp}</div>
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
      <footer>Sohbet gecmisine guvenme; yukaridaki dosyalari sirayla oku. Bu sayfa yerel kayitlardan uretildi; guncellik 24 saat onbelleklidir (hook icinde ag yok).</footer>
    </main>
  </div>
</body>
</html>
"""

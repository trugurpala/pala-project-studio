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


def _now_line(next_action: object) -> str:
    text = str(next_action).strip() if next_action else ""
    if not text:
        text = "Henuz sonraki is yok — register veya begin calistir."
    return f'<div class="nowline"><span class="now-k">Simdi:</span> {_e(text)}</div>'


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
            '<p class="muted">Henuz olay yok. register, begin, checkpoint veya '
            "provision calisinca burada gorunur.</p>"
        )
    items: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        kind = str(event.get("kind") or "")
        label = _KIND_LABELS.get(kind, kind)
        stamp = str(event.get("created_at") or "")[:19].replace("T", " ")
        name = event.get("project_name") or ""
        detail = event.get("detail") or ""
        items.append(
            "<li>"
            f'<span class="badge kind">{_e(label)}</span> '
            f'<span class="mono">{_e(stamp)}</span> '
            f"{_e(name)} — {_e(detail)}"
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
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif;
         margin: 0; background: #0f1117; color: #e6e8ee; }}
  input[type="radio"] {{ position: absolute; opacity: 0; pointer-events: none; }}
  .shell {{ display: grid; grid-template-columns: 220px 1fr; min-height: 100vh; }}
  .sidebar {{ background: #14171f; border-right: 1px solid #232734; padding: 16px 12px;
             display: flex; flex-direction: column; gap: 6px; }}
  .sidebar h1 {{ font-size: 14px; margin: 0 0 10px; color: #9aa4b2;
                 text-transform: uppercase; letter-spacing: .04em; }}
  .nav-item {{ display: flex; justify-content: space-between; align-items: center;
              gap: 8px; padding: 10px 12px; border-radius: 10px; cursor: pointer;
              border: 1px solid transparent; color: #e6e8ee; }}
  .nav-item:hover {{ background: #1b2030; }}
  .nav-name {{ font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  {checked_label_css}
  .main {{ padding: 24px; }}
  .panel {{ display: none; }}
  {show_css}
  h1.title {{ font-size: 20px; margin: 0 0 4px; }}
  h2 {{ font-size: 15px; margin: 24px 0 8px; color: #9aa4b2; text-transform: uppercase; letter-spacing: .04em; }}
  .sub {{ color: #7c8698; font-size: 13px; margin-bottom: 16px; }}
  .nowline {{ background: #1a2740; border: 1px solid #2f4a7a; color: #d7e6ff;
             padding: 14px 16px; border-radius: 12px; margin: 8px 0 16px; font-size: 16px; }}
  .now-k {{ color: #8eb6ff; font-weight: 600; margin-right: 6px; }}
  .progress-block {{ background: #171a22; border: 1px solid #232734; border-radius: 12px;
                    padding: 14px; margin: 8px 0 16px; }}
  .progress-head {{ font-size: 18px; margin-bottom: 8px; }}
  .gap-note {{ color: #f0917d; margin: 0; }}
  .ok-note {{ color: #59d089; margin: 0; }}
  .gap-list {{ margin: 6px 0 0; padding-left: 18px; color: #f0917d; }}
  .timeline {{ list-style: none; margin: 0; padding: 0; }}
  .timeline li {{ padding: 10px 0; border-bottom: 1px solid #232734; font-size: 13px; }}
  .timeline li:last-child {{ border-bottom: none; }}
  .badge.kind {{ background: #1e2638; color: #b7c0d0; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 12px 0; }}
  .card {{ background: #171a22; border: 1px solid #232734; border-radius: 12px; padding: 14px; }}
  .card .k {{ color: #7c8698; font-size: 12px; }}
  .card .v {{ font-size: 16px; margin-top: 4px; word-break: break-word; }}
  table {{ width: 100%; border-collapse: collapse; background: #171a22;
          border: 1px solid #232734; border-radius: 12px; overflow: hidden; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #232734; font-size: 13px; }}
  th {{ color: #9aa4b2; font-weight: 600; background: #14171f; }}
  tr:last-child td {{ border-bottom: none; }}
  td.num {{ color: #7c8698; width: 34px; }}
  .mono {{ font-family: ui-monospace, "Cascadia Code", Consolas, monospace; color: #b7c0d0; }}
  .muted {{ color: #7c8698; text-align: center; }}
  .muted-inline {{ color: #7c8698; font-size: 12px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; }}
  .badge.ok {{ background: #10331f; color: #59d089; }}
  .badge.gap {{ background: #3a2320; color: #f0917d; }}
  .badge.fresh {{ background: #10331f; color: #59d089; }}
  .badge.aging {{ background: #3a3218; color: #e0b84a; }}
  .badge.stale {{ background: #3a2320; color: #f0917d; }}
  .alert {{ background: #3a2320; color: #f0917d; padding: 10px 14px; border-radius: 10px; margin: 8px 0; }}
  .okline {{ background: #10331f; color: #59d089; padding: 10px 14px; border-radius: 10px; margin: 8px 0; }}
  .warnline {{ background: #2a2e3a; color: #c5cad6; padding: 10px 14px; border-radius: 10px; margin: 8px 0; }}
  a {{ color: #7eb6ff; }}
  footer {{ color: #7c8698; font-size: 12px; margin-top: 24px; }}
  @media (max-width: 720px) {{
    .shell {{ grid-template-columns: 1fr; }}
    .sidebar {{ border-right: none; border-bottom: 1px solid #232734; }}
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

    mismatch = bool(coherence.get("mismatch"))
    mismatch_banner = (
        f'<div class="alert">Ticket uyumsuzlugu: {_e(coherence.get("note"))}</div>'
        if mismatch
        else '<div class="okline">Ticket uyumu: tamam</div>'
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
        f"{_now_line(next_action)}"
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
  {"".join(radios)}
  <div class="shell">
    <aside class="sidebar">
      <h1>Projeler</h1>
      {"".join(labels)}
    </aside>
    <main class="main">
      <h1 class="title">Pala durum - {_e(root_name)}</h1>
      <div class="sub">{_e(root_path)} &middot; {stamp}</div>
      {_update_banner(update, update_checked_at if isinstance(update_checked_at, str) else None)}
      {"".join(panels)}
      <h2>Proje katalogu</h2>
      <table>
        <thead><tr><th>Proje</th><th>Faz</th><th>Sonraki is</th><th>Kalite</th><th>Tazelik</th><th>Teknoloji</th></tr></thead>
        <tbody>
          {"".join(catalog_rows)}
        </tbody>
      </table>
      <footer>Sohbet gecmisine guvenme; yukaridaki dosyalari sirayla oku. Bu sayfa yerel kayitlardan uretildi; guncellik 24 saat onbelleklidir (hook icinde ag yok).</footer>
    </main>
  </div>
</body>
</html>
"""

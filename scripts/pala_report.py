#!/usr/bin/env python3
"""Server-free local HTML status page for Pala (ADR-013 / ADR-014).

Renders the Project Memory Contract snapshot and cross-project catalog into a
single static HTML file with inline styles and a CSS-only left menu.
No server, no external assets, no scripts. Optional HTTPS links for repo/release
only. Deterministic scripts remain the source of truth; this only reads them.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

REPORT_REL = Path(".codex/pala-status.html")
FRESH_DAYS = 2
AGING_DAYS = 7

_PURPOSE_LABELS = {
    "instructions": "AGENTS / talimat",
    "status": "guncel durum",
    "progress": "ilerleme",
    "plan": "plan",
    "tooling": "arac kararlari",
    "debugging": "debug gunlugu",
    "git": "git durumu",
}


def _e(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def freshness(
    updated_at: object, now: datetime | None = None
) -> str:
    """Return fresh | aging | stale from an ISO timestamp."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if not isinstance(updated_at, str) or not updated_at.strip():
        return "stale"
    try:
        stamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except ValueError:
        return "stale"
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    age = now - stamp.astimezone(timezone.utc)
    if age < timedelta(0):
        return "fresh"
    if age < timedelta(days=FRESH_DAYS):
        return "fresh"
    if age < timedelta(days=AGING_DAYS):
        return "aging"
    return "stale"


def _freshness_badge(level: str) -> str:
    labels = {"fresh": "taze", "aging": "eskiyor", "stale": "bayat"}
    return f'<span class="badge {level}">{labels.get(level, level)}</span>'


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


def _project_detail_html(item: dict[str, object], now: datetime) -> str:
    tech = item.get("tech")
    tech_text = ", ".join(tech) if isinstance(tech, list) else ""
    blockers = item.get("blockers")
    blocker_list = blockers if isinstance(blockers, list) else []
    level = freshness(item.get("updated_at"), now)
    github = item.get("github")
    github_html = ""
    if isinstance(github, str) and github.startswith("https://"):
        github_html = (
            f'<p>GitHub: <a href="{_e(github)}">{_e(github)}</a></p>'
        )
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
        return (
            f'<div class="okline">Pala guncel ({installed}){checked}</div>'
        )
    return f'<div class="warnline">Pala guncellik: cevrimdisi / bilinmiyor{checked}</div>'


def _resolve_update(
    cache_path: Path | None = None,
) -> tuple[dict[str, object] | None, str | None]:
    import pala_update

    try:
        manifest = (
            Path(__file__).resolve().parent.parent
            / ".codex-plugin"
            / "plugin.json"
        )
        version = pala_update.installed_version(manifest)
        path = cache_path or pala_update.default_cache_path()
        result = pala_update.check_update(version, path)
        cached = pala_update.read_cache(path)
        checked = None
        if isinstance(cached, dict) and isinstance(cached.get("checked_at"), str):
            checked = cached["checked_at"]
        return result, checked
    except (OSError, ValueError, json.JSONDecodeError):
        return None, None


def render_html(
    root: Path,
    *,
    cache_path: Path | None = None,
    now: datetime | None = None,
    update: dict[str, object] | None = None,
    update_checked_at: str | None = None,
) -> str:
    """Build the full HTML document from live memory + catalog data."""
    from pala_memory import contract_context
    import pala_catalog

    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    documents: dict[str, object] = {}
    workflow: dict[str, object] = {}
    try:
        import pala_state

        manifest = pala_state.load_manifest(root)
        documents = dict(manifest.get("documents") or {})
        try:
            workflow = pala_state.load_workflow(root)
        except (OSError, ValueError, json.JSONDecodeError):
            workflow = {}
    except (OSError, ValueError, json.JSONDecodeError):
        try:
            import pala_state

            documents = dict(pala_state.discover(root).get("documents") or {})
        except (OSError, ValueError, json.JSONDecodeError):
            documents = {}

    memory = contract_context(root, documents, workflow)
    coherence = memory.get("ticket_coherence")
    coherence = coherence if isinstance(coherence, dict) else {}
    git = memory.get("git")
    git = git if isinstance(git, dict) else {}
    read_order = memory.get("read_order")
    read_order = read_order if isinstance(read_order, list) else []
    projects = pala_catalog.list_projects()

    if update is None:
        update, update_checked_at = _resolve_update(cache_path)

    mismatch = bool(coherence.get("mismatch"))
    mismatch_banner = (
        f'<div class="alert">Ticket uyumsuzlugu: {_e(coherence.get("note"))}</div>'
        if mismatch
        else '<div class="okline">Ticket uyumu: tamam</div>'
    )
    stamp = now.astimezone().strftime("%Y-%m-%d %H:%M")
    update_html = _update_banner(update, update_checked_at)

    # Sidebar radios + panels (CSS-only). Panel 0 = current project.
    radios: list[str] = []
    labels: list[str] = []
    panels: list[str] = []
    current_id = "nav-current"
    radios.append(
        f'<input type="radio" name="pala-nav" id="{current_id}" checked>'
    )
    labels.append(
        f'<label for="{current_id}" class="nav-item">'
        f'<span class="nav-name">{_e(root.name)}</span>'
        f'<span class="badge ok">aktif</span></label>'
    )
    current_panel = (
        f'<section id="panel-current" class="panel">'
        f"<h2>Aktif proje</h2>"
        f"{mismatch_banner}"
        f'<div class="grid">'
        f'<div class="card"><div class="k">Aktif ticket</div>'
        f'<div class="v">{_e(coherence.get("active") or "yok")}</div></div>'
        f'<div class="card"><div class="k">Sonraki is</div>'
        f'<div class="v">{_e(coherence.get("inferred_next") or "yok")}</div></div>'
        f'<div class="card"><div class="k">Git</div>'
        f'<div class="v mono">{_e(git.get("branch") or "?")}</div></div>'
        f'<div class="card"><div class="k">Degisen dosya</div>'
        f'<div class="v">{_e(git.get("dirty_count", 0))}</div></div>'
        f"</div>"
        f"<h2>Okuma sirasi (zorunlu)</h2>"
        f"<table><thead><tr><th>#</th><th>Amac</th><th>Dosya</th><th>Durum</th>"
        f"</tr></thead><tbody>{_read_order_rows(read_order)}</tbody></table>"
        f"</section>"
    )
    panels.append(current_panel)

    ordered = sorted(
        projects, key=lambda item: str(item.get("updated_at", "")), reverse=True
    )
    for index, item in enumerate(ordered):
        pid = f"nav-{index}"
        radios.append(f'<input type="radio" name="pala-nav" id="{pid}">')
        level = freshness(item.get("updated_at"), now)
        labels.append(
            f'<label for="{pid}" class="nav-item">'
            f'<span class="nav-name">{_e(item.get("name"))}</span>'
            f"{_freshness_badge(level)}</label>"
        )
        panels.append(
            f'<section id="panel-{index}" class="panel">'
            f'<h2>{_e(item.get("name"))}</h2>'
            f"{_project_detail_html(item, now)}"
            f"</section>"
        )

    # CSS rules: show panel when matching radio is checked.
    show_rules = ["#nav-current:checked ~ .shell #panel-current { display: block; }"]
    for index in range(len(ordered)):
        show_rules.append(
            f"#nav-{index}:checked ~ .shell #panel-{index} {{ display: block; }}"
        )
    show_css = "\n  ".join(show_rules)

    catalog_rows: list[str] = []
    if not ordered:
        catalog_rows.append(
            '<tr><td colspan="6" class="muted">Henuz kayitli proje yok. '
            "Bir projede register calistir.</td></tr>"
        )
    else:
        for item in ordered:
            level = freshness(item.get("updated_at"), now)
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

    checked_labels = ['#nav-current:checked ~ .shell label[for="nav-current"]']
    for i in range(len(ordered)):
        checked_labels.append(f'#nav-{i}:checked ~ .shell label[for="nav-{i}"]')
    checked_label_css = (
        ",\n  ".join(checked_labels)
        + " { background: #1e2638; border-color: #2f3a55; }"
    )

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pala durum - {_e(root.name)}</title>
<style>
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
</style>
</head>
<body>
  {"".join(radios)}
  <div class="shell">
    <aside class="sidebar">
      <h1>Projeler</h1>
      {"".join(labels)}
    </aside>
    <main class="main">
      <h1 class="title">Pala durum - {_e(root.name)}</h1>
      <div class="sub">{_e(root)} &middot; {stamp}</div>
      {update_html}
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


def write_report(
    root: Path,
    out: Path | None = None,
    *,
    cache_path: Path | None = None,
    now: datetime | None = None,
    update: dict[str, object] | None = None,
    update_checked_at: str | None = None,
) -> Path:
    target = out or (root / REPORT_REL)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        render_html(
            root,
            cache_path=cache_path,
            now=now,
            update=update,
            update_checked_at=update_checked_at,
        ),
        encoding="utf-8",
        newline="\n",
    )
    return target


def open_report(path: Path) -> None:
    """Open the status page in the default browser (agent/Status path only)."""
    resolved = path.resolve()
    if os.name == "nt":
        os.startfile(str(resolved))  # type: ignore[attr-defined]
    else:
        webbrowser.open(resolved.as_uri())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--out", default="")
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--cache", default="")
    args = parser.parse_args()
    root = Path(args.cwd).resolve()
    out = Path(args.out) if args.out else None
    cache = Path(args.cache) if args.cache else None
    target = write_report(root, out, cache_path=cache)
    print(str(target))
    if args.open:
        open_report(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

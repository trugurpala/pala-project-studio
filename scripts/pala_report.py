#!/usr/bin/env python3
"""Server-free local HTML status page for Pala (ADR-013 first step).

Renders the Project Memory Contract snapshot and cross-project catalog into a
single static HTML file with inline styles. No network, no external assets, no
server. The deterministic scripts remain the source of truth; this only reads
them.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

REPORT_REL = Path(".codex/pala-status.html")

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


def _catalog_rows(projects: list[dict[str, object]]) -> str:
    if not projects:
        return (
            '<tr><td colspan="5" class="muted">Henuz kayitli proje yok. '
            "Bir projede register calistir.</td></tr>"
        )
    ordered = sorted(
        projects, key=lambda item: str(item.get("updated_at", "")), reverse=True
    )
    rows: list[str] = []
    for item in ordered:
        tech = item.get("tech")
        tech_text = ", ".join(tech) if isinstance(tech, list) else ""
        blockers = item.get("blockers")
        blocker_count = len(blockers) if isinstance(blockers, list) else 0
        rows.append(
            "<tr>"
            f'<td>{_e(item.get("name"))}</td>'
            f'<td>{_e(item.get("phase") or "belirsiz")}</td>'
            f'<td>{_e(item.get("next_action") or "yok")}</td>'
            f'<td>{_e(item.get("quality_result") or "yok")}</td>'
            f'<td class="mono">{_e(tech_text or "?")}'
            + (f' <span class="badge gap">blokaj:{blocker_count}</span>' if blocker_count else "")
            + "</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_html(root: Path) -> str:
    """Build the full HTML document from live memory + catalog data."""
    from pala_memory import contract_context
    import pala_catalog

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

    mismatch = bool(coherence.get("mismatch"))
    mismatch_banner = (
        f'<div class="alert">Ticket uyumsuzlugu: {_e(coherence.get("note"))}</div>'
        if mismatch
        else '<div class="okline">Ticket uyumu: tamam</div>'
    )
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")

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
         margin: 0; padding: 24px; background: #0f1117; color: #e6e8ee; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
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
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; }}
  .badge.ok {{ background: #10331f; color: #59d089; }}
  .badge.gap {{ background: #3a2320; color: #f0917d; }}
  .alert {{ background: #3a2320; color: #f0917d; padding: 10px 14px; border-radius: 10px; margin: 8px 0; }}
  .okline {{ background: #10331f; color: #59d089; padding: 10px 14px; border-radius: 10px; margin: 8px 0; }}
  footer {{ color: #7c8698; font-size: 12px; margin-top: 24px; }}
</style>
</head>
<body>
  <h1>Pala durum - {_e(root.name)}</h1>
  <div class="sub">{_e(root)} &middot; {stamp}</div>
  {mismatch_banner}
  <div class="grid">
    <div class="card"><div class="k">Aktif ticket</div><div class="v">{_e(coherence.get("active") or "yok")}</div></div>
    <div class="card"><div class="k">Sonraki is</div><div class="v">{_e(coherence.get("inferred_next") or "yok")}</div></div>
    <div class="card"><div class="k">Git</div><div class="v mono">{_e(git.get("branch") or "?")}</div></div>
    <div class="card"><div class="k">Degisen dosya</div><div class="v">{_e(git.get("dirty_count", 0))}</div></div>
  </div>

  <h2>Okuma sirasi (zorunlu)</h2>
  <table>
    <thead><tr><th>#</th><th>Amac</th><th>Dosya</th><th>Durum</th></tr></thead>
    <tbody>
      {_read_order_rows(read_order)}
    </tbody>
  </table>

  <h2>Proje katalogu</h2>
  <table>
    <thead><tr><th>Proje</th><th>Faz</th><th>Sonraki is</th><th>Kalite</th><th>Teknoloji</th></tr></thead>
    <tbody>
      {_catalog_rows(projects)}
    </tbody>
  </table>

  <footer>Sohbet gecmisine guvenme; yukaridaki dosyalari sirayla oku. Bu sayfa yalnizca yerel kayitlardan uretildi (sunucu/ag yok).</footer>
</body>
</html>
"""


def write_report(root: Path, out: Path | None = None) -> Path:
    target = out or (root / REPORT_REL)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_html(root), encoding="utf-8", newline="\n")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--out", default="")
    args = parser.parse_args()
    root = Path(args.cwd).resolve()
    out = Path(args.out) if args.out else None
    target = write_report(root, out)
    print(str(target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

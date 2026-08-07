#!/usr/bin/env python3
"""Server-free local HTML status page for Pala (ADR-013 / ADR-014 / ADR-015).

Collects the Project Memory Contract snapshot, catalog, events and provisions,
then delegates HTML rendering to pala_view. No server, no external assets, no
scripts. Deterministic scripts remain the source of truth; this only reads them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pala_view

REPORT_REL = Path(".codex/pala-status.html")
FRESH_DAYS = 2
AGING_DAYS = 7


def freshness(updated_at: object, now: datetime | None = None) -> str:
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


def _read_order_progress(read_order: list[object]) -> dict[str, object]:
    ready = 0
    missing: list[str] = []
    labels = {
        "instructions": "AGENTS / talimat",
        "status": "guncel durum",
        "progress": "ilerleme",
        "plan": "plan",
        "tooling": "arac kararlari",
        "debugging": "debug gunlugu",
        "git": "git durumu",
    }
    for item in read_order:
        if not isinstance(item, dict):
            continue
        purpose = str(item.get("purpose") or "")
        if item.get("exists"):
            ready += 1
        else:
            missing.append(labels.get(purpose, purpose))
    return {"ready": ready, "total": len(read_order) or 7, "missing": missing}


def build_status_model(
    root: Path,
    *,
    cache_path: Path | None = None,
    now: datetime | None = None,
    update: dict[str, object] | None = None,
    update_checked_at: str | None = None,
) -> dict[str, object]:
    """Collect the status page data model from live memory + local store."""
    from pala_memory import contract_context
    import pala_catalog
    import pala_db

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

    db = pala_catalog.db_path()
    try:
        events = pala_db.recent_events(limit=15, path=db)
    except (OSError, ValueError, TypeError):
        events = []
    try:
        provisions = pala_db.recent_provisions(limit=10, path=db)
    except (OSError, ValueError, TypeError):
        provisions = []

    if update is None:
        update, update_checked_at = _resolve_update(cache_path)

    next_action = (
        coherence.get("inferred_next")
        or workflow.get("next_action")
        or ""
    )

    return {
        "root_name": root.name,
        "root_path": str(root),
        "stamp": now.astimezone().strftime("%Y-%m-%d %H:%M"),
        "coherence": coherence,
        "git": git,
        "read_order": read_order,
        "progress": _read_order_progress(read_order),
        "projects": projects,
        "events": events,
        "provisions": provisions,
        "next_action": next_action,
        "update": update,
        "update_checked_at": update_checked_at,
        "now": now,
    }


def render_html(
    root: Path,
    *,
    cache_path: Path | None = None,
    now: datetime | None = None,
    update: dict[str, object] | None = None,
    update_checked_at: str | None = None,
) -> str:
    """Build the full HTML document from live memory + catalog data."""
    model = build_status_model(
        root,
        cache_path=cache_path,
        now=now,
        update=update,
        update_checked_at=update_checked_at,
    )
    stamp_now = model.get("now")
    if isinstance(stamp_now, datetime):
        now_value = stamp_now
    else:
        now_value = now or datetime.now(timezone.utc)

    def _fresh(value: object) -> str:
        return freshness(value, now_value)

    return pala_view.render(model, freshness_fn=_fresh)


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

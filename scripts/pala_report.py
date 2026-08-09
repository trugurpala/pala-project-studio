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


_GATE_STATUSES = ("passed", "not-run", "blocked", "configured-not-verified", "failed")


def _gate_status_from_text(text: str) -> str:
    lowered = text.casefold()
    for status in _GATE_STATUSES:
        if status in lowered:
            return status
    return "not-run"


def last_gate_signal(
    workflow: dict[str, object] | None,
    events: list[object] | None = None,
) -> dict[str, str]:
    """Display-only last gate summary for the Status decision strip."""
    workflow = workflow if isinstance(workflow, dict) else {}
    verification = workflow.get("verification")
    if isinstance(verification, list) and verification:
        last = str(verification[-1]).strip()
        if last:
            return {
                "label": last[:80],
                "status": _gate_status_from_text(last),
            }
    evidence = workflow.get("verification_evidence")
    if isinstance(evidence, list) and evidence:
        last_ev = evidence[-1]
        if isinstance(last_ev, dict):
            label = str(last_ev.get("command") or last_ev.get("status") or "").strip()
            status = str(last_ev.get("status") or _gate_status_from_text(label))
        else:
            label = str(last_ev).strip()
            status = _gate_status_from_text(label)
        if label:
            return {"label": label[:80], "status": status or "not-run"}
    tier = str(workflow.get("verification_tier") or "").strip()
    if tier and tier != "not-run":
        return {"label": tier[:80], "status": _gate_status_from_text(tier)}
    for event in events or []:
        if not isinstance(event, dict):
            continue
        kind = str(event.get("kind") or "")
        if kind not in {"checkpoint", "mismatch"}:
            continue
        detail = str(event.get("evidence") or event.get("detail") or "").strip()
        if not detail:
            continue
        return {
            "label": detail[:80],
            "status": _gate_status_from_text(detail)
            if kind == "checkpoint"
            else "blocked",
        }
    if tier:
        return {"label": tier[:80], "status": "not-run"}
    return {"label": "not-run", "status": "not-run"}


def active_freshness_level(
    root: Path,
    projects: list[object],
    workflow: dict[str, object] | None,
    *,
    now: datetime | None = None,
) -> str:
    """Freshness for the active project strip (catalog path, else workflow stamp)."""
    root_resolved = root.resolve()
    for item in projects:
        if not isinstance(item, dict):
            continue
        path_raw = item.get("path")
        if not isinstance(path_raw, str) or not path_raw.strip():
            continue
        try:
            if Path(path_raw).resolve() == root_resolved:
                return freshness(item.get("updated_at"), now)
        except OSError:
            continue
    workflow = workflow if isinstance(workflow, dict) else {}
    return freshness(workflow.get("updated_at"), now)


def quality_signal(root: Path, workflow: dict[str, object]) -> dict[str, object]:
    """Return only safe, displayable ledger fields for the local status page."""
    ticket = str(workflow.get("active_ticket") or "").strip()
    empty: dict[str, object] = {
        "available": False,
        "status": "not-run",
        "ticket": ticket,
        "risk": {"level": "unknown", "reasons": []},
        "coverage": {"passed": 0, "required": 0},
        "last_problem": "quality ledger not initialized" if ticket else "no active ticket",
        "next_action": f"initialize quality ledger for {ticket}" if ticket else "begin a ticket",
    }
    if not ticket:
        return empty
    try:
        import pala_quality

        if not pala_quality.quality_ledger_path(root, ticket).is_file():
            return empty
        report = pala_quality.quality_gate(root, ticket)
        risk = report.get("risk") if isinstance(report.get("risk"), dict) else {}
        coverage = report.get("coverage") if isinstance(report.get("coverage"), dict) else {}
        return {
            "available": True,
            "status": str(report.get("status") or "blocked"),
            "ticket": str(report.get("ticket") or ticket),
            "risk": {
                "level": str(risk.get("level") or "unknown"),
                "reasons": [str(item)[:80] for item in list(risk.get("reasons") or [])[:4]],
            },
            "coverage": {
                "passed": int(coverage.get("passed") or 0),
                "required": int(coverage.get("required") or 0),
            },
            "last_problem": str(report.get("last_problem") or "yok")[:120],
            "next_action": str(report.get("next_action") or "")[:160],
        }
    except (ImportError, OSError, ValueError, json.JSONDecodeError):
        return {**empty, "status": "blocked", "last_problem": "quality ledger unreadable"}


def build_status_model(
    root: Path,
    *,
    cache_path: Path | None = None,
    now: datetime | None = None,
    update: dict[str, object] | None = None,
    update_checked_at: str | None = None,
    catalog_root: Path | None = None,
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
    except ImportError:
        pala_state = None  # type: ignore[assignment]
    if pala_state is not None:
        try:
            manifest = pala_state.load_manifest(root)
            documents = dict(manifest.get("documents") or {})
        except (OSError, ValueError, json.JSONDecodeError):
            documents = {}
        try:
            workflow = pala_state.load_workflow(root)
        except (OSError, ValueError, json.JSONDecodeError):
            workflow = {}
    if not documents:
        try:
            documents = dict(pala_state.discover(root).get("documents") or {})
        except (AttributeError, OSError, ValueError, json.JSONDecodeError):
            documents = {}

    memory = contract_context(root, documents, workflow)
    coherence = memory.get("ticket_coherence")
    coherence = coherence if isinstance(coherence, dict) else {}
    brain = memory.get("debugging_brain")
    brain = brain if isinstance(brain, dict) else {}
    git = memory.get("git")
    git = git if isinstance(git, dict) else {}
    read_order = memory.get("read_order")
    read_order = read_order if isinstance(read_order, list) else []
    projects = pala_catalog.list_projects(catalog_dir=catalog_root)

    db = pala_catalog.db_path(catalog_root)
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

    quality = quality_signal(root, workflow)
    next_action = (
        quality.get("next_action")
        if quality.get("status") == "blocked"
        else coherence.get("inferred_next")
        or workflow.get("next_action")
        or ""
    )

    return {
        "root_name": root.name,
        "root_path": str(root),
        "stamp": now.astimezone().strftime("%Y-%m-%d %H:%M"),
        "coherence": coherence,
        "debugging_brain": brain,
        "git": git,
        "read_order": read_order,
        "progress": _read_order_progress(read_order),
        "projects": projects,
        "events": events,
        "provisions": provisions,
        "next_action": next_action,
        "last_gate": last_gate_signal(workflow, events),
        "quality": quality,
        "freshness_level": active_freshness_level(
            root, projects, workflow, now=now
        ),
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
    catalog_root: Path | None = None,
) -> str:
    """Build the full HTML document from live memory + catalog data."""
    model = build_status_model(
        root,
        cache_path=cache_path,
        now=now,
        update=update,
        update_checked_at=update_checked_at,
        catalog_root=catalog_root,
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
    catalog_root: Path | None = None,
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
            catalog_root=catalog_root,
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


def format_open_hint(path: Path) -> str:
    """One-liner for agents/humans: how to open the Status HTML vitrin."""
    resolved = path.resolve()
    try:
        uri = resolved.as_uri()
    except ValueError:
        uri = str(resolved)
    return f"açmak için: {uri}"


def format_report_output(path: Path) -> str:
    """CLI stdout body: absolute path, contract relative path, open hint."""
    resolved = path.resolve()
    lines = [
        str(resolved),
        f"Status HTML: {REPORT_REL.as_posix()}",
        format_open_hint(resolved),
    ]
    return "\n".join(lines) + "\n"


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
    sys.stdout.write(format_report_output(target))
    if args.open:
        open_report(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

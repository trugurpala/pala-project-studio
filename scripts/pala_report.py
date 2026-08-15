#!/usr/bin/env python3
"""Server-free local HTML status page for Pala (ADR-013 / ADR-014 / ADR-015).

Collects the Project Memory Contract snapshot, catalog, events and provisions,
then delegates HTML rendering to pala_view. No server, no external assets.
One inline script may persist UI prefs (theme/toggles) in localStorage only.
Deterministic scripts remain the source of truth; this only reads them.
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
from pala_authority import shared_state_root
from pala_control_center_open import open_if_explicit

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
        "required_checks": [],
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
        checks = report.get("checks") if isinstance(report.get("checks"), list) else []
        required_checks = [
            {
                "id": str(item.get("id") or "quality-check")[:120],
                "status": str(item.get("status") or "not-run")[:40],
            }
            for item in checks
            if isinstance(item, dict) and bool(item.get("required"))
        ][:12]
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
            "required_checks": required_checks,
            "last_problem": str(report.get("last_problem") or "yok")[:120],
            "next_action": str(report.get("next_action") or "")[:160],
        }
    except (ImportError, OSError, ValueError, json.JSONDecodeError):
        return {**empty, "status": "blocked", "last_problem": "quality ledger unreadable"}


def delivery_decision(
    workflow: dict[str, object] | None,
    coherence: dict[str, object] | None,
    quality: dict[str, object] | None,
) -> dict[str, str]:
    """Separate a passed ticket gate from an honest delivery/release claim."""
    workflow = workflow if isinstance(workflow, dict) else {}
    coherence = coherence if isinstance(coherence, dict) else {}
    quality = quality if isinstance(quality, dict) else {}
    ticket = str(quality.get("ticket") or coherence.get("active") or "").strip()
    tier = str(workflow.get("verification_tier") or "not-run")
    quality_status = str(quality.get("status") or "not-run")
    if bool(coherence.get("mismatch")) or bool(workflow.get("needs_reconcile")):
        return {
            "status": "blocked",
            "label": "Bloke",
            "tier": tier,
            "detail": "Aktif ticket ile sonraki iş uyumsuz; önce kaydı eşleştir.",
        }
    if not ticket:
        return {
            "status": "not-assessed",
            "label": "Henüz değerlendirilmedi",
            "tier": tier,
            "detail": "Önce bir ticket başlat ve proje-yerel kalite planını oluştur.",
        }
    if quality_status != "passed":
        return {
            "status": "blocked" if quality_status in {"blocked", "failed"} else "not-assessed",
            "label": "Bloke" if quality_status in {"blocked", "failed"} else "Henüz değerlendirilmedi",
            "tier": tier,
            "detail": str(quality.get("last_problem") or "Zorunlu kalite kanıtı eksik.")[:160],
        }
    labels = {
        "ticket": "Ticket hazır",
        "milestone": "Milestone hazır",
        "release": "Sürüme hazır",
    }
    label = labels.get(tier)
    if label is None:
        return {
            "status": "not-assessed",
            "label": "Henüz değerlendirilmedi",
            "tier": tier,
            "detail": "Dar doğrulama geçti; ticket veya release kararı için uygun tier gerekir.",
        }
    return {
        "status": "passed",
        "label": label,
        "tier": tier,
        "detail": "Zorunlu proje-yerel kapılar bu tier için kanıtlı geçti.",
    }


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
    canonical_task: dict[str, object] | None = None
    try:
        from pala_store import WorkflowStore

        observed = WorkflowStore(root).active_task_contract()
        canonical_task = observed if isinstance(observed, dict) else None
    except (ImportError, OSError, RuntimeError, ValueError, TypeError):
        canonical_task = None
    if canonical_task is not None:
        ticket_id = str(canonical_task.get("id") or "").strip()
        if ticket_id:
            workflow = {
                **workflow,
                "active_ticket": ticket_id,
                "lifecycle": str(canonical_task.get("status") or "IN_PROGRESS"),
                "next_action": str(canonical_task.get("next_action") or ""),
                "verification_tier": "ticket",
            }
            coherence = {
                **coherence,
                "active": ticket_id,
                "inferred_next": str(canonical_task.get("next_action") or ""),
            }
    brain = memory.get("debugging_brain")
    brain = brain if isinstance(brain, dict) else {}
    git = memory.get("git")
    git = git if isinstance(git, dict) else {}
    read_order = memory.get("read_order")
    read_order = read_order if isinstance(read_order, list) else []
    try:
        projects = pala_catalog.list_projects(
            catalog_dir=catalog_root, read_only=True
        )
    except (OSError, RuntimeError, ValueError, TypeError):
        projects = []

    db = pala_catalog.db_path(catalog_root)
    project_id = pala_catalog._project_id(root)
    continuity_bundle: dict[str, object] = {}
    if pala_state is not None:
        try:
            continuity_bundle = pala_state.refresh_continuity(
                root, persist=False, db_path=db
            )
        except (OSError, RuntimeError, ValueError, TypeError, json.JSONDecodeError):
            continuity_bundle = {
                "status": "blocked",
                "finding": "CONTINUITY_READ_MODEL_UNAVAILABLE",
                "can_complete": False,
            }
    try:
        events = pala_db.recent_events(
            limit=15,
            path=db,
            project_id=project_id,
            read_only=True,
        )
    except (OSError, RuntimeError, ValueError, TypeError):
        events = []
    try:
        provisions = pala_db.recent_provisions(limit=10, path=db, read_only=True)
    except (OSError, RuntimeError, ValueError, TypeError):
        provisions = []
    try:
        from pala_project_history import list_history

        history_model = list_history(repository_id=project_id, path=db)
    except (ImportError, OSError, RuntimeError, ValueError, TypeError):
        history_model = {
            "validation_status": "blocked",
            "items": [],
            "can_complete": False,
        }
    live_history = continuity_bundle.get("history")
    if isinstance(live_history, dict):
        history_model = live_history

    if update is None:
        update, update_checked_at = _resolve_update(cache_path)

    quality = quality_signal(root, workflow)
    delivery = delivery_decision(workflow, coherence, quality)
    next_action = (
        quality.get("next_action")
        if quality.get("status") == "blocked"
        else coherence.get("inferred_next")
        or workflow.get("next_action")
        or ""
    )
    try:
        store_path = str(db.resolve())
    except OSError:
        store_path = str(db)

    owner_cockpit = ""
    try:
        from pala_owner_cockpit import render_owner_cockpit
        from pala_product_cli import public_status

        product = public_status(root)
        snapshot = product.get("owner_cockpit")
        if isinstance(snapshot, dict):
            owner_snapshot = dict(snapshot)
            if canonical_task is not None:
                acceptance = canonical_task.get("acceptance")
                acceptance = acceptance if isinstance(acceptance, list) else []
                owner_snapshot.update(
                    {
                        "project": root.name,
                        "state": str(canonical_task.get("status") or "IN_PROGRESS"),
                        "acceptance_verified": sum(
                            1
                            for item in acceptance
                            if isinstance(item, dict) and item.get("status") == "passed"
                        ),
                        "acceptance_total": max(1, len(acceptance)),
                        "quality": quality.get("status") or "not-run",
                        "delivery": delivery.get("status") or "not-run",
                        "next_action": str(
                            canonical_task.get("next_action") or next_action
                        ),
                    }
                )
            active_ticket = coherence.get("active")
            owner_snapshot["queue"] = {
                "items": [
                    {
                        "ticket": active_ticket,
                        "status": (
                            canonical_task.get("status")
                            if canonical_task is not None
                            else workflow.get("lifecycle")
                        )
                        or "not-run",
                    }
                ]
                if active_ticket
                else [],
                "can_complete": False,
            }
            receipt = continuity_bundle.get("receipt")
            if not isinstance(receipt, dict):
                receipt = workflow.get("context_receipt")
            owner_snapshot["context_receipts"] = {
                "items": [receipt] if isinstance(receipt, dict) else [],
                "can_complete": False,
            }
            owner_snapshot["project_history"] = history_model
            continuity_read_model = continuity_bundle.get("continuity")
            owner_snapshot["project_continuity"] = (
                continuity_read_model
                if isinstance(continuity_read_model, dict)
                else {
                    "validation_status": "not-run",
                    "can_complete": False,
                }
            )
            try:
                from pala_failure_intelligence import list_failures

                owner_snapshot["failure_intelligence"] = list_failures(
                    project_ref=project_id, limit=8, path=db
                )
            except (ImportError, OSError, RuntimeError, ValueError, TypeError):
                owner_snapshot["failure_intelligence"] = {
                    "status": "blocked",
                    "items": [],
                    "findings": ["FAILURE_INTELLIGENCE_UNAVAILABLE"],
                    "can_complete": False,
                }
            profile = continuity_bundle.get("profile")
            owner_snapshot["profiles"] = {
                "items": [profile] if isinstance(profile, dict) else [],
                "findings": (
                    []
                    if isinstance(profile, dict)
                    else ["PROFILE_SUMMARY_NOT_AVAILABLE"]
                ),
                "can_complete": False,
            }
            try:
                from pala_runtime_observations import read_runtime_observations

                runtime = read_runtime_observations(root)
                host = runtime.get("host")
                processes = runtime.get("processes")
                owner_snapshot["host_capabilities"] = (
                    host
                    if isinstance(host, dict)
                    else {
                        "items": [],
                        "findings": ["HOST_OBSERVATION_UNAVAILABLE"],
                        "can_complete": False,
                    }
                )
                owner_snapshot["host_processes"] = (
                    processes
                    if isinstance(processes, dict)
                    else {
                        "items": [],
                        "findings": ["PROCESS_OBSERVATION_UNAVAILABLE"],
                        "can_complete": False,
                    }
                )
            except (ImportError, OSError, RuntimeError, ValueError, TypeError):
                owner_snapshot["host_capabilities"] = {
                    "items": [],
                    "findings": ["HOST_OBSERVATION_UNAVAILABLE"],
                    "can_complete": False,
                }
                owner_snapshot["host_processes"] = {
                    "items": [],
                    "findings": ["PROCESS_OBSERVATION_UNAVAILABLE"],
                    "can_complete": False,
                }
            owner_snapshot["security_release"] = {
                "items": [
                    {
                        "quality_status": quality.get("status") or "not-run",
                        "quality_ticket": quality.get("ticket") or "not-run",
                        "required_checks": (
                            f"{quality.get('coverage', {}).get('passed', 0)}/"
                            f"{quality.get('coverage', {}).get('required', 0)}"
                            if isinstance(quality.get("coverage"), dict)
                            else "0/0"
                        ),
                        "delivery_status": delivery.get("status") or "not-run",
                        "verification_tier": delivery.get("tier") or "not-run",
                    }
                ],
                "findings": (
                    [str(quality.get("last_problem") or "")[:120]]
                    if quality.get("status") == "blocked" and quality.get("last_problem")
                    else []
                ),
                "can_complete": False,
            }
            owner_cockpit = render_owner_cockpit(owner_snapshot, fragment=True)
    except (ImportError, OSError, ValueError, json.JSONDecodeError):
        owner_cockpit = ""

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
        "project_history": history_model,
        "continuity": continuity_bundle,
        "provisions": provisions,
        "next_action": next_action,
        "last_gate": last_gate_signal(workflow, events),
        "quality": quality,
        "delivery": delivery,
        "verification_tier": str(workflow.get("verification_tier") or "not-run"),
        "store_path": store_path,
        "hooks_trust": "configured-not-verified",
        "freshness_level": active_freshness_level(
            root, projects, workflow, now=now
        ),
        "update": update,
        "update_checked_at": update_checked_at,
        "now": now,
        "owner_cockpit_html": owner_cockpit,
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
    if out is not None:
        target = out
    else:
        authority_root = shared_state_root(root)
        target = (
            authority_root / "generated" / "pala-status.html"
            if authority_root is not None
            else root / REPORT_REL
        )
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
    parser.add_argument("--intent", default="")
    parser.add_argument("--cache", default="")
    args = parser.parse_args()
    root = Path(args.cwd).resolve()
    out = Path(args.out) if args.out else None
    cache = Path(args.cache) if args.cache else None
    target = write_report(root, out, cache_path=cache)
    sys.stdout.write(format_report_output(target))
    if args.open and not open_if_explicit(
        args.intent,
        refresh=lambda: target,
        opener=open_report,
    ):
        print('Control Center not opened: explicit intent "paneli aç" is required.', file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

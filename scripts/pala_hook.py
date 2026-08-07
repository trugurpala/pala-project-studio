#!/usr/bin/env python3
"""Codex lifecycle hook for registered Pala projects."""

from __future__ import annotations

import json
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

from pala_store import WorkflowStore

MANIFEST = Path(".codex/pala-project.json")
WORKFLOW = Path(".codex/pala-workflow.json")
WORKFLOW_SCHEMA_VERSIONS = (1, 2)


def emit(value: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False))


def git_root(cwd: Path) -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    for candidate in (cwd.resolve(), *cwd.resolve().parents):
        if (candidate / MANIFEST).is_file():
            return candidate
    return None


def load(root: Path) -> dict[str, object] | None:
    path = root / MANIFEST
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("managed_by") != "pala-project-finisher":
        return None
    if not isinstance(payload.get("documents"), dict):
        return None
    return payload


def load_workflow(root: Path) -> dict[str, object] | None:
    path = root / WORKFLOW
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if payload.get("schema_version") in WORKFLOW_SCHEMA_VERSIONS else None


def reconciliation_report(
    root: Path,
    manifest: dict[str, object],
    workflow: dict[str, object] | None,
) -> dict[str, object]:
    if workflow is None:
        return {"needed": True, "reasons": ["workflow state is missing"]}
    state_path = Path(__file__).with_name("pala_state.py")
    try:
        spec = importlib.util.spec_from_file_location("pala_hook_state", state_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("state helper cannot be loaded")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.reconciliation_report(root, manifest, workflow)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
        return {"needed": True, "reasons": ["workflow freshness is unknown"]}


def save_workflow(root: Path, payload: dict[str, object]) -> None:
    (root / WORKFLOW).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def local_health(root: Path) -> dict[str, str]:
    """Return only fast, local lifecycle facts for the startup context."""
    return {
        "plugin": "loaded",
        "python": "ready" if Path(sys.executable).is_file() else "unknown",
        "git": "ready" if shutil.which("git") and root.is_dir() else "unknown",
        "hook": "running",
    }


def session_context(
    documents: dict[str, object],
    workflow: dict[str, object] | None,
    compacted: bool,
    project_kind: object = None,
    profiles: object = None,
    reconciliation: dict[str, object] | None = None,
    health: dict[str, str] | None = None,
    memory: dict[str, object] | None = None,
    tools_summary: str | None = None,
) -> dict[str, object]:
    status = documents.get("status")
    plan = documents.get("plan")
    project = documents.get("project")
    prefix = "Context was compacted; reconcile before edits. " if compacted else ""
    active = workflow.get("active_ticket") if workflow else None
    next_action = workflow.get("next_action") if workflow else None
    dirty = bool(workflow and workflow.get("dirty"))
    blockers = workflow.get("blockers", []) if workflow else []
    blocker_count = len(blockers) if isinstance(blockers, list) else 0
    needs_reconcile = bool(reconciliation and reconciliation.get("needed"))
    reason_count = len(reconciliation.get("reasons", [])) if reconciliation else 0
    kind = project_kind if isinstance(project_kind, str) else "unknown"
    health = health or {}
    health_text = (
        "Pala local health: "
        f"plugin={health.get('plugin', 'loaded')}; "
        f"python={health.get('python', 'unknown')}; "
        f"git={health.get('git', 'unknown')}; "
        f"hook={health.get('hook', 'running')}. "
    )
    coherence = (memory or {}).get("ticket_coherence") if isinstance(memory, dict) else None
    mismatch = bool(isinstance(coherence, dict) and coherence.get("mismatch"))
    tools = tools_summary or "tools=n/a"
    message = (
        f"{prefix}{health_text}Pala project kind={kind}. "
        f"Memory read_order=AGENTS>CURRENT_STATUS>PROGRESS>plan>TOOLING>DEBUG>git. "
        f"Read status first: status={status or project}; "
        f"inspect only the active ticket section in plan={plan}. "
        f"active={active or 'none'}; next={next_action or 'reconcile first'}; "
        f"dirty={str(dirty).lower()}; blockers={blocker_count}; "
        f"reconcile={str(needs_reconcile).lower()}({reason_count}); "
        f"ticket_mismatch={str(mismatch).lower()}; {tools}. "
        "Do not re-plan completed scope. Continue authorized local "
        "work; use the full gate only at the plan's milestone/release boundary, then "
        "checkpoint one coherent ticket."
    )
    if len(message) > 800:
        message = message[:797] + "..."
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": message,
        }
    }


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    root = git_root(Path(event.get("cwd") or os.getcwd()))
    if root is None:
        return 0
    payload = load(root)
    if payload is None:
        return 0
    documents = payload["documents"]
    event_name = event.get("hook_event_name")

    if event_name == "PreCompact":
        workflow = load_workflow(root)
        if workflow and workflow.get("active_ticket"):
            workflow["needs_reconcile"] = True
            save_workflow(root, workflow)
        session_id = event.get("session_id")
        if isinstance(session_id, str) and session_id.strip():
            WorkflowStore(root).heartbeat(session_id, "pre_compact")
        emit({"continue": True})
        return 0

    if event_name == "SessionStart":
        workflow = load_workflow(root)
        session_id = event.get("session_id")
        if isinstance(session_id, str) and session_id.strip():
            WorkflowStore(root).heartbeat(session_id, "session_start")
            owned_ticket = WorkflowStore(root).active_for_session(session_id)
            if owned_ticket is not None:
                workflow = {
                    "active_ticket": owned_ticket.get("ticket"),
                    "next_action": owned_ticket.get("next_action"),
                    "dirty": owned_ticket.get("dirty"),
                    "blockers": [],
                }
        reconciliation = reconciliation_report(root, payload, workflow)
        compacted = event.get("source") == "compact" or bool(
            workflow and workflow.get("needs_reconcile")
        )
        memory = None
        tools_summary = None
        try:
            from pala_memory import contract_context
            from pala_tool_memory import short_hook_summary, tool_memory_report

            memory = contract_context(root, documents, workflow)
            profiles = payload.get("profiles")
            tools = tool_memory_report(
                profiles=list(profiles) if isinstance(profiles, list) else []
            )
            tools_summary = short_hook_summary(tools)
            if (
                isinstance(memory.get("ticket_coherence"), dict)
                and memory["ticket_coherence"].get("mismatch")
            ):
                if workflow is not None:
                    workflow = dict(workflow)
                    workflow["memory_mismatch"] = memory["ticket_coherence"]
                    workflow["needs_reconcile"] = True
        except (OSError, ValueError, TypeError, ImportError):
            memory = None
            tools_summary = None
        emit(
            session_context(
                documents,
                workflow,
                compacted,
                payload.get("project_kind"),
                payload.get("profiles"),
                reconciliation,
                local_health(root),
                memory,
                tools_summary,
            )
        )
        return 0

    if event_name == "SessionEnd":
        session_id = event.get("session_id")
        if isinstance(session_id, str) and session_id.strip():
            WorkflowStore(root).heartbeat(session_id, "session_end")
        emit({})
        return 0

    if event_name == "Stop":
        if event.get("stop_hook_active"):
            emit({})
            return 0
        workflow = load_workflow(root)
        if workflow and workflow.get("dirty"):
            emit(
                {
                    "decision": "block",
                    "reason": (
                        "Before ending this turn, reconcile the active ticket, "
                        "verification evidence, blockers, and exactly one next "
                        "action in the registered plan/status documents. Then "
                        "run the Pala state validator. Run /hooks if hook safety is unknown."
                    ),
                }
            )
        else:
            emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

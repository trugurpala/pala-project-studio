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
from pala_state_core import workflow_path
from pala_tokens import approx_tokens
from pala_hook_session import session_context as _session_context

MANIFEST = Path(".codex/pala-project.json")
WORKFLOW = Path(".codex/pala-workflow.json")
WORKFLOW_SCHEMA_VERSIONS = (1, 2)
# Presence + minimal cold packet for registered projects only.
PRESENCE_LINE = "Pala burada â€” bu oturumda yanÄ±ndayÄ±m."
# Codex host spill threshold configured in hooks.json.  The host interprets it
# as an approximate token threshold (default ~2500); it is deliberately not
# Pala's own output-size limit even if the same numeric value may match.
ADDITIONAL_CONTEXT_SPILL_TOKEN_THRESHOLD = 1800
# Pala product character ceiling for the message it constructs.
SESSION_CONTEXT_CHAR_LIMIT = 1800
# Pala's conservative approximate-token product budget, independent of host
# spill handling.  It preserves room for normal conversation context.
SESSION_CONTEXT_TOKEN_BUDGET = 900
# Back-compat alias for older imports/tests during migration.
SESSION_CONTEXT_LIMIT = SESSION_CONTEXT_CHAR_LIMIT


def emit(value: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False))


def _fit_session_message(message: str) -> str:
    """Trim legacy middle first so presence + tail (cold packet / gate) survive."""
    if (
        len(message) <= SESSION_CONTEXT_CHAR_LIMIT
        and approx_tokens(message) <= SESSION_CONTEXT_TOKEN_BUDGET
    ):
        return message
    prefix = PRESENCE_LINE
    if not message.startswith(prefix):
        clipped = message[: SESSION_CONTEXT_CHAR_LIMIT - 3] + "..."
        while approx_tokens(clipped) > SESSION_CONTEXT_TOKEN_BUDGET and len(clipped) > 64:
            clipped = clipped[: max(64, len(clipped) - 64)]
        return clipped
    body = message[len(prefix) :].lstrip()
    keep_tail = max(160, int(len(body) * 0.4))
    while True:
        candidate = f"{prefix} {body}"
        if (
            len(candidate) <= SESSION_CONTEXT_CHAR_LIMIT
            and approx_tokens(candidate) <= SESSION_CONTEXT_TOKEN_BUDGET
        ):
            return candidate
        if len(body) <= keep_tail + 32:
            tail = body[-keep_tail:] if len(body) > keep_tail else body
            candidate = f"{prefix} ...{tail}"
            if len(candidate) > SESSION_CONTEXT_CHAR_LIMIT:
                candidate = candidate[: SESSION_CONTEXT_CHAR_LIMIT - 3] + "..."
            while (
                approx_tokens(candidate) > SESSION_CONTEXT_TOKEN_BUDGET
                and len(candidate) > len(prefix) + 32
            ):
                candidate = candidate[: max(len(prefix) + 16, len(candidate) - 48)]
            return candidate
        drop = max(48, (len(body) - keep_tail) // 4)
        head = body[: max(0, len(body) - keep_tail - drop)]
        tail = body[-keep_tail:]
        body = f"{head}...{tail}"


def git_root(cwd: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        result = None
    if (
        result is not None
        and result.returncode == 0
        and result.stdout.strip()
    ):
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
    path = workflow_path(root)
    legacy_path = root / WORKFLOW
    if not path.is_file() and legacy_path.is_file():
        path = legacy_path
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
    path = workflow_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
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


def _session_restore_prefix(source: str | None, compacted: bool) -> str:
    """Orient after host SessionStart sources; never claim mid-turn memory."""
    if compacted or source == "compact":
        return "Context was compacted; reconcile before edits. "
    if source == "resume":
        return "Session resumed; re-read STATUS + active ticket before edits. "
    if source == "clear":
        return "Session cleared; reload STATUS + active ticket before edits. "
    return ""


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
    cold_packet_text: str | None = None,
    source: str | None = None,
) -> dict[str, object]:
    return _session_context(
        documents,
        workflow,
        compacted,
        project_kind=project_kind,
        profiles=profiles,
        reconciliation=reconciliation,
        health=health,
        memory=memory,
        tools_summary=tools_summary,
        cold_packet_text=cold_packet_text,
        source=source,
        operations={
            "PRESENCE_LINE": PRESENCE_LINE,
            "SESSION_CONTEXT_CHAR_LIMIT": SESSION_CONTEXT_CHAR_LIMIT,
            "_fit_session_message": _fit_session_message,
            "_session_restore_prefix": _session_restore_prefix,
        },
    )


def _handle_precompact(event: dict[str, object], root: Path) -> int:
    workflow = load_workflow(root)
    if workflow and (
        workflow.get("active_ticket") or workflow.get("dirty") or workflow.get("next_action")
    ):
        workflow["needs_reconcile"] = True
        save_workflow(root, workflow)
    session_id = event.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        WorkflowStore(root).heartbeat(session_id, "pre_compact")
    emit({"continue": True})
    return 0


def _merge_session_ticket(
    root: Path, workflow: dict[str, object] | None, session_id: object
) -> dict[str, object] | None:
    if not isinstance(session_id, str) or not session_id.strip():
        return workflow
    WorkflowStore(root).heartbeat(session_id, "session_start")
    owned_ticket = WorkflowStore(root).active_for_session(session_id)
    if owned_ticket is None:
        return workflow
    merged = dict(workflow) if isinstance(workflow, dict) else {
        "schema_version": 2,
        "blockers": [],
    }
    merged["active_ticket"] = owned_ticket.get("ticket")
    owned_next = owned_ticket.get("next_action")
    merged["next_action"] = (
        owned_next
        if isinstance(owned_next, str) and owned_next.strip()
        else (merged.get("next_action") or "reconcile first")
    )
    merged["dirty"] = owned_ticket.get("dirty")
    if not isinstance(merged.get("blockers"), list):
        merged["blockers"] = []
    return merged


def _session_memory(
    root: Path,
    documents: dict[str, object],
    payload: dict[str, object],
    workflow: dict[str, object] | None,
) -> tuple[dict[str, object] | None, str | None, dict[str, object] | None]:
    try:
        from pala_memory import contract_context
        from pala_tool_memory import short_hook_summary, tool_memory_report

        memory = contract_context(root, documents, workflow)
        try:
            from pala_debug_gate import evaluate_gate, session_memory_hit

            memory["debug_gate"] = evaluate_gate(root, documents, surface="session")
            brain = memory.get("debugging_brain")
            debug_open = int(brain.get("open") or 0) if isinstance(brain, dict) else 0
            debugging_read = any(
                isinstance(item, dict)
                and item.get("purpose") == "debugging"
                and bool(item.get("exists"))
                for item in memory.get("read_order") or []
            )
            memory["memory_hit"] = session_memory_hit(
                debug_open=debug_open, debugging_read=debugging_read
            )
            from pala_cmd_memory import active_blocks, context_packet_hint

            memory["cmd_memory"] = {
                "blocks": active_blocks(limit=5),
                "hint": context_packet_hint(limit=3),
            }
        except (OSError, ValueError, TypeError, ImportError):
            pass
        profiles = payload.get("profiles")
        tools = tool_memory_report(
            profiles=list(profiles) if isinstance(profiles, list) else []
        )
        if isinstance(memory.get("ticket_coherence"), dict) and memory["ticket_coherence"].get("mismatch") and workflow is not None:
            workflow = dict(workflow)
            workflow["memory_mismatch"] = memory["ticket_coherence"]
            workflow["needs_reconcile"] = True
        return memory, short_hook_summary(tools), workflow
    except (OSError, ValueError, TypeError, ImportError):
        return None, None, workflow


def _cold_session_text(
    root: Path,
    documents: dict[str, object],
    workflow: dict[str, object] | None,
    session_id: object,
) -> str | None:
    try:
        from pala_cold_packet import session_packet_snippet, stamp_workflow_parallel

        key = session_id if isinstance(session_id, str) else None
        text = session_packet_snippet(
            root,
            documents=documents,
            workflow=workflow,
            session_id=key,
            max_bytes=900,
        )
        stamp_workflow_parallel(root, session_id=key)
        return text
    except (OSError, ValueError, TypeError, ImportError):
        return None


def _handle_session_start(
    event: dict[str, object], root: Path, payload: dict[str, object]
) -> int:
    documents = payload["documents"]
    workflow = _merge_session_ticket(root, load_workflow(root), event.get("session_id"))
    source = event.get("source") if isinstance(event.get("source"), str) else None
    reconciliation = reconciliation_report(root, payload, workflow)
    compacted = source == "compact" or bool(workflow and workflow.get("needs_reconcile"))
    memory, tools_summary, workflow = _session_memory(root, documents, payload, workflow)
    cold_text = _cold_session_text(root, documents, workflow, event.get("session_id"))
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
            cold_packet_text=cold_text,
            source=source,
        )
    )
    return 0


def _handle_session_end(event: dict[str, object], root: Path) -> int:
    session_id = event.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        WorkflowStore(root).heartbeat(session_id, "session_end")
    emit({})
    return 0


def _handle_stop(event: dict[str, object], root: Path) -> int:
    if event.get("stop_hook_active"):
        emit({})
        return 0
    workflow = load_workflow(root)
    if workflow and workflow.get("dirty"):
        emit({
            "decision": "block",
            "reason": (
                "Before ending this turn, reconcile the active ticket, "
                "verification evidence, blockers, and exactly one next "
                "action in the registered plan/status documents. Then "
                "run the Pala state validator. Run /hooks if hook safety is unknown."
            ),
        })
    else:
        emit({})
    return 0


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
    event_name = event.get("hook_event_name")
    if event_name == "PreCompact":
        return _handle_precompact(event, root)
    if event_name == "SessionStart":
        return _handle_session_start(event, root, payload)
    if event_name == "SessionEnd":
        return _handle_session_end(event, root)
    if event_name == "Stop":
        return _handle_stop(event, root)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

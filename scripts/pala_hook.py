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
from pala_tokens import approx_tokens

MANIFEST = Path(".codex/pala-project.json")
WORKFLOW = Path(".codex/pala-workflow.json")
WORKFLOW_SCHEMA_VERSIONS = (1, 2)
# Presence + minimal cold packet for registered projects only.
PRESENCE_LINE = "Pala burada — bu oturumda yanındayım."
# Pala product char ceiling. hooks.json additionalContextLimit mirrors this
# number for self-audit sync — it is NOT the Codex host token-spill semantic
# by itself. Real clip is the approx-token budget below (host hard ~1000).
SESSION_CONTEXT_CHAR_LIMIT = 1800
# Approx-token budget under Codex hard ~1000-token additionalContext cap.
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
    cold_packet_text: str | None = None,
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
    brain = (memory or {}).get("debugging_brain") if isinstance(memory, dict) else None
    if isinstance(brain, dict) and "open" in brain:
        debug_open = int(brain.get("open") or 0)
    else:
        debug_open = 0
    gate = (memory or {}).get("debug_gate") if isinstance(memory, dict) else None
    gate_message = None
    if isinstance(gate, dict) and gate.get("message"):
        if gate.get("warn") or gate.get("do_not_retry"):
            gate_message = str(gate.get("message") or "").strip() or None
    cmd_hint = None
    if isinstance(memory, dict):
        cmd_memory = memory.get("cmd_memory")
        if isinstance(cmd_memory, dict) and cmd_memory.get("hint"):
            cmd_hint = str(cmd_memory.get("hint") or "").strip() or None
    tools = tools_summary or "tools=n/a"
    packet = (cold_packet_text or "").strip()
    if packet:
        message = (
            f"{PRESENCE_LINE} {prefix}{health_text}"
            f"kind={kind}; active={active or 'none'}; "
            f"status={status or project}; plan={plan}. "
            f"dirty={str(dirty).lower()}; blockers={blocker_count}; "
            f"reconcile={str(needs_reconcile).lower()}({reason_count}); "
            f"ticket_mismatch={str(mismatch).lower()}; debug_open={debug_open}."
        )
    else:
        message = (
            f"{PRESENCE_LINE} {prefix}{health_text}Pala project kind={kind}. "
            f"Once durum sayfasini ac: pala_report.py --open. "
            f"Memory read_order=AGENTS>CURRENT_STATUS>PROGRESS>plan>TOOLING>DEBUG>git. "
            f"Read status first: status={status or project}; "
            f"active ticket only in plan={plan}. "
            f"active={active or 'none'}; next={next_action or 'reconcile first'}; "
            f"dirty={str(dirty).lower()}; blockers={blocker_count}; "
            f"reconcile={str(needs_reconcile).lower()}({reason_count}); "
            f"ticket_mismatch={str(mismatch).lower()}; debug_open={debug_open}; {tools}. "
            "Do not re-plan completed scope. Continue authorized local work; "
            "full gate only at milestone/release; then checkpoint one ticket."
        )
    if gate_message:
        try:
            from pala_debug_gate import inject_session_gate

            message = inject_session_gate(message, gate_message, SESSION_CONTEXT_CHAR_LIMIT)
        except ImportError:
            if len(message) + len(gate_message) + 1 <= SESSION_CONTEXT_CHAR_LIMIT:
                message = f"{message} {gate_message}"
            else:
                message = (
                    message[: SESSION_CONTEXT_CHAR_LIMIT - len(gate_message) - 4]
                    + "... "
                    + gate_message
                )
    if cmd_hint and "do not retry" not in message.casefold():
        extra = cmd_hint
        if len(message) + len(extra) + 1 <= SESSION_CONTEXT_CHAR_LIMIT:
            message = f"{message} {extra}"
        else:
            message = (
                message[: SESSION_CONTEXT_CHAR_LIMIT - len(extra) - 4] + "... " + extra
            )
    if packet:
        room = SESSION_CONTEXT_CHAR_LIMIT - len(message) - 1
        if room >= 80:
            if len(packet) > room:
                packet = packet[: room - 3] + "..."
            message = f"{message}\n{packet}"
        else:
            keep_head = PRESENCE_LINE
            body_budget = max(
                120, SESSION_CONTEXT_CHAR_LIMIT - len(packet) - len(keep_head) - 8
            )
            legacy = message[len(PRESENCE_LINE) :].strip()
            if len(legacy) > body_budget:
                legacy = legacy[: body_budget - 3] + "..."
            message = f"{keep_head} {legacy}\n{packet}"
    message = _fit_session_message(message)
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
            try:
                from pala_debug_gate import evaluate_gate, session_memory_hit

                docs = documents if isinstance(documents, dict) else {}
                gate = evaluate_gate(root, docs, surface="session")
                memory["debug_gate"] = gate
                brain = memory.get("debugging_brain")
                debug_open = (
                    int(brain.get("open") or 0) if isinstance(brain, dict) else 0
                )
                debugging_read = False
                for item in memory.get("read_order") or []:
                    if isinstance(item, dict) and item.get("purpose") == "debugging":
                        debugging_read = bool(item.get("exists"))
                        break
                memory["memory_hit"] = session_memory_hit(
                    debug_open=debug_open, debugging_read=debugging_read
                )
                try:
                    from pala_cmd_memory import active_blocks, context_packet_hint

                    memory["cmd_memory"] = {
                        "blocks": active_blocks(limit=5),
                        "hint": context_packet_hint(limit=3),
                    }
                except (OSError, ValueError, TypeError, ImportError):
                    pass
            except (OSError, ValueError, TypeError, ImportError):
                pass
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
        cold_text = None
        try:
            from pala_cold_packet import session_packet_snippet, stamp_workflow_parallel

            cold_text = session_packet_snippet(
                root,
                documents=documents if isinstance(documents, dict) else None,
                workflow=workflow if isinstance(workflow, dict) else None,
                session_id=session_id if isinstance(session_id, str) else None,
                max_bytes=900,
            )
            stamp_workflow_parallel(
                root,
                session_id=session_id if isinstance(session_id, str) else None,
            )
        except (OSError, ValueError, TypeError, ImportError):
            cold_text = None
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

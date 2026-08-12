#!/usr/bin/env python3
"""Pure SessionStart context rendering for the Pala hook."""

from __future__ import annotations


def _session_facts(
    documents: dict[str, object],
    workflow: dict[str, object] | None,
    reconciliation: dict[str, object] | None,
    health: dict[str, str] | None,
    memory: dict[str, object] | None,
    project_kind: object,
) -> dict[str, object]:
    blockers = workflow.get("blockers", []) if workflow else []
    brain = (memory or {}).get("debugging_brain") if isinstance(memory, dict) else None
    coherence = (memory or {}).get("ticket_coherence") if isinstance(memory, dict) else None
    return {
        "status": documents.get("status"),
        "plan": documents.get("plan"),
        "project": documents.get("project"),
        "active": workflow.get("active_ticket") if workflow else None,
        "next_action": workflow.get("next_action") if workflow else None,
        "dirty": bool(workflow and workflow.get("dirty")),
        "blocker_count": len(blockers) if isinstance(blockers, list) else 0,
        "needs_reconcile": bool(
            (reconciliation and reconciliation.get("needed"))
            or (workflow and workflow.get("needs_reconcile"))
        ),
        "reason_count": len(reconciliation.get("reasons", [])) if reconciliation else 0,
        "kind": project_kind if isinstance(project_kind, str) else "unknown",
        "health": health or {},
        "mismatch": bool(isinstance(coherence, dict) and coherence.get("mismatch")),
        "debug_open": int(brain.get("open") or 0)
        if isinstance(brain, dict) and "open" in brain
        else 0,
    }


def _base_message(
    facts: dict[str, object],
    *,
    prefix: str,
    packet: str,
    tools_summary: str | None,
    presence: str,
) -> str:
    health = facts["health"]
    health_text = (
        "Pala local health: "
        f"plugin={health.get('plugin', 'loaded')}; "
        f"python={health.get('python', 'unknown')}; "
        f"git={health.get('git', 'unknown')}; "
        f"hook={health.get('hook', 'running')}. "
    )
    next_text = facts["next_action"] or "reconcile first"
    common = (
        f"kind={facts['kind']}; active={facts['active'] or 'none'}; next={next_text}; "
        f"status={facts['status'] or facts['project']}; plan={facts['plan']}. "
        f"dirty={str(facts['dirty']).lower()}; blockers={facts['blocker_count']}; "
        f"reconcile={str(facts['needs_reconcile']).lower()}({facts['reason_count']}); "
        f"ticket_mismatch={str(facts['mismatch']).lower()}; debug_open={facts['debug_open']}."
    )
    if packet:
        return f"{presence} {prefix}{health_text}{common}"
    tools = tools_summary or "tools=n/a"
    return (
        f"{presence} {prefix}{health_text}Pala project kind={facts['kind']}. "
        "Once durum sayfasini ac: pala_report.py --open. "
        "Memory read_order=AGENTS>CURRENT_STATUS>PROGRESS>plan>TOOLING>DEBUG>git. "
        f"Read status first: status={facts['status'] or facts['project']}; "
        f"active ticket only in plan={facts['plan']}. {common[:-1]}; {tools}. "
        "Do not re-plan completed scope. Continue authorized local work; "
        "full gate only at milestone/release; then checkpoint one ticket."
    )


def _gate_and_hint(
    message: str,
    memory: dict[str, object] | None,
    *,
    fit,
    char_limit: int,
) -> str:
    gate = (memory or {}).get("debug_gate") if isinstance(memory, dict) else None
    gate_message = None
    if isinstance(gate, dict) and gate.get("message") and (
        gate.get("warn") or gate.get("do_not_retry")
    ):
        gate_message = str(gate.get("message") or "").strip() or None
    cmd_hint = None
    if isinstance(memory, dict):
        command_memory = memory.get("cmd_memory")
        if isinstance(command_memory, dict) and command_memory.get("hint"):
            cmd_hint = str(command_memory.get("hint") or "").strip() or None
    if gate_message:
        try:
            from pala_debug_gate import inject_session_gate

            message = inject_session_gate(message, gate_message, char_limit)
        except ImportError:
            if len(message) + len(gate_message) + 1 <= char_limit:
                message = f"{message} {gate_message}"
            else:
                message = message[: char_limit - len(gate_message) - 4] + "... " + gate_message
    if cmd_hint and "do not retry" not in message.casefold():
        if len(message) + len(cmd_hint) + 1 <= char_limit:
            message = f"{message} {cmd_hint}"
        else:
            message = message[: char_limit - len(cmd_hint) - 4] + "... " + cmd_hint
    return fit(message)


def _attach_packet(message: str, packet: str, *, presence: str, char_limit: int) -> str:
    if not packet:
        return message
    room = char_limit - len(message) - 1
    if room >= 80:
        if len(packet) > room:
            packet = packet[: room - 3] + "..."
        return f"{message}\n{packet}"
    body_budget = max(120, char_limit - len(packet) - len(presence) - 8)
    legacy = message[len(presence) :].strip()
    if len(legacy) > body_budget:
        legacy = legacy[: body_budget - 3] + "..."
    return f"{presence} {legacy}\n{packet}"


def session_context(
    documents: dict[str, object],
    workflow: dict[str, object] | None,
    compacted: bool,
    *,
    operations: dict[str, object],
    project_kind: object = None,
    profiles: object = None,
    reconciliation: dict[str, object] | None = None,
    health: dict[str, str] | None = None,
    memory: dict[str, object] | None = None,
    tools_summary: str | None = None,
    cold_packet_text: str | None = None,
    source: str | None = None,
) -> dict[str, object]:
    """Render bounded SessionStart context without touching workflow state."""
    del profiles
    presence = operations["PRESENCE_LINE"]
    packet = (cold_packet_text or "").strip()
    prefix = operations["_session_restore_prefix"](source, compacted)
    facts = _session_facts(
        documents, workflow, reconciliation, health, memory, project_kind
    )
    message = _base_message(
        facts,
        prefix=prefix,
        packet=packet,
        tools_summary=tools_summary,
        presence=presence,
    )
    message = _gate_and_hint(
        message,
        memory,
        fit=operations["_fit_session_message"],
        char_limit=operations["SESSION_CONTEXT_CHAR_LIMIT"],
    )
    message = _attach_packet(
        message,
        packet,
        presence=presence,
        char_limit=operations["SESSION_CONTEXT_CHAR_LIMIT"],
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": operations["_fit_session_message"](message),
        }
    }

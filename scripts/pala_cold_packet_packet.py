#!/usr/bin/env python3
"""Cold-packet assembly owner; receives facade helpers for compatibility."""

from __future__ import annotations

from pathlib import Path


def _resolve_session_state(
    root: Path,
    *,
    profile: str,
    documents: dict[str, object] | None,
    workflow: dict[str, object] | None,
    authority: dict[str, bool] | None,
    operations: dict[str, object],
) -> dict[str, object]:
    load_workflow = operations["_load_workflow"]
    git_surface = operations["git_surface"]
    detect_stale = operations["detect_stale_context"]
    capabilities = operations["capability_manifest"]
    conflict_report = operations["detect_worktree_conflict"]
    status_snippet = operations["_status_snippet"]
    last_verified = operations["_last_verified"]

    root = root.resolve()
    workflow_data = workflow if isinstance(workflow, dict) else load_workflow(root)
    git = git_surface(root)
    stale = detect_stale(root, workflow_data, git)
    caps = capabilities(root, authority=authority, git_surface_data=git)
    parallel = (
        workflow_data.get("parallel")
        if isinstance(workflow_data.get("parallel"), dict)
        else {}
    )
    conflict = conflict_report(
        ticket=str(workflow_data.get("active_ticket") or ""),
        this_worktree=str(git.get("worktree") or root),
        other_worktree=str(parallel.get("worktree") or "") or None,
        other_branch=str(parallel.get("branch") or "") or None,
        this_branch=str(git.get("branch") or "") or None,
    )

    if stale.get("stale_context") and not stale.get("apply_state"):
        active_ticket, goal = None, None
        next_action, freshness = (
            "reconcile stale-context against Git HEAD",
            "stale-context",
        )
    else:
        active_ticket = workflow_data.get("active_ticket")
        goal = workflow_data.get("goal")
        next_action = (
            workflow_data.get("next_action")
            or status_snippet(root, documents)
            or "reconcile first"
        )
        freshness = "fresh" if workflow_data else "missing"
    if conflict.get("reconcile_required"):
        next_action, freshness = "reconcile parallel worktree conflict", "conflict"

    verified = last_verified(workflow_data)
    continue_ok = True
    status = str(verified.get("status") or "")
    if status in {"timeout", "in-progress", "unknown", "interrupted"}:
        continue_ok = False
        next_action = "verify before continue (state in-progress/unknown)"
    if git.get("freshness") == "partial":
        continue_ok = False
        next_action = "verify Git worktree state before continue"
        if freshness == "fresh":
            freshness = "partial"
    if caps.get("browser") in {"not-run", "blocked"} and "browser" in str(
        next_action
    ).casefold():
        verified = {
            **verified,
            "browser_fallback": "not-run",
            "note": "browser unavailable; do not claim passed",
        }
    return {
        "root": root,
        "workflow": workflow_data,
        "git": git,
        "stale": stale,
        "capability": caps,
        "parallel": parallel,
        "conflict": conflict,
        "active_ticket": active_ticket,
        "goal": goal,
        "next_action": next_action,
        "state_freshness": freshness,
        "last_verified": verified,
        "continue_without_verify": continue_ok,
    }


def _context_records(
    state: dict[str, object],
    *,
    profile: str,
    documents: dict[str, object] | None,
    operations: dict[str, object],
) -> tuple[list[dict[str, object]], str | None, list[dict[str, object]]]:
    do_not_retry = operations["_do_not_retry_lines"](limit=3)
    blocker = operations["_open_blocker"](state["workflow"], state["stale"])
    conflict = state["conflict"]
    if conflict.get("conflict"):
        blocker = str(conflict.get("reason") or blocker)
    records = operations["select_documents_for_profile"](
        state["root"], documents, profile
    )
    context_record = operations["context_record"]
    if blocker:
        records.append(
            context_record(
                name="open_blocker",
                scope="open_blocker",
                text=blocker,
                freshness="live",
                confidence="high",
                protected=True,
            )
        )
    verified = state["last_verified"]
    records.append(
        context_record(
            name="test_evidence",
            scope="test_evidence",
            text=f"{verified.get('name')}={verified.get('status')}",
            freshness="workflow",
            confidence="high",
            protected=True,
        )
    )
    if do_not_retry:
        records.append(
            context_record(
                name="do_not_retry",
                scope="do_not_retry",
                text="; ".join(
                    f"{item.get('failure_class')}/{item.get('command_family')}"
                    for item in do_not_retry
                ),
                freshness="sqlite",
                confidence="high",
                protected=True,
            )
        )
    caps = {"minimal": 500, "standard": 2500, "milestone": 8000}
    records = operations["apply_doc_budget"](records, max_tokens=caps[profile])
    return records, blocker, do_not_retry


def build_cold_packet(
    root: Path,
    *,
    profile: str = "minimal",
    session_id: str | None = None,
    documents: dict[str, object] | None = None,
    workflow: dict[str, object] | None = None,
    authority: dict[str, bool] | None = None,
    max_bytes: int | None = None,
    operations: dict[str, object],
) -> dict[str, object]:
    """Assemble evidence-first packet from small, independently testable steps."""
    profiles = operations["PROFILES"]
    if profile not in profiles:
        profile = "minimal"
    state = _resolve_session_state(
        root,
        profile=profile,
        documents=documents,
        workflow=workflow,
        authority=authority,
        operations=operations,
    )
    records, blocker, do_not_retry = _context_records(
        state, profile=profile, documents=documents, operations=operations
    )
    git = state["git"]
    stale = state["stale"]
    parallel = state["parallel"]
    conflict = state["conflict"]
    packet: dict[str, object] = {
        "schema": "pala.cold_packet.v1",
        "profile": profile,
        "active_ticket": state["active_ticket"],
        "goal": state["goal"],
        "branch": git.get("branch"),
        "worktree": git.get("worktree"),
        "base_commit": git.get("base_commit"),
        "last_verified": state["last_verified"],
        "critical_changed_files": (
            git.get("changed_files")
            or state["workflow"].get("changed_files")
            or []
        ),
        "open_blocker": blocker,
        "next_action": state["next_action"],
        "do_not_retry": do_not_retry,
        "state_freshness": state["state_freshness"],
        "evidence_source": (
            "source_git_test"
            if stale.get("stale_context") or git.get("base_commit")
            else ("pala_sqlite" if state["workflow"] else "markdown_handoff")
        ),
        "evidence_priority": list(operations["EVIDENCE_SOURCES"]),
        "stale_context": bool(stale.get("stale_context")),
        "apply_state": bool(stale.get("apply_state")) and not conflict.get("conflict"),
        "stale_reasons": stale.get("reasons") or [],
        "continue_without_verify": state["continue_without_verify"],
        "parallel": operations["parallel_checkpoint_fields"](
            session_id=session_id
            or (str(parallel.get("session_id") or "") or None),
            worktree=str(git.get("worktree") or state["root"]),
            branch=str(git.get("branch") or "unknown"),
            base_commit=str(git.get("base_commit") or "") or None,
            file_scope=list(git.get("changed_files") or [])[:16],
        ),
        "worktree_conflict": conflict,
        "capability": state["capability"],
        "context_records": [{key: value for key, value in item.items() if key != "text"} for item in records],
        "generated_at": operations["_utc_now"](),
    }
    text = operations["format_packet_text"](packet, max_bytes=max_bytes)
    packet["text"] = text
    packet["bytes"] = len(text.encode("utf-8"))
    packet["within_budget"] = packet["bytes"] <= (
        max_bytes or operations["MINIMAL_MAX_BYTES"]
    )
    return packet

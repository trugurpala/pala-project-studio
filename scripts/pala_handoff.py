"""Secrets-free generated handoff read-model for canonical task state."""
from __future__ import annotations
from pathlib import Path
from pala_knowledge import build_index

def make_handoff(root: Path, task: dict[str, object] | None = None) -> dict[str, object]:
    if not isinstance(task, dict):
        from pala_store import WorkflowStore
        task = WorkflowStore(root).active_task_contract() or {}
    status = str(task.get("status", "BACKLOG"))
    active = task.get("id") if status not in {"DONE", "VERIFIED", "CANCELLED"} else None
    lease = task.get("lease") if isinstance(task.get("lease"), dict) else {}
    return {
        "project": Path(root).name,
        "active_task": active,
        "status": status,
        "owner": task.get("owner"),
        "assignee": task.get("assignee"),
        "lease_status": lease.get("status"),
        "branch": task.get("branch"),
        "worktree": "redacted" if task.get("worktree") else None,
        "last_verified_sha": task.get("last_verified_sha"),
        "verification_basis": task.get("verification_basis"),
        "acceptance": task.get("acceptance", []),
        "write_scope": task.get("write_scope", []),
        "deny_scope": task.get("deny_scope", []),
        "completed": task.get("completed", []),
        "remaining": task.get("remaining", []),
        "blocker": task.get("blocker"),
        "external_conflict": task.get("external_conflict"),
        "related_decisions": task.get("architecture_refs", []),
        "latest_evidence": task.get("evidence", [])[-3:] if isinstance(task.get("evidence"), list) else [],
        "next_action": task.get("next_action"),
        "verify_with": task.get("verification_commands", []),
        "knowledge": build_index(root),
    }

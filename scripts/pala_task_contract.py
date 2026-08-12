"""Canonical, local-first task contract and evidence policy for Pala 0.9."""

from __future__ import annotations

import hashlib
from fnmatch import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

STATES = {
    "BACKLOG", "READY", "CLAIMED", "IN_PROGRESS", "REVIEW", "VERIFYING",
    "VERIFIED", "DONE", "BLOCKED", "NEEDS_DECISION", "FAILED", "CANCELLED",
    "REOPENED",
}
TRANSITIONS = {
    "BACKLOG": {"READY", "BLOCKED", "NEEDS_DECISION", "CANCELLED"},
    "READY": {"CLAIMED", "BLOCKED", "NEEDS_DECISION", "CANCELLED"},
    "CLAIMED": {"IN_PROGRESS", "BLOCKED", "FAILED", "CANCELLED"},
    "IN_PROGRESS": {"REVIEW", "BLOCKED", "FAILED", "CANCELLED"},
    "REVIEW": {"VERIFYING", "IN_PROGRESS", "BLOCKED", "FAILED", "CANCELLED"},
    "VERIFYING": {"VERIFIED", "IN_PROGRESS", "FAILED", "BLOCKED"},
    "VERIFIED": {"DONE", "IN_PROGRESS"},
    "DONE": {"REOPENED"},
    "BLOCKED": {"READY", "CLAIMED", "IN_PROGRESS", "NEEDS_DECISION", "CANCELLED"},
    "NEEDS_DECISION": {"READY", "IN_PROGRESS", "BLOCKED", "CANCELLED"},
    "FAILED": {"READY", "CLAIMED", "IN_PROGRESS", "CANCELLED"},
    "REOPENED": {"READY", "IN_PROGRESS", "CANCELLED"},
    "CANCELLED": set(),
}


def _hash_session(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def scope_violations(paths: list[str], write_scope: list[str], deny_scope: list[str]) -> list[str]:
    """Return changed paths outside the task write boundary.

    This is an authorization/verification policy, not an operating-system sandbox.
    """
    violations: list[str] = []
    for path in paths:
        normalized = str(path).replace("\\", "/")
        denied = any(fnmatch(normalized, pattern) for pattern in deny_scope)
        allowed = not write_scope or any(fnmatch(normalized, pattern) for pattern in write_scope)
        if denied or not allowed:
            violations.append(normalized)
    return sorted(set(violations), key=str.casefold)


@dataclass
class Evidence:
    kind: str
    command: str
    exit_code: int | None
    status: str
    sha: str | None = None
    surface_digest: str | None = None
    summary: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        fingerprint = hashlib.sha256(
            f"{self.kind}\n{self.command}\n{self.sha or ''}\n{self.surface_digest or ''}".encode("utf-8")
        ).hexdigest()[:24]
        return {
            "id": self.id or f"EV-{fingerprint}",
            "kind": self.kind[:80],
            "command": self.command[:240],
            "exit_code": self.exit_code,
            "status": self.status,
            "sha": self.sha,
            "surface_digest": self.surface_digest,
            "summary": self.summary[:500],
            "timestamp": self.timestamp,
        }


@dataclass
class TaskContract:
    id: str
    project_id: str
    title: str
    goal: str
    scope: list[str] = field(default_factory=list)
    out_of_scope: list[str] = field(default_factory=list)
    acceptance: list[Any] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    architecture_refs: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    status: str = "BACKLOG"
    owner: str | None = None
    session_key: str | None = None
    branch: str | None = None
    worktree: str | None = None
    last_verified_sha: str | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    blocker: str | None = None
    next_action: str | None = None
    assignee: dict[str, Any] | None = None
    lease: dict[str, Any] = field(default_factory=dict)
    write_scope: list[str] = field(default_factory=list)
    deny_scope: list[str] = field(default_factory=list)
    verification_policy: dict[str, Any] = field(default_factory=dict)
    verification_basis: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    retry_policy: dict[str, Any] = field(default_factory=lambda: {"verification_budget": 2, "repeated_failure_action": "BLOCKED"})
    external_conflict: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.project_id.strip() or not self.title.strip() or not self.goal.strip():
            raise ValueError("task id, project_id, title, and goal are required")
        if self.status not in STATES:
            raise ValueError(f"unsupported task state: {self.status}")
        if self.owner and not self.assignee:
            self.assignee = {"type": "agent", "id": self.owner}
        self.acceptance = list(self.acceptance or [])
        self.evidence = list(self.evidence or [])[-16:]

    def transition(self, target: str) -> None:
        if target not in STATES or target not in TRANSITIONS[self.status]:
            raise ValueError(f"invalid task transition: {self.status} -> {target}")
        self.status = target

    def claim(self, owner: str, session_key: str, *, worktree_id: str | None = None) -> None:
        if not owner.strip() or not session_key.strip():
            raise ValueError("owner and session_key are required")
        session_hash = _hash_session(session_key)
        current_hash = self.lease.get("session_key_hash") if isinstance(self.lease, dict) else None
        if self.owner not in (None, owner) or current_hash not in (None, session_hash):
            raise ValueError("task is owned by another session")
        if self.status == "BACKLOG":
            self.transition("READY")
        if self.status in {"READY", "BLOCKED", "FAILED", "REOPENED"}:
            if self.status in {"BLOCKED", "FAILED", "REOPENED"}:
                self.status = "READY"
            self.transition("CLAIMED")
        now = datetime.now(timezone.utc).isoformat()
        generation = int(self.lease.get("generation", 0)) + 1 if isinstance(self.lease, dict) else 1
        self.owner = owner[:120]
        self.session_key = session_hash
        self.assignee = self.assignee or {"type": "agent", "id": owner[:120]}
        self.lease = {
            "status": "claimed",
            "holder_type": "agent_session",
            "session_key_hash": session_hash,
            "claimed_at": now,
            "heartbeat_at": now,
            "worktree_id": (worktree_id or self.worktree or "local")[:120],
            "generation": generation,
        }

    def acceptance_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for index, item in enumerate(self.acceptance):
            if isinstance(item, dict):
                normalized = dict(item)
                normalized.setdefault("id", f"AC-{index + 1:02d}")
                normalized.setdefault("text", "")
                normalized.setdefault("status", "not-run")
                normalized.setdefault("evidence_refs", [])
                items.append(normalized)
            else:
                # v3 string criteria remain compatible; they are satisfied by a passed gate.
                items.append({"id": f"AC-{index + 1:02d}", "text": str(item), "status": "legacy", "evidence_refs": []})
        return items

    def record_evidence(self, evidence: Evidence) -> str:
        item = evidence.to_dict()
        evidence_id = str(item["id"])
        self.evidence.append(item)
        self.evidence = self.evidence[-16:]
        if evidence_id not in self.evidence_refs:
            self.evidence_refs.append(evidence_id)
        if evidence.status == "passed" and self.status == "VERIFYING":
            self.transition("VERIFIED")
        return evidence_id

    def set_verification_basis(self, head_sha: str | None, index_digest: str | None, worktree_digest: str | None, surface_digest: str | None) -> None:
        self.verification_basis = {
            "head_sha": head_sha,
            "index_digest": index_digest,
            "worktree_digest": worktree_digest,
            "surface_digest": surface_digest,
        }
        self.last_verified_sha = head_sha

    def acceptance_passed(self) -> tuple[bool, str]:
        items = self.acceptance_items()
        if not items:
            return False, "acceptance criteria are required"
        structured = [item for item in items if item["status"] != "legacy"]
        if structured:
            failed = [item["id"] for item in structured if item.get("status") != "passed"]
            if failed:
                return False, "acceptance criteria not passed: " + ", ".join(failed)
            known = {str(item.get("id")) for item in self.evidence}
            missing_refs = [item["id"] for item in structured if not set(map(str, item.get("evidence_refs") or [])) & known]
            if missing_refs:
                return False, "acceptance evidence references missing: " + ", ".join(missing_refs)
        return True, "acceptance passed"

    def can_complete(self) -> tuple[bool, str]:
        if self.blocker or self.status != "VERIFIED":
            return False, "task must be VERIFIED with no blocker"
        accepted, reason = self.acceptance_passed()
        if not accepted:
            return False, reason
        passed = [item for item in self.evidence if item.get("status") == "passed" and item.get("exit_code", 0) == 0]
        if not passed:
            return False, "passed verification evidence is required"
        if any(item.get("status") in {"failed", "timeout", "blocked", "not-run"} for item in self.evidence):
            return False, "failed or incomplete verification evidence exists"
        return True, "ready"

    def complete(self) -> None:
        allowed, reason = self.can_complete()
        if not allowed:
            raise ValueError(reason)
        self.transition("DONE")
        self.owner = None
        self.session_key = None
        if isinstance(self.lease, dict):
            self.lease["status"] = "released"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 4,
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "goal": self.goal,
            "scope": self.scope,
            "out_of_scope": self.out_of_scope,
            "acceptance": self.acceptance,
            "dependencies": self.dependencies,
            "architecture_refs": self.architecture_refs,
            "verification_commands": self.verification_commands,
            "status": self.status,
            "owner": self.owner,
            "assignee": self.assignee,
            "session_key_hash": self.session_key,
            "lease": self.lease,
            "branch": self.branch,
            "worktree": self.worktree,
            "last_verified_sha": self.last_verified_sha,
            "verification_basis": self.verification_basis,
            "evidence": self.evidence,
            "evidence_refs": self.evidence_refs,
            "blocker": self.blocker,
            "next_action": self.next_action,
            "write_scope": self.write_scope,
            "deny_scope": self.deny_scope,
            "verification_policy": self.verification_policy,
            "retry_policy": self.retry_policy,
            "external_conflict": self.external_conflict,
            "allowed_states": sorted(STATES),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TaskContract":
        lifecycle = str(payload.get("status") or payload.get("lifecycle") or "BACKLOG").upper()
        lifecycle = {"ACTIVE": "IN_PROGRESS", "CHECKPOINTED": "VERIFIED", "COMPLETED": "DONE"}.get(lifecycle, lifecycle)
        lease = dict(payload.get("lease") or {})
        session_hash = payload.get("session_key_hash") or payload.get("session_key") or lease.get("session_key_hash")
        return cls(
            id=str(payload.get("id") or payload.get("ticket") or ""),
            project_id=str(payload.get("project_id") or "local"),
            title=str(payload.get("title") or payload.get("ticket") or "task"),
            goal=str(payload.get("goal") or "continue task"),
            scope=list(payload.get("scope") or []), out_of_scope=list(payload.get("out_of_scope") or []),
            acceptance=list(payload.get("acceptance") or []), dependencies=list(payload.get("dependencies") or []),
            architecture_refs=list(payload.get("architecture_refs") or []), verification_commands=list(payload.get("verification_commands") or []),
            status=lifecycle, owner=payload.get("owner"), session_key=session_hash, branch=payload.get("branch"), worktree=payload.get("worktree"),
            last_verified_sha=payload.get("last_verified_sha"), evidence=list(payload.get("evidence") or payload.get("verification") or []),
            blocker=(payload.get("blocker") or (payload.get("blockers") or [None])[0]), next_action=payload.get("next_action"),
            assignee=dict(payload.get("assignee") or {}) or None, lease=lease, write_scope=list(payload.get("write_scope") or []),
            deny_scope=list(payload.get("deny_scope") or []), verification_policy=dict(payload.get("verification_policy") or {}),
            verification_basis=dict(payload.get("verification_basis") or {}), evidence_refs=list(payload.get("evidence_refs") or []),
            retry_policy=dict(payload.get("retry_policy") or {"verification_budget": 2, "repeated_failure_action": "BLOCKED"}),
            external_conflict=dict(payload.get("external_conflict") or {}) or None,
        )

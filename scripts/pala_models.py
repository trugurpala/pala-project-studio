"""Bounded, serializable records for Pala v3 ticket state."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

SESSION_KEY_LENGTH = 24
VERIFICATION_STATUSES = {"passed", "failed", "timeout", "blocked", "not-run"}


@dataclass(frozen=True)
class RepoIdentity:
    """Privacy-safe identity shared by every checkout of one repository."""

    common_dir_digest: str


@dataclass(frozen=True)
class WorktreeIdentity:
    """Runtime identity for one checkout; only digests are safe to persist."""

    root: str
    git_dir_digest: str
    branch: str | None
    head: str | None


@dataclass(frozen=True)
class ReconciliationFinding:
    code: str
    severity: str
    source: str
    expected: str | None
    observed: str | None
    action: str

    def to_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "severity": self.severity,
            "source": self.source,
            "expected": self.expected,
            "observed": self.observed,
            "action": self.action,
        }


@dataclass(frozen=True)
class TicketView:
    ticket: str
    goal: str
    lifecycle: str
    dirty: bool
    owner: str | None
    worktree_git_dir_digest: str | None
    next_action: str | None
    verification_tier: str
    blockers: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "ticket": self.ticket,
            "goal": self.goal,
            "lifecycle": self.lifecycle,
            "dirty": self.dirty,
            "owner": self.owner,
            "worktree_git_dir_digest": self.worktree_git_dir_digest,
            "next_action": self.next_action,
            "verification_tier": self.verification_tier,
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class ProjectSnapshot:
    schema_version: int
    repo: RepoIdentity | None
    worktrees: tuple[WorktreeIdentity, ...]
    selected_worktree: WorktreeIdentity | None
    active_ticket: TicketView | None
    documents: tuple[tuple[str, str], ...]
    findings: tuple[ReconciliationFinding, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "repo": (
                {"common_dir_digest": self.repo.common_dir_digest}
                if self.repo
                else None
            ),
            "worktrees": [
                {
                    "root": item.root,
                    "git_dir_digest": item.git_dir_digest,
                    "branch": item.branch,
                    "head": item.head,
                }
                for item in self.worktrees
            ],
            "selected_worktree": (
                {
                    "root": self.selected_worktree.root,
                    "git_dir_digest": self.selected_worktree.git_dir_digest,
                    "branch": self.selected_worktree.branch,
                    "head": self.selected_worktree.head,
                }
                if self.selected_worktree
                else None
            ),
            "active_ticket": self.active_ticket.to_dict() if self.active_ticket else None,
            "documents": dict(self.documents),
            "findings": [item.to_dict() for item in self.findings],
        }


class SessionKey:
    @staticmethod
    def from_session_id(value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("session id must be non-empty")
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:SESSION_KEY_LENGTH]


def _bounded(value: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("text must be non-empty")
    return value.strip()[:limit]


@dataclass(frozen=True)
class TicketRecord:
    ticket: str
    goal: str
    lifecycle: str
    owner: str | None
    dirty: bool
    next_action: str | None
    verification: tuple[dict[str, str], ...]
    blockers: tuple[str, ...]
    checkpoint_basis: str | None
    updated_at: str

    @classmethod
    def new(cls, ticket: str, goal: str, session_id: str) -> "TicketRecord":
        return cls(
            ticket=_bounded(ticket, 120),
            goal=_bounded(goal, 500),
            lifecycle="active",
            owner=SessionKey.from_session_id(session_id),
            dirty=True,
            next_action=None,
            verification=(),
            blockers=(),
            checkpoint_basis=None,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 3,
            "ticket": self.ticket,
            "goal": self.goal,
            "lifecycle": self.lifecycle,
            "owner": self.owner,
            "dirty": self.dirty,
            "next_action": self.next_action,
            "verification": list(self.verification),
            "blockers": list(self.blockers),
            "checkpoint_basis": self.checkpoint_basis,
            "updated_at": self.updated_at,
        }

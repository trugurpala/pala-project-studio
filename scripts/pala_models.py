"""Bounded, serializable records for Pala v3 ticket state."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

SESSION_KEY_LENGTH = 24
VERIFICATION_STATUSES = {
    "passed",
    "failed",
    "timeout",
    "blocked",
    "not-run",
    "configured-not-verified",
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

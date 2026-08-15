#!/usr/bin/env python3
"""Downward-only assembly of bounded project continuity context.

This module deliberately has no dependency on state, reports, cold packets,
WorkflowStore, or Quality.  Those authority-owning surfaces may supply inputs
and consume its read models, but cannot be reached from here.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pala_context_receipt import ContextExpectation, ContextReceipt
from pala_project_history import (
    get_continuity,
    list_history,
    persist_context_summary,
    record_closure,
    record_reopen,
)
from pala_project_profile import ProjectProfile
from pala_project_snapshot import ProjectSnapshot, capture_project_snapshot
from pala_task_contract import TaskContract


class ContinuityError(ValueError):
    """Sanitized, stable failure at the integration boundary."""

    def __init__(self, code: str, field: str) -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code} at {field}")


@dataclass(frozen=True, slots=True)
class ContinuityContext:
    """Validated ephemeral context; callers choose whether to persist it."""

    snapshot: ProjectSnapshot
    profile: ProjectProfile
    expectation: ContextExpectation
    receipt: ContextReceipt

    def receipt_read_model(self) -> dict[str, object]:
        """Return the bounded receipt projection without creating state."""
        from pala_context_receipt import receipt_summary

        return receipt_summary(self.receipt, expected=self.expectation)


def _canonical_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _active_task_binding(task_contract: object) -> tuple[dict[str, object], dict[str, object]]:
    if not isinstance(task_contract, dict):
        raise ContinuityError("CONTINUITY_TASK_INVALID", "task_contract")
    try:
        contract = TaskContract.from_dict(dict(task_contract))
    except (TypeError, ValueError) as exc:
        raise ContinuityError("CONTINUITY_TASK_INVALID", "task_contract") from exc
    canonical = contract.to_dict()
    return canonical, {
        "ticket": contract.id,
        "status": contract.status,
        "contract_digest": _canonical_digest(canonical),
    }


def _require_observable_snapshot(snapshot: ProjectSnapshot) -> None:
    if snapshot.head_state == "unavailable" or snapshot.git_state == "unknown":
        raise ContinuityError("CONTINUITY_SNAPSHOT_UNAVAILABLE", "snapshot")
    if any(finding.severity == "blocking" for finding in snapshot.findings):
        raise ContinuityError("CONTINUITY_SNAPSHOT_UNAVAILABLE", "snapshot")


def build_context(
    root: Path,
    *,
    profile_payload: object,
    task_contract: object,
    source_refs: list[object] | tuple[object, ...],
    capabilities: list[object] | tuple[object, ...],
    verifications: list[object] | tuple[object, ...],
    risk_codes: list[object] | tuple[object, ...],
    next_action: str,
) -> ContinuityContext:
    """Build one receipt from live observation without persistence or markers."""
    snapshot = capture_project_snapshot(Path(root))
    _require_observable_snapshot(snapshot)
    try:
        profile = ProjectProfile.from_dict(profile_payload)
    except (TypeError, ValueError) as exc:
        raise ContinuityError("CONTINUITY_PROFILE_INVALID", "profile") from exc
    _canonical, active_task = _active_task_binding(task_contract)
    profile_digest = profile.digest()
    try:
        expectation = ContextExpectation.create(
            snapshot=snapshot,
            active_task=active_task,
            profile_digest=profile_digest,
            source_refs=source_refs,
        )
        receipt = ContextReceipt.create(
            snapshot=snapshot,
            active_task=active_task,
            profile_digest=profile_digest,
            source_refs=source_refs,
            capabilities=capabilities,
            verifications=verifications,
            risk_codes=risk_codes,
            next_action=next_action,
        )
        ContextReceipt.from_dict(receipt.to_dict(), expected=expectation)
    except (TypeError, ValueError) as exc:
        raise ContinuityError("CONTINUITY_RECEIPT_INVALID", "receipt") from exc
    return ContinuityContext(snapshot, profile, expectation, receipt)


def persist_context(context: ContinuityContext, *, db_path: Path) -> dict[str, object]:
    """Persist only History's validated scalar continuity summary."""
    if not isinstance(context, ContinuityContext):
        raise ContinuityError("CONTINUITY_CONTEXT_INVALID", "context")
    try:
        return persist_context_summary(
            context.profile.to_dict(),
            context.receipt,
            expected=context.expectation,
            path=Path(db_path),
        )
    except (TypeError, ValueError) as exc:
        raise ContinuityError("CONTINUITY_PERSIST_FAILED", "context") from exc


def read_models(
    *,
    project_id: str,
    repository_id: str,
    db_path: Path,
    history_limit: int = 50,
) -> dict[str, dict[str, object]]:
    """Read bounded continuity/history projections without opening a new store."""
    path = Path(db_path)
    continuity = get_continuity(project_id, path=path)
    history = list_history(
        repository_id=repository_id,
        limit=history_limit,
        path=path,
    )
    return {"continuity": continuity, "history": history}


def close_context(
    context: ContinuityContext,
    *,
    summary: str,
    final_commit: str,
    release_ref: str | None,
    risk_codes: list[object] | tuple[object, ...],
    lessons: list[object] | tuple[object, ...],
    authority_ref: str,
    db_path: Path,
) -> dict[str, object]:
    """Explicitly close a project against its current validated receipt."""
    persist_context(context, db_path=db_path)
    try:
        return record_closure(
            context.profile.project_id,
            current_receipt_id=context.receipt.receipt_id,
            summary=summary,
            final_commit=final_commit,
            release_ref=release_ref,
            risk_codes=risk_codes,
            lessons=lessons,
            authority_ref=authority_ref,
            path=Path(db_path),
        )
    except (TypeError, ValueError) as exc:
        raise ContinuityError("CONTINUITY_CLOSE_FAILED", "context") from exc


def reopen_context(
    context: ContinuityContext,
    *,
    closure_id: str,
    authority_ref: str,
    db_path: Path,
) -> dict[str, object]:
    """Explicitly reopen a closure with fresh live context."""
    try:
        return record_reopen(
            context.profile.project_id,
            closure_id=closure_id,
            profile_payload=context.profile.to_dict(),
            receipt_payload=context.receipt,
            expected=context.expectation,
            authority_ref=authority_ref,
            path=Path(db_path),
        )
    except (TypeError, ValueError) as exc:
        raise ContinuityError("CONTINUITY_REOPEN_FAILED", "context") from exc


__all__ = [
    "ContinuityContext",
    "ContinuityError",
    "build_context",
    "close_context",
    "persist_context",
    "read_models",
    "reopen_context",
]

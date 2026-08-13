#!/usr/bin/env python3
"""Canonical milestone read model; historical artifacts are never authority."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class TicketReader(Protocol):
    def ticket_record(self, ticket: str) -> dict[str, object] | None: ...


def canonical_milestone(
    root: Path, ticket: str, *, store: TicketReader | None = None
) -> dict[str, object]:
    if store is None:
        from pala_store import WorkflowStore

        store = WorkflowStore(root)
    record = store.ticket_record(ticket)
    if not isinstance(record, dict):
        return {
            "ticket": ticket, "status": "not-run", "task_status": "BACKLOG",
            "workflow_lifecycle": "missing", "acceptance_status": "not-run",
            "authority": "WorkflowStore/TaskContract",
        }
    contract = record.get("task_contract")
    contract = contract if isinstance(contract, dict) else {}
    acceptance = contract.get("acceptance")
    items = acceptance if isinstance(acceptance, list) else []
    acceptance_passed = bool(items) and all(
        isinstance(item, dict) and item.get("status") == "passed" for item in items
    )
    task_status = str(contract.get("status") or "BACKLOG")
    lifecycle = str(record.get("lifecycle") or "unknown")
    complete = task_status == "DONE" and lifecycle == "completed" and acceptance_passed
    return {
        "ticket": ticket, "status": "passed" if complete else "blocked",
        "task_status": task_status, "workflow_lifecycle": lifecycle,
        "acceptance_status": "passed" if acceptance_passed else "not-run",
        "authority": "WorkflowStore/TaskContract",
    }


def current_milestones(
    root: Path, *, store: TicketReader | None = None
) -> dict[str, dict[str, object]]:
    return {"M70-T3": canonical_milestone(root, "M70-T3", store=store)}

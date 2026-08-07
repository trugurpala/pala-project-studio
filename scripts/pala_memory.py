#!/usr/bin/env python3
"""Project Memory Contract: forced read order, coherence, stubs."""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

MEMORY_CONTRACT_VERSION = 1

# Purpose slots in forced bootstrap order (git is synthetic, not a document purpose).
MEMORY_READ_ORDER = (
    "instructions",
    "status",
    "progress",
    "plan",
    "tooling",
    "debugging",
    "git",
)

STUB_BODIES = {
    "status": (
        "# Current status\n\n"
        "- Active ticket: none\n"
        "- Last checkpoint: none\n"
        "- Next action: discover and register\n"
        "- Blockers: none\n"
        f"- Updated: {datetime.now(timezone.utc).date().isoformat()}\n"
    ),
    "progress": (
        "# Progress\n\n"
        "Milestone log. Append completed outcomes with evidence labels "
        "(passed | not-run | blocked | configured-not-verified).\n"
    ),
    "tooling": (
        "# Tooling decisions\n\n"
        "| Tool | Status | Evidence | Notes |\n"
        "| --- | --- | --- | --- |\n"
        "| (none yet) | not_installed | | |\n\n"
        "Statuses: installed | recommended | installed_unverified | "
        "not_installed | unavailable\n"
    ),
    "debugging": (
        "# Debugging log\n\n"
        "Record root cause, fix criteria, and verification status. "
        "Do not claim fixed without evidence.\n"
    ),
}

DEFAULT_STUB_PATHS = {
    "status": "reports/CURRENT_STATUS.md",
    "progress": "PROGRESS.md",
    "tooling": "TOOLING_DECISIONS.md",
    "debugging": "DEBUGGING.md",
}

TICKET_RE = re.compile(r"\b([A-Z]{1,8}\d*-T\d+|[A-Z]{2,12}-\d+|F\d+-T\d+)\b")
NEXT_LINE_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:next(?:\s+action)?|sonraki(?:\s+i[sş]e?)?)\s*[:\-]\s*(.+)$"
)


def git_status_summary(root: Path) -> dict[str, object]:
    """Short, secrets-free git snapshot for context (not checkpoint hashes)."""
    try:
        branch = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False, "branch": None, "dirty_count": 0, "preview": ""}
    if branch.returncode != 0:
        return {"available": False, "branch": None, "dirty_count": 0, "preview": ""}
    lines = [line for line in branch.stdout.splitlines() if line.strip()]
    head = lines[0] if lines else ""
    dirty = [line for line in lines[1:] if line.strip()]
    preview = head[:120]
    return {
        "available": True,
        "branch": head[:160],
        "dirty_count": len(dirty),
        "preview": preview,
    }


def resolve_read_order(
    root: Path, documents: dict[str, object] | None
) -> list[dict[str, object]]:
    docs = documents if isinstance(documents, dict) else {}
    ordered: list[dict[str, object]] = []
    for purpose in MEMORY_READ_ORDER:
        if purpose == "git":
            git = git_status_summary(root)
            ordered.append(
                {
                    "purpose": "git",
                    "path": None,
                    "exists": bool(git.get("available")),
                    "detail": git,
                }
            )
            continue
        raw = docs.get(purpose)
        path = raw if isinstance(raw, str) and raw.strip() else None
        exists = bool(path and (root / path).is_file())
        ordered.append(
            {
                "purpose": purpose,
                "path": path,
                "exists": exists,
                "detail": None,
            }
        )
    return ordered


def ensure_memory_stubs(root: Path, documents: dict[str, str | None]) -> dict[str, str]:
    """Create missing contract stubs; return updated document map."""
    updated = dict(documents)
    for purpose, rel in DEFAULT_STUB_PATHS.items():
        current = updated.get(purpose)
        if isinstance(current, str) and current.strip() and (root / current).is_file():
            continue
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file():
            body = STUB_BODIES[purpose]
            target.write_text(body, encoding="utf-8", newline="\n")
        updated[purpose] = rel.replace("\\", "/")
    return updated


def _infer_next_from_text(text: str) -> str | None:
    match = NEXT_LINE_RE.search(text or "")
    if match:
        return match.group(1).strip()[:200]
    return None


def _ticket_tokens(text: str) -> set[str]:
    return {m.group(1) for m in TICKET_RE.finditer(text or "")}


def ticket_coherence_report(
    workflow: dict[str, object] | None,
    status_text: str = "",
    plan_text: str = "",
) -> dict[str, object]:
    """Compare active ticket with next-action / status wording."""
    workflow = workflow or {}
    active = workflow.get("active_ticket")
    active_s = active.strip() if isinstance(active, str) else ""
    next_action = workflow.get("next_action")
    next_s = next_action.strip() if isinstance(next_action, str) else ""
    inferred = _infer_next_from_text(status_text) or ""
    combined_next = " ".join(part for part in (next_s, inferred) if part)
    next_tickets = _ticket_tokens(combined_next) | _ticket_tokens(plan_text[:2000])
    mismatch = False
    note = "ok"
    if active_s and next_tickets and active_s not in next_tickets:
        # Next work names a different ticket id than active.
        if any(token != active_s for token in next_tickets):
            mismatch = True
            note = (
                f"active={active_s} but next/status references "
                f"{', '.join(sorted(next_tickets))}"
            )
    elif active_s and inferred and active_s not in inferred and TICKET_RE.search(inferred):
        other = _ticket_tokens(inferred)
        if other and active_s not in other:
            mismatch = True
            note = f"active={active_s} but status next is {inferred[:120]}"
    return {
        "ok": not mismatch,
        "active": active_s or None,
        "inferred_next": inferred or next_s or None,
        "mismatch": mismatch,
        "note": note,
    }


def append_status_mismatch(status_path: Path, report: dict[str, object]) -> None:
    if not report.get("mismatch"):
        return
    stamp = datetime.now(timezone.utc).isoformat()
    block = (
        f"\n## Memory mismatch\n\n"
        f"- Detected: {stamp}\n"
        f"- Detail: {report.get('note')}\n"
        f"- Action: reconcile active ticket with next work before claiming progress.\n"
    )
    existing = status_path.read_text(encoding="utf-8") if status_path.is_file() else ""
    if "## Memory mismatch" in existing and str(report.get("note")) in existing:
        return
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(existing.rstrip() + "\n" + block, encoding="utf-8", newline="\n")


def contract_context(
    root: Path,
    documents: dict[str, object] | None,
    workflow: dict[str, object] | None = None,
) -> dict[str, object]:
    docs = documents if isinstance(documents, dict) else {}
    status_rel = docs.get("status") if isinstance(docs.get("status"), str) else None
    plan_rel = docs.get("plan") if isinstance(docs.get("plan"), str) else None
    status_text = ""
    plan_text = ""
    if status_rel and (root / status_rel).is_file():
        status_text = (root / status_rel).read_text(encoding="utf-8")
    if plan_rel and (root / plan_rel).is_file():
        plan_text = (root / plan_rel).read_text(encoding="utf-8")
    coherence = ticket_coherence_report(workflow, status_text, plan_text)
    return {
        "memory_contract_version": MEMORY_CONTRACT_VERSION,
        "read_order": resolve_read_order(root, docs),
        "ticket_coherence": coherence,
        "git": git_status_summary(root),
        "evidence_policy_version": 1,
    }

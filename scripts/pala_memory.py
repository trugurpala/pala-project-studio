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
        "Durable error brain for this project. Read before repeating a known failure.\n"
        "No secrets, tokens, transcripts, or real user plugin data.\n\n"
        "## Format\n\n"
        "Each incident uses heading `### INC-YYYYMMDD-slug` and these fields:\n"
        "Symptoms, Root cause, Fix criteria, Proved by, Related files, Date, Status.\n"
        "Status may be `open`, `fixed`, or `wontfix`; fixed requires evidence labels "
        "(passed | not-run | blocked | configured-not-verified), not soft done/ok.\n\n"
        "## Incidents\n\n"
        "(none yet)\n"
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

DEBUGGING_REQUIRED_FIELDS = (
    "Symptoms",
    "Root cause",
    "Fix criteria",
    "Proved by",
    "Related files",
    "Date",
    "Status",
)
INCIDENT_HEADING_RE = re.compile(r"(?m)^###\s+(INC-[A-Za-z0-9][\w.-]*)\s*$")
INCIDENT_FIELD_RE = re.compile(
    r"(?im)^\s*[-*]\s*\*\*("
    + "|".join(re.escape(name) for name in DEBUGGING_REQUIRED_FIELDS)
    + r"):\*\*\s*(.*)$"
)

AGENT_TASK_HEADING_RE = re.compile(
    r"(?m)^#{4}\s+(M\d+-T\d+)\s*[—–-]\s*(.+?)\s*$"
)
AGENT_TASK_FIELD_LABELS = (
    "Sahip ajan",
    "Amaç",
    "Dosyalar",
    "Bitti sayılır",
    "Bağımlılık",
    "Kanıt",
)
AGENT_TASK_FIELD_RE = re.compile(
    r"(?im)^\s*[-*]\s*\*\*("
    + "|".join(re.escape(name) for name in AGENT_TASK_FIELD_LABELS)
    + r"):\*\*\s*(.*)$"
)
VALID_EVIDENCE_LABELS = frozenset(
    {
        "passed",
        "not-run",
        "blocked",
        "configured-not-verified",
        "failed",
        "timeout",
    }
)


def parse_debugging_brain(text: str) -> dict[str, object]:
    """Fail-closed parse of DEBUGGING.md Format + INC-* incident entries."""
    body = text or ""
    format_match = re.search(r"(?im)^##\s+Format\s*$", body)
    if not format_match:
        return {
            "ok": False,
            "detail": "missing ## Format section",
            "incidents": [],
        }
    next_heading = re.search(r"(?m)^##\s+\S+", body[format_match.end() :])
    format_end = (
        format_match.end() + next_heading.start()
        if next_heading
        else len(body)
    )
    format_block = body[format_match.start() : format_end]
    missing_labels = [
        name
        for name in DEBUGGING_REQUIRED_FIELDS
        if name.casefold() not in format_block.casefold()
    ]
    if missing_labels:
        return {
            "ok": False,
            "detail": "Format missing field labels: " + ", ".join(missing_labels),
            "incidents": [],
        }

    headings = list(INCIDENT_HEADING_RE.finditer(body))
    incidents: list[dict[str, object]] = []
    for index, match in enumerate(headings):
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        chunk = body[start:end]
        fields: dict[str, str] = {}
        for field_match in INCIDENT_FIELD_RE.finditer(chunk):
            key = field_match.group(1)
            # Preserve canonical casing from DEBUGGING_REQUIRED_FIELDS.
            canonical = next(
                name for name in DEBUGGING_REQUIRED_FIELDS if name.casefold() == key.casefold()
            )
            fields[canonical] = field_match.group(2).strip()
        missing = [name for name in DEBUGGING_REQUIRED_FIELDS if not fields.get(name)]
        if missing:
            return {
                "ok": False,
                "detail": f"{match.group(1)} missing fields: {', '.join(missing)}",
                "incidents": incidents,
            }
        incidents.append({"id": match.group(1), "fields": fields})
    return {"ok": True, "detail": "ok", "incidents": incidents}


def _normalize_evidence(raw: str) -> str:
    value = (raw or "").strip().strip("`").strip()
    if not value:
        return "not-run"
    lowered = value.casefold()
    if lowered in VALID_EVIDENCE_LABELS:
        return lowered
    for label in sorted(VALID_EVIDENCE_LABELS, key=len, reverse=True):
        if label in lowered:
            return label
    return lowered


def parse_agent_task_cards(text: str) -> dict[str, object]:
    """Parse PLAN.md M*-T* agent task cards (Sahip ajan + Amaç required)."""
    body = text or ""
    headings = list(AGENT_TASK_HEADING_RE.finditer(body))
    if not headings:
        return {"ok": True, "detail": "no cards", "cards": []}

    cards: list[dict[str, str]] = []
    for index, match in enumerate(headings):
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        chunk = body[start:end]
        fields: dict[str, str] = {}
        for field_match in AGENT_TASK_FIELD_RE.finditer(chunk):
            key = field_match.group(1)
            canonical = next(
                name
                for name in AGENT_TASK_FIELD_LABELS
                if name.casefold() == key.casefold()
            )
            fields[canonical] = field_match.group(2).strip()
        card_id = match.group(1)
        title = match.group(2).strip()
        owner = fields.get("Sahip ajan", "").strip()
        goal = fields.get("Amaç", "").strip()
        if not owner or not goal:
            missing = []
            if not owner:
                missing.append("Sahip ajan")
            if not goal:
                missing.append("Amaç")
            return {
                "ok": False,
                "detail": f"{card_id} missing fields: {', '.join(missing)}",
                "cards": cards,
            }
        cards.append(
            {
                "id": card_id,
                "title": title,
                "owner": owner,
                "goal": goal,
                "files": fields.get("Dosyalar", ""),
                "done_when": fields.get("Bitti sayılır", ""),
                "depends": fields.get("Bağımlılık", ""),
                "evidence": _normalize_evidence(fields.get("Kanıt", "")),
            }
        )
    return {"ok": True, "detail": "ok", "cards": cards}


def debugging_brain_summary(
    root: Path,
    documents: dict[str, object] | None = None,
) -> dict[str, object]:
    """Count open vs closed INC entries for SessionStart / Status surfaces."""
    docs = documents if isinstance(documents, dict) else {}
    rel = docs.get("debugging")
    if isinstance(rel, str) and rel.strip():
        path = root / rel
    else:
        path = root / DEFAULT_STUB_PATHS["debugging"]
    if not path.is_file():
        return {
            "ok": False,
            "detail": "DEBUGGING.md missing",
            "path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
            "open": 0,
            "fixed": 0,
            "total": 0,
        }
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "ok": False,
            "detail": str(exc),
            "path": str(path),
            "open": 0,
            "fixed": 0,
            "total": 0,
        }
    parsed = parse_debugging_brain(text)
    if not parsed.get("ok"):
        return {
            "ok": False,
            "detail": str(parsed.get("detail") or "parse failed"),
            "path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
            "open": 0,
            "fixed": 0,
            "total": 0,
        }
    open_count = 0
    fixed_count = 0
    for entry in parsed.get("incidents") or []:
        if not isinstance(entry, dict):
            continue
        fields = entry.get("fields")
        if not isinstance(fields, dict):
            continue
        status = str(fields.get("Status") or "").strip().casefold()
        if status.startswith("open"):
            open_count += 1
        elif status.startswith("fixed") or status.startswith("wontfix"):
            fixed_count += 1
    total = len(parsed.get("incidents") or [])
    try:
        rel_path = str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        rel_path = str(path)
    return {
        "ok": True,
        "detail": "ok",
        "path": rel_path,
        "open": open_count,
        "fixed": fixed_count,
        "total": total,
    }


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
        "debugging_brain": debugging_brain_summary(root, docs),
        "git": git_status_summary(root),
        "evidence_policy_version": 1,
    }


_PURPOSE_LABELS = {
    "instructions": "AGENTS / talimat",
    "status": "güncel durum",
    "progress": "ilerleme",
    "plan": "plan",
    "tooling": "araç kararları",
    "debugging": "debug günlüğü",
    "git": "git durumu",
}


def plain_memory_report(
    root: Path,
    *,
    documents: dict[str, object] | None = None,
    workflow: dict[str, object] | None = None,
    tool_counts: dict[str, object] | None = None,
) -> str:
    """Human-readable memory snapshot for vibe / owner use (not JSON)."""
    memory = contract_context(root, documents, workflow)
    coherence = memory.get("ticket_coherence")
    if not isinstance(coherence, dict):
        coherence = {}
    git = memory.get("git")
    if not isinstance(git, dict):
        git = {}
    lines = [
        "Pala hafıza durumu",
        "==================",
        f"Kök: {root}",
        f"Aktif ticket: {coherence.get('active') or 'yok'}",
        f"Sonraki iş: {coherence.get('inferred_next') or 'yok'}",
    ]
    if coherence.get("mismatch"):
        lines.append(f"Ticket uyumu: SORUN — {coherence.get('note')}")
    else:
        lines.append("Ticket uyumu: tamam")
    lines.append("")
    lines.append("Okuma sırası (zorunlu):")
    read_order = memory.get("read_order")
    if isinstance(read_order, list):
        for index, item in enumerate(read_order, start=1):
            if not isinstance(item, dict):
                continue
            purpose = str(item.get("purpose") or "")
            label = _PURPOSE_LABELS.get(purpose, purpose)
            path = item.get("path") or "(yok)"
            mark = "var" if item.get("exists") else "eksik"
            lines.append(f"  {index}. {label}: {path} [{mark}]")
    lines.append("")
    branch = git.get("branch") or "?"
    dirty = git.get("dirty_count", 0)
    lines.append(f"Git: {branch} · değişen dosya: {dirty}")
    if isinstance(tool_counts, dict) and tool_counts:
        parts = [f"{key}={value}" for key, value in sorted(tool_counts.items())]
        lines.append("Araç özeti: " + ", ".join(parts))
    lines.append("")
    lines.append(
        "İpucu: sohbet geçmişine güvenme; yukarıdaki dosyaları sırayla oku."
    )
    return "\n".join(lines) + "\n"

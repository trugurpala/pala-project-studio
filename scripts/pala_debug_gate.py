#!/usr/bin/env python3
"""Memory-as-Governance debug gate (Wave B / M28).

When open INC-* entries exist, SessionStart / begin / checkpoint surfaces warn
agents to read them and not repeat the same Fix criteria. Optional complete
fail-closed blocks passed claims on related files while those INC remain open.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from pala_memory import debugging_brain_summary, parse_debugging_brain

GATE_PREFIX = "DEBUG GATE:"
RELATED_FILE_RE = re.compile(r"`([^`]+)`|([^\s,;]+)")


def hooks_ui_trust_label() -> str:
    """Hooks UI trust is never auto-verified from CLI/Doctor file safety."""
    return "configured-not-verified"


def _debugging_path(root: Path, documents: dict[str, object] | None) -> Path:
    docs = documents if isinstance(documents, dict) else {}
    rel = docs.get("debugging")
    if isinstance(rel, str) and rel.strip():
        return root / rel
    return root / "DEBUGGING.md"


def _load_brain(
    root: Path, documents: dict[str, object] | None = None
) -> dict[str, object]:
    path = _debugging_path(root, documents)
    if not path.is_file():
        return {"ok": False, "detail": "DEBUGGING.md missing", "incidents": []}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "detail": str(exc), "incidents": []}
    return parse_debugging_brain(text)


def _related_files(raw: str) -> list[str]:
    files: list[str] = []
    for match in RELATED_FILE_RE.finditer(raw or ""):
        token = (match.group(1) or match.group(2) or "").strip().strip(",")
        if not token or token in {"and", "or"}:
            continue
        # Skip bare status words / empty.
        if token.casefold() in {"none", "n/a", "-"}:
            continue
        files.append(token.replace("\\", "/"))
    return files


def open_incidents(
    root: Path, documents: dict[str, object] | None = None
) -> list[dict[str, object]]:
    """Return open INC entries with id, fix_criteria, related_files, fields."""
    parsed = _load_brain(root, documents)
    if not parsed.get("ok"):
        return []
    open_entries: list[dict[str, object]] = []
    for entry in parsed.get("incidents") or []:
        if not isinstance(entry, dict):
            continue
        fields = entry.get("fields")
        if not isinstance(fields, dict):
            continue
        status = str(fields.get("Status") or "").strip().casefold()
        if not status.startswith("open"):
            continue
        related = _related_files(str(fields.get("Related files") or ""))
        open_entries.append(
            {
                "id": str(entry.get("id") or ""),
                "fix_criteria": str(fields.get("Fix criteria") or ""),
                "proved_by": str(fields.get("Proved by") or ""),
                "attempts": str(fields.get("Attempts") or ""),
                "related_files": related,
                "fields": fields,
            }
        )
    return open_entries


def gate_warning_text(
    root: Path,
    documents: dict[str, object] | None = None,
    *,
    max_len: int = 220,
) -> str | None:
    """Compact warning when open INC exist; None otherwise."""
    opens = open_incidents(root, documents)
    if not opens:
        return None
    ids = [str(item["id"]) for item in opens if item.get("id")]
    id_text = ", ".join(ids[:3])
    if len(ids) > 3:
        id_text += f" (+{len(ids) - 3})"
    message = (
        f"{GATE_PREFIX} read {id_text}; do not repeat same Fix criteria. "
        "Update Attempts/Proved by before claiming passed."
    )
    if len(message) > max_len:
        message = message[: max_len - 3] + "..."
    return message


def evaluate_gate(
    root: Path,
    documents: dict[str, object] | None = None,
    *,
    surface: str = "begin",
) -> dict[str, object]:
    """Structured gate report for CLI / hook / begin / checkpoint."""
    summary = debugging_brain_summary(root, documents)
    opens = open_incidents(root, documents)
    message = gate_warning_text(root, documents) or ""
    warn = bool(opens)
    cmd_hint = None
    cmd_blocks: list[dict[str, object]] = []
    try:
        from pala_cmd_memory import active_blocks, context_packet_hint

        cmd_hint = context_packet_hint(limit=3, max_len=140)
        cmd_blocks = active_blocks(limit=5)
    except (OSError, ValueError, TypeError, ImportError):
        pass
    if cmd_hint and not warn:
        # Surface path/command memory without claiming an open INC.
        message = cmd_hint
    elif cmd_hint and warn and cmd_hint not in message:
        combined = f"{message} {cmd_hint}"
        message = combined if len(combined) <= 240 else combined[:237] + "..."
    return {
        "ok": bool(summary.get("ok")),
        "surface": surface,
        "open": len(opens),
        "fixed": int(summary.get("fixed") or 0),
        "warn": warn,
        "message": message,
        "do_not_retry": bool(cmd_hint),
        "cmd_memory": {"hint": cmd_hint, "blocks": cmd_blocks},
        "incidents": [
            {
                "id": item["id"],
                "related_files": item["related_files"],
                "fix_criteria": str(item["fix_criteria"])[:160],
            }
            for item in opens
        ],
        "hooks_ui_trust": hooks_ui_trust_label(),
    }

def surface_warning(
    root: Path,
    documents: dict[str, object] | None = None,
    *,
    surface: str = "begin",
) -> str | None:
    report = evaluate_gate(root, documents, surface=surface)
    if not report.get("warn"):
        return None
    return str(report.get("message") or "") or None


def inject_session_gate(message: str, gate_message: str | None, limit: int) -> str:
    """Ensure DEBUG GATE text appears in SessionStart budget."""
    text = message or ""
    if not gate_message:
        return text if len(text) <= limit else text[: limit - 3] + "..."
    if GATE_PREFIX in text and "Fix criteria" in text:
        return text if len(text) <= limit else text[: limit - 3] + "..."
    # Prefer gate near the front after presence, within budget.
    marker = "Pala local health:"
    insert = f" {gate_message.strip()} "
    if marker in text:
        head, tail = text.split(marker, 1)
        combined = f"{head.rstrip()} {insert}{marker}{tail}"
    else:
        combined = f"{text} {gate_message.strip()}"
    if len(combined) <= limit:
        return combined
    # Drop trailing advice first to keep gate + ticket facts.
    budget = limit - len(insert) - 3
    if budget < 40:
        return (insert.strip() + " " + text)[: limit - 3] + "..."
    trimmed = text[:budget].rstrip()
    if marker in trimmed:
        head, tail = trimmed.split(marker, 1)
        combined = f"{head.rstrip()} {insert}{marker}{tail}"
    else:
        combined = f"{trimmed} {insert.strip()}"
    if len(combined) > limit:
        combined = combined[: limit - 3] + "..."
    return combined


def _norm_path(value: str) -> str:
    return value.replace("\\", "/").lstrip("./").casefold()


def _paths_overlap(related: list[str], changed: list[str]) -> bool:
    if not related or not changed:
        return False
    changed_norm = {_norm_path(item) for item in changed if item}
    for rel in related:
        needle = _norm_path(rel)
        if not needle:
            continue
        for changed_item in changed_norm:
            if (
                needle == changed_item
                or changed_item.endswith("/" + needle)
                or needle.endswith("/" + changed_item)
                or needle in changed_item
                or changed_item in needle
            ):
                return True
    return False


def _verification_has_passed(verification: list[object]) -> bool:
    for item in verification:
        if isinstance(item, dict):
            if str(item.get("status") or "").casefold() == "passed":
                return True
            continue
        text = str(item).casefold()
        if "=passed" in text or ": passed" in text or text.endswith("passed"):
            return True
    return False


def complete_fail_closed(
    root: Path,
    *,
    documents: dict[str, object] | None = None,
    changed_files: list[str] | None = None,
    verification: list[object] | None = None,
    enabled: bool = True,
) -> dict[str, object]:
    """Optional fail-closed: open INC + passed + related files touched → block."""
    if not enabled:
        return {"allowed": True, "reason": "fail-closed disabled", "incidents": []}
    opens = open_incidents(root, documents)
    if not opens:
        return {"allowed": True, "reason": "no open INC", "incidents": []}
    if not _verification_has_passed(verification or []):
        return {
            "allowed": True,
            "reason": "no passed claim",
            "incidents": [item["id"] for item in opens],
        }
    changed = list(changed_files or [])
    blocking = [
        item
        for item in opens
        if _paths_overlap(list(item.get("related_files") or []), changed)
    ]
    if not blocking:
        return {
            "allowed": True,
            "reason": "open INC related files untouched",
            "incidents": [item["id"] for item in opens],
        }
    ids = ", ".join(str(item["id"]) for item in blocking)
    return {
        "allowed": False,
        "reason": (
            f"complete refused: open {ids} still open while passed claimed on "
            "related files; update INC Status/Proved by or use honest evidence "
            "labels (not soft done)"
        ),
        "incidents": [item["id"] for item in blocking],
    }


def record_debug_attempt(
    root: Path,
    inc_id: str,
    *,
    detail: str = "",
    evidence: str = "",
    path: Path | None = None,
) -> int | None:
    """Append kind=debug_attempt to the local SQLite event store."""
    try:
        import pala_db
        from pala_catalog import _project_id, db_path

        target = path if path is not None else db_path()
        return pala_db.add_event(
            "debug_attempt",
            project_id=_project_id(root),
            project_name=root.name,
            detail=(detail or f"{inc_id} attempt")[:300],
            evidence=(evidence or f"inc={inc_id}")[:500],
            path=target,
        )
    except (OSError, ValueError, TypeError, KeyError, ImportError):
        return None
    except Exception as exc:
        # SQLite is an optional observational ledger; a locked/unavailable
        # store must not block begin/checkpoint lifecycle operations.
        if exc.__class__.__module__ == "sqlite3":
            return None
        raise


def session_memory_hit(*, debug_open: int, debugging_read: bool) -> dict[str, object]:
    """Per-session retrieval proxy: opportunity when open INC exist."""
    opportunity = int(debug_open or 0) > 0
    hit = bool(opportunity and debugging_read)
    return {
        "opportunity": opportunity,
        "hit": hit,
        "debug_open": int(debug_open or 0),
        "debugging_read": bool(debugging_read),
    }


def memory_hit_rate(*, opportunities: int, hits: int) -> dict[str, object]:
    """Aggregate proxy KPI (ratio 0..1; no percent claims)."""
    opps = max(int(opportunities), 0)
    hit_count = max(int(hits), 0)
    rate: float | None
    if opps <= 0:
        rate = None
    else:
        rate = round(hit_count / opps, 4)
    return {
        "opportunities": opps,
        "hits": min(hit_count, opps) if opps else hit_count,
        "memory_hit_rate": rate,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--cwd", default=".", help="Project root")
    result.add_argument(
        "--surface",
        default="begin",
        choices=("session", "begin", "checkpoint", "complete"),
    )
    result.add_argument("--json", action="store_true", help="Emit JSON report")
    result.add_argument(
        "--record-attempt",
        metavar="INC_ID",
        help="Record a debug_attempt event for INC_ID",
    )
    result.add_argument("--attempt-detail", default="", help="Attempt detail text")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.cwd).resolve()
    documents: dict[str, object] | None = None
    manifest_path = root / ".codex" / "pala-project.json"
    if manifest_path.is_file():
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            docs = payload.get("documents")
            if isinstance(docs, dict):
                documents = docs
        except (OSError, json.JSONDecodeError):
            documents = None
    report = evaluate_gate(root, documents, surface=args.surface)
    if args.record_attempt:
        event_id = record_debug_attempt(
            root,
            args.record_attempt,
            detail=args.attempt_detail or f"{args.record_attempt} via CLI",
            evidence=f"surface={args.surface}",
        )
        report["attempt_event_id"] = event_id
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if report.get("warn") and report.get("message"):
            print(str(report["message"]), file=sys.stderr)
        print(
            json.dumps(
                {
                    "open": report["open"],
                    "warn": report["warn"],
                    "surface": report["surface"],
                    "hooks_ui_trust": report["hooks_ui_trust"],
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

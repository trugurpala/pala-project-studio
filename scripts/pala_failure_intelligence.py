#!/usr/bin/env python3
"""Shared, redacted failure memory on Pala's existing local SQLite store.

This module is advisory diagnostic memory. It never owns task lifecycle,
acceptance, or Quality Engine decisions, and it never persists raw commands or
raw exception text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import unicodedata
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pala_db

STATES = ("OBSERVED", "CANDIDATE", "VERIFIED", "STALE", "REJECTED")
DEFAULT_RETRY_BUDGET = 2
_SECRET = re.compile(
    r"(?i)\b(?:token|secret|password|authorization|api[-_ ]?key)\b"
    r"\s*[:=]\s*[^\s,;]+"
)
_URL_CREDENTIAL = re.compile(r"(?i)(://)[^\s/@:]+:[^\s/@]+@")
_WINDOWS_PATH = re.compile(r"(?i)(?:[a-z]:[\\/]|\\\\)[^\s<>\"']+")
_POSIX_PATH = re.compile(r"(?<![\w])/(?:home|users|tmp|var|private|workspace)/[^\s<>\"']+")
_TEMP_ID = re.compile(r"(?i)\b(?:tmp|temp|run)[_-][a-z0-9-]{5,}\b")
_LONG_HEX = re.compile(r"(?i)\b[a-f0-9]{16,}\b")
_SCHEMA = """
CREATE TABLE IF NOT EXISTS failure_intelligence (
    fingerprint TEXT PRIMARY KEY,
    failure_id TEXT NOT NULL,
    failure_class TEXT NOT NULL,
    command_family TEXT NOT NULL,
    exception_type TEXT NOT NULL,
    normalized_message TEXT NOT NULL,
    tool TEXT NOT NULL,
    tool_version TEXT NOT NULL,
    platform TEXT NOT NULL,
    runtime_version TEXT NOT NULL,
    relevant_surface TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    project_refs_json TEXT NOT NULL DEFAULT '[]',
    attempts INTEGER NOT NULL DEFAULT 1,
    root_cause TEXT NOT NULL DEFAULT '',
    resolution_state TEXT NOT NULL DEFAULT 'OBSERVED',
    resolution_recipe TEXT NOT NULL DEFAULT '',
    verification_basis_json TEXT NOT NULL DEFAULT '{}',
    freshness TEXT NOT NULL DEFAULT 'fresh',
    retry_budget INTEGER NOT NULL DEFAULT 2
)
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(value: object, limit: int = 500) -> str:
    return str(value or "")[:limit]


def normalize_text(value: object) -> str:
    """Normalize diagnostic text while removing credentials, paths, and IDs."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = _SECRET.sub("<redacted-secret>", text)
    text = _URL_CREDENTIAL.sub(r"\1<redacted>@", text)
    text = _WINDOWS_PATH.sub("<redacted-path>", text)
    text = _POSIX_PATH.sub("<redacted-path>", text)
    text = _TEMP_ID.sub("<redacted-temp>", text)
    text = _LONG_HEX.sub("<redacted-id>", text)
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text[:500]


def _major(version: str) -> str | None:
    match = re.search(r"(?:^|\s|v)(\d+)(?:\.|$)", version or "")
    return match.group(1) if match else None


def _freshness(record_version: str, current_version: str) -> str:
    if not record_version or not current_version:
        return "unknown"
    return "fresh" if _major(record_version) == _major(current_version) else "stale"


@dataclass(frozen=True)
class FailureRecord:
    failure_id: str
    fingerprint: str
    failure_class: str
    command_family: str
    exception_type: str
    normalized_message: str
    tool: str
    tool_version: str
    platform: str
    runtime_version: str
    relevant_surface: str
    first_seen: str
    last_seen: str
    occurrence_count: int
    project_refs: tuple[str, ...]
    attempts: int
    root_cause: str
    resolution_state: str
    resolution_recipe: str
    verification_basis: dict[str, object]
    freshness: str
    retry_budget: int

    def public(self) -> dict[str, object]:
        return asdict(self) | {"project_refs": list(self.project_refs)}


def _fingerprint(fields: list[str]) -> str:
    payload = "|".join(fields).encode("utf-8", "replace")
    return hashlib.sha256(payload).hexdigest()


def _ensure_schema(conn: Any) -> None:
    conn.execute(_SCHEMA)


def _decode(row: Any) -> FailureRecord:
    try:
        projects = json.loads(row["project_refs_json"])
    except (TypeError, json.JSONDecodeError):
        projects = []
    try:
        basis = json.loads(row["verification_basis_json"])
    except (TypeError, json.JSONDecodeError):
        basis = {}
    return FailureRecord(
        failure_id=row["failure_id"], fingerprint=row["fingerprint"],
        failure_class=row["failure_class"], command_family=row["command_family"],
        exception_type=row["exception_type"], normalized_message=row["normalized_message"],
        tool=row["tool"], tool_version=row["tool_version"], platform=row["platform"],
        runtime_version=row["runtime_version"], relevant_surface=row["relevant_surface"],
        first_seen=row["first_seen"], last_seen=row["last_seen"],
        occurrence_count=int(row["occurrence_count"]),
        project_refs=tuple(str(item) for item in projects if isinstance(item, str)),
        attempts=int(row["attempts"]), root_cause=row["root_cause"],
        resolution_state=row["resolution_state"], resolution_recipe=row["resolution_recipe"],
        verification_basis=basis if isinstance(basis, dict) else {},
        freshness=row["freshness"], retry_budget=int(row["retry_budget"]),
    )


@contextmanager
def _open(path: Path | None) -> Any:
    with pala_db.connect(path) as conn:
        _ensure_schema(conn)
        yield conn


def record_failure(
    *, message: str, command: str, failure_class: str = "unknown",
    exception_type: str = "", tool: str = "", tool_version: str = "",
    runtime_version: str = "", relevant_surface: str = "", project_ref: str = "",
    root_cause: str = "", resolution_recipe: str = "", path: Path | None = None,
    retry_budget: int = DEFAULT_RETRY_BUDGET,
) -> FailureRecord:
    """Insert or aggregate one redacted diagnostic observation."""
    command_family = normalize_text(command).split(" ", 1)[0][:160] or "unknown"
    normalized_message = normalize_text(message)
    fields = [normalize_text(failure_class), command_family, normalize_text(exception_type), normalized_message]
    fingerprint = _fingerprint(fields)
    now = _now()
    with _open(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM failure_intelligence WHERE fingerprint = ?", (fingerprint,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO failure_intelligence (fingerprint, failure_id, failure_class, command_family, "
                "exception_type, normalized_message, tool, tool_version, platform, runtime_version, "
                "relevant_surface, first_seen, last_seen, project_refs_json, root_cause, resolution_recipe, "
                "retry_budget) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (fingerprint, "fi-" + fingerprint[:12], normalize_text(failure_class)[:80], command_family,
                 normalize_text(exception_type)[:120], normalized_message, normalize_text(tool)[:80],
                 normalize_text(tool_version)[:80], platform.platform()[:120], normalize_text(runtime_version)[:80],
                 normalize_text(relevant_surface)[:120], now, now,
                 json.dumps([normalize_text(project_ref)[:160]] if project_ref else []),
                 normalize_text(root_cause), normalize_text(resolution_recipe), max(int(retry_budget), 0)),
            )
        else:
            projects = json.loads(row["project_refs_json"] or "[]")
            if project_ref and normalize_text(project_ref) not in projects:
                projects = (projects + [normalize_text(project_ref)[:160]])[:12]
            conn.execute(
                "UPDATE failure_intelligence SET last_seen = ?, occurrence_count = occurrence_count + 1, "
                "attempts = attempts + 1, project_refs_json = ?, freshness = ?, root_cause = ?, "
                "resolution_recipe = ? WHERE fingerprint = ?",
                (now, json.dumps(projects), _freshness(row["tool_version"], tool_version),
                 normalize_text(root_cause) or row["root_cause"], normalize_text(resolution_recipe) or row["resolution_recipe"], fingerprint),
            )
        result = conn.execute("SELECT * FROM failure_intelligence WHERE fingerprint = ?", (fingerprint,)).fetchone()
        decoded = _decode(result)
        conn.commit()
        return decoded


def get_failure(fingerprint: str, *, path: Path | None = None) -> FailureRecord | None:
    with _open(path) as conn:
        row = conn.execute("SELECT * FROM failure_intelligence WHERE fingerprint = ?", (_safe(fingerprint, 64),)).fetchone()
        return _decode(row) if row is not None else None


def mark_verified(fingerprint: str, verification_basis: Mapping[str, object], *, path: Path | None = None) -> FailureRecord:
    """Promote a recipe only with explicit passed, exit-0 evidence."""
    status = str(verification_basis.get("status") or "").casefold()
    exit_code = verification_basis.get("exit_code")
    evidence_ref = str(verification_basis.get("evidence_ref") or "").strip()
    if status != "passed" or exit_code != 0 or not evidence_ref:
        raise ValueError("verification requires status=passed, exit_code=0, and evidence_ref")
    safe_basis = {"status": "passed", "exit_code": 0, "evidence_ref": normalize_text(evidence_ref)[:240]}
    with _open(path) as conn:
        row = conn.execute("SELECT * FROM failure_intelligence WHERE fingerprint = ?", (_safe(fingerprint, 64),)).fetchone()
        if row is None:
            raise KeyError("failure fingerprint not found")
        conn.execute(
            "UPDATE failure_intelligence SET resolution_state = 'VERIFIED', verification_basis_json = ?, "
            "freshness = 'fresh' WHERE fingerprint = ?",
            (json.dumps(safe_basis, sort_keys=True), fingerprint),
        )
        return _decode(conn.execute("SELECT * FROM failure_intelligence WHERE fingerprint = ?", (fingerprint,)).fetchone())


def retry_decision(fingerprint: str, *, path: Path | None = None) -> dict[str, object]:
    record = get_failure(fingerprint, path=path)
    if record is None:
        return {"allowed": True, "reason": "no prior failure"}
    if record.attempts >= record.retry_budget:
        return {"allowed": False, "reason": "retry budget exhausted", "attempts": record.attempts, "budget": record.retry_budget}
    if record.freshness == "stale" or record.resolution_state in {"STALE", "REJECTED"}:
        return {"allowed": False, "reason": "resolution is not current", "state": record.resolution_state}
    return {"allowed": True, "reason": "within retry budget", "attempts": record.attempts, "budget": record.retry_budget}


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--failure-class", default="unknown")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    record = record_failure(message=args.message, command=args.command, failure_class=args.failure_class)
    print(json.dumps(record.public(), ensure_ascii=True, sort_keys=True) if args.json else record.failure_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

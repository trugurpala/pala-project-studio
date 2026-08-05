"""Small, local-first storage for Pala session-owned ticket records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pala_models import SessionKey, VERIFICATION_STATUSES


def session_key(session: str) -> str:
    return SessionKey.from_session_id(session)


def _verification_fingerprint(command: str, error: str) -> str:
    command = command.strip()[:240]
    error = re.sub(r"(?i)(token|secret|password|authorization)\s*[:=]\s*\S+", r"\1=[redacted]", error.strip())[:240]
    return hashlib.sha256(f"{command}\n{error}".encode("utf-8")).hexdigest()[:24]


class ClaimResult:
    def __init__(self, status: str, record: dict[str, object]) -> None:
        self.status = status
        self.record = record


class WorkflowStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _ticket_path(self, ticket: str) -> Path:
        digest = hashlib.sha256(ticket.encode("utf-8")).hexdigest()
        return self.root / ".codex" / "plugin-data" / "pala" / "v3" / "tickets" / f"{digest}.json"

    def _migration_path(self) -> Path:
        return self.root / ".codex" / "plugin-data" / "pala" / "v3" / "migration-v2.json"

    @staticmethod
    def _read(path: Path) -> dict[str, object] | None:
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _write(path: Path, payload: dict[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            temporary = Path(handle.name)
        os.replace(temporary, path)

    @staticmethod
    def _acquire_lock(path: Path) -> Path | None:
        lock_path = path.with_suffix(".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            lock_path.mkdir()
        except FileExistsError:
            return None
        return lock_path

    @staticmethod
    def _release_lock(lock_path: Path) -> None:
        lock_path.rmdir()

    def claim(self, ticket: str, goal: str, session: str) -> ClaimResult:
        if not ticket.strip() or not goal.strip():
            raise ValueError("ticket and goal must be non-empty")
        owner = session_key(session)
        path = self._ticket_path(ticket)
        lock_path = self._acquire_lock(path)
        if lock_path is None:
            return ClaimResult("busy", {})
        try:
            existing = self._read(path)
            if existing is not None and existing.get("owner") not in (None, owner):
                return ClaimResult("owned_by_other", existing)
            record = existing or {
                "schema_version": 3,
                "ticket": ticket.strip(),
                "goal": goal.strip(),
                "lifecycle": "active",
                "dirty": True,
            }
            record["owner"] = owner
            record["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write(path, record)
            return ClaimResult("claimed", record)
        finally:
            self._release_lock(lock_path)

    def checkpoint(self, ticket: str, session: str, next_action: str) -> ClaimResult:
        if not next_action.strip():
            raise ValueError("next action must be non-empty")
        path = self._ticket_path(ticket)
        lock_path = self._acquire_lock(path)
        if lock_path is None:
            return ClaimResult("busy", {})
        try:
            record = self._read(path)
            if record is None:
                raise ValueError("ticket record not found")
            owner = session_key(session)
            if record.get("owner") != owner:
                return ClaimResult("owned_by_other", record)
            record.update(
                {
                    "lifecycle": "checkpointed",
                    "owner": None,
                    "dirty": False,
                    "next_action": next_action.strip()[:500],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            self._write(path, record)
            return ClaimResult("checkpointed", record)
        finally:
            self._release_lock(lock_path)

    def active_for_session(self, session: str) -> dict[str, object] | None:
        owner = session_key(session)
        tickets = self.root / ".codex" / "plugin-data" / "pala" / "v3" / "tickets"
        if not tickets.is_dir():
            return None
        for path in tickets.glob("*.json"):
            try:
                record = self._read(path)
            except (OSError, json.JSONDecodeError):
                continue
            if record and record.get("owner") == owner and record.get("dirty") is True:
                return record
        return None

    def heartbeat(self, session: str, event: str) -> ClaimResult:
        if event not in {"session_start", "session_end", "pre_compact"}:
            raise ValueError("unsupported lifecycle event")
        record = self.active_for_session(session)
        if record is None:
            return ClaimResult("not_found", {})
        path = self._ticket_path(str(record["ticket"]))
        lock_path = self._acquire_lock(path)
        if lock_path is None:
            return ClaimResult("busy", {})
        try:
            current = self._read(path)
            if current is None or current.get("owner") != session_key(session):
                return ClaimResult("not_found", {})
            current["last_event"] = event
            current["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write(path, current)
            return ClaimResult("updated", current)
        finally:
            self._release_lock(lock_path)

    def record_verification(
        self, ticket: str, session: str, status: str, command: str, error: str = ""
    ) -> ClaimResult:
        if status not in VERIFICATION_STATUSES:
            raise ValueError("unsupported verification status")
        path = self._ticket_path(ticket)
        lock_path = self._acquire_lock(path)
        if lock_path is None:
            return ClaimResult("busy", {})
        try:
            record = self._read(path)
            if record is None:
                raise ValueError("ticket record not found")
            if record.get("owner") != session_key(session):
                return ClaimResult("owned_by_other", record)
            fingerprint = _verification_fingerprint(command, error)
            verification = record.get("verification", [])
            if not isinstance(verification, list):
                verification = []
            entry = {
                "status": status,
                "command": command.strip()[:240],
                "fingerprint": fingerprint,
            }
            if error.strip():
                entry["error"] = re.sub(
                    r"(?i)(token|secret|password|authorization)\s*[:=]\s*\S+",
                    r"\1=[redacted]",
                    error.strip(),
                )[:240]
            verification.append(entry)
            record["verification"] = verification[-8:]
            if status == "failed":
                repeats = sum(
                    item.get("fingerprint") == fingerprint and item.get("status") == "failed"
                    for item in verification
                    if isinstance(item, dict)
                )
                if repeats >= 2:
                    blockers = record.get("blockers", [])
                    if not isinstance(blockers, list):
                        blockers = []
                    if "verification repeated twice" not in blockers:
                        blockers.append("verification repeated twice")
                    record["blockers"] = blockers[-5:]
                    record["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._write(path, record)
                    return ClaimResult("blocked", record)
            record["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write(path, record)
            return ClaimResult("recorded", record)
        finally:
            self._release_lock(lock_path)

    def complete(self, ticket: str, session: str) -> ClaimResult:
        path = self._ticket_path(ticket)
        lock_path = self._acquire_lock(path)
        if lock_path is None:
            return ClaimResult("busy", {})
        try:
            record = self._read(path)
            if record is None:
                raise ValueError("ticket record not found")
            if record.get("owner") != session_key(session):
                return ClaimResult("owned_by_other", record)
            verification = record.get("verification", [])
            passed = any(
                isinstance(item, dict) and item.get("status") == "passed"
                for item in verification
            )
            failed = any(
                isinstance(item, dict) and item.get("status") in {"failed", "blocked", "timeout"}
                for item in verification
            )
            blockers = record.get("blockers", [])
            if not passed or failed or blockers:
                return ClaimResult("verification_required", record)
            record.update(
                {
                    "lifecycle": "completed",
                    "owner": None,
                    "dirty": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            self._write(path, record)
            return ClaimResult("completed", record)
        finally:
            self._release_lock(lock_path)

    def recover(self, ticket: str, session: str) -> ClaimResult:
        path = self._ticket_path(ticket)
        lock_path = self._acquire_lock(path)
        if lock_path is None:
            return ClaimResult("busy", {})
        try:
            record = self._read(path)
            if record is None:
                raise ValueError("ticket record not found")
            if record.get("dirty") is True:
                return ClaimResult("dirty_takeover_refused", record)
            record.update(
                {
                    "lifecycle": "active",
                    "owner": session_key(session),
                    "dirty": True,
                    "recovered_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            self._write(path, record)
            return ClaimResult("recovered", record)
        finally:
            self._release_lock(lock_path)

    def migrate_v2(self) -> ClaimResult:
        legacy_path = self.root / ".codex" / "pala-workflow.json"
        marker_path = self._migration_path()
        if marker_path.is_file():
            marker = self._read(marker_path) or {}
            return ClaimResult("already_migrated", marker)
        if not legacy_path.is_file():
            return ClaimResult("not_found", {})
        try:
            legacy = self._read(legacy_path)
        except (OSError, json.JSONDecodeError):
            return ClaimResult("invalid_legacy", {})
        if not legacy or legacy.get("schema_version") != 2:
            return ClaimResult("not_found", {})
        marker = {
            "schema_version": 3,
            "migration": "v2-observed",
            "legacy_active_ticket": str(legacy.get("active_ticket") or "")[:120],
            "migrated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._write(marker_path, marker)
        return ClaimResult("migrated", marker)

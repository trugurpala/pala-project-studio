"""Small, local-first storage for Pala session-owned ticket records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pala_models import SessionKey, VERIFICATION_STATUSES

VERIFICATION_BUDGET = 2
VERIFICATION_FAILURE_STATUSES = {"failed", "timeout", "not-run", "blocked"}


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

    def _state_root(self) -> Path:
        """Use shared Git metadata when possible, with a non-Git test fallback."""

        try:
            result = subprocess.run(
                [
                    "git",
                    "rev-parse",
                    "--path-format=absolute",
                    "--git-common-dir",
                ],
                cwd=self.root,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            result = None
        if result is not None and result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).resolve() / "pala" / "v3"
        return self.root / ".codex" / "plugin-data" / "pala" / "v3"

    def _ticket_path(self, ticket: str) -> Path:
        digest = hashlib.sha256(ticket.encode("utf-8")).hexdigest()
        return self._state_root() / "tickets" / f"{digest}.json"

    def _migration_path(self) -> Path:
        return self._state_root() / "migration-v2.json"

    def record(self, ticket: str) -> dict[str, object] | None:
        return self._read(self._ticket_path(ticket))

    def list_records(self) -> tuple[dict[str, object], ...]:
        tickets = self._state_root() / "tickets"
        if not tickets.is_dir():
            return ()
        records: list[dict[str, object]] = []
        for path in sorted(tickets.glob("*.json"), key=lambda value: value.name):
            try:
                record = self._read(path)
            except (OSError, json.JSONDecodeError):
                raise ValueError(f"STATE_RECORD_INVALID: {path.name}") from None
            if record is None or not self._valid_record(record):
                raise ValueError(f"STATE_RECORD_INVALID: {path.name}")
            records.append(record)
        return tuple(records)

    @staticmethod
    def _valid_record(record: dict[str, object]) -> bool:
        lifecycle = record.get("lifecycle")
        owner = record.get("owner")
        basis = record.get("basis")
        worktree = record.get("worktree_git_dir_digest")
        digest = re.compile(r"^[0-9a-f]{24}$")
        if (
            record.get("schema_version") != 3
            or not isinstance(record.get("ticket"), str)
            or not str(record.get("ticket")).strip()
            or not isinstance(record.get("goal"), str)
            or not str(record.get("goal")).strip()
            or lifecycle not in {"active", "checkpointed", "completed"}
            or not isinstance(record.get("dirty"), bool)
            or (owner is not None and (not isinstance(owner, str) or not digest.fullmatch(owner)))
            or (worktree is not None and (not isinstance(worktree, str) or not digest.fullmatch(worktree)))
            or (basis is not None and not isinstance(basis, dict))
        ):
            return False
        if lifecycle == "active":
            return record.get("dirty") is True and owner is not None
        return record.get("dirty") is False and owner is None

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

    def _current_basis(self) -> tuple[dict[str, object], str | None]:
        documents: dict[str, str | None] = {}
        manifest_path = self.root / ".codex" / "pala-project.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            mappings = manifest.get("documents", {})
            if isinstance(mappings, dict):
                for purpose, value in mappings.items():
                    if not isinstance(value, str) or not value:
                        continue
                    path = self.root / value
                    documents[str(purpose)] = (
                        hashlib.sha256(path.read_bytes()).hexdigest()
                        if path.is_file()
                        else None
                    )
        except (OSError, json.JSONDecodeError):
            documents = {}
        try:
            from pala_snapshot import git_identity, working_tree_status_digest

            _, worktree = git_identity(self.root)
            return (
                {
                    "head": worktree.head,
                    "worktree_git_dir_digest": worktree.git_dir_digest,
                    "working_tree_status_digest": working_tree_status_digest(self.root),
                    "documents": documents,
                },
                worktree.git_dir_digest,
            )
        except (OSError, ValueError):
            return (
                {
                    "head": None,
                    "worktree_git_dir_digest": None,
                    "documents": documents,
                },
                None,
            )

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
            basis, worktree_digest = self._current_basis()
            record["owner"] = owner
            record["basis"] = basis
            record["worktree_git_dir_digest"] = worktree_digest
            record["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write(path, record)
            return ClaimResult("claimed", record)
        finally:
            self._release_lock(lock_path)

    def checkpoint(
        self,
        ticket: str,
        session: str,
        next_action: str,
        verification: list[str] | None = None,
        tier: str = "ticket",
        blockers: list[str] | None = None,
    ) -> ClaimResult:
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
            if not verification or not all(
                re.search(r"(?:^|[:=]\s*)passed(?:\s*(?:;|$))", item, re.IGNORECASE)
                and not re.search(r"\bnot\s+passed\b", item, re.IGNORECASE)
                and not re.search(
                    r"\b(?:failed|error|timeout|blocked|not[- ]?run)\b",
                    item,
                    re.IGNORECASE,
                )
                for item in verification
            ):
                return ClaimResult("verification_required", record)
            if tier not in {"narrow", "ticket", "milestone", "release"}:
                raise ValueError("unsupported verification tier")
            bounded_blockers = [str(item).strip()[:240] for item in (blockers or []) if str(item).strip()]
            record["verification"] = [str(item).strip()[:240] for item in verification][-8:]
            record["verification_tier"] = tier
            record["blockers"] = bounded_blockers[-5:]
            if bounded_blockers:
                record["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._write(path, record)
                return ClaimResult("blocked", record)
            basis, worktree_digest = self._current_basis()
            record.update(
                {
                    "lifecycle": "checkpointed",
                    "owner": None,
                    "dirty": False,
                    "next_action": next_action.strip()[:500],
                    "basis": basis,
                    "worktree_git_dir_digest": worktree_digest,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            self._write(path, record)
            return ClaimResult("checkpointed", record)
        finally:
            self._release_lock(lock_path)

    def active_for_session(self, session: str) -> dict[str, object] | None:
        owner = session_key(session)
        tickets = self._state_root() / "tickets"
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

    def has_dirty_record(self) -> bool:
        tickets = self._state_root() / "tickets"
        if not tickets.is_dir():
            return False
        for path in tickets.glob("*.json"):
            try:
                record = self._read(path)
            except (OSError, json.JSONDecodeError):
                continue
            if record and record.get("dirty") is True:
                return True
        return False

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

    def handle_event(self, session: str, event: str) -> ClaimResult:
        """Apply one lifecycle event only to the ticket owned by its session."""

        return self.heartbeat(session, event)

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
            if status in VERIFICATION_FAILURE_STATUSES:
                failures = [
                    item
                    for item in verification
                    if isinstance(item, dict)
                    and item.get("fingerprint") == fingerprint
                    and item.get("status") in VERIFICATION_FAILURE_STATUSES
                ]
                first_failure = record.get("first_verification_failure")
                if not isinstance(first_failure, dict):
                    record["first_verification_failure"] = {
                        "status": status,
                        "command": entry["command"],
                        "fingerprint": fingerprint,
                    }
                    if entry.get("error"):
                        record["first_verification_failure"]["error"] = entry["error"]
                record["verification_attempts"] = len(failures)
                if len(failures) >= VERIFICATION_BUDGET:
                    blockers = record.get("blockers", [])
                    if not isinstance(blockers, list):
                        blockers = []
                    if "verification repeated twice" not in blockers:
                        blockers.append("verification repeated twice")
                    if "verification budget exhausted" not in blockers:
                        blockers.append("verification budget exhausted")
                    record["blockers"] = blockers[-5:]
                    record["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self._write(path, record)
                    return ClaimResult("blocked", record)
            else:
                record["verification_attempts"] = 0
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
                isinstance(item, dict) and item.get("status") in VERIFICATION_FAILURE_STATUSES
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

    def migrate_v2(self, *, apply: bool = True) -> ClaimResult:
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
        legacy_sha256 = hashlib.sha256(legacy_path.read_bytes()).hexdigest()
        marker = {
            "schema_version": 3,
            "migration": "v2-observed",
            "legacy_active_ticket": str(legacy.get("active_ticket") or "")[:120],
            "legacy_sha256": legacy_sha256,
            "migrated_at": datetime.now(timezone.utc).isoformat(),
        }
        if not apply:
            return ClaimResult("would_migrate", marker)
        self._write(marker_path, marker)
        return ClaimResult("migrated", marker)

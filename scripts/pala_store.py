"""Small, local-first storage for Pala session-owned ticket records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pala_authority import shared_state_root, worktree_id
from pala_models import VERIFICATION_STATUSES, SessionKey
from pala_task_contract import Evidence, TaskContract, scope_violations

VERIFICATION_BUDGET = 2
VERIFICATION_FAILURE_STATUSES = {"failed", "timeout", "not-run", "blocked"}
LEASE_STALE_AFTER = timedelta(minutes=30)


def session_key(session: str) -> str:
    return SessionKey.from_session_id(session)


def _verification_fingerprint(command: str, error: str) -> str:
    command = command.strip()[:240]
    error = re.sub(r"(?i)(token|secret|password|authorization)\s*[:=]\s*\S+", r"\1=[redacted]", error.strip())[:240]
    return hashlib.sha256(f"{command}\n{error}".encode()).hexdigest()[:24]


class ClaimResult:
    def __init__(self, status: str, record: dict[str, object]) -> None:
        self.status = status
        self.record = record


class WorkflowStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def _ticket_path(self, ticket: str) -> Path:
        digest = hashlib.sha256(ticket.encode("utf-8")).hexdigest()
        shared = shared_state_root(self.root)
        if shared is not None:
            return shared / "tasks" / f"{digest}.json"
        return self.root / ".codex" / "plugin-data" / "pala" / "v3" / "tickets" / f"{digest}.json"

    def _legacy_ticket_path(self, ticket: str) -> Path:
        digest = hashlib.sha256(ticket.encode("utf-8")).hexdigest()
        return self.root / ".codex" / "plugin-data" / "pala" / "v3" / "tickets" / f"{digest}.json"

    def _read_ticket(self, ticket: str) -> dict[str, object] | None:
        shared = self._read(self._ticket_path(ticket))
        if shared is not None:
            return shared
        legacy = self._legacy_ticket_path(ticket)
        if legacy != self._ticket_path(ticket):
            return self._read(legacy)
        return None

    def _migration_path(self) -> Path:
        shared = shared_state_root(self.root)
        if shared is not None:
            return shared / "migration" / "v2-observed.json"
        return self.root / ".codex" / "plugin-data" / "pala" / "v3" / "migration-v2.json"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def _lease_stale(cls, record: dict[str, object]) -> bool:
        lease = record.get("lease")
        if not isinstance(lease, dict):
            return False
        value = lease.get("heartbeat_at") or lease.get("claimed_at")
        if not isinstance(value, str):
            return False
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return True
        return datetime.now(timezone.utc) - timestamp > LEASE_STALE_AFTER

    @staticmethod
    def _read(path: Path) -> dict[str, object] | None:
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _structured_acceptance(items: list[object] | None) -> list[object]:
        """Persist explicit criteria as structured, initially-unverified contract items."""
        normalized: list[object] = []
        for index, item in enumerate(items or [], start=1):
            if isinstance(item, dict):
                value = dict(item)
                value.setdefault("id", f"AC-{index:02d}")
                value.setdefault("text", "")
                value.setdefault("status", "not-run")
                value.setdefault("evidence_refs", [])
                normalized.append(value)
            elif str(item).strip():
                normalized.append({
                    "id": f"AC-{index:02d}", "text": str(item).strip(),
                    "status": "not-run", "evidence_refs": [],
                })
        return normalized

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

    def _acquire_lock(self, path: Path) -> Path | None:
        shared = shared_state_root(self.root)
        lock_path = (
            shared / "leases" / f"{path.stem}.lock"
            if shared is not None
            else path.with_suffix(".lock")
        )
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            lock_path.mkdir()
        except FileExistsError:
            return None
        return lock_path

    @staticmethod
    def _release_lock(lock_path: Path) -> None:
        lock_path.rmdir()

    def claim(
        self, ticket: str, goal: str, session: str, *, acceptance: list[object] | None = None
    ) -> ClaimResult:
        if not ticket.strip() or not goal.strip():
            raise ValueError("ticket and goal must be non-empty")
        owner = session_key(session)
        path = self._ticket_path(ticket)
        lock_path = self._acquire_lock(path)
        if lock_path is None:
            return ClaimResult("busy", {})
        try:
            existing = self._read_ticket(ticket)
            if existing is not None and existing.get("owner") not in (None, owner):
                if self._lease_stale(existing):
                    lease = existing.get("lease")
                    if isinstance(lease, dict):
                        lease["status"] = "orphaned"
                    existing["external_conflict"] = {
                        "type": "orphaned_claim",
                        "observed_at": self._now(),
                        "resolution": "needs_decision",
                    }
                    return ClaimResult("orphaned", existing)
                return ClaimResult("owned_by_other", existing)
            record = existing or {
                "schema_version": 4,
                "ticket": ticket.strip(),
                "goal": goal.strip(),
                "lifecycle": "active",
                "dirty": True,
                "task_contract": TaskContract(
                    id=ticket.strip(), project_id="local", title=ticket.strip(), goal=goal.strip(),
                    acceptance=self._structured_acceptance(acceptance),
                ).to_dict(),
            }
            record["owner"] = owner
            record["assignee"] = {"type": "agent", "id": "codex-default"}
            record["lease"] = {
                "status": "claimed",
                "holder_type": "agent_session",
                "session_key_hash": owner,
                "claimed_at": self._now(),
                "heartbeat_at": self._now(),
                "worktree_id": worktree_id(self.root),
                "generation": int((record.get("lease") or {}).get("generation", 0)) + 1 if isinstance(record.get("lease"), dict) else 1,
            }
            record["lease_status"] = "claimed"
            record["updated_at"] = self._now()
            contract = TaskContract.from_dict(dict(record["task_contract"]))
            contract.claim("codex-default", session, worktree_id=worktree_id(self.root))
            if contract.status == "CLAIMED":
                contract.transition("IN_PROGRESS")
            record["task_contract"] = contract.to_dict()
            record["acceptance"] = contract.acceptance
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
            record = self._read_ticket(ticket)
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
                    "lease_status": "released",
                    "next_action": next_action.strip()[:500],
                    "updated_at": self._now(),
                }
            )
            if isinstance(record.get("lease"), dict):
                record["lease"]["status"] = "released"
            contract_payload = record.get("task_contract")
            if isinstance(contract_payload, dict):
                contract = TaskContract.from_dict(contract_payload)
                contract.owner = None
                contract.session_key = None
                if isinstance(contract.lease, dict):
                    contract.lease["status"] = "released"
                    contract.lease["session_key_hash"] = None
                record["task_contract"] = contract.to_dict()
            self._write(path, record)
            return ClaimResult("checkpointed", record)
        finally:
            self._release_lock(lock_path)

    def active_for_session(self, session: str) -> dict[str, object] | None:
        owner = session_key(session)
        tickets = {self._ticket_path("__scan__").parent, self._legacy_ticket_path("__scan__").parent}
        for directory in tickets:
            if not directory.is_dir():
                continue
            for path in directory.glob("*.json"):
                try:
                    record = self._read(path)
                except (OSError, json.JSONDecodeError):
                    continue
                if record and record.get("owner") == owner and record.get("dirty") is True:
                    return record
        return None

    def has_dirty_record(self) -> bool:
        for directory in {self._ticket_path("__scan__").parent, self._legacy_ticket_path("__scan__").parent}:
            if not directory.is_dir():
                continue
            for path in directory.glob("*.json"):
                try:
                    record = self._read(path)
                except (OSError, json.JSONDecodeError):
                    continue
                if record and record.get("dirty") is True:
                    return True
        return False

    def _task_contracts(self) -> dict[str, dict[str, object]]:
        contracts: dict[str, dict[str, object]] = {}
        directories = {self._ticket_path("__scan__").parent, self._legacy_ticket_path("__scan__").parent}
        for directory in directories:
            if not directory.is_dir():
                continue
            for candidate in directory.glob("*.json"):
                try:
                    record = self._read(candidate)
                except (OSError, json.JSONDecodeError):
                    continue
                if not isinstance(record, dict):
                    continue
                payload = record.get("task_contract")
                if not isinstance(payload, dict):
                    continue
                task_id = str(payload.get("id") or record.get("ticket") or "")
                if task_id:
                    contracts[task_id] = payload
        return contracts

    def active_task_contract(self) -> dict[str, object] | None:
        """Return one canonical dirty task contract for generated read models."""
        candidates: list[dict[str, object]] = []
        for directory in {self._ticket_path("__scan__").parent, self._legacy_ticket_path("__scan__").parent}:
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.json"), key=lambda item: item.name):
                try:
                    record = self._read(path)
                except (OSError, json.JSONDecodeError):
                    continue
                if isinstance(record, dict) and record.get("dirty") is True and isinstance(record.get("task_contract"), dict):
                    candidates.append(dict(record["task_contract"]))
        return candidates[0] if len(candidates) == 1 else None

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
            current = self._read_ticket(str(record["ticket"]))
            if current is None or current.get("owner") != session_key(session):
                return ClaimResult("not_found", {})
            current["last_event"] = event
            current["updated_at"] = self._now()
            if isinstance(current.get("lease"), dict):
                current["lease"]["heartbeat_at"] = self._now()
            self._write(path, current)
            return ClaimResult("updated", current)
        finally:
            self._release_lock(lock_path)

    def record_verification(
        self, ticket: str, session: str, status: str, command: str, error: str = "", basis: dict[str, object] | None = None
    ) -> ClaimResult:
        if status not in VERIFICATION_STATUSES:
            raise ValueError("unsupported verification status")
        path = self._ticket_path(ticket)
        lock_path = self._acquire_lock(path)
        if lock_path is None:
            return ClaimResult("busy", {})
        try:
            record = self._read_ticket(ticket)
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
                "id": f"EV-{fingerprint}",
                "exit_code": 0 if status == "passed" else None,
                "timestamp": self._now(),
            }
            if basis is None:
                try:
                    from pala_verification_basis import capture_basis

                    basis = capture_basis(self.root)
                except (OSError, ValueError, ImportError):
                    basis = None
            if basis is not None:
                entry["verification_basis"] = basis
                record["verification_basis"] = basis
                record["last_verified_basis"] = basis
            if error.strip():
                entry["error"] = re.sub(
                    r"(?i)(token|secret|password|authorization)\s*[:=]\s*\S+",
                    r"\1=[redacted]",
                    error.strip(),
                )[:240]
            verification.append(entry)
            record["verification"] = verification[-8:]
            contract = TaskContract.from_dict(dict(record.get("task_contract") or {}))
            if status == "passed":
                if contract.status == "IN_PROGRESS":
                    contract.transition("REVIEW")
                if contract.status == "REVIEW":
                    contract.transition("VERIFYING")
            contract.record_evidence(Evidence(
                kind="workflow-verification", command=entry["command"],
                exit_code=entry["exit_code"], status=status,
                summary=str(entry.get("error") or ""), id=str(entry["id"]),
            ))
            record["task_contract"] = contract.to_dict()
            record["acceptance"] = contract.acceptance
            record["evidence"] = contract.evidence
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
                    record["updated_at"] = self._now()
                    self._write(path, record)
                    return ClaimResult("blocked", record)
            else:
                record["verification_attempts"] = 0
            record["updated_at"] = self._now()
            self._write(path, record)
            return ClaimResult("recorded", record)
        finally:
            self._release_lock(lock_path)

    def sync_quality_evidence(self, ticket: str, session: str, quality_ticket: str) -> ClaimResult:
        """Map current, required Pala Quality Engine evidence into TaskContract items."""
        path = self._ticket_path(ticket)
        lock_path = self._acquire_lock(path)
        if lock_path is None:
            return ClaimResult("busy", {})
        try:
            record = self._read_ticket(ticket)
            if record is None:
                raise ValueError("ticket record not found")
            if record.get("owner") != session_key(session):
                return ClaimResult("owned_by_other", record)
            from pala_quality import quality_gate, read_ledger

            gate = quality_gate(self.root, quality_ticket)
            if gate.get("status") != "passed":
                return ClaimResult("quality_required", record)
            ledger = read_ledger(self.root, quality_ticket)
            checks = {
                str(item.get("id")): item for item in ledger.get("checks", [])
                if isinstance(item, dict)
            }
            contract = TaskContract.from_dict(dict(record.get("task_contract") or {}))
            acceptance = contract.acceptance_items()
            if not acceptance:
                return ClaimResult("acceptance_required", record)
            from pala_verification_basis import basis_matches, capture_basis

            current_basis = capture_basis(self.root)
            evidence_by_id = {str(item.get("id")): item for item in contract.evidence}
            for item in acceptance:
                check_ids = [str(value) for value in item.get("quality_check_ids") or [] if str(value)]
                if not check_ids:
                    return ClaimResult("quality_mapping_required", record)
                matched = [checks.get(check_id) for check_id in check_ids]
                if any(check is None or check.get("status") != "passed" or check.get("exit_code") != 0 for check in matched):
                    return ClaimResult("quality_required", record)
                required_authority = str(item.get("quality_execution_authority") or "")
                if required_authority and any(
                    check is None
                    or check.get("execution_authority") != required_authority
                    or not isinstance(check.get("execution_basis"), dict)
                    or not basis_matches(check["execution_basis"], current_basis)
                    for check in matched
                ):
                    return ClaimResult("trusted_quality_required", record)
                refs: list[str] = []
                for check_id, check in zip(check_ids, matched, strict=True):
                    evidence_id = "QE-" + hashlib.sha256(
                        f"{quality_ticket}\n{check_id}\n{ledger.get('surface_digest') or ''}".encode()
                    ).hexdigest()[:24]
                    if evidence_id not in evidence_by_id:
                        contract.record_evidence(Evidence(
                            kind="quality", command=str(check.get("command") or ""),
                            exit_code=0, status="passed", id=evidence_id,
                            surface_digest=str(ledger.get("surface_digest") or "") or None,
                            summary=f"quality_ticket={quality_ticket}; check_id={check_id}",
                        ))
                        evidence_by_id = {str(value.get("id")): value for value in contract.evidence}
                    refs.append(evidence_id)
                item["status"] = "passed"
                item["evidence_refs"] = refs
            if contract.status == "IN_PROGRESS":
                contract.transition("REVIEW")
            if contract.status == "REVIEW":
                contract.transition("VERIFYING")
            if contract.status == "VERIFYING":
                contract.transition("VERIFIED")
            contract.acceptance = acceptance
            basis = current_basis
            contract.set_verification_basis(
                str(basis.get("head_sha") or "") or None,
                str(basis.get("index_digest") or "") or None,
                str(basis.get("worktree_digest") or "") or None,
                str(basis.get("surface_digest") or "") or None,
            )
            record["task_contract"] = contract.to_dict()
            record["acceptance"] = contract.acceptance
            record["evidence"] = contract.evidence
            record["quality_ticket"] = quality_ticket
            record["verification_basis"] = contract.verification_basis
            record["updated_at"] = self._now()
            self._write(path, record)
            return ClaimResult("mapped", record)
        finally:
            self._release_lock(lock_path)

    def configure_quality_mapping(
        self,
        ticket: str,
        session: str,
        check_ids: list[str],
        execution_authority: str,
    ) -> ClaimResult:
        """Bind every active acceptance item to trusted Quality Engine checks."""
        path = self._ticket_path(ticket)
        lock_path = self._acquire_lock(path)
        if lock_path is None:
            return ClaimResult("busy", {})
        try:
            record = self._read_ticket(ticket)
            if record is None:
                raise ValueError("ticket record not found")
            if record.get("owner") != session_key(session):
                return ClaimResult("owned_by_other", record)
            contract = TaskContract.from_dict(dict(record.get("task_contract") or {}))
            if contract.status != "IN_PROGRESS":
                return ClaimResult("task_not_active", record)
            normalized_ids = list(dict.fromkeys(str(value).strip() for value in check_ids))
            authority = execution_authority.strip()
            if not normalized_ids or any(not value for value in normalized_ids) or not authority:
                raise ValueError("quality mapping requires check IDs and execution authority")
            acceptance = contract.acceptance_items()
            if not acceptance:
                return ClaimResult("acceptance_required", record)
            for item in acceptance:
                item["quality_check_ids"] = normalized_ids
                item["quality_execution_authority"] = authority
                item["status"] = "not-run"
                item["evidence_refs"] = []
            contract.acceptance = acceptance
            record["task_contract"] = contract.to_dict()
            record["acceptance"] = contract.acceptance
            record["updated_at"] = self._now()
            self._write(path, record)
            return ClaimResult("configured", record)
        finally:
            self._release_lock(lock_path)

    def configure_task(
        self,
        ticket: str,
        session: str,
        *,
        dependencies: list[str],
        architecture_refs: list[str],
        write_scope: list[str],
        next_action: str,
    ) -> ClaimResult:
        """Map a validated product-plan node into its claimed TaskContract."""
        path = self._ticket_path(ticket)
        lock_path = self._acquire_lock(path)
        if lock_path is None:
            return ClaimResult("busy", {})
        try:
            record = self._read_ticket(ticket)
            if record is None:
                raise ValueError("ticket record not found")
            if record.get("owner") != session_key(session):
                return ClaimResult("owned_by_other", record)
            contract = TaskContract.from_dict(dict(record.get("task_contract") or {}))
            if contract.status != "IN_PROGRESS":
                return ClaimResult("task_not_active", record)
            values = dependencies + architecture_refs + write_scope
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError("task mapping values must be non-empty strings")
            contract.dependencies = list(dict.fromkeys(dependencies))
            contract.architecture_refs = list(dict.fromkeys(architecture_refs))
            contract.write_scope = list(dict.fromkeys(write_scope))
            contract.next_action = next_action.strip()
            record["task_contract"] = contract.to_dict()
            record["acceptance"] = contract.acceptance
            record["updated_at"] = self._now()
            self._write(path, record)
            return ClaimResult("configured", record)
        finally:
            self._release_lock(lock_path)

    def complete(self, ticket: str, session: str) -> ClaimResult:
        path = self._ticket_path(ticket)
        lock_path = self._acquire_lock(path)
        if lock_path is None:
            return ClaimResult("busy", {})
        try:
            record = self._read_ticket(ticket)
            if record is None:
                raise ValueError("ticket record not found")
            if record.get("owner") != session_key(session):
                return ClaimResult("owned_by_other", record)
            contract = TaskContract.from_dict(dict(record.get("task_contract") or {}))
            from pala_dependencies import dependency_ready

            tasks = self._task_contracts()
            tasks[contract.id] = contract.to_dict()
            dependency = dependency_ready(tasks, contract.id)
            if dependency.get("status") != "passed":
                return ClaimResult("dependency_required", record)
            changed_files = [str(item) for item in record.get("changed_files", []) if str(item)]
            violations = scope_violations(changed_files, contract.write_scope, contract.deny_scope)
            if violations:
                record["scope_violations"] = violations
                return ClaimResult("scope_required", record)
            allowed, _reason = contract.can_complete()
            expected_basis = record.get("verification_basis")
            if allowed and isinstance(expected_basis, dict) and expected_basis.get("head_sha"):
                try:
                    from pala_verification_basis import basis_matches, capture_basis

                    if not basis_matches(expected_basis, capture_basis(self.root)):
                        return ClaimResult("verification_stale", record)
                except (OSError, ValueError, ImportError):
                    return ClaimResult("verification_required", record)
            blockers = record.get("blockers", [])
            if not allowed or blockers:
                return ClaimResult("verification_required", record)
            contract.complete()
            record.update(
                {
                    "lifecycle": "completed",
                    "owner": None,
                    "dirty": False,
                    "updated_at": self._now(),
                }
            )
            record["task_contract"] = contract.to_dict()
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
            record = self._read_ticket(ticket)
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

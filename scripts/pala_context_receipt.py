#!/usr/bin/env python3
"""Typed, deterministic, privacy-safe Context Receipt v1."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import ClassVar, TypeVar

from pala_privacy import has_private_data
from pala_project_snapshot import ProjectSnapshot
from pala_task_contract import STATES as TASK_STATES

CONTEXT_RECEIPT_SCHEMA = "pala.context_receipt.v1"
MAX_RECEIPT_BYTES = 16_384
MAX_COLLECTION_ITEMS = 32
EVIDENCE_STATUSES = (
    "blocked",
    "configured-not-verified",
    "not-run",
    "passed",
)

_AUTHORITY = "ContextReceipt/read-only"
_PERSISTENCE = "not-run"
_INTEGRITY = "sha256-content-digest-not-authenticity"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_SHORT_DIGEST = re.compile(r"^[0-9a-f]{24}$")
_HEAD = re.compile(r"^[0-9a-f]{40}$")
_SENSITIVE_FILENAME = re.compile(
    r"(?i)^(?:\.env(?:\..*)?|id_(?:rsa|dsa|ecdsa|ed25519)|.*\.(?:key|pem|p12|pfx))$"
)


class ContextReceiptError(ValueError):
    """Sanitized, stable failure for untrusted receipt input."""

    def __init__(self, code: str, field: str) -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code} at {field}")

    def finding(self) -> dict[str, str]:
        return {"status": "blocked", "code": self.code, "field": self.field}


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest_mapping(payload: dict[str, object]) -> str:
    """Digest a mapping without including its potentially private values."""
    try:
        encoded = _canonical_json(payload).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContextReceiptError(
            "CONTEXT_RECEIPT_TYPE_INVALID", "active_task.contract"
        ) from exc
    return hashlib.sha256(encoded).hexdigest()


def _mapping(
    value: object,
    field: str,
    required: tuple[str, ...],
) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ContextReceiptError("CONTEXT_RECEIPT_TYPE_INVALID", field)
    keys = set(value)
    missing = sorted(set(required) - keys, key=str.casefold)
    if missing:
        name = f"{field}.{missing[0]}" if field else missing[0]
        raise ContextReceiptError("CONTEXT_RECEIPT_FIELD_MISSING", name)
    unknown = sorted(keys - set(required), key=str.casefold)
    if unknown:
        name = f"{field}.{unknown[0]}" if field else unknown[0]
        raise ContextReceiptError("CONTEXT_RECEIPT_FIELD_UNKNOWN", name)
    return value


def _reject_private_data(value: str, field: str) -> None:
    if has_private_data(value):
        raise ContextReceiptError("CONTEXT_RECEIPT_PRIVATE_DATA_REJECTED", field)


def _text(
    value: object,
    field: str,
    *,
    limit: int = 120,
    identifier: bool = False,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContextReceiptError("CONTEXT_RECEIPT_VALUE_INVALID", field)
    normalized = unicodedata.normalize("NFC", value.strip())
    if len(normalized) > limit:
        raise ContextReceiptError("CONTEXT_RECEIPT_LIMIT_EXCEEDED", field)
    _reject_private_data(normalized, field)
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ContextReceiptError("CONTEXT_RECEIPT_VALUE_INVALID", field)
    if identifier and not _IDENTIFIER.fullmatch(normalized):
        raise ContextReceiptError("CONTEXT_RECEIPT_VALUE_INVALID", field)
    return normalized


def _optional_text(
    value: object,
    field: str,
    *,
    limit: int = 120,
    identifier: bool = False,
) -> str | None:
    if value is None:
        return None
    return _text(value, field, limit=limit, identifier=identifier)


def _digest(value: object, field: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise ContextReceiptError("CONTEXT_RECEIPT_VALUE_INVALID", field)
    return value


def _bounded_sequence(value: object, field: str) -> list[object]:
    if not isinstance(value, (list, tuple)):
        raise ContextReceiptError("CONTEXT_RECEIPT_TYPE_INVALID", field)
    if len(value) > MAX_COLLECTION_ITEMS:
        raise ContextReceiptError("CONTEXT_RECEIPT_LIMIT_EXCEEDED", field)
    return list(value)


def _source_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 240:
        raise ContextReceiptError("CONTEXT_RECEIPT_SOURCE_REF_INVALID", field)
    try:
        _reject_private_data(value, field)
    except ContextReceiptError as exc:
        raise ContextReceiptError(
            "CONTEXT_RECEIPT_SOURCE_REF_INVALID", field
        ) from exc
    normalized = value.replace("\\", "/")
    raw_parts = normalized.split("/")
    path = PurePosixPath(normalized)
    if (
        path.is_absolute()
        or normalized.startswith("//")
        or re.match(r"(?i)^[a-z][a-z0-9+.-]*://", normalized)
        or re.match(r"(?i)^[a-z]:", normalized)
        or any(ord(character) < 32 or ord(character) == 127 for character in normalized)
        or not path.parts
        or any(part in {"", ".", ".."} for part in raw_parts)
        or any(_SENSITIVE_FILENAME.fullmatch(part) for part in path.parts)
    ):
        raise ContextReceiptError("CONTEXT_RECEIPT_SOURCE_REF_INVALID", field)
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class SnapshotBinding:
    repository_id: str
    worktree_id: str
    head: str | None
    head_state: str
    branch: str | None
    git_state: str
    changed_count: int | None
    changed_digest: str | None
    finding_codes: tuple[str, ...]

    _FIELDS: ClassVar[tuple[str, ...]] = (
        "repository_id",
        "worktree_id",
        "head",
        "head_state",
        "branch",
        "git_state",
        "changed_count",
        "changed_digest",
        "finding_codes",
    )

    @classmethod
    def from_snapshot(cls, snapshot: ProjectSnapshot) -> SnapshotBinding:
        if not isinstance(snapshot, ProjectSnapshot):
            raise ContextReceiptError("CONTEXT_RECEIPT_TYPE_INVALID", "snapshot")
        return cls.from_dict(
            {
                "repository_id": snapshot.repository_id,
                "worktree_id": snapshot.worktree_id,
                "head": snapshot.head,
                "head_state": snapshot.head_state,
                "branch": snapshot.branch,
                "git_state": snapshot.git_state,
                "changed_count": snapshot.changed_count,
                "changed_digest": snapshot.changed_digest,
                "finding_codes": list(snapshot.finding_codes),
            }
        )

    @classmethod
    def from_dict(cls, payload: object) -> SnapshotBinding:
        raw = _mapping(payload, "project", cls._FIELDS)
        repository_id = raw["repository_id"]
        worktree_id = raw["worktree_id"]
        if not isinstance(repository_id, str) or not _SHORT_DIGEST.fullmatch(repository_id):
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_VALUE_INVALID", "project.repository_id"
            )
        if not isinstance(worktree_id, str) or not _SHORT_DIGEST.fullmatch(worktree_id):
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_VALUE_INVALID", "project.worktree_id"
            )
        head = raw["head"]
        if head is not None and (not isinstance(head, str) or not _HEAD.fullmatch(head)):
            raise ContextReceiptError("CONTEXT_RECEIPT_VALUE_INVALID", "project.head")
        head_state = _text(raw["head_state"], "project.head_state", identifier=True)
        if head_state not in {"attached", "detached", "unavailable", "unborn"}:
            raise ContextReceiptError("CONTEXT_RECEIPT_VALUE_UNKNOWN", "project.head_state")
        branch = _optional_text(raw["branch"], "project.branch", identifier=True)
        git_state = _text(raw["git_state"], "project.git_state", identifier=True)
        if git_state not in {"clean", "dirty", "unknown"}:
            raise ContextReceiptError("CONTEXT_RECEIPT_VALUE_UNKNOWN", "project.git_state")
        changed_count = raw["changed_count"]
        if changed_count is not None and (
            not isinstance(changed_count, int)
            or isinstance(changed_count, bool)
            or changed_count < 0
        ):
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_TYPE_INVALID", "project.changed_count"
            )
        changed_digest = _digest(
            raw["changed_digest"], "project.changed_digest", optional=True
        )
        if git_state == "unknown" and (
            changed_count is not None or changed_digest is not None
        ):
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_VALUE_INVALID", "project.changed_digest"
            )
        if git_state != "unknown" and (
            changed_count is None or changed_digest is None
        ):
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_VALUE_INVALID", "project.changed_digest"
            )
        if git_state == "clean" and changed_count != 0:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_VALUE_INVALID", "project.changed_count"
            )
        if git_state == "dirty" and (changed_count is None or changed_count < 1):
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_VALUE_INVALID", "project.changed_count"
            )
        if head_state == "attached" and (head is None or branch is None):
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_VALUE_INVALID", "project.head_state"
            )
        if head_state == "detached" and (head is None or branch is not None):
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_VALUE_INVALID", "project.head_state"
            )
        if head_state in {"unavailable", "unborn"} and head is not None:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_VALUE_INVALID", "project.head_state"
            )
        codes = tuple(
            sorted(
                {
                    _text(item, f"project.finding_codes[{index}]", identifier=True)
                    for index, item in enumerate(
                        _bounded_sequence(raw["finding_codes"], "project.finding_codes")
                    )
                },
                key=str.casefold,
            )
        )
        return cls(
            repository_id,
            worktree_id,
            head,
            head_state,
            branch,
            git_state,
            changed_count,
            changed_digest,
            codes,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "repository_id": self.repository_id,
            "worktree_id": self.worktree_id,
            "head": self.head,
            "head_state": self.head_state,
            "branch": self.branch,
            "git_state": self.git_state,
            "changed_count": self.changed_count,
            "changed_digest": self.changed_digest,
            "finding_codes": list(self.finding_codes),
        }


@dataclass(frozen=True, slots=True)
class TaskBinding:
    ticket: str
    status: str
    contract_digest: str

    @classmethod
    def from_dict(cls, payload: object) -> TaskBinding:
        raw = _mapping(
            payload,
            "active_task",
            ("ticket", "status", "contract_digest"),
        )
        ticket = _text(raw["ticket"], "active_task.ticket", identifier=True)
        status = _text(raw["status"], "active_task.status", identifier=True)
        if status not in TASK_STATES:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_VALUE_UNKNOWN", "active_task.status"
            )
        contract_digest = _digest(raw["contract_digest"], "active_task.contract_digest")
        return cls(ticket, status, str(contract_digest))

    def to_dict(self) -> dict[str, str]:
        return {
            "ticket": self.ticket,
            "status": self.status,
            "contract_digest": self.contract_digest,
        }


@dataclass(frozen=True, slots=True)
class SourceRef:
    path: str
    digest: str

    @classmethod
    def from_dict(cls, payload: object, field: str) -> SourceRef:
        raw = _mapping(payload, field, ("path", "digest"))
        path = _source_path(raw["path"], f"{field}.path")
        digest = _digest(raw["digest"], f"{field}.digest")
        return cls(path, str(digest))

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "digest": self.digest}


@dataclass(frozen=True, slots=True)
class ContextExpectation:
    """Trusted current basis used to reject stale self-asserted receipts."""

    project: SnapshotBinding
    active_task: TaskBinding
    profile_digest: str | None
    source_refs: tuple[SourceRef, ...]

    @classmethod
    def create(
        cls,
        *,
        snapshot: ProjectSnapshot,
        active_task: dict[str, object],
        profile_digest: str | None,
        source_refs: list[object] | tuple[object, ...],
    ) -> ContextExpectation:
        refs = tuple(
            SourceRef.from_dict(item, f"source_refs[{index}]")
            for index, item in enumerate(
                _bounded_sequence(source_refs, "source_refs")
            )
        )
        by_path: dict[str, SourceRef] = {}
        for item in refs:
            key = item.path.casefold()
            prior = by_path.get(key)
            if prior is not None and prior != item:
                raise ContextReceiptError(
                    "CONTEXT_RECEIPT_SOURCE_REF_INVALID", "source_refs"
                )
            by_path[key] = item
        return cls(
            project=SnapshotBinding.from_snapshot(snapshot),
            active_task=TaskBinding.from_dict(active_task),
            profile_digest=_digest(
                profile_digest, "profile_digest", optional=True
            ),
            source_refs=tuple(
                sorted(by_path.values(), key=lambda item: item.path.casefold())
            ),
        )


@dataclass(frozen=True, slots=True)
class CapabilitySummary:
    name: str
    status: str
    evidence_ref: str | None

    @classmethod
    def from_dict(cls, payload: object, field: str) -> CapabilitySummary:
        raw = _mapping(payload, field, ("name", "status", "evidence_ref"))
        name = _text(raw["name"], f"{field}.name", identifier=True)
        status = _text(raw["status"], f"{field}.status", identifier=True)
        if status not in EVIDENCE_STATUSES:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_EVIDENCE_INVALID", f"{field}.status"
            )
        evidence_ref = _optional_text(
            raw["evidence_ref"], f"{field}.evidence_ref", identifier=True
        )
        if status == "passed" and evidence_ref is None:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_EVIDENCE_INVALID", f"{field}.evidence_ref"
            )
        if status == "not-run" and evidence_ref is not None:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_EVIDENCE_INVALID", f"{field}.evidence_ref"
            )
        return cls(name, status, evidence_ref)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class VerificationSummary:
    check_id: str
    status: str
    exit_code: int | None
    evidence_ref: str | None

    @classmethod
    def from_dict(cls, payload: object, field: str) -> VerificationSummary:
        raw = _mapping(
            payload,
            field,
            ("check_id", "status", "exit_code", "evidence_ref"),
        )
        check_id = _text(raw["check_id"], f"{field}.check_id", identifier=True)
        status = _text(raw["status"], f"{field}.status", identifier=True)
        if status not in EVIDENCE_STATUSES:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_EVIDENCE_INVALID", f"{field}.status"
            )
        exit_code = raw["exit_code"]
        if exit_code is not None and (
            not isinstance(exit_code, int) or isinstance(exit_code, bool)
        ):
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_EVIDENCE_INVALID", f"{field}.exit_code"
            )
        evidence_ref = _optional_text(
            raw["evidence_ref"], f"{field}.evidence_ref", identifier=True
        )
        if status == "passed":
            if exit_code != 0:
                raise ContextReceiptError(
                    "CONTEXT_RECEIPT_EVIDENCE_INVALID", f"{field}.exit_code"
                )
            if evidence_ref is None:
                raise ContextReceiptError(
                    "CONTEXT_RECEIPT_EVIDENCE_INVALID", f"{field}.evidence_ref"
                )
        elif status == "not-run":
            if exit_code is not None:
                raise ContextReceiptError(
                    "CONTEXT_RECEIPT_EVIDENCE_INVALID", f"{field}.exit_code"
                )
            if evidence_ref is not None:
                raise ContextReceiptError(
                    "CONTEXT_RECEIPT_EVIDENCE_INVALID", f"{field}.evidence_ref"
                )
        return cls(check_id, status, exit_code, evidence_ref)

    def to_dict(self) -> dict[str, object]:
        return {
            "check_id": self.check_id,
            "status": self.status,
            "exit_code": self.exit_code,
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class ContextReceipt:
    project: SnapshotBinding
    active_task: TaskBinding
    profile_digest: str | None
    source_refs: tuple[SourceRef, ...]
    capabilities: tuple[CapabilitySummary, ...]
    verifications: tuple[VerificationSummary, ...]
    risk_codes: tuple[str, ...]
    next_action: str
    receipt_id: str
    schema_version: str = CONTEXT_RECEIPT_SCHEMA

    _FIELDS: ClassVar[tuple[str, ...]] = (
        "schema_version",
        "project",
        "active_task",
        "profile_digest",
        "source_refs",
        "capabilities",
        "verifications",
        "risk_codes",
        "next_action",
        "authority",
        "persistence",
        "integrity",
        "can_complete",
        "receipt_id",
    )

    @classmethod
    def create(
        cls,
        *,
        snapshot: ProjectSnapshot,
        active_task: dict[str, object],
        profile_digest: str | None,
        source_refs: list[object] | tuple[object, ...],
        capabilities: list[object] | tuple[object, ...],
        verifications: list[object] | tuple[object, ...],
        risk_codes: list[object] | tuple[object, ...],
        next_action: str,
    ) -> ContextReceipt:
        body = {
            "schema_version": CONTEXT_RECEIPT_SCHEMA,
            "project": SnapshotBinding.from_snapshot(snapshot).to_dict(),
            "active_task": active_task,
            "profile_digest": profile_digest,
            "source_refs": list(source_refs),
            "capabilities": list(capabilities),
            "verifications": list(verifications),
            "risk_codes": list(risk_codes),
            "next_action": next_action,
            "authority": _AUTHORITY,
            "persistence": _PERSISTENCE,
            "integrity": _INTEGRITY,
            "can_complete": False,
        }
        parsed = cls._parse_body(body)
        receipt_id = hashlib.sha256(
            _canonical_json(parsed).encode("utf-8")
        ).hexdigest()
        return cls._from_parsed(parsed, receipt_id)

    @classmethod
    def from_dict(
        cls,
        payload: object,
        *,
        expected: ContextExpectation | None = None,
        expected_snapshot: ProjectSnapshot | None = None,
    ) -> ContextReceipt:
        raw = _mapping(payload, "", cls._FIELDS)
        try:
            payload_bytes = len(_canonical_json(raw).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_TYPE_INVALID", "receipt"
            ) from exc
        if payload_bytes > MAX_RECEIPT_BYTES:
            raise ContextReceiptError("CONTEXT_RECEIPT_LIMIT_EXCEEDED", "receipt")
        supplied_id = raw["receipt_id"]
        if not isinstance(supplied_id, str) or not _DIGEST.fullmatch(supplied_id):
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_VALUE_INVALID", "receipt_id"
            )
        body = {key: value for key, value in raw.items() if key != "receipt_id"}
        parsed = cls._parse_body(body)
        expected_id = hashlib.sha256(
            _canonical_json(parsed).encode("utf-8")
        ).hexdigest()
        if supplied_id != expected_id:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_DIGEST_MISMATCH", "receipt_id"
            )
        result = cls._from_parsed(parsed, supplied_id)
        if expected is not None:
            result._require_expectation(expected)
        elif expected_snapshot is not None:
            result._require_snapshot(expected_snapshot)
        return result

    @classmethod
    def _parse_body(cls, payload: dict[str, object]) -> dict[str, object]:
        required = tuple(item for item in cls._FIELDS if item != "receipt_id")
        raw = _mapping(payload, "", required)
        if raw["schema_version"] != CONTEXT_RECEIPT_SCHEMA:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_SCHEMA_UNSUPPORTED", "schema_version"
            )
        if raw["authority"] != _AUTHORITY:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_AUTHORITY_INVALID", "authority"
            )
        if raw["persistence"] != _PERSISTENCE:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_AUTHORITY_INVALID", "persistence"
            )
        if raw["integrity"] != _INTEGRITY:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_AUTHORITY_INVALID", "integrity"
            )
        if raw["can_complete"] is not False:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_AUTHORITY_INVALID", "can_complete"
            )
        project = SnapshotBinding.from_dict(raw["project"])
        active_task = TaskBinding.from_dict(raw["active_task"])
        profile_digest = _digest(
            raw["profile_digest"], "profile_digest", optional=True
        )
        source_refs = tuple(
            SourceRef.from_dict(item, f"source_refs[{index}]")
            for index, item in enumerate(
                _bounded_sequence(raw["source_refs"], "source_refs")
            )
        )
        source_by_path: dict[str, SourceRef] = {}
        for item in source_refs:
            key = item.path.casefold()
            prior = source_by_path.get(key)
            if prior is not None and prior != item:
                raise ContextReceiptError(
                    "CONTEXT_RECEIPT_SOURCE_REF_INVALID", "source_refs"
                )
            source_by_path[key] = item
        source_refs = tuple(
            sorted(source_by_path.values(), key=lambda item: item.path.casefold())
        )
        capabilities = tuple(
            CapabilitySummary.from_dict(item, f"capabilities[{index}]")
            for index, item in enumerate(
                _bounded_sequence(raw["capabilities"], "capabilities")
            )
        )
        capabilities = _unique_named(capabilities, "capabilities", lambda item: item.name)
        verifications = tuple(
            VerificationSummary.from_dict(item, f"verifications[{index}]")
            for index, item in enumerate(
                _bounded_sequence(raw["verifications"], "verifications")
            )
        )
        verifications = _unique_named(
            verifications, "verifications", lambda item: item.check_id
        )
        risk_codes = tuple(
            sorted(
                {
                    _text(item, f"risk_codes[{index}]", identifier=True)
                    for index, item in enumerate(
                        _bounded_sequence(raw["risk_codes"], "risk_codes")
                    )
                },
                key=str.casefold,
            )
        )
        next_action = _text(
            raw["next_action"], "next_action", limit=240, identifier=True
        )
        result = {
            "schema_version": CONTEXT_RECEIPT_SCHEMA,
            "project": project.to_dict(),
            "active_task": active_task.to_dict(),
            "profile_digest": profile_digest,
            "source_refs": [item.to_dict() for item in source_refs],
            "capabilities": [item.to_dict() for item in capabilities],
            "verifications": [item.to_dict() for item in verifications],
            "risk_codes": list(risk_codes),
            "next_action": next_action,
            "authority": _AUTHORITY,
            "persistence": _PERSISTENCE,
            "integrity": _INTEGRITY,
            "can_complete": False,
        }
        if len(_canonical_json(result).encode("utf-8")) > MAX_RECEIPT_BYTES:
            raise ContextReceiptError("CONTEXT_RECEIPT_LIMIT_EXCEEDED", "receipt")
        return result

    @classmethod
    def _from_parsed(
        cls, parsed: dict[str, object], receipt_id: str
    ) -> ContextReceipt:
        return cls(
            project=SnapshotBinding.from_dict(parsed["project"]),
            active_task=TaskBinding.from_dict(parsed["active_task"]),
            profile_digest=parsed["profile_digest"]
            if isinstance(parsed["profile_digest"], str)
            else None,
            source_refs=tuple(
                SourceRef.from_dict(item, f"source_refs[{index}]")
                for index, item in enumerate(parsed["source_refs"])
            ),
            capabilities=tuple(
                CapabilitySummary.from_dict(item, f"capabilities[{index}]")
                for index, item in enumerate(parsed["capabilities"])
            ),
            verifications=tuple(
                VerificationSummary.from_dict(item, f"verifications[{index}]")
                for index, item in enumerate(parsed["verifications"])
            ),
            risk_codes=tuple(str(item) for item in parsed["risk_codes"]),
            next_action=str(parsed["next_action"]),
            receipt_id=receipt_id,
        )

    def _require_snapshot(self, expected: ProjectSnapshot) -> None:
        self._require_snapshot_binding(SnapshotBinding.from_snapshot(expected))

    def _require_expectation(self, expected: ContextExpectation) -> None:
        if not isinstance(expected, ContextExpectation):
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_TYPE_INVALID", "expected"
            )
        self._require_snapshot_binding(expected.project)
        comparisons = (
            (self.active_task.ticket, expected.active_task.ticket, "active_task.ticket"),
            (self.active_task.status, expected.active_task.status, "active_task.status"),
            (
                self.active_task.contract_digest,
                expected.active_task.contract_digest,
                "active_task.contract_digest",
            ),
            (self.profile_digest, expected.profile_digest, "profile_digest"),
            (self.source_refs, expected.source_refs, "source_refs"),
        )
        for actual, current, field in comparisons:
            if actual != current:
                raise ContextReceiptError(
                    "CONTEXT_RECEIPT_CONTEXT_MISMATCH", field
                )

    def _require_snapshot_binding(self, observed: SnapshotBinding) -> None:
        fields = (
            "repository_id",
            "worktree_id",
            "head",
            "head_state",
            "branch",
            "git_state",
            "changed_count",
            "changed_digest",
            "finding_codes",
        )
        for field in fields:
            if getattr(self.project, field) != getattr(observed, field):
                raise ContextReceiptError(
                    "CONTEXT_RECEIPT_SNAPSHOT_MISMATCH", f"project.{field}"
                )

    def _body_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project": self.project.to_dict(),
            "active_task": self.active_task.to_dict(),
            "profile_digest": self.profile_digest,
            "source_refs": [item.to_dict() for item in self.source_refs],
            "capabilities": [item.to_dict() for item in self.capabilities],
            "verifications": [item.to_dict() for item in self.verifications],
            "risk_codes": list(self.risk_codes),
            "next_action": self.next_action,
            "authority": _AUTHORITY,
            "persistence": _PERSISTENCE,
            "integrity": _INTEGRITY,
            "can_complete": False,
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._body_dict(), "receipt_id": self.receipt_id}

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())


_T = TypeVar("_T")


def _unique_named(
    items: tuple[_T, ...],
    field: str,
    name: Callable[[_T], str],
) -> tuple[_T, ...]:
    by_name: dict[str, _T] = {}
    for item in items:
        key = name(item).casefold()
        prior = by_name.get(key)
        if prior is not None and prior != item:
            raise ContextReceiptError("CONTEXT_RECEIPT_EVIDENCE_INVALID", field)
        by_name[key] = item
    return tuple(sorted(by_name.values(), key=lambda item: name(item).casefold()))


def receipt_summary(
    payload: ContextReceipt | dict[str, object],
    *,
    expected: ContextExpectation | None = None,
    expected_snapshot: ProjectSnapshot | None = None,
) -> dict[str, object]:
    """Return a bounded read model; never expose sources or decide completion."""
    try:
        if expected is None and expected_snapshot is None:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_EXPECTATION_REQUIRED", "expected"
            )
        value = (
            payload
            if isinstance(payload, ContextReceipt)
            else ContextReceipt.from_dict(
                payload,
                expected=expected,
                expected_snapshot=expected_snapshot,
            )
        )
        if isinstance(payload, ContextReceipt):
            if expected is not None:
                value._require_expectation(expected)
            elif expected_snapshot is not None:
                value._require_snapshot(expected_snapshot)
        if value.project.git_state == "unknown" or value.project.finding_codes:
            raise ContextReceiptError(
                "CONTEXT_RECEIPT_SNAPSHOT_UNVERIFIABLE", "project.git_state"
            )
    except ContextReceiptError as exc:
        return {
            "schema_version": CONTEXT_RECEIPT_SCHEMA,
            "validation_status": "blocked",
            "finding": exc.finding(),
            "can_complete": False,
            "authority": _AUTHORITY,
        }
    counts = {status: 0 for status in EVIDENCE_STATUSES}
    for item in value.verifications:
        counts[item.status] += 1
    return {
        "schema_version": value.schema_version,
        "validation_status": "passed",
        "receipt_id": value.receipt_id,
        "integrity": _INTEGRITY,
        "repository_id": value.project.repository_id,
        "worktree_id": value.project.worktree_id,
        "active_ticket": value.active_task.ticket,
        "task_status": value.active_task.status,
        "verification_counts": counts,
        "risk_count": len(value.risk_codes),
        "can_complete": False,
        "authority": _AUTHORITY,
    }

#!/usr/bin/env python3
"""Immutable, privacy-safe delegation boundary for host-provided workers."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import ClassVar

from pala_privacy import private_data_reason

SUBAGENT_TASK_SCHEMA = "pala.subagent_task_contract.v1"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,119}")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_SHORT_DIGEST = re.compile(r"[0-9a-f]{24}")


def _text(value: object, field: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"invalid {field}")
    if private_data_reason(value):
        raise ValueError(f"private data rejected in {field}")
    return value


def _items(values: object, field: str, pattern: re.Pattern[str]) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError(f"{field} must be a non-empty list")
    items = tuple(_text(item, field, pattern) for item in values)
    if len({item.casefold() for item in items}) != len(items):
        raise ValueError(f"duplicate {field}")
    return tuple(sorted(items, key=str.casefold))


def _scope(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 240:
        raise ValueError(f"invalid {field}")
    if private_data_reason(value):
        raise ValueError(f"private data rejected in {field}")
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe {field}")
    if field != "deny_scope" and path.name.casefold() in {
        ".env",
        "credentials.json",
        "id_rsa",
        "id_ed25519",
    }:
        raise ValueError(f"sensitive {field}")
    return path.as_posix()


def _scopes(values: object, field: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or (not values and not allow_empty):
        raise ValueError(f"invalid {field} list")
    items = tuple(_scope(item, field) for item in values)
    if len({item.casefold() for item in items}) != len(items):
        raise ValueError(f"duplicate {field}")
    return tuple(sorted(items, key=str.casefold))


def _overlaps(left: str, right: str) -> bool:
    left_key, right_key = left.casefold(), right.casefold()
    return (
        left_key == right_key
        or left_key.startswith(right_key + "/")
        or right_key.startswith(left_key + "/")
    )


def _within(path: str, boundary: str) -> bool:
    path_key, boundary_key = path.casefold(), boundary.casefold()
    return path_key == boundary_key or path_key.startswith(boundary_key + "/")


@dataclass(frozen=True, slots=True)
class SubagentTaskContract:
    schema_version: str
    delegation_id: str
    task_id: str
    parent_task_id: str
    task_contract_digest: str
    context_receipt_id: str
    repository_id: str
    worktree_id: str
    requested_capabilities: tuple[str, ...]
    read_scope: tuple[str, ...]
    write_scope: tuple[str, ...]
    deny_scope: tuple[str, ...]
    acceptance_ids: tuple[str, ...]
    verification_check_ids: tuple[str, ...]
    execution_mode: str
    integration_mode: str
    can_complete: bool = False

    _FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_version",
            "delegation_id",
            "task_id",
            "parent_task_id",
            "task_contract_digest",
            "context_receipt_id",
            "repository_id",
            "worktree_id",
            "requested_capabilities",
            "read_scope",
            "write_scope",
            "deny_scope",
            "acceptance_ids",
            "verification_check_ids",
            "execution_mode",
            "integration_mode",
            "can_complete",
        }
    )

    @classmethod
    def create(
        cls,
        *,
        task_id: str,
        parent_task_id: str,
        task_contract_digest: str,
        context_receipt_id: str,
        repository_id: str,
        worktree_id: str,
        requested_capabilities: list[str] | tuple[str, ...],
        read_scope: list[str] | tuple[str, ...],
        write_scope: list[str] | tuple[str, ...],
        deny_scope: list[str] | tuple[str, ...],
        acceptance_ids: list[str] | tuple[str, ...],
        verification_check_ids: list[str] | tuple[str, ...],
        execution_mode: str,
        integration_mode: str,
    ) -> SubagentTaskContract:
        read_values = _scopes(read_scope, "read_scope")
        write_values = _scopes(write_scope, "write_scope", allow_empty=True)
        deny_values = _scopes(deny_scope, "deny_scope", allow_empty=True)
        values = {
            "schema_version": SUBAGENT_TASK_SCHEMA,
            "task_id": _text(task_id, "task_id", _ID),
            "parent_task_id": _text(parent_task_id, "parent_task_id", _ID),
            "task_contract_digest": _text(task_contract_digest, "task_contract_digest", _DIGEST),
            "context_receipt_id": _text(context_receipt_id, "context_receipt_id", _DIGEST),
            "repository_id": _text(repository_id, "repository_id", _SHORT_DIGEST),
            "worktree_id": _text(worktree_id, "worktree_id", _SHORT_DIGEST),
            "requested_capabilities": _items(requested_capabilities, "requested_capabilities", _ID),
            "read_scope": read_values,
            "write_scope": write_values,
            "deny_scope": deny_values,
            "acceptance_ids": _items(acceptance_ids, "acceptance_ids", _ID),
            "verification_check_ids": _items(
                verification_check_ids, "verification_check_ids", _ID
            ),
            "execution_mode": execution_mode,
            "integration_mode": integration_mode,
            "can_complete": False,
        }
        if execution_mode not in {"read-only", "writer"}:
            raise ValueError("invalid execution mode")
        if (execution_mode == "writer") != bool(write_values):
            raise ValueError("execution mode and write scope disagree")
        if integration_mode != "candidate-only":
            raise ValueError("integration mode must be candidate-only")
        if any(
            _overlaps(write_path, denied_path)
            for write_path in write_values
            for denied_path in deny_values
        ):
            raise ValueError("write scope conflicts with deny scope")
        body = json.dumps(values, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        delegation_id = hashlib.sha256(body.encode("utf-8")).hexdigest()
        return cls(delegation_id=delegation_id, **values)  # type: ignore[arg-type]

    @classmethod
    def from_dict(cls, payload: object) -> SubagentTaskContract:
        if not isinstance(payload, dict) or set(payload) != cls._FIELDS:
            raise ValueError("invalid delegation contract fields")
        if (
            payload.get("schema_version") != SUBAGENT_TASK_SCHEMA
            or payload.get("can_complete") is not False
        ):
            raise ValueError("invalid delegation contract authority")
        excluded = {"schema_version", "delegation_id", "can_complete"}
        created = cls.create(
            **{key: payload[key] for key in cls._FIELDS if key not in excluded}
        )
        if payload.get("delegation_id") != created.delegation_id:
            raise ValueError("delegation contract digest mismatch")
        return created

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "delegation_id": self.delegation_id,
            "task_id": self.task_id,
            "parent_task_id": self.parent_task_id,
            "task_contract_digest": self.task_contract_digest,
            "context_receipt_id": self.context_receipt_id,
            "repository_id": self.repository_id,
            "worktree_id": self.worktree_id,
            "requested_capabilities": list(self.requested_capabilities),
            "read_scope": list(self.read_scope),
            "write_scope": list(self.write_scope),
            "deny_scope": list(self.deny_scope),
            "acceptance_ids": list(self.acceptance_ids),
            "verification_check_ids": list(self.verification_check_ids),
            "execution_mode": self.execution_mode,
            "integration_mode": self.integration_mode,
            "can_complete": False,
        }

    def validate_candidate(self, changed_paths: list[str] | tuple[str, ...]) -> dict[str, object]:
        changed = _scopes(changed_paths, "changed_paths", allow_empty=True)
        if self.execution_mode == "read-only" and changed:
            raise ValueError("read-only delegation produced changes")
        if any(
            not any(_within(path, allowed) for allowed in self.write_scope)
            for path in changed
        ):
            raise ValueError("candidate scope violation")
        return {
            "delegation_id": self.delegation_id,
            "status": "awaiting_primary_review",
            "changed_paths": list(changed),
            "can_complete": False,
        }

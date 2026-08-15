#!/usr/bin/env python3
"""Evidence-backed host capability observation and candidate-only routing."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass

from pala_execution import ExecutionConflictError, ExecutionCoordinator
from pala_privacy import private_data_reason
from pala_subagent_contract import SubagentTaskContract

HOST_CAPABILITY_SCHEMA = "pala.host_capability_snapshot.v1"
CAPABILITIES = frozenset(
    {"browser", "isolated_worktree", "local_edit", "local_read", "process_control", "subagents"}
)


class HostCapabilityError(ValueError):
    """A sanitized, stable host-routing failure."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code.replace("_", " ").lower())


@dataclass(frozen=True, slots=True)
class CapabilityObservation:
    capability_id: str
    status: str
    evidence_ref: str

    def to_dict(self) -> dict[str, str]:
        return {
            "capability_id": self.capability_id,
            "status": self.status,
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class HostCapabilitySnapshot:
    schema_version: str
    snapshot_id: str
    host_kind: str
    max_concurrency: int
    capabilities: tuple[CapabilityObservation, ...]
    authority: str = "HostCapabilitySnapshot/read-only"
    can_complete: bool = False

    @classmethod
    def from_dict(cls, payload: object) -> HostCapabilitySnapshot:
        """Accept only an intact, bounded observation from the host boundary."""
        if not isinstance(payload, dict) or set(payload) != {
            "schema_version", "snapshot_id", "host_kind", "max_concurrency",
            "capabilities", "authority", "can_complete",
        }:
            raise HostCapabilityError("SNAPSHOT_INVALID")
        if (
            payload.get("schema_version") != HOST_CAPABILITY_SCHEMA
            or payload.get("host_kind") != "codex"
            or payload.get("authority") != "HostCapabilitySnapshot/read-only"
            or payload.get("can_complete") is not False
        ):
            raise HostCapabilityError("SNAPSHOT_INVALID")
        max_concurrency = payload.get("max_concurrency")
        if (
            isinstance(max_concurrency, bool)
            or not isinstance(max_concurrency, int)
            or not 1 <= max_concurrency <= 64
        ):
            raise HostCapabilityError("CONCURRENCY_INVALID")
        raw_capabilities = payload.get("capabilities")
        if not isinstance(raw_capabilities, list) or len(raw_capabilities) != len(CAPABILITIES):
            raise HostCapabilityError("SNAPSHOT_INVALID")
        observations: list[CapabilityObservation] = []
        for raw in raw_capabilities:
            if not isinstance(raw, dict) or set(raw) != {
                "capability_id", "status", "evidence_ref",
            }:
                raise HostCapabilityError("SNAPSHOT_INVALID")
            capability_id = raw.get("capability_id")
            status = raw.get("status")
            evidence_ref = raw.get("evidence_ref")
            if (
                not isinstance(capability_id, str)
                or capability_id not in CAPABILITIES
                or status not in {"passed", "not-run"}
                or not isinstance(evidence_ref, str)
                or not evidence_ref
                or len(evidence_ref) > 160
                or private_data_reason(evidence_ref)
            ):
                raise HostCapabilityError("SNAPSHOT_INVALID")
            observations.append(CapabilityObservation(capability_id, status, evidence_ref))
        if [item.capability_id for item in observations] != sorted(CAPABILITIES):
            raise HostCapabilityError("SNAPSHOT_INVALID")
        body = {
            "schema_version": HOST_CAPABILITY_SCHEMA,
            "host_kind": "codex",
            "max_concurrency": max_concurrency,
            "capabilities": [item.to_dict() for item in observations],
            "authority": "HostCapabilitySnapshot/read-only",
            "can_complete": False,
        }
        expected_id = hashlib.sha256(
            json.dumps(
                body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("utf-8")
        ).hexdigest()
        if payload.get("snapshot_id") != expected_id:
            raise HostCapabilityError("SNAPSHOT_DIGEST_MISMATCH")
        return cls(
            HOST_CAPABILITY_SCHEMA, expected_id, "codex", max_concurrency, tuple(observations)
        )

    def status_of(self, capability_id: str) -> str:
        for observation in self.capabilities:
            if observation.capability_id == capability_id:
                return observation.status
        return "unsupported"

    def evidence_for(self, capability_id: str) -> str | None:
        for observation in self.capabilities:
            if observation.capability_id == capability_id:
                return observation.evidence_ref
        return None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "host_kind": self.host_kind,
            "max_concurrency": self.max_concurrency,
            "capabilities": [item.to_dict() for item in self.capabilities],
            "authority": self.authority,
            "can_complete": False,
        }


@dataclass(frozen=True, slots=True)
class BrokerDecision:
    status: str
    selected_capability: str
    evidence_refs: tuple[str, ...]
    finding_codes: tuple[str, ...]
    authority: str = "HostCapabilityBroker/read-only"
    can_complete: bool = False


def _tool_name(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.rsplit(".", 1)[-1].rsplit("__", 1)[-1]


def observe_codex_host(
    *,
    available_tools: Iterable[str],
    evidence_ref: str,
    max_concurrency: int,
    git_worktree_supported: bool = False,
) -> HostCapabilitySnapshot:
    """Convert the caller-observed Codex tool inventory into a safe snapshot."""
    if (
        not isinstance(evidence_ref, str)
        or not evidence_ref
        or len(evidence_ref) > 160
        or private_data_reason(evidence_ref)
    ):
        raise HostCapabilityError("PRIVATE_DATA_REJECTED")
    if (
        isinstance(max_concurrency, bool)
        or not isinstance(max_concurrency, int)
        or not 1 <= max_concurrency <= 64
    ):
        raise HostCapabilityError("CONCURRENCY_INVALID")
    raw_tools = tuple(available_tools)
    if len(raw_tools) > 256 or any(
        not isinstance(item, str) or not item for item in raw_tools
    ):
        raise HostCapabilityError("PRIVATE_DATA_REJECTED")
    tool_values = tuple(str(item) for item in raw_tools)
    if any(private_data_reason(item) for item in tool_values):
        raise HostCapabilityError("PRIVATE_DATA_REJECTED")
    tools = frozenset(filter(None, (_tool_name(item) for item in tool_values)))
    required = {
        "browser": frozenset({"browser_navigate", "browser_snapshot"}),
        "local_edit": frozenset({"apply_patch"}),
        "local_read": frozenset({"shell_command"}),
        "process_control": frozenset({"shell_command"}),
        "subagents": frozenset({"spawn_agent", "send_message", "wait_agent"}),
    }
    observations: list[CapabilityObservation] = []
    for capability_id in sorted(CAPABILITIES):
        if capability_id == "isolated_worktree":
            passed = git_worktree_supported is True
        else:
            passed = required[capability_id].issubset(tools)
        observations.append(
            CapabilityObservation(capability_id, "passed" if passed else "not-run", evidence_ref)
        )
    body = {
        "schema_version": HOST_CAPABILITY_SCHEMA,
        "host_kind": "codex",
        "max_concurrency": max_concurrency,
        "capabilities": [item.to_dict() for item in observations],
        "authority": "HostCapabilitySnapshot/read-only",
        "can_complete": False,
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return HostCapabilitySnapshot(
        HOST_CAPABILITY_SCHEMA,
        hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "codex",
        max_concurrency,
        tuple(observations),
    )


class HostCapabilityBroker:
    """Route verified capabilities; never make TaskContract completion decisions."""

    def __init__(
        self,
        snapshot: HostCapabilitySnapshot,
        coordinator: ExecutionCoordinator | None = None,
    ) -> None:
        self.snapshot = snapshot
        self.coordinator = coordinator or ExecutionCoordinator(
            max_concurrency=snapshot.max_concurrency, case_sensitive=False
        )
        self._submitted_delegations: set[str] = set()

    def route(
        self,
        capabilities: Iterable[str],
        *,
        fallback_capabilities: Iterable[str] = (),
    ) -> BrokerDecision:
        requested = tuple(capabilities)
        fallback = tuple(fallback_capabilities)
        for capability_id in requested:
            if self.snapshot.status_of(capability_id) == "passed":
                evidence = self.snapshot.evidence_for(capability_id)
                return BrokerDecision(
                    "selected", capability_id, (evidence,) if evidence else (), ()
                )
        for capability_id in fallback:
            if self.snapshot.status_of(capability_id) == "passed":
                evidence = self.snapshot.evidence_for(capability_id)
                return BrokerDecision(
                    "fallback",
                    capability_id,
                    (evidence,) if evidence else (),
                    ("CAPABILITY_FALLBACK",),
                )
        known = [item for item in requested + fallback if item in CAPABILITIES]
        raise HostCapabilityError("CAPABILITY_UNVERIFIED" if known else "CAPABILITY_UNSUPPORTED")

    def reserve(
        self,
        task: SubagentTaskContract,
        *,
        capability: str,
        live_repository_id: str,
        live_worktree_id: str,
        expected_context_receipt_id: str,
        parent_write_scope: Iterable[str],
    ) -> BrokerDecision:
        if capability not in task.requested_capabilities:
            raise HostCapabilityError("CAPABILITY_NOT_REQUESTED")
        decision = self.route([capability])
        if task.repository_id != live_repository_id:
            raise HostCapabilityError("REPOSITORY_MISMATCH")
        if task.worktree_id != live_worktree_id:
            raise HostCapabilityError("WORKTREE_MISMATCH")
        if task.context_receipt_id != expected_context_receipt_id:
            raise HostCapabilityError("CONTEXT_RECEIPT_MISMATCH")
        parent_scope = tuple(parent_write_scope)
        if task.execution_mode == "writer" and any(
            not any(_path_within(path, allowed) for allowed in parent_scope)
            for path in task.write_scope
        ):
            raise HostCapabilityError("PARENT_SCOPE_ESCAPE")
        try:
            surface = (
                list(task.write_scope)
                if task.write_scope
                else [f".pala-read-only/{task.delegation_id}"]
            )
            self.coordinator.claim(
                task.task_id,
                task.delegation_id,
                surface,
                worktree=task.worktree_id,
            )
        except ExecutionConflictError as exc:
            raise HostCapabilityError(exc.code) from None
        return decision

    def release(self, task: SubagentTaskContract) -> None:
        try:
            self.coordinator.release(task.task_id, task.delegation_id)
            self._submitted_delegations.discard(task.delegation_id)
        except ExecutionConflictError as exc:
            raise HostCapabilityError(exc.code) from None

    def submit_candidate(
        self,
        task: SubagentTaskContract,
        candidate: dict[str, object],
        *,
        changed_paths: Iterable[str],
    ) -> dict[str, object]:
        """Hand a scoped result to the primary reviewer, never to completion."""
        if (
            not isinstance(candidate, dict)
            or not candidate
            or any(key in candidate for key in ("authority", "can_complete"))
            or candidate.get("canonical_done") not in (None, False)
            or any(private_data_reason(str(value)) for value in candidate.values())
        ):
            raise HostCapabilityError("CANDIDATE_AUTHORITY_REJECTED")
        if task.delegation_id in self._submitted_delegations:
            raise HostCapabilityError("CANDIDATE_ALREADY_SUBMITTED")
        try:
            review = task.validate_candidate(tuple(changed_paths))
            bounded_candidate = {
                key: value for key, value in candidate.items() if key != "canonical_done"
            }
            self.coordinator.submit_candidate(task.task_id, task.delegation_id, bounded_candidate)
        except (ExecutionConflictError, ValueError) as exc:
            code = getattr(exc, "code", "CANDIDATE_NOT_RESERVED")
            raise HostCapabilityError(code) from None
        self._submitted_delegations.add(task.delegation_id)
        return review


def _paths_overlap(left: str, right: str) -> bool:
    left_key, right_key = left.casefold(), right.casefold()
    return (
        left_key == right_key
        or left_key.startswith(right_key + "/")
        or right_key.startswith(left_key + "/")
    )


def _path_within(path: str, boundary: str) -> bool:
    path_key, boundary_key = path.casefold(), boundary.replace("\\", "/").casefold()
    return path_key == boundary_key or path_key.startswith(boundary_key + "/")

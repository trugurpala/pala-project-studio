#!/usr/bin/env python3
"""Privacy-safe runtime observations for Control Center read models."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pala_authority import (
    atomic_json_write,
    repository_instance,
    runtime_repositories_root,
    shared_state_root,
)
from pala_host_capability_broker import HostCapabilityError, HostCapabilitySnapshot
from pala_privacy import private_data_reason
from pala_process_supervisor import PROCESS_EVIDENCE_SCHEMA, ProcessEvidence

RUNTIME_OBSERVATION_SCHEMA = "pala.runtime_observations.v1"
MAX_PROCESS_ITEMS = 8
_PROCESS_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
_FINDING_CODE = re.compile(r"[A-Z][A-Z0-9_]{1,79}\Z")


class RuntimeObservationError(ValueError):
    """Sanitized validation failure for non-authoritative observations."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code.replace("_", " ").lower())


def runtime_observation_path(root: Path) -> Path:
    """Resolve without creating runtime directories or migration markers."""
    return (
        runtime_repositories_root()
        / repository_instance(Path(root).resolve())
        / "generated"
        / "runtime-observations.json"
    )


def _empty_storage() -> dict[str, object]:
    return {
        "schema_version": RUNTIME_OBSERVATION_SCHEMA,
        "host_snapshot": None,
        "processes": [],
    }


def _load_storage(root: Path) -> dict[str, object]:
    path = runtime_observation_path(root)
    if not path.is_file():
        return _empty_storage()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeObservationError("RUNTIME_OBSERVATION_INVALID") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != RUNTIME_OBSERVATION_SCHEMA
        or set(payload) != {"schema_version", "host_snapshot", "processes"}
        or not isinstance(payload.get("processes"), list)
    ):
        raise RuntimeObservationError("RUNTIME_OBSERVATION_INVALID")
    return payload


def _write_storage(root: Path, payload: dict[str, object]) -> None:
    runtime_root = shared_state_root(Path(root).resolve())
    if runtime_root is None:
        raise RuntimeObservationError("RUNTIME_AUTHORITY_UNAVAILABLE")
    atomic_json_write(runtime_root / "generated" / "runtime-observations.json", payload)


def _validated_process_payload(value: ProcessEvidence | dict[str, object]) -> dict[str, object]:
    payload = value.to_dict() if isinstance(value, ProcessEvidence) else value
    required = {
        "schema_version",
        "process_id",
        "pid",
        "generation",
        "command_digest",
        "health_port",
        "status",
        "exit_code",
        "finding_codes",
        "authority",
        "can_complete",
    }
    if not isinstance(payload, dict) or set(payload) != required:
        raise RuntimeObservationError("PROCESS_EVIDENCE_INVALID")
    process_id = payload.get("process_id")
    pid = payload.get("pid")
    generation = payload.get("generation")
    command_digest = payload.get("command_digest")
    health_port = payload.get("health_port")
    exit_code = payload.get("exit_code")
    finding_codes = payload.get("finding_codes")
    if (
        payload.get("schema_version") != PROCESS_EVIDENCE_SCHEMA
        or payload.get("authority") != "ProcessSupervisor/read-only"
        or payload.get("can_complete") is not False
        or not isinstance(process_id, str)
        or not _PROCESS_ID.fullmatch(process_id)
        or isinstance(pid, bool)
        or not isinstance(pid, int)
        or pid <= 0
        or isinstance(generation, bool)
        or not isinstance(generation, int)
        or generation <= 0
        or not isinstance(command_digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", command_digest)
        or (
            health_port is not None
            and (
                isinstance(health_port, bool)
                or not isinstance(health_port, int)
                or not 1 <= health_port <= 65535
            )
        )
        or payload.get("status")
        not in {
            "completed",
            "failed",
            "healthy",
            "running",
            "stopped",
            "timeout",
            "unexpected_exit",
            "orphan_detected",
            "orphan_unknown",
        }
        or (
            exit_code is not None
            and (isinstance(exit_code, bool) or not isinstance(exit_code, int))
        )
        or not isinstance(finding_codes, list)
        or len(finding_codes) > 16
        or any(
            not isinstance(code, str) or not _FINDING_CODE.fullmatch(code)
            for code in finding_codes
        )
        or private_data_reason(json.dumps(payload, sort_keys=True, ensure_ascii=True))
    ):
        raise RuntimeObservationError("PROCESS_EVIDENCE_INVALID")
    return dict(payload)


def record_host_observation(root: Path, payload: dict[str, object]) -> None:
    try:
        snapshot = HostCapabilitySnapshot.from_dict(payload)
    except HostCapabilityError as exc:
        raise RuntimeObservationError("HOST_OBSERVATION_INVALID") from exc
    storage = _load_storage(root)
    storage["host_snapshot"] = snapshot.to_dict()
    _write_storage(root, storage)


def record_process_observation(
    root: Path, value: ProcessEvidence | dict[str, object]
) -> None:
    evidence = _validated_process_payload(value)
    storage = _load_storage(root)
    items = [
        dict(item)
        for item in storage.get("processes", [])
        if isinstance(item, dict)
    ]
    items.append(evidence)
    storage["processes"] = items[-MAX_PROCESS_ITEMS:]
    _write_storage(root, storage)


def _empty_model(status: str = "not-run", finding: str | None = None) -> dict[str, object]:
    model: dict[str, object] = {
        "status": status,
        "items": [],
        "authority": "RuntimeObservations/read-only",
        "can_complete": False,
    }
    if finding:
        model["finding_codes"] = [finding]
    return model


def read_runtime_observations(root: Path) -> dict[str, object]:
    """Read a bounded model without creating a database, directory, or marker."""
    try:
        storage = _load_storage(root)
        host_payload = storage.get("host_snapshot")
        host = _empty_model()
        if isinstance(host_payload, dict):
            snapshot = HostCapabilitySnapshot.from_dict(host_payload)
            host = {
                "status": "passed",
                "snapshot_id": snapshot.snapshot_id,
                "host_kind": snapshot.host_kind,
                "max_concurrency": snapshot.max_concurrency,
                "items": [item.to_dict() for item in snapshot.capabilities],
                "authority": "HostCapabilitySnapshot/read-only",
                "can_complete": False,
            }
        processes = [
            _validated_process_payload(dict(item))
            for item in storage.get("processes", [])[-MAX_PROCESS_ITEMS:]
            if isinstance(item, dict)
        ]
        process_model = {
            "status": "passed" if processes else "not-run",
            "items": processes,
            "authority": "ProcessSupervisor/read-only",
            "can_complete": False,
        }
        return {
            "schema_version": RUNTIME_OBSERVATION_SCHEMA,
            "status": "passed" if isinstance(host_payload, dict) or processes else "not-run",
            "host": host,
            "processes": process_model,
            "authority": "RuntimeObservations/read-only",
            "can_complete": False,
        }
    except (RuntimeObservationError, HostCapabilityError):
        return {
            "schema_version": RUNTIME_OBSERVATION_SCHEMA,
            "status": "blocked",
            "host": _empty_model("blocked", "RUNTIME_OBSERVATION_INVALID"),
            "processes": _empty_model("blocked", "RUNTIME_OBSERVATION_INVALID"),
            "authority": "RuntimeObservations/read-only",
            "can_complete": False,
        }


__all__ = [
    "RuntimeObservationError",
    "read_runtime_observations",
    "record_host_observation",
    "record_process_observation",
    "runtime_observation_path",
]

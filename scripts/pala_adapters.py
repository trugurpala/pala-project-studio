"""Typed, side-effect-free contracts for optional Pala adapters."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

ADAPTER_STATES = {"ready", "missing", "external_conflict", "unsupported", "failed"}


@dataclass(frozen=True)
class AdapterResult:
    name: str
    state: str
    changed: bool
    detail: str
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.state not in ADAPTER_STATES:
            raise ValueError("unsupported adapter state")
        if not self.name.strip() or len(self.name) > 80:
            raise ValueError("adapter name must be bounded")
        if len(self.detail) > 500 or len(self.evidence) > 8:
            raise ValueError("adapter detail must be bounded")


@runtime_checkable
class ITool(Protocol):
    def inspect(self) -> AdapterResult: ...
    def install(self, dry_run: bool) -> AdapterResult: ...
    def doctor(self) -> AdapterResult: ...


@runtime_checkable
class IMCP(Protocol):
    def inspect(self, spec: dict[str, object]) -> AdapterResult: ...
    def ensure(self, spec: dict[str, object], dry_run: bool) -> AdapterResult: ...


@runtime_checkable
class IGraph(Protocol):
    def inspect(self) -> AdapterResult: ...
    def analyze(self, root: Path) -> AdapterResult: ...


def load_managed_tools_lock(path: Path) -> dict[str, dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("unsupported managed tools lock")
    tools = payload.get("tools")
    if not isinstance(tools, dict):
        raise ValueError("managed tools must be an object")
    result: dict[str, dict[str, str]] = {}
    for name, entry in tools.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise ValueError("invalid managed tool entry")
        for field in ("version", "source_url", "license", "platform"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise ValueError(f"managed tool {name} is missing {field}")
        integrity = entry.get("sha256", entry.get("integrity"))
        if not isinstance(integrity, str) or not integrity:
            raise ValueError(f"managed tool {name} has no integrity")
        result[name] = {key: str(value) for key, value in entry.items()}
    return result

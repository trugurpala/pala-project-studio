"""Provider-neutral execution boundary; results remain non-canonical candidates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCapability:
    name: str
    status: str = "VERIFIED"


@dataclass(frozen=True)
class ExecutionRequest:
    request_id: str
    task_id: str
    packet: dict[str, object]
    requested_capabilities: list[str]

    def __post_init__(self) -> None:
        if not self.request_id.strip() or not self.task_id.strip():
            raise ValueError("request_id and task_id are required")
        if self.packet.get("authority") != "TaskContract":
            raise ValueError("execution packet must retain TaskContract authority")


@dataclass(frozen=True)
class AgentResult:
    request_id: str
    task_id: str
    provider: str
    status: str
    candidate: dict[str, object]
    canonical_done: bool = False

    def __post_init__(self) -> None:
        if self.status != "candidate" or self.canonical_done:
            raise ValueError("provider results cannot declare canonical completion")


class AgentProvider(ABC):
    name: str

    @abstractmethod
    def capabilities(self) -> list[ProviderCapability]:
        raise NotImplementedError

    @abstractmethod
    def execute(self, request: ExecutionRequest) -> AgentResult:
        raise NotImplementedError

    def _require(self, request: ExecutionRequest) -> None:
        available = {item.name for item in self.capabilities() if item.status == "VERIFIED"}
        missing = set(request.requested_capabilities) - available
        if missing:
            raise ValueError(f"provider capability not verified: {sorted(missing)}")


class FakeProvider(AgentProvider):
    name = "fake"

    def __init__(self, *, capabilities: set[str], candidate: dict[str, object]) -> None:
        self._capabilities = capabilities
        self._candidate = candidate

    def capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability(name) for name in sorted(self._capabilities)]

    def execute(self, request: ExecutionRequest) -> AgentResult:
        self._require(request)
        return AgentResult(
            request.request_id, request.task_id, self.name, "candidate", dict(self._candidate)
        )


class CodexProvider(AgentProvider):
    """Adapter for the current Codex host callable; it grants no extra authority."""

    name = "codex"

    def __init__(self, executor: Callable[[ExecutionRequest], dict[str, object]]) -> None:
        self._executor = executor

    def capabilities(self) -> list[ProviderCapability]:
        return [ProviderCapability("local_edit")]

    def execute(self, request: ExecutionRequest) -> AgentResult:
        self._require(request)
        candidate = self._executor(request)
        if not isinstance(candidate, dict):
            raise ValueError("provider returned an invalid candidate")
        return AgentResult(request.request_id, request.task_id, self.name, "candidate", candidate)

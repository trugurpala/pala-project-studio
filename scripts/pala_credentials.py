"""Secret-free credential references and explicit external action authority."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

SECRET_SHAPE = re.compile(r"(?i)(password|secret|token|authorization)\s*[:=]")
WINDOWS_NATIVE_VAULT = "not-run"


@dataclass(frozen=True)
class CredentialRef:
    provider: str
    key: str
    purpose: str

    def __post_init__(self) -> None:
        values = (self.provider, self.key, self.purpose)
        if any(not value.strip() or SECRET_SHAPE.search(value) for value in values):
            raise ValueError("CredentialRef must contain identifiers, never secret values")

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class FakeCredentialVault:
    """In-memory test provider; audit records references, never values."""

    def __init__(self, values: dict[str, str]) -> None:
        self._values = dict(values)
        self.audit_events: list[dict[str, str]] = []

    def resolve(self, reference: CredentialRef) -> str:
        if reference.provider != "fake" or reference.key not in self._values:
            raise ValueError("credential reference is unavailable")
        self.audit_events.append(
            {"operation": "resolve", "key": reference.key, "purpose": reference.purpose}
        )
        return self._values[reference.key]


@dataclass(frozen=True)
class ExternalAction:
    action_id: str
    kind: str
    credential_ref: CredentialRef | None = None

    def __post_init__(self) -> None:
        if not self.action_id.strip() or not self.kind.strip():
            raise ValueError("external action id and kind are required")


@dataclass(frozen=True)
class OwnerAuthority:
    action_id: str
    approved: bool


def authorize_external_action(action: ExternalAction, authority: OwnerAuthority | None) -> bool:
    return bool(authority and authority.approved and authority.action_id == action.action_id)

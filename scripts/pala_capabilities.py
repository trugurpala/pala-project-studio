"""Observed capability and architecture decision contracts."""

from __future__ import annotations

from dataclasses import dataclass

CAPABILITY_STATUSES = {
    "VERIFIED",
    "UNSUPPORTED",
    "UNKNOWN",
    "CONFIGURED_NOT_VERIFIED",
    "BLOCKED",
}


@dataclass(frozen=True)
class CapabilityEvidence:
    source: str
    observed: str
    evidence: str
    confidence: str
    status: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> CapabilityEvidence:
        fields = ("source", "observed", "evidence", "confidence", "status")
        if any(
            not isinstance(payload.get(name), str) or not str(payload[name]).strip()
            for name in fields
        ):
            raise ValueError("capability evidence is incomplete")
        status = str(payload["status"])
        if status not in CAPABILITY_STATUSES:
            raise ValueError("invalid capability status")
        return cls(*(str(payload[name]).strip() for name in fields))


@dataclass(frozen=True)
class CapabilityProfile:
    provider: str
    capabilities: dict[str, CapabilityEvidence]

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> CapabilityProfile:
        provider = payload.get("provider")
        raw = payload.get("capabilities")
        if not isinstance(provider, str) or not provider.strip() or not isinstance(raw, dict):
            raise ValueError("provider and capabilities are required")
        capabilities: dict[str, CapabilityEvidence] = {}
        for name, evidence in raw.items():
            if not isinstance(name, str) or not name.strip() or not isinstance(evidence, dict):
                raise ValueError("invalid capability entry")
            capabilities[name] = CapabilityEvidence.from_dict(evidence)
        return cls(provider.strip(), capabilities)

    def status_of(self, name: str) -> str:
        evidence = self.capabilities.get(name)
        return evidence.status if evidence else "UNKNOWN"


@dataclass(frozen=True)
class ArchitectureDecision:
    selected: str | None
    requirements: list[str]
    matched: list[str]
    unknown_dependencies: list[str]
    rejected: dict[str, str]
    reason: str
    evidence_refs: list[str]
    status: str


def choose_architecture(
    candidates: dict[str, list[str]],
    requirements: list[str],
    profile: CapabilityProfile,
) -> ArchitectureDecision:
    """Choose only from evidence; UNKNOWN never becomes an assumed feature."""
    unknown = [
        name
        for name in requirements
        if profile.status_of(name) in {"UNKNOWN", "CONFIGURED_NOT_VERIFIED"}
    ]
    blocked = [
        name for name in requirements if profile.status_of(name) in {"UNSUPPORTED", "BLOCKED"}
    ]
    matched = [name for name in requirements if profile.status_of(name) == "VERIFIED"]
    evidence_refs = [profile.capabilities[name].evidence for name in matched]
    rejected: dict[str, str] = {}
    for candidate, needs in candidates.items():
        unavailable = [name for name in needs if profile.status_of(name) != "VERIFIED"]
        if unavailable:
            rejected[candidate] = "unverified: " + ", ".join(unavailable)
    if unknown:
        return ArchitectureDecision(
            None,
            requirements,
            matched,
            unknown,
            rejected,
            "capability discovery required",
            evidence_refs,
            "discovery_required",
        )
    if blocked:
        return ArchitectureDecision(
            None,
            requirements,
            matched,
            [],
            rejected,
            "owner decision required for unsupported capability",
            evidence_refs,
            "needs_decision",
        )
    selected = next((name for name in candidates if name not in rejected), None)
    if selected is None:
        return ArchitectureDecision(
            None,
            requirements,
            matched,
            [],
            rejected,
            "no evidence-compatible candidate",
            evidence_refs,
            "needs_decision",
        )
    return ArchitectureDecision(
        selected,
        requirements,
        matched,
        [],
        rejected,
        "all required capabilities verified",
        evidence_refs,
        "passed",
    )

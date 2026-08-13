#!/usr/bin/env python3
"""Typed Professional Workbench capability contracts and runtime truth."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Iterable

CAPABILITY_CATEGORIES = {
    "DEFAULT",
    "PROJECT_PROFILE",
    "LAZY_FALLBACK",
    "OPTIONAL_EXTERNAL",
}
RUNTIME_STATES = {"absent", "exact", "old", "external", "foreign", "offline"}


@dataclass(frozen=True)
class CapabilityContract:
    capability_id: str
    provider: str
    category: str
    install_policy: str
    execution_policy: str
    lifecycle_stage: tuple[str, ...]
    version: str
    official_source: str
    license: str
    integrity: str
    provenance: str
    ownership: str
    network_policy: str
    telemetry_policy: str
    update_policy: str
    authority: str
    fallback: str
    required_for_core_health: bool
    health_policy: str
    data_policy: str
    ui_policy: str
    freshness_policy: str

    def __post_init__(self) -> None:
        string_fields = (
            "capability_id", "provider", "install_policy", "execution_policy",
            "version", "official_source", "license", "integrity", "provenance",
            "ownership", "network_policy", "telemetry_policy", "update_policy",
            "authority", "fallback", "health_policy", "data_policy", "ui_policy",
            "freshness_policy",
        )
        if any(not str(getattr(self, name)).strip() for name in string_fields):
            raise ValueError("capability contract fields must be non-empty")
        if self.category not in CAPABILITY_CATEGORIES:
            raise ValueError("unsupported capability category")
        if self.authority != "advisory":
            raise ValueError("workbench providers must remain advisory")
        if not self.official_source.startswith("https://"):
            raise ValueError("official capability source must use HTTPS")
        if not self.lifecycle_stage:
            raise ValueError("capability lifecycle stages are required")
        if self.category == "OPTIONAL_EXTERNAL" and self.required_for_core_health:
            raise ValueError("optional external capability cannot own core health")


@dataclass(frozen=True)
class CapabilityRuntimeState:
    capability_id: str
    state: str
    version: str | None
    provenance: str
    integrity: str
    ownership: str
    health: str
    freshness: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.capability_id.strip() or self.state not in RUNTIME_STATES:
            raise ValueError("invalid capability runtime state")
        if self.state == "exact" and not self.version:
            raise ValueError("exact runtime state requires a version")

    @classmethod
    def exact(
        cls, capability_id: str, version: str, provenance: str, integrity: str,
        *, ownership: str = "pala-owned", evidence_refs: tuple[str, ...] = (),
    ) -> CapabilityRuntimeState:
        return cls(
            capability_id, "exact", version, provenance, integrity, ownership,
            "passed", "current", evidence_refs,
        )

    def with_freshness(self, freshness: str) -> CapabilityRuntimeState:
        return replace(self, freshness=freshness)


@dataclass(frozen=True)
class CapabilityRegistry:
    contracts: tuple[CapabilityContract, ...]
    schema_version: int = 1
    authority_invariant: str = (
        "TOOLS PROVIDE INFORMATION. PALA MAKES DECISIONS. QUALITY ENGINE PROVES COMPLETION."
    )

    def __post_init__(self) -> None:
        identifiers = [item.capability_id for item in self.contracts]
        if not identifiers or len(identifiers) != len(set(identifiers)):
            raise ValueError("capability IDs must be non-empty and unique")

    def capability_ids(self) -> tuple[str, ...]:
        return tuple(item.capability_id for item in self.contracts)

    def categories(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.category for item in self.contracts))

    def get(self, capability_id: str) -> CapabilityContract:
        for item in self.contracts:
            if item.capability_id == capability_id:
                return item
        raise KeyError(capability_id)

    def core_health(self, runtime: dict[str, CapabilityRuntimeState]) -> dict[str, object]:
        problems: list[str] = []
        for contract in self.contracts:
            if not contract.required_for_core_health:
                continue
            state = runtime.get(contract.capability_id)
            if state is None:
                problems.append(f"{contract.capability_id}=absent")
                continue
            if (
                state.state != "exact" or state.version != contract.version
                or state.health != "passed" or state.freshness not in {"current", "fresh"}
            ):
                problems.append(
                    f"{contract.capability_id}={state.state}/{state.health}/{state.freshness}"
                )
        return {
            "status": "passed" if not problems else "blocked",
            "problems": problems,
            "authority": "pala-capability-registry",
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "authority_invariant": self.authority_invariant,
            "contracts": [asdict(item) for item in self.contracts],
        }


def _contract(**values: object) -> CapabilityContract:
    defaults: dict[str, object] = {
        "authority": "advisory",
        "health_policy": "version-integrity-ownership-health",
        "data_policy": "local-project-data-no-upload",
        "ui_policy": "no-automatic-helper-ui",
        "freshness_policy": "verify-before-use",
    }
    return CapabilityContract(**{**defaults, **values})  # type: ignore[arg-type]


def default_registry() -> CapabilityRegistry:
    """Return the immutable M71 stack; host runtime state lives elsewhere."""
    return CapabilityRegistry((
        _contract(
            capability_id="code_intelligence", provider="CodeGraph",
            category="DEFAULT", install_policy="transactional-pala-owned-artifact",
            execution_policy="manual-sync-bounded-local",
            lifecycle_stage=("project-takeover", "pre-implementation", "post-implementation", "pre-quality"),
            version="1.5.0",
            official_source="https://github.com/colbymchenry/codegraph/releases/tag/v1.5.0",
            license="MIT",
            integrity="sha256:d6798622b4f44ee6757c94335f437ee27a9ff7d3537b554cb6a2b3baf11bc4a1",
            provenance="official-github-release-win32-x64", ownership="pala-owned-versioned",
            network_policy="install-update-only", telemetry_policy="disabled",
            update_policy="pala-manual-transaction", fallback="direct-source",
            required_for_core_health=True,
        ),
        _contract(
            capability_id="security_static", provider="Semgrep",
            category="DEFAULT", install_policy="hash-locked-wheelhouse-isolated-venv",
            execution_policy="bounded-local-rules-only",
            lifecycle_stage=("security", "pre-quality", "pre-release"), version="1.172.0",
            official_source="https://pypi.org/project/semgrep/1.172.0/",
            license="LGPL-2.1-or-later",
            integrity="sha256:e32868faeb67b241bbd3fabd82a12fba4b467464dedde9da285b9bf78e808ba3",
            provenance="pypi-verified-win-amd64-wheel", ownership="pala-owned-isolated-venv",
            network_policy="install-only-no-rule-fetch", telemetry_policy="disabled",
            update_policy="pala-manual-transaction", fallback="project-native-security-tools",
            required_for_core_health=True,
        ),
        _contract(
            capability_id="browser_exploration", provider="@playwright/cli",
            category="PROJECT_PROFILE", install_policy="pala-controlled-project-profile",
            execution_policy="explicit-headless-exploration", lifecycle_stage=("browser-user-journey",),
            version="0.1.18",
            official_source="https://www.npmjs.com/package/@playwright/cli/v/0.1.18",
            license="Apache-2.0",
            integrity="sha512:ggNfYYH+GsZTGUiBEL8f6N5j0seYEUE52v+fIWqK/A36QG36cL0EJ79qWTXYO2uZMUU7vm+jk3x0fKCPL6UuIw==",
            provenance="npm-registry-dist-integrity", ownership="pala-profile-cache",
            network_policy="browser-download-explicit-only", telemetry_policy="disabled-by-policy",
            update_policy="profile-pin-only", fallback="direct-browser-inspection",
            required_for_core_health=False,
        ),
        _contract(
            capability_id="browser_e2e", provider="@playwright/test",
            category="PROJECT_PROFILE", install_policy="reuse-compatible-project-exact-version",
            execution_policy="project-native-mechanical-quality",
            lifecycle_stage=("quality", "browser-user-journey"), version="1.62.1",
            official_source="https://www.npmjs.com/package/@playwright/test/v/1.62.1",
            license="Apache-2.0",
            integrity="sha512:DTcUc8qii+cpHvtOwggMtBRMjKZHXYWdw8syRYu2vtzuq4Wxphqq4NfCs5Zt44L6mA8rfDfj+PHnxFc/FeK6mQ==",
            provenance="npm-registry-dist-integrity", ownership="project-owned-when-explicit",
            network_policy="browser-download-explicit-only", telemetry_policy="disabled-by-policy",
            update_policy="never-silent-project-upgrade", fallback="project-native-browser-tests-or-not-run",
            required_for_core_health=False,
        ),
        _contract(
            capability_id="symbol_precision", provider="serena-agent",
            category="LAZY_FALLBACK", install_policy="transactional-pala-owned-on-demand",
            execution_policy="free-open-lsp-read-only-no-memory", lifecycle_stage=("implementation-context",),
            version="1.7.0", official_source="https://pypi.org/project/serena-agent/1.7.0/",
            license="MIT",
            integrity="sha256:6dbf1459670d96fb0595f84932adef34260a6fe14ba5135b901fdb3c8c76e891",
            provenance="pypi-wheel-and-official-github-license", ownership="pala-owned-isolated-venv",
            network_policy="install-only", telemetry_policy="disabled-by-policy",
            update_policy="pala-manual-transaction", fallback="direct-source",
            required_for_core_health=False,
        ),
        _contract(
            capability_id="current_docs", provider="Context7",
            category="OPTIONAL_EXTERNAL", install_policy="never-default-explicit-external-only",
            execution_policy="explicit-current-docs-query", lifecycle_stage=("third-party-docs",),
            version="4.0.2",
            official_source="https://www.npmjs.com/package/@upstash/context7-mcp/v/4.0.2",
            license="MIT",
            integrity="sha512:PdNL3hFK7tFe4oDzTa10nH8M+Ue82ShZXrsKnY0OY29TXhazeb9qZp2B/BwrxHfKua3ywu7FlqQ8HG6uyQHdaw==",
            provenance="npm-registry-dist-integrity", ownership="external-user-controlled",
            network_policy="explicit-query-only", telemetry_policy="external-provider-policy",
            update_policy="not-managed-by-pala", fallback="official-docs-or-direct-source",
            required_for_core_health=False,
        ),
    ))


def registry_payload(contracts: Iterable[CapabilityContract] | None = None) -> dict[str, object]:
    selected = tuple(contracts) if contracts is not None else default_registry().contracts
    return CapabilityRegistry(selected).to_dict()

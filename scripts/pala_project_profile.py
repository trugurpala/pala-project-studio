#!/usr/bin/env python3
"""Typed, deterministic, secrets-free professional ProjectProfile v1."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from pala_privacy import has_private_data

PROJECT_PROFILE_SCHEMA = "pala.project_profile.v1"
MAX_PROFILE_BYTES = 16_384
MAX_COLLECTION_ITEMS = 32

_IDENTIFIER = re.compile(r"^[a-z][a-z0-9._:-]{0,119}$")
_ROLE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


class ProjectProfileError(ValueError):
    """Sanitized, stable failure for untrusted profile input."""

    def __init__(self, code: str, field: str) -> None:
        self.code = code
        self.field = field
        super().__init__(f"{code} at {field}")

    def finding(self) -> dict[str, str]:
        return {"status": "blocked", "code": self.code, "field": self.field}


class ProfileKind(StrEnum):
    STANDARD = "standard"
    CONFIDENTIAL = "confidential"
    REGULATED = "regulated"
    PUBLIC_RELEASE = "public-release"


class DataClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(StrEnum):
    NONE = "none"
    CODE_EXECUTION = "code-execution"
    CREDENTIALS = "credentials"
    NETWORK = "network"
    PERSISTENCE = "persistence"
    PERSONAL_DATA = "personal-data"
    PUBLICATION = "publication"
    SUPPLY_CHAIN = "supply-chain"


class QualityTier(StrEnum):
    NARROW = "narrow"
    TICKET = "ticket"
    MILESTONE = "milestone"
    RELEASE = "release"


class ReleaseTarget(StrEnum):
    LOCAL_ONLY = "local-only"
    PRIVATE_ARTIFACT = "private-artifact"
    PUBLIC_ARTIFACT = "public-artifact"


class NetworkPolicy(StrEnum):
    OFFLINE_FIRST = "offline-first"
    APPROVED_EXTERNAL = "approved-external"


class PiiPolicy(StrEnum):
    PROHIBITED = "prohibited"
    EXPLICITLY_AUTHORIZED = "explicitly-authorized"


PROFILE_KINDS = tuple(sorted(item.value for item in ProfileKind))


def _field(prefix: str, name: str) -> str:
    return f"{prefix}.{name}" if prefix else name


def _mapping(
    value: object,
    field: str,
    required: tuple[str, ...],
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ProjectProfileError("PROFILE_TYPE_INVALID", field)
    keys = {str(key) for key in value}
    missing = sorted(set(required) - keys, key=str.casefold)
    if missing:
        raise ProjectProfileError("PROFILE_FIELD_MISSING", _field(field, missing[0]))
    unknown = sorted(keys - set(required), key=str.casefold)
    if unknown:
        raise ProjectProfileError("PROFILE_FIELD_UNKNOWN", _field(field, unknown[0]))
    return value


def _reject_private_data(value: str, field: str) -> None:
    if has_private_data(value):
        raise ProjectProfileError("PROFILE_PRIVATE_DATA_REJECTED", field)


def _text(
    value: object,
    field: str,
    *,
    limit: int = 120,
    identifier: bool = False,
    role: bool = False,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectProfileError("PROFILE_VALUE_INVALID", field)
    normalized = value.strip()
    if len(normalized) > limit:
        raise ProjectProfileError("PROFILE_VALUE_INVALID", field)
    _reject_private_data(normalized, field)
    if identifier and not _IDENTIFIER.fullmatch(normalized):
        raise ProjectProfileError("PROFILE_VALUE_INVALID", field)
    if role and not _ROLE.fullmatch(normalized):
        raise ProjectProfileError("PROFILE_VALUE_INVALID", field)
    return normalized


def _boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ProjectProfileError("PROFILE_TYPE_INVALID", field)
    return value


def _strings(
    value: object,
    field: str,
    *,
    required: bool,
    identifier: bool = True,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ProjectProfileError("PROFILE_TYPE_INVALID", field)
    if len(value) > MAX_COLLECTION_ITEMS:
        raise ProjectProfileError("PROFILE_VALUE_INVALID", field)
    normalized = tuple(
        sorted(
            {
                _text(item, f"{field}[{index}]", identifier=identifier)
                for index, item in enumerate(value)
            },
            key=str.casefold,
        )
    )
    if required and not normalized:
        raise ProjectProfileError("PROFILE_VALUE_INVALID", field)
    return normalized


def _enum(enum_type: type[StrEnum], value: object, field: str) -> StrEnum:
    if not isinstance(value, str):
        raise ProjectProfileError("PROFILE_TYPE_INVALID", field)
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ProjectProfileError("PROFILE_VALUE_UNKNOWN", field) from exc


@dataclass(frozen=True, slots=True)
class ScopeContract:
    summary: str
    in_scope: tuple[str, ...]
    out_of_scope: tuple[str, ...]
    trust_boundaries: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: object) -> ScopeContract:
        raw = _mapping(
            payload,
            "scope",
            ("summary", "in_scope", "out_of_scope", "trust_boundaries"),
        )
        return cls(
            summary=_text(raw["summary"], "scope.summary", limit=500),
            in_scope=_strings(raw["in_scope"], "scope.in_scope", required=True),
            out_of_scope=_strings(
                raw["out_of_scope"], "scope.out_of_scope", required=False
            ),
            trust_boundaries=_strings(
                raw["trust_boundaries"], "scope.trust_boundaries", required=True
            ),
        )


@dataclass(frozen=True, slots=True)
class StackContract:
    languages: tuple[str, ...]
    frameworks: tuple[str, ...]
    package_managers: tuple[str, ...]
    runtimes: tuple[str, ...]

    @classmethod
    def from_dict(cls, payload: object) -> StackContract:
        raw = _mapping(
            payload,
            "stack",
            ("languages", "frameworks", "package_managers", "runtimes"),
        )
        return cls(
            languages=_strings(raw["languages"], "stack.languages", required=True),
            frameworks=_strings(
                raw["frameworks"], "stack.frameworks", required=False
            ),
            package_managers=_strings(
                raw["package_managers"], "stack.package_managers", required=False
            ),
            runtimes=_strings(raw["runtimes"], "stack.runtimes", required=True),
        )


@dataclass(frozen=True, slots=True)
class RiskContract:
    level: RiskLevel
    categories: tuple[RiskCategory, ...]

    @classmethod
    def from_dict(cls, payload: object) -> RiskContract:
        raw = _mapping(payload, "risk", ("level", "categories"))
        values = _strings(raw["categories"], "risk.categories", required=True)
        categories = tuple(
            sorted(
                (
                    _enum(RiskCategory, value, "risk.categories")
                    for value in values
                ),
                key=lambda item: item.value,
            )
        )
        if RiskCategory.NONE in categories and len(categories) != 1:
            raise ProjectProfileError("PROFILE_POLICY_VIOLATION", "risk.categories")
        return cls(
            level=_enum(RiskLevel, raw["level"], "risk.level"),  # type: ignore[arg-type]
            categories=categories,  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class QualityContract:
    minimum_tier: QualityTier
    required_check_ids: tuple[str, ...]
    completion_authority: str

    @classmethod
    def from_dict(cls, payload: object) -> QualityContract:
        raw = _mapping(
            payload,
            "quality",
            ("minimum_tier", "required_check_ids", "completion_authority"),
        )
        authority = _text(
            raw["completion_authority"],
            "quality.completion_authority",
            identifier=True,
        )
        if authority != "pala-quality-engine":
            raise ProjectProfileError(
                "PROFILE_POLICY_VIOLATION", "quality.completion_authority"
            )
        return cls(
            minimum_tier=_enum(  # type: ignore[arg-type]
                QualityTier, raw["minimum_tier"], "quality.minimum_tier"
            ),
            required_check_ids=_strings(
                raw["required_check_ids"],
                "quality.required_check_ids",
                required=True,
            ),
            completion_authority=authority,
        )


@dataclass(frozen=True, slots=True)
class ReleaseContract:
    target: ReleaseTarget
    required_gates: tuple[str, ...]
    publication_authority: str
    sbom_required: bool
    rollback_required: bool

    @classmethod
    def from_dict(cls, payload: object) -> ReleaseContract:
        raw = _mapping(
            payload,
            "release",
            (
                "target",
                "required_gates",
                "publication_authority",
                "sbom_required",
                "rollback_required",
            ),
        )
        authority = _text(
            raw["publication_authority"],
            "release.publication_authority",
            identifier=True,
        )
        if authority != "explicit-owner-approval":
            raise ProjectProfileError(
                "PROFILE_POLICY_VIOLATION", "release.publication_authority"
            )
        return cls(
            target=_enum(ReleaseTarget, raw["target"], "release.target"),  # type: ignore[arg-type]
            required_gates=_strings(
                raw["required_gates"], "release.required_gates", required=True
            ),
            publication_authority=authority,
            sbom_required=_boolean(raw["sbom_required"], "release.sbom_required"),
            rollback_required=_boolean(
                raw["rollback_required"], "release.rollback_required"
            ),
        )


@dataclass(frozen=True, slots=True)
class OwnershipContract:
    product_owner_role: str
    engineering_owner_role: str
    security_owner_role: str
    data_owner_role: str

    @classmethod
    def from_dict(cls, payload: object) -> OwnershipContract:
        fields = (
            "product_owner_role",
            "engineering_owner_role",
            "security_owner_role",
            "data_owner_role",
        )
        raw = _mapping(payload, "ownership", fields)
        return cls(
            **{
                name: _text(raw[name], f"ownership.{name}", role=True)
                for name in fields
            }
        )


@dataclass(frozen=True, slots=True)
class SecurityContract:
    secret_handling: str
    network_policy: NetworkPolicy
    pii_policy: PiiPolicy
    review_required: bool

    @classmethod
    def from_dict(cls, payload: object) -> SecurityContract:
        raw = _mapping(
            payload,
            "security",
            ("secret_handling", "network_policy", "pii_policy", "review_required"),
        )
        handling = _text(
            raw["secret_handling"], "security.secret_handling", identifier=True
        )
        if handling != "external-references-only":
            raise ProjectProfileError(
                "PROFILE_POLICY_VIOLATION", "security.secret_handling"
            )
        return cls(
            secret_handling=handling,
            network_policy=_enum(  # type: ignore[arg-type]
                NetworkPolicy, raw["network_policy"], "security.network_policy"
            ),
            pii_policy=_enum(  # type: ignore[arg-type]
                PiiPolicy, raw["pii_policy"], "security.pii_policy"
            ),
            review_required=_boolean(
                raw["review_required"], "security.review_required"
            ),
        )


@dataclass(frozen=True, slots=True)
class ProjectProfile:
    schema_version: str
    project_id: str
    display_name: str
    profile_kind: ProfileKind
    data_classification: DataClassification
    scope: ScopeContract
    stack: StackContract
    risk: RiskContract
    quality: QualityContract
    release: ReleaseContract
    ownership: OwnershipContract
    security: SecurityContract

    REQUIRED_FIELDS: ClassVar[tuple[str, ...]] = (
        "schema_version",
        "project_id",
        "display_name",
        "profile_kind",
        "data_classification",
        "scope",
        "stack",
        "risk",
        "quality",
        "release",
        "ownership",
        "security",
    )

    @classmethod
    def from_dict(cls, payload: object) -> ProjectProfile:
        raw = _mapping(payload, "", cls.REQUIRED_FIELDS)
        schema = _text(raw["schema_version"], "schema_version", identifier=True)
        if schema != PROJECT_PROFILE_SCHEMA:
            raise ProjectProfileError("PROFILE_VALUE_UNKNOWN", "schema_version")
        profile = cls(
            schema_version=schema,
            project_id=_text(raw["project_id"], "project_id", identifier=True),
            display_name=_text(raw["display_name"], "display_name"),
            profile_kind=_enum(  # type: ignore[arg-type]
                ProfileKind, raw["profile_kind"], "profile_kind"
            ),
            data_classification=_enum(  # type: ignore[arg-type]
                DataClassification,
                raw["data_classification"],
                "data_classification",
            ),
            scope=ScopeContract.from_dict(raw["scope"]),
            stack=StackContract.from_dict(raw["stack"]),
            risk=RiskContract.from_dict(raw["risk"]),
            quality=QualityContract.from_dict(raw["quality"]),
            release=ReleaseContract.from_dict(raw["release"]),
            ownership=OwnershipContract.from_dict(raw["ownership"]),
            security=SecurityContract.from_dict(raw["security"]),
        )
        _validate_policy(profile)
        if len(profile.to_json().encode("utf-8")) > MAX_PROFILE_BYTES:
            raise ProjectProfileError("PROFILE_TOO_LARGE", "profile")
        return profile

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "display_name": self.display_name,
            "profile_kind": self.profile_kind.value,
            "data_classification": self.data_classification.value,
            "scope": {
                "summary": self.scope.summary,
                "in_scope": list(self.scope.in_scope),
                "out_of_scope": list(self.scope.out_of_scope),
                "trust_boundaries": list(self.scope.trust_boundaries),
            },
            "stack": {
                "languages": list(self.stack.languages),
                "frameworks": list(self.stack.frameworks),
                "package_managers": list(self.stack.package_managers),
                "runtimes": list(self.stack.runtimes),
            },
            "risk": {
                "level": self.risk.level.value,
                "categories": [item.value for item in self.risk.categories],
            },
            "quality": {
                "minimum_tier": self.quality.minimum_tier.value,
                "required_check_ids": list(self.quality.required_check_ids),
                "completion_authority": self.quality.completion_authority,
            },
            "release": {
                "target": self.release.target.value,
                "required_gates": list(self.release.required_gates),
                "publication_authority": self.release.publication_authority,
                "sbom_required": self.release.sbom_required,
                "rollback_required": self.release.rollback_required,
            },
            "ownership": {
                "product_owner_role": self.ownership.product_owner_role,
                "engineering_owner_role": self.ownership.engineering_owner_role,
                "security_owner_role": self.ownership.security_owner_role,
                "data_owner_role": self.ownership.data_owner_role,
            },
            "security": {
                "secret_handling": self.security.secret_handling,
                "network_policy": self.security.network_policy.value,
                "pii_policy": self.security.pii_policy.value,
                "review_required": self.security.review_required,
            },
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )

    def digest(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


def _require_release_baseline(profile: ProjectProfile) -> None:
    if profile.quality.minimum_tier is not QualityTier.RELEASE:
        raise ProjectProfileError(
            "PROFILE_POLICY_VIOLATION", "quality.minimum_tier"
        )
    if not profile.release.sbom_required:
        raise ProjectProfileError(
            "PROFILE_POLICY_VIOLATION", "release.sbom_required"
        )
    if not profile.release.rollback_required:
        raise ProjectProfileError(
            "PROFILE_POLICY_VIOLATION", "release.rollback_required"
        )
    if not {"dependency", "package", "security"}.issubset(
        profile.release.required_gates
    ):
        raise ProjectProfileError(
            "PROFILE_POLICY_VIOLATION", "release.required_gates"
        )


def _validate_policy(profile: ProjectProfile) -> None:
    kind = profile.profile_kind
    classification = profile.data_classification
    target = profile.release.target

    if profile.risk.level in {RiskLevel.HIGH, RiskLevel.CRITICAL} and not (
        profile.security.review_required
    ):
        raise ProjectProfileError(
            "PROFILE_POLICY_VIOLATION", "security.review_required"
        )
    if kind is not ProfileKind.STANDARD and RiskCategory.NONE in profile.risk.categories:
        raise ProjectProfileError("PROFILE_POLICY_VIOLATION", "risk.categories")

    if kind is ProfileKind.STANDARD:
        if classification not in {
            DataClassification.PUBLIC,
            DataClassification.INTERNAL,
        }:
            raise ProjectProfileError(
                "PROFILE_POLICY_VIOLATION", "data_classification"
            )
        if target is ReleaseTarget.PUBLIC_ARTIFACT:
            raise ProjectProfileError("PROFILE_POLICY_VIOLATION", "release.target")
    elif kind is ProfileKind.CONFIDENTIAL:
        if classification not in {
            DataClassification.CONFIDENTIAL,
            DataClassification.RESTRICTED,
        }:
            raise ProjectProfileError(
                "PROFILE_POLICY_VIOLATION", "data_classification"
            )
        if target is ReleaseTarget.PUBLIC_ARTIFACT:
            raise ProjectProfileError("PROFILE_POLICY_VIOLATION", "release.target")
        if not profile.security.review_required:
            raise ProjectProfileError(
                "PROFILE_POLICY_VIOLATION", "security.review_required"
            )
    elif kind is ProfileKind.REGULATED:
        if classification is not DataClassification.RESTRICTED:
            raise ProjectProfileError(
                "PROFILE_POLICY_VIOLATION", "data_classification"
            )
        if target is ReleaseTarget.PUBLIC_ARTIFACT:
            raise ProjectProfileError("PROFILE_POLICY_VIOLATION", "release.target")
        if not profile.security.review_required:
            raise ProjectProfileError(
                "PROFILE_POLICY_VIOLATION", "security.review_required"
            )
        _require_release_baseline(profile)
    else:
        if classification is not DataClassification.PUBLIC:
            raise ProjectProfileError(
                "PROFILE_POLICY_VIOLATION", "data_classification"
            )
        if target is not ReleaseTarget.PUBLIC_ARTIFACT:
            raise ProjectProfileError("PROFILE_POLICY_VIOLATION", "release.target")
        if profile.security.pii_policy is not PiiPolicy.PROHIBITED:
            raise ProjectProfileError(
                "PROFILE_POLICY_VIOLATION", "security.pii_policy"
            )
        if not profile.security.review_required:
            raise ProjectProfileError(
                "PROFILE_POLICY_VIOLATION", "security.review_required"
            )
        _require_release_baseline(profile)


def profile_contract_summary() -> dict[str, object]:
    """Return bounded schema metadata, never a profile or persistence claim."""
    return {
        "schema_version": PROJECT_PROFILE_SCHEMA,
        "profile_kinds": list(PROFILE_KINDS),
        "authority": "ProjectProfile",
        "status": "not-run",
        "persistence": "not-run",
    }


__all__ = [
    "PROJECT_PROFILE_SCHEMA",
    "PROFILE_KINDS",
    "ProjectProfile",
    "ProjectProfileError",
    "profile_contract_summary",
]

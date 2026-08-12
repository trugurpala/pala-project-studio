"""Provider-neutral product contract above Pala's canonical task authority."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

from pala_authority import atomic_json_write, shared_state_root

PROJECT_CONTRACT_SCHEMA = 1
PROJECT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")

PROJECT_STATES = {
    "DISCOVERING",
    "PLANNED",
    "BUILDING",
    "VERIFYING",
    "PACKAGE_READY",
    "AWAITING_DEPLOY_AUTH",
    "DEPLOYING",
    "LIVE_VERIFYING",
    "DELIVERED",
    "BLOCKED",
    "NEEDS_DECISION",
}

PROJECT_TRANSITIONS = {
    "DISCOVERING": {"PLANNED", "BLOCKED", "NEEDS_DECISION"},
    "PLANNED": {"BUILDING", "BLOCKED", "NEEDS_DECISION"},
    "BUILDING": {"VERIFYING", "BLOCKED", "NEEDS_DECISION"},
    "VERIFYING": {"BUILDING", "PACKAGE_READY", "BLOCKED", "NEEDS_DECISION"},
    "PACKAGE_READY": {"AWAITING_DEPLOY_AUTH", "BLOCKED", "NEEDS_DECISION"},
    "AWAITING_DEPLOY_AUTH": {"DEPLOYING", "BLOCKED", "NEEDS_DECISION"},
    "DEPLOYING": {"LIVE_VERIFYING", "BLOCKED", "NEEDS_DECISION"},
    "LIVE_VERIFYING": {"DELIVERED", "BLOCKED", "NEEDS_DECISION"},
    "DELIVERED": set(),
    "BLOCKED": {
        "DISCOVERING",
        "PLANNED",
        "BUILDING",
        "VERIFYING",
        "PACKAGE_READY",
        "AWAITING_DEPLOY_AUTH",
        "DEPLOYING",
        "LIVE_VERIFYING",
        "NEEDS_DECISION",
    },
    "NEEDS_DECISION": {
        "DISCOVERING",
        "PLANNED",
        "BUILDING",
        "VERIFYING",
        "PACKAGE_READY",
        "AWAITING_DEPLOY_AUTH",
        "BLOCKED",
    },
}


def _text(payload: dict[str, object], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _texts(payload: dict[str, object], name: str, *, allow_empty: bool = False) -> list[str]:
    value = payload.get(name)
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{name} must be a list of strings")
    result = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    if len(result) != len(value):
        raise ValueError(f"{name} must contain only non-empty strings")
    return result


@dataclass(frozen=True)
class ProductSpec:
    project_id: str
    title: str
    goal: str
    user_outcome: str
    product_type: str
    target_users: list[str]
    declared_facts: list[str]
    unknowns: list[str]
    constraints: list[str]
    non_goals: list[str]
    environment_requirements: list[str]
    architecture_decision_ref: str
    acceptance: list[str]
    milestones: list[str]
    delivery_target: str
    project_status: str

    REQUIRED_FIELDS: ClassVar[set[str]] = {
        "project_id",
        "title",
        "goal",
        "user_outcome",
        "product_type",
        "target_users",
        "declared_facts",
        "unknowns",
        "constraints",
        "non_goals",
        "environment_requirements",
        "architecture_decision_ref",
        "acceptance",
        "milestones",
        "delivery_target",
        "project_status",
    }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> ProductSpec:
        missing = cls.REQUIRED_FIELDS - payload.keys()
        extra = payload.keys() - cls.REQUIRED_FIELDS
        if missing or extra:
            raise ValueError(
                f"invalid ProductSpec fields: missing={sorted(missing)} extra={sorted(extra)}"
            )
        status = _text(payload, "project_status")
        if status not in PROJECT_STATES:
            raise ValueError("unsupported project_status")
        return cls(
            project_id=_text(payload, "project_id"),
            title=_text(payload, "title"),
            goal=_text(payload, "goal"),
            user_outcome=_text(payload, "user_outcome"),
            product_type=_text(payload, "product_type"),
            target_users=_texts(payload, "target_users"),
            declared_facts=_texts(payload, "declared_facts"),
            unknowns=_texts(payload, "unknowns", allow_empty=True),
            constraints=_texts(payload, "constraints", allow_empty=True),
            non_goals=_texts(payload, "non_goals", allow_empty=True),
            environment_requirements=_texts(payload, "environment_requirements"),
            architecture_decision_ref=_text(payload, "architecture_decision_ref"),
            acceptance=_texts(payload, "acceptance"),
            milestones=_texts(payload, "milestones"),
            delivery_target=_text(payload, "delivery_target"),
            project_status=status,
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ProjectLifecycle:
    """Explicit project state; TaskContract state observations never mutate it."""

    def __init__(self, status: str) -> None:
        if status not in PROJECT_STATES:
            raise ValueError("unsupported project status")
        self.status = status

    def transition(self, target: str) -> None:
        if target not in PROJECT_TRANSITIONS[self.status]:
            raise ValueError(f"invalid project transition {self.status}->{target}")
        self.status = target

    def observe_task_status(self, _task_status: str) -> None:
        """Deliberately do nothing: task DONE is not project delivery."""


def project_contract_path(root: Path, project_id: str) -> Path:
    """Return the canonical repository-scoped product contract path."""
    if not PROJECT_ID.fullmatch(project_id):
        raise ValueError("project_id must be a safe 1-80 character identifier")
    authority = shared_state_root(Path(root).resolve())
    if authority is None:
        raise ValueError("a Git repository is required for durable product authority")
    return authority / "product" / f"{project_id}.json"


def save_project_contract(root: Path, payload: dict[str, object]) -> Path:
    """Validate and atomically persist the project contract above task authority."""
    if payload.get("schema_version") != PROJECT_CONTRACT_SCHEMA:
        raise ValueError("unsupported project contract schema")
    spec_payload = payload.get("product_spec")
    if not isinstance(spec_payload, dict):
        raise ValueError("project contract requires product_spec")
    spec = ProductSpec.from_dict(spec_payload)
    state = payload.get("project_state")
    if not isinstance(state, str) or state not in PROJECT_STATES:
        raise ValueError("project contract requires an explicit project_state")
    if payload.get("project_id") != spec.project_id:
        raise ValueError("project contract identity does not match ProductSpec")
    record = dict(payload)
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = project_contract_path(root, spec.project_id)
    atomic_json_write(path, record)
    return path


def load_project_contract(root: Path, project_id: str) -> dict[str, object]:
    path = project_contract_path(root, project_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("project contract must be an object")
    save_check = dict(payload)
    if save_check.get("schema_version") != PROJECT_CONTRACT_SCHEMA:
        raise ValueError("unsupported project contract schema")
    spec_payload = save_check.get("product_spec")
    if not isinstance(spec_payload, dict):
        raise ValueError("project contract requires product_spec")
    ProductSpec.from_dict(spec_payload)
    if save_check.get("project_state") not in PROJECT_STATES:
        raise ValueError("invalid durable project state")
    return save_check


def load_current_project_contract(root: Path) -> dict[str, object] | None:
    authority = shared_state_root(Path(root).resolve())
    if authority is None:
        return None
    paths = sorted((authority / "product").glob("*.json"))
    if not paths:
        return None
    if len(paths) != 1:
        raise ValueError("multiple canonical product contracts require an explicit project_id")
    payload = json.loads(paths[0].read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("project_id"), str):
        raise ValueError("invalid canonical product contract")
    return load_project_contract(root, str(payload["project_id"]))

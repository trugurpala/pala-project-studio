"""Dry-run-first generic Linux/cPanel delivery contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from pala_credentials import ExternalAction, OwnerAuthority, authorize_external_action

DELIVERY_STEPS = ("backup", "package", "upload", "configure", "activate", "verify", "rollback")


@dataclass(frozen=True)
class DeliveryPlan:
    target: str
    artifact: str
    transfer_mode: str
    steps: tuple[str, ...]
    dry_run: bool
    action: ExternalAction


class FakeDeliveryAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run_step(self, step: str, _plan: DeliveryPlan) -> None:
        self.calls.append(step)


def create_cpanel_plan(artifact: str, capabilities: dict[str, str]) -> DeliveryPlan:
    path = PurePosixPath(artifact.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.name:
        raise ValueError("delivery artifact must be a safe relative path")
    required = ("linux", "cpanel")
    if any(capabilities.get(name) != "VERIFIED" for name in required):
        raise ValueError("generic Linux and cPanel capabilities must be verified")
    transfer = next(
        (name for name in ("sftp", "ssh", "cpanel_api") if capabilities.get(name) == "VERIFIED"),
        "manual",
    )
    action = ExternalAction("DELIVERY-CPANEL-1", "remote_delivery")
    return DeliveryPlan(
        target="generic-linux-cpanel",
        artifact=path.as_posix(),
        transfer_mode=transfer,
        steps=DELIVERY_STEPS,
        dry_run=True,
        action=action,
    )


def run_delivery(
    plan: DeliveryPlan,
    adapter: FakeDeliveryAdapter,
    *,
    authority: OwnerAuthority | None = None,
    mutate: bool = False,
) -> dict[str, object]:
    if not mutate:
        return {"status": "passed", "mode": "dry-run", "steps": list(plan.steps)}
    if not authorize_external_action(plan.action, authority):
        return {"status": "blocked", "reason": "explicit owner authority required"}
    for step in plan.steps:
        adapter.run_step(step, plan)
    return {"status": "passed", "mode": "fake-authorized", "steps": list(plan.steps)}

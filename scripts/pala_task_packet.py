"""Bounded TaskPacket compiler with TaskContract as the sole task authority."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

PACKET_BUDGETS = {"minimal": 2_048, "standard": 8_192, "milestone": 16_384}


@dataclass(frozen=True)
class TaskPacket:
    task_id: str
    profile: str
    goal: str
    acceptance: list[object]
    dependencies: list[str]
    architecture_refs: list[str]
    next_action: str
    context: str
    authority: str = "TaskContract"

    def encoded_size(self) -> int:
        return len(json.dumps(asdict(self), ensure_ascii=False, separators=(",", ":")).encode())


def _active_task(source: dict[str, object]) -> str | None:
    value = source.get("active_task") or source.get("task_id")
    return value.strip() if isinstance(value, str) and value.strip() else None


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def compile_task_packet(
    task_contract: dict[str, object],
    cold_packet: dict[str, object],
    knowledge: dict[str, object],
    handoff: dict[str, object],
    profile: str,
) -> TaskPacket | None:
    if profile not in PACKET_BUDGETS:
        raise ValueError("unsupported packet profile")
    task_id = task_contract.get("id")
    goal = task_contract.get("goal")
    if (
        not isinstance(task_id, str)
        or not task_id.strip()
        or not isinstance(goal, str)
        or not goal.strip()
    ):
        raise ValueError("canonical task id and goal are required")
    if str(task_contract.get("status", "")).upper() == "DONE":
        return None
    observed = {_active_task(source) for source in (cold_packet, handoff)} - {None}
    if observed and observed != {task_id}:
        raise ValueError("read model conflicts with canonical TaskContract")
    acceptance = task_contract.get("acceptance")
    if not isinstance(acceptance, list) or not acceptance:
        raise ValueError("canonical task acceptance is required")
    sources: list[object]
    if profile == "minimal":
        sources = [cold_packet.get("summary", ""), handoff.get("next_action", "")]
    elif profile == "standard":
        sources = [cold_packet, handoff]
    else:
        sources = [cold_packet, knowledge, handoff]
    context = json.dumps(sources, ensure_ascii=False, separators=(",", ":"), default=str)
    packet = TaskPacket(
        task_id=task_id,
        profile=profile,
        goal=goal.strip(),
        acceptance=list(acceptance),
        dependencies=_strings(task_contract.get("dependencies")),
        architecture_refs=_strings(task_contract.get("architecture_refs")),
        next_action=str(
            task_contract.get("next_action") or handoff.get("next_action") or ""
        ).strip(),
        context=context,
    )
    budget = PACKET_BUDGETS[profile]
    excess = packet.encoded_size() - budget
    if excess > 0:
        context = context[: max(0, len(context) - excess - 16)] + "...[bounded]"
        packet = TaskPacket(**{**asdict(packet), "context": context})
    if packet.encoded_size() > budget:
        raise ValueError("canonical task fields exceed packet budget")
    return packet

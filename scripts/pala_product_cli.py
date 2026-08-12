#!/usr/bin/env python3
"""Thin public Pala 1.0 facade over existing product and runtime authorities."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from pala_agent_provider import CodexProvider, ExecutionRequest
from pala_capabilities import ArchitectureDecision, CapabilityProfile, choose_architecture
from pala_execution import ExecutionCoordinator
from pala_product import (
    PROJECT_CONTRACT_SCHEMA,
    ProjectLifecycle,
    load_current_project_contract,
    load_project_contract,
    save_project_contract,
)
from pala_product_planner import ProductPlan, validate_plan
from pala_quality import quality_gate, read_ledger
from pala_quality_runner import EXECUTION_AUTHORITY, run_approved_check
from pala_store import WorkflowStore
from pala_task_packet import compile_task_packet


def _read_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _first_task(plan: ProductPlan) -> tuple[str, dict[str, object]]:
    roots = [
        (task_id, node)
        for task_id, node in sorted(plan.task_dag.items())
        if not list(node.get("dependencies") or [])
    ]
    if len(roots) != 1:
        raise ValueError("product plan requires exactly one initial task")
    return roots[0]


def _owner_snapshot(record: dict[str, object]) -> dict[str, object]:
    spec = record.get("product_spec") if isinstance(record.get("product_spec"), dict) else {}
    acceptance = record.get("acceptance_matrix")
    acceptance_rows = acceptance if isinstance(acceptance, list) else []
    quality = record.get("quality") if isinstance(record.get("quality"), dict) else {}
    live = (
        record.get("live_verification") if isinstance(record.get("live_verification"), dict) else {}
    )
    verified = len(acceptance_rows) if quality.get("status") == "passed" else 0
    return {
        "project": str(spec.get("title") or record.get("project_id") or "Project"),
        "state": str(record.get("project_state") or "DISCOVERING"),
        "acceptance_verified": verified,
        "acceptance_total": max(1, len(acceptance_rows)),
        "quality": str(quality.get("status") or "not-run"),
        "environment": str(record.get("environment_status") or "configured-not-verified"),
        "delivery": str(record.get("delivery_status") or "not-run"),
        "live_verification": str(live.get("status") or "not-run"),
        "blocker": str(record.get("blocker") or "none"),
        "next_action": str(record.get("next_action") or "Review project state"),
        "owner_request": str(record.get("owner_request") or "Review the local product candidate."),
    }


def public_status(root: Path, project_id: str | None = None) -> dict[str, object]:
    record = (
        load_project_contract(root, project_id)
        if project_id
        else load_current_project_contract(root)
    )
    if record is None:
        raise ValueError("canonical product contract not found")
    snapshot = _owner_snapshot(record)
    return {**record, "owner_cockpit": snapshot}


def _resolve_architecture(
    payload: dict[str, object],
) -> tuple[CapabilityProfile, ArchitectureDecision]:
    profile = CapabilityProfile.from_dict(payload)
    candidates = payload.get("architecture_candidates")
    requirements = payload.get("architecture_requirements")
    if not isinstance(candidates, dict) or not isinstance(requirements, list):
        raise ValueError("architecture candidates and requirements are required")
    normalized_candidates = {
        str(name): [str(item) for item in needs]
        for name, needs in candidates.items()
        if isinstance(name, str) and isinstance(needs, list)
    }
    normalized_requirements = [str(item) for item in requirements if isinstance(item, str)]
    architecture = choose_architecture(normalized_candidates, normalized_requirements, profile)
    if architecture.status != "passed":
        raise ValueError(f"architecture is not evidence-ready: {architecture.status}")
    return profile, architecture


def start_product(
    root: Path,
    intent: str,
    plan_payload: dict[str, object],
    capability_payload: dict[str, object],
    provider_candidate: dict[str, object],
    session_key: str,
) -> dict[str, object]:
    if not intent.strip():
        raise ValueError("natural-language intent is required")
    plan = validate_plan(plan_payload)
    profile, architecture = _resolve_architecture(capability_payload)

    source_task_id, node = _first_task(plan)
    task_id = f"{plan.product_spec.project_id}-{source_task_id}"
    goal = str(node.get("goal") or "").strip()
    write_surface = node.get("write_surface")
    if not goal or not isinstance(write_surface, list) or not write_surface:
        raise ValueError("initial task goal and write_surface are required")
    acceptance = [
        {
            "id": str(item["id"]),
            "text": str(item["criterion"]),
            "status": "not-run",
            "evidence_refs": [],
            "quality_check_ids": [],
            "quality_execution_authority": EXECUTION_AUTHORITY,
        }
        for item in plan.acceptance_matrix
    ]
    store = WorkflowStore(root)
    claimed = store.claim(task_id, goal, session_key, acceptance=acceptance)
    if claimed.status != "claimed":
        raise ValueError(f"canonical task claim refused: {claimed.status}")
    configured = store.configure_task(
        task_id,
        session_key,
        dependencies=[],
        architecture_refs=[plan.product_spec.architecture_decision_ref],
        write_scope=[str(item) for item in write_surface],
        next_action="Run the provider candidate through the Pala Quality Engine",
    )
    if configured.status != "configured":
        raise ValueError(f"canonical task mapping refused: {configured.status}")
    task_contract = dict(configured.record["task_contract"])
    packet = compile_task_packet(
        task_contract,
        {"active_task": task_id, "summary": intent.strip()},
        {"architecture": asdict(architecture)},
        {"active_task": task_id, "next_action": task_contract.get("next_action")},
        "standard",
    )
    if packet is None:
        raise ValueError("active TaskPacket was unexpectedly excluded")
    request = ExecutionRequest(
        request_id=f"REQ-{task_id}",
        task_id=task_id,
        packet=asdict(packet),
        requested_capabilities=["local_edit"],
    )
    provider = CodexProvider(lambda _request: dict(provider_candidate))
    result = provider.execute(request)
    lease_holder = str(configured.record.get("owner") or "")
    coordinator = ExecutionCoordinator()
    coordinator.claim(task_id, lease_holder, [str(item) for item in write_surface])
    candidate = coordinator.submit_candidate(task_id, lease_holder, result.candidate)

    lifecycle = ProjectLifecycle(plan.product_spec.project_status)
    lifecycle.transition("PLANNED")
    lifecycle.transition("BUILDING")
    record: dict[str, object] = {
        "schema_version": PROJECT_CONTRACT_SCHEMA,
        "project_id": plan.product_spec.project_id,
        "intent": intent.strip(),
        "product_spec": plan.product_spec.to_dict(),
        "project_state": lifecycle.status,
        "acceptance_matrix": plan.acceptance_matrix,
        "environment_requirements": plan.environment_requirements,
        "milestone_graph": plan.milestone_graph,
        "task_dag": plan.task_dag,
        "capability_profile": {
            "provider": profile.provider,
            "capabilities": {name: asdict(value) for name, value in profile.capabilities.items()},
        },
        "architecture_decision": asdict(architecture),
        "task_mapping": {source_task_id: task_id},
        "active_task_id": task_id,
        "provider_candidate": {
            "provider": result.provider,
            "status": candidate["status"],
            "request_id": result.request_id,
        },
        "quality": {"status": "not-run", "check_id": None},
        "environment_status": "configured-not-verified",
        "delivery_target": plan.product_spec.delivery_target,
        "delivery_status": "not-run",
        "live_verification": {"status": "not-run", "evidence_refs": []},
        "blocker": "none",
        "next_action": "Run the canonical quality command",
        "owner_request": "No owner action is required before local verification.",
        "remote_publish": "not-run",
        "real_remote_deploy": "not-run",
    }
    path = save_project_contract(root, record)
    return {
        "status": "awaiting_quality",
        "project_id": plan.product_spec.project_id,
        "task_id": task_id,
        "provider": result.provider,
        "task_authority": packet.authority,
        "explicit_unknowns": plan.product_spec.unknowns,
        "contract_path": str(path),
    }


def complete_product(
    root: Path,
    project_id: str,
    session_key: str,
    quality_ticket: str,
    check_id: str,
    timeout_seconds: float,
) -> dict[str, object]:
    record = load_project_contract(root, project_id)
    task_id = str(record.get("active_task_id") or "")
    if not task_id:
        raise ValueError("project contract has no active canonical task")
    store = WorkflowStore(root)
    configured = store.configure_quality_mapping(
        task_id,
        session_key,
        [check_id],
        EXECUTION_AUTHORITY,
    )
    if configured.status != "configured":
        raise ValueError(f"quality mapping refused: {configured.status}")
    execution = run_approved_check(
        root,
        quality_ticket,
        check_id,
        timeout_seconds=timeout_seconds,
    )
    if execution.get("status") != "passed":
        record["quality"] = {"status": "blocked", "check_id": check_id}
        record["blocker"] = str(execution.get("detail") or "quality evidence blocked")
        save_project_contract(root, record)
        return {"status": "blocked", "task_id": task_id, "quality": "blocked"}

    gate = quality_gate(root, quality_ticket)
    if gate["status"] != "passed":
        record["quality"] = {"status": "blocked", "check_id": check_id}
        record["blocker"] = str(gate.get("last_problem") or "quality evidence blocked")
        save_project_contract(root, record)
        return {"status": "blocked", "task_id": task_id, "quality": "blocked"}

    mapped = store.sync_quality_evidence(task_id, session_key, quality_ticket)
    if mapped.status != "mapped":
        raise ValueError(f"quality evidence mapping refused: {mapped.status}")
    completed = store.complete(task_id, session_key)
    if completed.status != "completed":
        raise ValueError(f"canonical completion refused: {completed.status}")
    lifecycle = ProjectLifecycle(str(record["project_state"]))
    lifecycle.transition("VERIFYING")
    lifecycle.transition("PACKAGE_READY")
    record["project_state"] = lifecycle.status
    record["quality"] = {
        "status": "passed",
        "check_id": check_id,
        "execution_authority": EXECUTION_AUTHORITY,
    }
    record["delivery_status"] = "package-ready; remote deploy not-run"
    record["blocker"] = "none"
    record["next_action"] = "Owner may review the local release candidate"
    record["owner_request"] = "Review the local candidate; remote deploy remains not-run."
    save_project_contract(root, record)
    return {
        "status": "package-ready",
        "project_id": project_id,
        "task_id": task_id,
        "project_state": lifecycle.status,
        "quality": "passed",
        "remote_publish": "not-run",
        "real_remote_deploy": "not-run",
    }


def record_local_live_verification(
    root: Path,
    project_id: str,
    quality_ticket: str,
    check_id: str,
) -> dict[str, object]:
    """Project real browser evidence from the existing Quality Engine ledger."""
    ledger = read_ledger(root, quality_ticket)
    checks = ledger.get("checks") if isinstance(ledger.get("checks"), list) else []
    check = next(
        (item for item in checks if isinstance(item, dict) and item.get("id") == check_id),
        None,
    )
    if not isinstance(check, dict):
        raise ValueError("browser quality evidence was not found")
    if (
        check.get("kind") != "browser"
        or check.get("status") != "passed"
        or check.get("exit_code") != 0
        or not check.get("artifact")
    ):
        raise ValueError("live verification requires passed browser evidence with artifact")
    record = load_project_contract(root, project_id)
    record["live_verification"] = {
        "status": "passed",
        "scope": "local-fixture",
        "evidence_refs": [f"{quality_ticket}:{check_id}"],
        "artifact": str(check["artifact"]),
        "remote_site": "not-run",
    }
    save_project_contract(root, record)
    return {
        "status": "passed",
        "scope": "local-fixture",
        "artifact": str(check["artifact"]),
        "real_remote_deploy": "not-run",
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start")
    start.add_argument("--cwd", default=".")
    start.add_argument("--intent", required=True)
    start.add_argument("--plan", required=True, type=Path)
    start.add_argument("--capabilities", required=True, type=Path)
    start.add_argument("--provider-candidate", required=True, type=Path)
    start.add_argument("--session-key", required=True)
    status = subparsers.add_parser("status")
    status.add_argument("--cwd", default=".")
    status.add_argument("--project-id")
    complete = subparsers.add_parser("complete")
    complete.add_argument("--cwd", default=".")
    complete.add_argument("--project-id", required=True)
    complete.add_argument("--session-key", required=True)
    complete.add_argument("--quality-ticket")
    complete.add_argument("--check-id")
    complete.add_argument("--quality-timeout-seconds", default=120.0, type=float)
    complete.add_argument("--quality-command", help=argparse.SUPPRESS)
    complete.add_argument("--quality-exit-code", type=int, help=argparse.SUPPRESS)
    live = subparsers.add_parser("live-verify")
    live.add_argument("--cwd", default=".")
    live.add_argument("--project-id", required=True)
    live.add_argument("--quality-ticket", required=True)
    live.add_argument("--check-id", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.cwd).resolve()
    try:
        if args.command == "start":
            payload = start_product(
                root,
                args.intent,
                _read_object(args.plan),
                _read_object(args.capabilities),
                _read_object(args.provider_candidate),
                args.session_key,
            )
        elif args.command == "complete":
            if args.quality_command is not None or args.quality_exit_code is not None:
                raise ValueError(
                    "caller-supplied quality command or exit code is not authoritative"
                )
            if not args.quality_ticket or not args.check_id:
                raise ValueError("quality-ticket and check-id are required")
            payload = complete_product(
                root,
                args.project_id,
                args.session_key,
                args.quality_ticket,
                args.check_id,
                args.quality_timeout_seconds,
            )
        elif args.command == "live-verify":
            payload = record_local_live_verification(
                root,
                args.project_id,
                args.quality_ticket,
                args.check_id,
            )
        else:
            payload = public_status(root, args.project_id)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

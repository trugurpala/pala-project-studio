"""Golden PALA 1.0 product scenarios and final local evidence manifest."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from pala_agent_provider import ExecutionRequest, FakeProvider
from pala_delivery import FakeDeliveryAdapter, create_cpanel_plan, run_delivery
from pala_execution import ExecutionCoordinator
from pala_owner_cockpit import LiveVerification, render_owner_cockpit
from pala_product import ProductSpec
from pala_product_planner import validate_plan
from pala_task_packet import compile_task_packet

REQUIRED_EVIDENCE_FIELDS = {
    "schema_version",
    "product",
    "product_version",
    "plugin_version",
    "source_head",
    "surface_digest",
    "changed_files",
    "tool_versions",
    "canonical_test_command",
    "canonical_test_exit_code",
    "canonical_test_count",
    "canonical_test_skip_count",
    "pytest_command",
    "pytest_exit_code",
    "pytest_count",
    "ruff_command",
    "ruff_exit_code",
    "legacy_ruff_count",
    "mypy_command",
    "mypy_exit_code",
    "mypy_scope",
    "coverage_command",
    "coverage_exit_code",
    "coverage_percent",
    "bandit_command",
    "bandit_exit_code",
    "bandit_high",
    "bandit_medium",
    "pip_audit_command",
    "pip_audit_exit_code",
    "pip_audit_known_vulnerabilities",
    "source_verify_command",
    "source_verify_exit_code",
    "portable_verify_command",
    "portable_verify_exit_code",
    "installed_verify_command",
    "installed_verify_exit_code",
    "doctor_status",
    "quality_execution_authority",
    "evidence_forgery_regression",
    "product_contract_tests",
    "production_wiring_tests",
    "planner_tests",
    "provider_tests",
    "worktree_tests",
    "credential_tests",
    "delivery_tests",
    "playwright_command",
    "playwright_exit_code",
    "playwright_report",
    "browser_tests",
    "owner_cockpit_tests",
    "golden_contract",
    "golden_real_e2e",
    "artifact_path",
    "artifact_sha256",
    "artifact_entries",
    "open_p0",
    "open_p1",
    "technical_debt",
    "needs_decision",
    "remote_publish",
    "real_remote_deploy",
    "generated_at",
}


def _spec() -> dict[str, object]:
    return {
        "project_id": "water-tracker",
        "title": "Water Tracker",
        "goal": "Deliver a verified water tracking product",
        "user_outcome": "Users record and review water intake",
        "product_type": "web_application",
        "target_users": ["registered user"],
        "declared_facts": ["Natro", "cPanel", "Linux", "water tracking"],
        "unknowns": ["php", "mysql", "node", "python", "ssh", "sftp", "cron", "ssl"],
        "constraints": ["local-first"],
        "non_goals": ["real remote deployment"],
        "environment_requirements": ["web runtime", "persistent store"],
        "architecture_decision_ref": "ADR-water",
        "acceptance": ["intake persists"],
        "milestones": ["plan", "build", "verify", "package"],
        "delivery_target": "generic-linux-cpanel",
        "project_status": "DISCOVERING",
    }


def run_golden_scenarios() -> dict[str, object]:
    rows: list[dict[str, str]] = []

    spec = ProductSpec.from_dict(_spec())
    rows.append(
        {
            "id": "A",
            "name": "new_project",
            "status": "passed" if spec.project_id == "water-tracker" else "blocked",
        }
    )

    plan = validate_plan(
        {
            "product_spec": _spec(),
            "acceptance_matrix": [{"id": "AC-1", "criterion": "persists", "evidence": "browser"}],
            "environment_requirements": [{"id": "ENV-1", "capability": "php", "status": "UNKNOWN"}],
            "milestone_graph": {"plan": {"dependencies": []}, "build": {"dependencies": ["plan"]}},
            "task_dag": {"T-1": {"dependencies": []}, "T-2": {"dependencies": ["T-1"]}},
        }
    )
    rows.append({"id": "B", "name": "existing_project", "status": plan.status})

    packet = compile_task_packet(
        {
            "id": "T-1",
            "status": "IN_PROGRESS",
            "goal": "resume",
            "acceptance": ["verified"],
            "dependencies": [],
            "architecture_refs": [],
        },
        {"active_task": "T-1", "summary": "resume"},
        {},
        {"active_task": "T-1"},
        "minimal",
    )
    rows.append(
        {
            "id": "C",
            "name": "resume",
            "status": "passed" if packet and packet.task_id == "T-1" else "blocked",
        }
    )

    coordinator = ExecutionCoordinator()
    coordinator.claim("T-1", "lease-a", ["app/core.py"])
    parallel_blocked = False
    try:
        coordinator.claim("T-2", "lease-b", ["app/core.py"])
    except ValueError:
        parallel_blocked = True
    rows.append(
        {"id": "D", "name": "parallel", "status": "passed" if parallel_blocked else "blocked"}
    )

    failure_blocked = False
    try:
        FakeProvider(capabilities=set(), candidate={}).execute(
            ExecutionRequest("REQ-1", "T-1", {"authority": "TaskContract"}, ["local_edit"])
        )
    except ValueError:
        failure_blocked = True
    rows.append(
        {"id": "E", "name": "failure", "status": "passed" if failure_blocked else "blocked"}
    )

    delivery = create_cpanel_plan("dist/water.zip", {"linux": "VERIFIED", "cpanel": "VERIFIED"})
    denied = run_delivery(delivery, FakeDeliveryAdapter(), mutate=True)
    rows.append(
        {
            "id": "F",
            "name": "delivery_auth",
            "status": "passed" if denied["status"] == "blocked" else "blocked",
        }
    )
    rows.append(
        {
            "id": "G",
            "name": "cpanel",
            "status": "passed" if delivery.transfer_mode == "manual" else "blocked",
        }
    )

    live = LiveVerification("DEPLOYED", "not-run", []).with_result("passed", ["EV-browser"])
    rows.append(
        {
            "id": "H",
            "name": "live_verify",
            "status": "passed" if live.is_live_verified() else "blocked",
        }
    )

    cockpit = render_owner_cockpit(
        {
            "project": "Water Tracker",
            "state": "LIVE_VERIFYING",
            "acceptance_verified": 1,
            "acceptance_total": 1,
            "quality": "passed",
            "environment": "configured-not-verified",
            "delivery": "not-run",
            "live_verification": "passed",
            "blocker": "none",
            "next_action": "owner review",
            "owner_request": "Review local candidate.",
        }
    )
    rows.append(
        {"id": "I", "name": "owner_cockpit", "status": "passed" if "1/1" in cockpit else "blocked"}
    )

    return {
        "status": "passed" if all(row["status"] == "passed" for row in rows) else "blocked",
        "rows": rows,
        "remote_publish": "not-run",
        "real_remote_deploy": "not-run",
    }


def write_evidence_manifest(
    root: Path,
    artifact: Path,
    evidence: dict[str, object],
) -> Path:
    root = root.resolve()
    artifact = artifact.resolve()
    if root not in artifact.parents or not artifact.is_file():
        raise ValueError("artifact must be an existing project file")
    missing = REQUIRED_EVIDENCE_FIELDS - evidence.keys()
    if missing:
        raise ValueError(f"release evidence is incomplete: {sorted(missing)}")
    payload = {name: evidence[name] for name in REQUIRED_EVIDENCE_FIELDS}
    payload["schema_version"] = 2
    payload["artifact_path"] = artifact.relative_to(root).as_posix()
    payload["artifact_sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest().upper()
    with zipfile.ZipFile(artifact) as archive:
        payload["artifact_entries"] = len(archive.infolist())
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    path = root / "artifacts" / "final" / "pala-1.0-evidence-manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)
    return path


__all__ = ["REQUIRED_EVIDENCE_FIELDS", "run_golden_scenarios", "write_evidence_manifest"]

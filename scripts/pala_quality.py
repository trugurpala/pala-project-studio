#!/usr/bin/env python3
"""Derive and record evidence-first quality gates without running project tools.

This is Pala's Delivery Quality Engine v1. It deliberately discovers only
existing project commands and already-installed scanners. Running a command is
an explicit agent/user action; hooks never invoke this module to execute work.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess  # nosec B404
import sys
from datetime import datetime, timezone
from pathlib import Path

from pala_authority import shared_state_root
from pala_quality_discovery import (
    changed_paths,
    read_json,
    surface_digest,
)
from pala_quality_policy import SENSITIVE_VALUE, TIERS, build_quality_plan, risk_assessment

SCHEMA_VERSION = 1
QUALITY_DIR = Path(".codex/plugin-data/pala/v3/quality")
MAX_CHANGED_FILES = 80
STATUSES = ("passed", "failed", "not-run", "blocked", "configured-not-verified")
TICKET_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")

__all__ = ["TIERS", "build_quality_plan", "risk_assessment"]


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_ticket(ticket: str) -> str:
    value = str(ticket or "").strip()
    if not TICKET_NAME.fullmatch(value):
        raise ValueError("ticket must be 1-80 safe characters (letters, digits, . _ -)")
    return value


def _safe_text(value: object, *, field: str, limit: int = 500) -> str:
    text = str(value or "").strip()
    if SENSITIVE_VALUE.search(text):
        raise ValueError(f"{field} may not contain a secret value")
    return text[:limit]


def quality_ledger_path(root: Path, ticket: str) -> Path:
    project_root = Path(root).resolve()
    shared = shared_state_root(project_root)
    if shared is not None:
        return shared / "quality" / f"{_safe_ticket(ticket)}.json"
    return project_root / QUALITY_DIR / f"{_safe_ticket(ticket)}.json"


def _atomic_write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def write_ledger(root: Path, ticket: str, plan: dict[str, object]) -> Path:
    ticket = _safe_ticket(ticket)
    raw_checks = plan.get("checks")
    if not isinstance(raw_checks, list):
        raise ValueError("quality plan checks must be a list")
    checks: list[dict[str, object]] = []
    for item in raw_checks:
        if not isinstance(item, dict):
            raise ValueError("quality plan check must be an object")
        check_id = str(item.get("id") or "").strip()
        kind = str(item.get("kind") or "").strip()
        status = str(item.get("status") or "not-run").strip()
        if not check_id or not kind or status not in STATUSES:
            raise ValueError("quality plan contains invalid check")
        raw_argv = item.get("argv")
        approved_argv: list[str] | None = None
        if raw_argv is not None:
            if (
                not isinstance(raw_argv, list)
                or not raw_argv
                or len(raw_argv) > 32
                or any(
                    not isinstance(value, str)
                    or not value.strip()
                    or len(value) > 240
                    or any(character in value for character in ("\n", "\r", "\0"))
                    for value in raw_argv
                )
            ):
                raise ValueError("quality plan argv is invalid")
            approved_argv = [str(value) for value in raw_argv]
        command = _safe_text(item.get("command"), field="command", limit=8192) or None
        if approved_argv is not None and subprocess.list2cmdline(approved_argv) != command:
            raise ValueError("quality plan command does not match approved argv")
        checks.append(
            {
                "id": check_id[:120],
                "kind": kind[:40],
                "required": bool(item.get("required")),
                "argv": approved_argv,
                "command": command,
                "source": _safe_text(item.get("source"), field="source", limit=120),
                "status": status,
                "reason": _safe_text(item.get("reason"), field="reason", limit=240),
                "exit_code": None,
                "artifact": None,
                "updated_at": _stamp(),
            }
        )
    path = quality_ledger_path(root, ticket)
    previous: dict[str, object] = {}
    if path.is_file():
        previous = read_ledger(root, ticket)
    previous_files = [str(item) for item in list(previous.get("changed_files") or [])]
    current_files = [
        str(item)
        for item in list(plan.get("changed_files") or [])[:MAX_CHANGED_FILES]
    ]
    previous_git = previous.get("git") if isinstance(previous.get("git"), dict) else {}
    current_git = plan.get("git") if isinstance(plan.get("git"), dict) else {}
    retain_evidence = (
        str(previous.get("tier") or "ticket") == str(plan.get("tier") or "ticket")
        and previous_files == current_files
        and str(previous.get("surface_digest") or "") == str(plan.get("surface_digest") or "")
        and str(previous_git.get("head") or "unknown") == str(current_git.get("head") or "unknown")
    )
    previous_checks = {
        str(item.get("id")): item
        for item in previous.get("checks", [])
        if isinstance(item, dict)
    }
    for check in checks:
        old = previous_checks.get(str(check["id"]))
        # A reopened ticket retains evidence only when the exact gate remains
        # executable in the same way. New or changed gates start honestly.
        if (
            retain_evidence
            and isinstance(old, dict)
            and old.get("command") == check.get("command")
            and old.get("argv") == check.get("argv")
        ):
            for key in (
                "status",
                "exit_code",
                "artifact",
                "detail",
                "execution_authority",
                "execution_basis",
                "stdout_sha256",
                "stdout_bytes",
                "stderr_sha256",
                "stderr_bytes",
                "duration_ms",
                "updated_at",
            ):
                if key in old:
                    check[key] = old[key]
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "ticket": ticket,
        "risk": copy.deepcopy(plan.get("risk") if isinstance(plan.get("risk"), dict) else {}),
        "tier": str(plan.get("tier") or "ticket"),
        "changed_files": current_files,
        "ignored_changed_paths": [
            str(item) for item in list(plan.get("ignored_changed_paths") or [])[:40]
        ],
        "surface_digest": str(plan.get("surface_digest") or ""),
        "git": copy.deepcopy(plan.get("git") if isinstance(plan.get("git"), dict) else {}),
        "checks": checks,
        "created_at": previous.get("created_at") or _stamp(),
        "updated_at": _stamp(),
    }
    _atomic_write(path, payload)
    return path


def read_ledger(root: Path, ticket: str) -> dict[str, object]:
    payload = read_json(quality_ledger_path(root, ticket))
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("ticket") != _safe_ticket(ticket):
        raise ValueError("unsupported quality ledger")
    checks = payload.get("checks")
    if not isinstance(checks, list):
        raise ValueError("quality ledger checks are missing")
    return payload


def _artifact_path(root: Path, artifact: str | None) -> str | None:
    if not artifact:
        return None
    candidate = Path(artifact)
    if candidate.is_absolute():
        raise ValueError("artifact must be relative to the project root")
    resolved_root = Path(root).resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        relative = resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("artifact must remain inside the project root") from exc
    if not resolved.is_file():
        raise ValueError("artifact file does not exist")
    return relative.as_posix()


def record_result(
    root: Path,
    ticket: str,
    check_id: str,
    *,
    status: str,
    command: str,
    exit_code: int | None,
    artifact: str | None = None,
    detail: str = "",
    execution_authority: str | None = None,
    execution_basis: dict[str, object] | None = None,
    stdout_sha256: str | None = None,
    stdout_bytes: int | None = None,
    stderr_sha256: str | None = None,
    stderr_bytes: int | None = None,
    duration_ms: int | None = None,
) -> dict[str, object]:
    if status not in STATUSES:
        raise ValueError(f"unsupported quality status: {status}")
    safe_command = _safe_text(command, field="command", limit=8192)
    if not safe_command:
        raise ValueError("command is required")
    if status == "passed" and exit_code != 0:
        raise ValueError("passed quality evidence requires exit_code=0")
    if status == "failed" and (not isinstance(exit_code, int) or exit_code == 0):
        raise ValueError("failed quality evidence requires a non-zero exit code")
    if exit_code is not None and not isinstance(exit_code, int):
        raise ValueError("exit_code must be an integer or null")
    payload = read_ledger(root, ticket)
    checks = payload.get("checks")
    if not isinstance(checks, list):
        raise ValueError("quality ledger checks are missing")
    check = next((item for item in checks if isinstance(item, dict) and item.get("id") == check_id), None)
    if not isinstance(check, dict):
        raise ValueError(f"quality check not found: {check_id}")
    expected = check.get("command")
    if expected is None and status == "passed":
        raise ValueError("quality check is not executable from the approved plan")
    if isinstance(expected, str) and expected and expected != safe_command:
        raise ValueError("recorded command does not match the quality plan")
    safe_authority = (
        _safe_text(execution_authority, field="execution_authority", limit=80)
        if execution_authority
        else None
    )
    safe_basis = None
    if execution_basis is not None:
        safe_basis = {
            key: execution_basis.get(key)
            for key in ("head_sha", "index_digest", "worktree_digest", "surface_digest")
        }
    for name, digest in (("stdout_sha256", stdout_sha256), ("stderr_sha256", stderr_sha256)):
        if digest is not None and not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"{name} must be a SHA-256 digest")
    for name, value in (
        ("stdout_bytes", stdout_bytes),
        ("stderr_bytes", stderr_bytes),
        ("duration_ms", duration_ms),
    ):
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ValueError(f"{name} must be a non-negative integer")
    check.update(
        {
            "status": status,
            "command": safe_command,
            "exit_code": exit_code,
            "artifact": _artifact_path(root, artifact),
            "detail": _safe_text(detail, field="detail", limit=500),
            "execution_authority": safe_authority,
            "execution_basis": safe_basis,
            "stdout_sha256": stdout_sha256,
            "stdout_bytes": stdout_bytes,
            "stderr_sha256": stderr_sha256,
            "stderr_bytes": stderr_bytes,
            "duration_ms": duration_ms,
            "updated_at": _stamp(),
        }
    )
    payload["updated_at"] = _stamp()
    _atomic_write(quality_ledger_path(root, ticket), payload)
    return payload


def quality_gate(root: Path, ticket: str) -> dict[str, object]:
    payload = read_ledger(root, ticket)
    checks = [item for item in payload.get("checks", []) if isinstance(item, dict)]
    required = [item for item in checks if bool(item.get("required"))]
    passed_count = sum(1 for item in required if item.get("status") == "passed")
    recorded_files = [str(item) for item in list(payload.get("changed_files") or [])]
    recorded_digest = str(payload.get("surface_digest") or "")
    current_files, _ignored_files = changed_paths(Path(root).resolve())
    current_digest = surface_digest(Path(root).resolve(), current_files)
    current_snapshot = current_files[:MAX_CHANGED_FILES]
    if recorded_digest and (
        recorded_files != current_snapshot or recorded_digest != current_digest
    ):
        return {
            "status": "blocked",
            "ticket": payload.get("ticket"),
            "risk": payload.get("risk") if isinstance(payload.get("risk"), dict) else {},
            "coverage": {"passed": passed_count, "required": len(required)},
            "last_problem": "changed-surface=drifted",
            "next_action": "refresh quality plan and rerun required gates",
            "checks": checks,
        }
    if not checks:
        return {
            "status": "blocked",
            "ticket": payload.get("ticket"),
            "risk": payload.get("risk") if isinstance(payload.get("risk"), dict) else {},
            "coverage": {"passed": 0, "required": 0},
            "last_problem": "no quality gate discovered",
            "next_action": "configure project-native quality gate",
            "checks": checks,
        }
    problem = next((item for item in required if item.get("status") == "failed"), None)
    if problem is None:
        problem = next((item for item in required if item.get("status") != "passed"), None)
    if problem is None:
        status, next_action, last_problem = "passed", "", ""
    else:
        check_id = str(problem.get("id") or "quality-check")
        state = str(problem.get("status") or "not-run")
        status = "blocked"
        next_action = f"fix {check_id}" if state == "failed" else f"run {check_id}"
        if state == "configured-not-verified":
            next_action = f"configure {check_id}"
        last_problem = f"{check_id}={state}"
    risk = payload.get("risk") if isinstance(payload.get("risk"), dict) else {}
    return {
        "status": status,
        "ticket": payload.get("ticket"),
        "risk": risk,
        "coverage": {"passed": passed_count, "required": len(required)},
        "last_problem": last_problem,
        "next_action": next_action,
        "checks": checks,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan", help="Discover existing quality gates without writing or running them")
    plan.add_argument("--cwd", default=".")
    plan.add_argument("--tier", choices=TIERS, default="ticket")
    plan.add_argument("--changed", action="append", default=[])
    init = subparsers.add_parser("init", help="Create or refresh one local evidence ledger without running gates")
    init.add_argument("--cwd", default=".")
    init.add_argument("--ticket", required=True)
    init.add_argument("--tier", choices=TIERS, default="ticket")
    init.add_argument("--changed", action="append", default=[])
    record = subparsers.add_parser("record", help="Record one explicitly executed quality gate")
    record.add_argument("--cwd", default=".")
    record.add_argument("--ticket", required=True)
    record.add_argument("--check", required=True)
    record.add_argument("--status", choices=STATUSES, required=True)
    record.add_argument("--command", dest="quality_command", required=True)
    record.add_argument("--exit-code", type=int)
    record.add_argument("--artifact")
    record.add_argument("--detail", default="")
    status = subparsers.add_parser("status", help="Read the deterministic gate decision for a ticket")
    status.add_argument("--cwd", default=".")
    status.add_argument("--ticket", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.cwd).resolve()
    try:
        if args.command == "plan":
            print(json.dumps(build_quality_plan(root, tier=args.tier, changed_files=args.changed or None), ensure_ascii=False, indent=2))
            return 0
        if args.command == "init":
            plan = build_quality_plan(root, tier=args.tier, changed_files=args.changed or None)
            write_ledger(root, args.ticket, plan)
            print(json.dumps(quality_gate(root, args.ticket), ensure_ascii=False, indent=2))
            return 0
        if args.command == "record":
            record_result(root, args.ticket, args.check, status=args.status, command=args.quality_command, exit_code=args.exit_code, artifact=args.artifact, detail=args.detail)
            print(json.dumps(quality_gate(root, args.ticket), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(quality_gate(root, args.ticket), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

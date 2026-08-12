#!/usr/bin/env python3
"""Deterministic, local-only policy for Pala quality-plan discovery.

This owner turns already-observed repository metadata into an evidence plan.  It
never runs a project command, installs a scanner, makes a network call, or
executes inside a hook.  Ledger persistence and gate decisions stay in the
``pala_quality`` facade.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from pala_quality_discovery import (
    DANGEROUS_SCRIPT,
    changed_paths,
    git_summary,
    has_ui,
    package_scripts,
    project_package,
    python_unittest_discovery,
    read_json,
    surface_digest,
    workflow_commands,
    workflow_text,
)


SCHEMA_VERSION = 1
QUALITY_CONTRACT_PATH = Path(".pala/quality.json")
TIERS = ("narrow", "ticket", "milestone", "release")
CHECK_KINDS = (
    "unit",
    "lint",
    "typecheck",
    "build",
    "integration",
    "browser",
    "security",
    "dependency",
    "migration",
    "runtime-smoke",
)
SENSITIVE_VALUE = re.compile(
    r"(?i)(?:\b(?:api[_-]?key|token|password|secret)\s*=|--(?:api[_-]?key|token|password|secret)=)"
)
CHECK_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
PLAYWRIGHT_CONFIGS = (
    "playwright.config.ts",
    "playwright.config.js",
    "playwright.config.mjs",
    "playwright.config.cjs",
)
NATIVE_SCRIPT_CHECKS = (
    ("lint", ("lint",)),
    ("typecheck", ("typecheck", "check-types")),
    ("build", ("build",)),
    ("integration", ("test:integration", "integration")),
    ("migration", ("migrate:check", "migration:check")),
    ("runtime-smoke", ("smoke", "test:smoke")),
)
SCANNER_SPECS = (
    ("gitleaks", "security"),
    ("zizmor", "security"),
    ("osv-scanner", "dependency"),
)


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_text(value: object, *, field: str, limit: int = 500) -> str:
    text = str(value or "").strip()
    if SENSITIVE_VALUE.search(text):
        raise ValueError(f"{field} may not contain a secret value")
    return text[:limit]


def risk_assessment(
    changed_files: list[str], *, has_project_code: bool
) -> dict[str, object]:
    reasons: list[str] = []
    lowered = "\n".join(changed_files).casefold()
    if any(token in lowered for token in ("auth", "permission", "role", "session", "oauth")):
        reasons.append("authentication")
    if any(token in lowered for token in ("migration", "schema", "database", "db/")):
        reasons.append("migration")
    if any(token in lowered for token in ("payment", "billing", "checkout")):
        reasons.append("payments")
    if any(
        token in lowered
        for token in ("deploy", "infra", "terraform", "dockerfile", "workflow")
    ):
        reasons.append("delivery")
    if reasons:
        level = "high"
    elif changed_files or has_project_code:
        level = "medium"
    else:
        level = "low"
    return {
        "level": level,
        "reasons": reasons or (["project-code"] if has_project_code else []),
    }


def _required_for_tier(kind: str, tier: str) -> bool:
    return kind == "unit" if tier == "narrow" else True


def _add_check(
    checks: list[dict[str, object]],
    *,
    kind: str,
    name: str,
    command: str | None,
    source: str,
    tier: str,
    status: str = "not-run",
    reason: str = "",
    argv: list[str] | None = None,
) -> None:
    check_id = f"{kind}:{name}"
    if any(item.get("id") == check_id for item in checks):
        return
    checks.append(
        {
            "id": check_id,
            "kind": kind,
            "required": _required_for_tier(kind, tier),
            "argv": argv,
            "command": command,
            "source": source,
            "status": status,
            "reason": reason[:240],
        }
    )


def _contract_command(argv: object) -> tuple[list[str], str]:
    """Validate a shell-free command contract and return argv plus display form."""
    if not isinstance(argv, list) or not argv or len(argv) > 32:
        raise ValueError("argv must be a non-empty list with at most 32 arguments")
    values: list[str] = []
    for raw in argv:
        if not isinstance(raw, str) or not raw.strip() or len(raw) > 240:
            raise ValueError("each argv item must be a short non-empty string")
        value = raw.strip()
        if any(character in value for character in ("\n", "\r", "\0")):
            raise ValueError("argv items may not contain control characters")
        if value in {";", "|", "||", "&&", "&"}:
            raise ValueError("argv may not contain shell operators")
        values.append(value)
    command = subprocess.list2cmdline(values)
    if DANGEROUS_SCRIPT.search(command):
        raise ValueError("argv resolves to a command requiring manual safety review")
    _safe_text(command, field="contract command", limit=8192)
    return values, command


def _quality_contract_checks(
    root: Path, tier: str
) -> tuple[list[dict[str, object]], str]:
    """Load an optional project-owned contract; invalid input fails closed."""
    path = root / QUALITY_CONTRACT_PATH
    if not path.is_file():
        return [], ""
    try:
        payload = read_json(path)
        if payload.get("schema_version") != 1:
            raise ValueError("schema_version must be 1")
        raw_checks = payload.get("checks")
        if not isinstance(raw_checks, list) or not raw_checks:
            raise ValueError("checks must be a non-empty list")
        checks: list[dict[str, object]] = []
        seen: set[str] = set()
        for raw in raw_checks:
            if not isinstance(raw, dict):
                raise ValueError("each check must be an object")
            name = str(raw.get("id") or "").strip()
            kind = str(raw.get("kind") or "").strip()
            if not CHECK_NAME.fullmatch(name):
                raise ValueError(
                    "check id must use safe letters, digits, dots, underscores, or hyphens"
                )
            if kind not in CHECK_KINDS:
                raise ValueError(f"unsupported contract check kind: {kind}")
            check_id = f"{kind}:{name}"
            if check_id in seen:
                raise ValueError(f"duplicate contract check: {check_id}")
            seen.add(check_id)
            tiers = raw.get("tiers", list(TIERS))
            if (
                not isinstance(tiers, list)
                or not tiers
                or any(item not in TIERS for item in tiers)
            ):
                raise ValueError("tiers must be a non-empty list of supported tiers")
            argv, command = _contract_command(raw.get("argv"))
            checks.append(
                {
                    "id": check_id,
                    "kind": kind,
                    "required": tier in tiers and _required_for_tier(kind, tier),
                    "argv": argv,
                    "command": command,
                    "source": "pala-quality-contract",
                    "status": "not-run",
                    "reason": "",
                }
            )
        return checks, ""
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [], f"invalid {QUALITY_CONTRACT_PATH.as_posix()}: {exc}"[:240]


def _add_contract_checks(checks: list[dict[str, object]], root: Path, tier: str) -> None:
    contract_checks, contract_error = _quality_contract_checks(root, tier)
    checks.extend(contract_checks)
    if contract_error:
        _add_check(
            checks,
            kind="integration",
            name="quality-contract",
            command=None,
            source="pala-quality-contract",
            tier=tier,
            status="blocked",
            reason=contract_error,
        )


def _add_script_check(
    checks: list[dict[str, object]],
    *,
    kind: str,
    name: str,
    scripts: dict[str, str],
    tier: str,
) -> None:
    """Add a project-native script, but never normalize a destructive command."""
    configured = scripts[name]
    if DANGEROUS_SCRIPT.search(configured):
        _add_check(
            checks,
            kind=kind,
            name=name,
            command=None,
            source="package.json",
            tier=tier,
            status="blocked",
            reason="configured script needs manual safety review",
        )
        return
    _add_check(
        checks,
        kind=kind,
        name=name,
        command=f"npm run {name}",
        source="package.json",
        tier=tier,
        argv=["npm", "run", name],
    )


def _add_native_project_checks(
    checks: list[dict[str, object]],
    *,
    root: Path,
    scripts: dict[str, str],
    tier: str,
) -> bool:
    for name in ("test:unit", "test"):
        if name in scripts:
            _add_script_check(checks, kind="unit", name=name, scripts=scripts, tier=tier)
            break
    python_tests_detected = False
    if not any(item["kind"] == "unit" for item in checks):
        command, reason = python_unittest_discovery(root)
        python_tests_detected = bool(command or reason)
        if python_tests_detected:
            _add_check(
                checks,
                kind="unit",
                name="unittest",
                command=command,
                source="python-tests",
                tier=tier,
                status="not-run" if command else "configured-not-verified",
                reason=reason,
            )
    for kind, candidates in NATIVE_SCRIPT_CHECKS:
        for name in candidates:
            if name in scripts:
                _add_script_check(checks, kind=kind, name=name, scripts=scripts, tier=tier)
                break
    return python_tests_detected


def _add_browser_checks(
    checks: list[dict[str, object]],
    *,
    root: Path,
    package: dict[str, object],
    scripts: dict[str, str],
    tier: str,
) -> None:
    ui = has_ui(package, root)
    playwright_config = any((root / name).is_file() for name in PLAYWRIGHT_CONFIGS)
    for name, command in scripts.items():
        has_playwright_command = "playwright" in command.casefold()
        if ui and (playwright_config or has_playwright_command) and (
            "e2e" in name.casefold() or has_playwright_command
        ):
            _add_script_check(checks, kind="browser", name=name, scripts=scripts, tier=tier)
            break
    if ui and playwright_config and not any(item["kind"] == "browser" for item in checks):
        _add_check(
            checks,
            kind="browser",
            name="playwright-config",
            command=None,
            source="playwright-config",
            tier=tier,
            status="configured-not-verified",
            reason="Playwright config exists but no explicit project-owned browser command was found",
        )


def _add_scanner_checks(
    checks: list[dict[str, object]],
    *,
    root: Path,
    scripts: dict[str, str],
    tier: str,
    which: Callable[[str], str | None],
) -> None:
    workflow = workflow_text(root)
    ci_commands = workflow_commands(root)
    for scanner, kind in SCANNER_SPECS:
        if scanner not in workflow:
            continue
        script_name = next(
            (name for name, command in scripts.items() if scanner in command.casefold()),
            None,
        )
        workflow_command = next(
            (
                command
                for command in ci_commands
                if scanner in command.casefold() and not DANGEROUS_SCRIPT.search(command)
            ),
            None,
        )
        if scanner == "osv-scanner":
            _add_check(
                checks,
                kind=kind,
                name=scanner,
                command=None,
                source="existing-ci",
                tier=tier,
                status="configured-not-verified",
                reason="OSV scanner may use the network; use an explicit project-owned offline contract command",
            )
        elif script_name is not None:
            _add_script_check(
                checks, kind=kind, name=script_name, scripts=scripts, tier=tier
            )
        elif workflow_command and which(scanner):
            _add_check(
                checks,
                kind=kind,
                name=scanner,
                command=workflow_command,
                source="existing-ci",
                tier=tier,
            )
        else:
            _add_check(
                checks,
                kind=kind,
                name=scanner,
                command=None,
                source="existing-ci",
                tier=tier,
                status="configured-not-verified",
                reason="explicit installed project scanner command required",
            )
    if "audit" in scripts:
        _add_script_check(checks, kind="dependency", name="audit", scripts=scripts, tier=tier)


def _add_risk_surface_checks(
    checks: list[dict[str, object]], *, risk: dict[str, object], tier: str
) -> None:
    reasons = set(risk.get("reasons") or [])
    if "migration" in reasons and not any(item["kind"] == "migration" for item in checks):
        _add_check(
            checks,
            kind="migration",
            name="risk-surface",
            command=None,
            source="changed-surface",
            tier=tier,
            status="blocked",
            reason="migration changed; configure a project-native migration check",
        )
    if reasons.intersection({"authentication", "payments"}) and not any(
        item["kind"] == "security" for item in checks
    ):
        _add_check(
            checks,
            kind="security",
            name="risk-surface",
            command=None,
            source="changed-surface",
            tier=tier,
            status="blocked",
            reason="high-risk surface changed; configure a project-native security check",
        )


def build_quality_plan(
    root: Path,
    *,
    tier: str = "ticket",
    changed_files: list[str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> dict[str, object]:
    """Return a deterministic plan; this function never executes project commands."""
    root = Path(root).resolve()
    if tier not in TIERS:
        raise ValueError(f"unsupported quality tier: {tier}")
    package = project_package(root)
    scripts = package_scripts(package)
    checks: list[dict[str, object]] = []
    _add_contract_checks(checks, root, tier)
    python_tests_detected = _add_native_project_checks(
        checks, root=root, scripts=scripts, tier=tier
    )
    _add_browser_checks(
        checks, root=root, package=package, scripts=scripts, tier=tier
    )
    _add_scanner_checks(
        checks, root=root, scripts=scripts, tier=tier, which=which
    )
    if changed_files is None:
        files, ignored_files = changed_paths(root)
    else:
        files = sorted({str(item) for item in changed_files}, key=str.casefold)
        ignored_files = []
    risk = risk_assessment(
        files, has_project_code=bool(package) or python_tests_detected
    )
    _add_risk_surface_checks(checks, risk=risk, tier=tier)
    return {
        "schema_version": SCHEMA_VERSION,
        "root": root.name,
        "tier": tier,
        "changed_files": [str(item)[:240] for item in files[:80]],
        "ignored_changed_paths": [str(item)[:240] for item in ignored_files[:40]],
        "surface_digest": surface_digest(root, files),
        "risk": risk,
        "git": git_summary(root, files),
        "checks": checks,
        "generated_at": _stamp(),
        "execution": "not-run: run only selected project-native commands; hooks never execute gates",
    }

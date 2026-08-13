#!/usr/bin/env python3
"""Explicit Playwright project-profile policy and evidence validation."""

from __future__ import annotations

import json
from pathlib import Path

CLI_VERSION = "0.1.18"
CLI_INTEGRITY = "sha512:ggNfYYH+GsZTGUiBEL8f6N5j0seYEUE52v+fIWqK/A36QG36cL0EJ79qWTXYO2uZMUU7vm+jk3x0fKCPL6UuIw=="
TEST_VERSION = "1.62.1"
TEST_INTEGRITY = "sha512:DTcUc8qii+cpHvtOwggMtBRMjKZHXYWdw8syRYu2vtzuq4Wxphqq4NfCs5Zt44L6mA8rfDfj+PHnxFc/FeK6mQ=="


def _package(root: Path) -> dict[str, object]:
    try:
        value = json.loads((Path(root) / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def inspect_project_profile(root: Path, *, task_requires_browser: bool) -> dict[str, object]:
    package = _package(root)
    dependencies: dict[str, object] = {}
    for name in ("dependencies", "devDependencies"):
        values = package.get(name)
        if isinstance(values, dict):
            dependencies.update(values)
    declared = dependencies.get("@playwright/test")
    exact = declared == TEST_VERSION
    if not task_requires_browser:
        status = "not-run"
        action = "profile-not-selected"
    elif exact:
        status = "passed"
        action = "reuse-project-dependency"
    else:
        status = "blocked"
        action = "explicit-taskcontract-change-required"
    return {
        "status": status,
        "profile": "PROJECT_PROFILE",
        "task_requires_browser": task_requires_browser,
        "affects_core_health": task_requires_browser,
        "action": action,
        "mutation_authorized": False,
        "default_mcp_registered": False,
        "browser_exploration": {
            "provider": "@playwright/cli",
            "version": CLI_VERSION,
            "state": "absent",
            "installation": "explicit-pala-profile-only",
            "authority": "advisory",
        },
        "browser_e2e": {
            "provider": "@playwright/test",
            "version": TEST_VERSION,
            "declared": declared,
            "state": "exact" if exact else ("absent" if declared is None else "old"),
            "authority": "Pala Quality Engine runner",
        },
    }


def browser_environment(cache_root: Path) -> dict[str, str]:
    return {
        "PLAYWRIGHT_BROWSERS_PATH": str(Path(cache_root).resolve()),
        "CI": "1",
        "PW_TEST_HTML_REPORT_OPEN": "never",
        "NO_COLOR": "1",
    }


def validate_browser_evidence(root: Path, record: dict[str, object]) -> dict[str, object]:
    base = Path(root).resolve()
    missing: list[str] = []
    resolved: dict[str, str] = {}
    for field in ("trace", "screenshot", "console", "network"):
        raw = record.get(field)
        if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
            missing.append(field)
            continue
        path = (base / raw).resolve()
        try:
            relative = path.relative_to(base)
        except ValueError:
            missing.append(field)
            continue
        if not path.is_file():
            missing.append(field)
            continue
        resolved[field] = relative.as_posix()
    browser_version = record.get("browser_version")
    if not isinstance(browser_version, str) or not browser_version.strip():
        missing.append("browser_version")
    forbidden_ui = record.get("ui_opened") is True or record.get("trace_viewer_opened") is True
    return {
        "status": "passed" if not missing and not forbidden_ui else "blocked",
        "validated": resolved,
        "browser_version": browser_version,
        "missing": missing,
        "automatic_ui_opened": forbidden_ui,
        "authority": "Pala Quality Engine evidence validator",
        "read_only": True,
    }

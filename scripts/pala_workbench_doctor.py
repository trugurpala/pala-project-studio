#!/usr/bin/env python3
"""Capability-oriented Workbench Doctor projection."""

from __future__ import annotations

from pathlib import Path

from pala_codegraph import CODEGRAPH_EXECUTABLE, artifact_spec
from pala_playwright import inspect_project_profile
from pala_semgrep import language_coverage, probe_health as semgrep_probe
from pala_workbench_install import inventory as codegraph_inventory_raw


def codegraph_inventory(state_root: Path) -> dict[str, object]:
    return codegraph_inventory_raw(artifact_spec(), state_root, executable=CODEGRAPH_EXECUTABLE)


def doctor(
    state_root: Path,
    project_root: Path,
    *,
    task_requires_browser: bool,
    offline: bool = False,
) -> dict[str, object]:
    codegraph = codegraph_inventory(state_root)
    semgrep = semgrep_probe(state_root)
    security_coverage = language_coverage(
        project_root, {"python", "javascript", "typescript"}
    )
    playwright = inspect_project_profile(project_root, task_requires_browser=task_requires_browser)
    problems: list[str] = []
    if not (
        codegraph.get("state") == "exact"
        and codegraph.get("health") == "passed"
        and codegraph.get("version") == "1.5.0"
    ):
        problems.append("code_intelligence")
    if not (
        semgrep.get("state") == "exact"
        and semgrep.get("status") == "passed"
        and semgrep.get("version") == "1.172.0"
    ):
        problems.append("security_static")
    if task_requires_browser and playwright.get("status") != "passed":
        problems.append("browser_e2e")
    capabilities = {
        "code_intelligence": codegraph,
        "security_static": semgrep,
        "browser_profile": playwright,
        "symbol_precision": {"state": "absent", "required": False, "profile": "LAZY_FALLBACK"},
        "current_docs": {"state": "absent", "required": False, "profile": "OPTIONAL_EXTERNAL"},
    }
    experts = Path(state_root) / "experts"
    retired = {
        name: (experts / name).exists()
        for name in (
            "graphify",
            "codebase-memory",
            "code-review-graph",
            "ollama",
            "rtk",
            "playwright-mcp",
            "serena",
        )
    }
    code_ready = "code_intelligence" not in problems
    security_ready = "security_static" not in problems
    browser_ready = "browser_e2e" not in problems
    return {
        "status": "ready" if not problems else "attention_required",
        "healthy": not problems,
        "problems": problems,
        "capabilities": capabilities,
        "normal": {
            "Pala Core": "hazir" if not problems else "dikkat-gerektiriyor",
            "Kod anlayisi": "hazir" if code_ready else "kullanilamiyor",
            "Guvenlik": {
                "motor": "hazir" if security_ready else "kullanilamiyor",
                "proje_kapsami": security_coverage["status"],
            },
            "Tarayici dogrulama": (
                "hazir"
                if task_requires_browser and browser_ready
                else "proje-gerektirdiginde"
                if not task_requires_browser
                else "kullanilamiyor"
            ),
            "Control Center": "hazir",
        },
        "security_truth": {
            "engine_ready": security_ready,
            "coverage_verified": security_coverage["status"] == "passed",
            "coverage": security_coverage,
        },
        "advanced": {
            "ownership": {
                key: value.get("ownership", "external-or-not-run")
                for key, value in capabilities.items() if isinstance(value, dict)
            },
            "version_integrity_provenance": {
                "codegraph": {key: codegraph.get(key) for key in ("version", "integrity", "provenance")},
                "semgrep": {key: semgrep.get(key) for key in ("version", "integrity", "provenance")},
            },
            "freshness_offline": {
                "codegraph": "current" if "code_intelligence" not in problems else "stale-or-unavailable",
                "offline": offline,
            },
            "forbidden_runtime": {
                "shared_daemon": False,
                "global_path_mutation": False,
                "automatic_ui": False,
            },
            "retired_remnants": retired,
        },
        "authority": "pala-workbench-doctor",
    }

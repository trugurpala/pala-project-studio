#!/usr/bin/env python3
"""Quality-runner face for the bounded local Semgrep capability."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pala_semgrep import run_local_scan


def default_state_root() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise RuntimeError("LOCALAPPDATA is required for Pala-owned Workbench state")
    return Path(local) / "Pala"


def sanitized_result(result: dict[str, object]) -> dict[str, object]:
    capability = result.get("capability_health")
    capability = capability if isinstance(capability, dict) else {}
    findings = result.get("findings")
    findings = findings if isinstance(findings, dict) else {}
    return {
        "status": result.get("status"),
        "capability": {
            "state": capability.get("state"),
            "version": capability.get("version"),
            "health": capability.get("health"),
            "integrity": capability.get("integrity"),
            "ownership": capability.get("ownership"),
        },
        "coverage": result.get("coverage"),
        "scan": {
            "exit_code": findings.get("scan_exit_code"),
            "finding_count": findings.get("finding_count"),
            "error_count": findings.get("error_count"),
            "candidate_check_ids": result.get("candidate_check_ids", []),
        },
        "network": "disabled",
        "metrics": "off",
        "authority": "Pala Quality Engine runner candidate",
        "sanitized": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", type=Path)
    parser.add_argument("--state-root", type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_local_scan(
            args.project.resolve(),
            (args.state_root or default_state_root()).resolve(),
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "blocked", "reason": type(exc).__name__, "sanitized": True}))
        return 2
    print(json.dumps(sanitized_result(result), ensure_ascii=True, sort_keys=True))
    findings = result.get("findings")
    if not isinstance(findings, dict) or result.get("status") != "passed":
        return 2
    if int(findings.get("finding_count", 0) or 0) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

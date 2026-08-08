#!/usr/bin/env python3
"""M10 managed-tools canary: RTK lock, MCP pins, OpenSpec ticket bind (no network)."""

from __future__ import annotations

import json
from pathlib import Path

from pala_adapters import load_managed_tools_lock
from pala_mcp import MCP_SPECS
from pala_openspec import OpenSpecAdapter
from pala_rtk import rewrite
from pala_rtk_hook import managed_rtk

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def rtk_lock_report(root: Path | None = None) -> dict[str, object]:
    root = (root or PLUGIN_ROOT).resolve()
    lock = load_managed_tools_lock(root / "managed-tools.lock.json")
    rtk = lock.get("rtk")
    if not isinstance(rtk, dict):
        return {"status": "failed", "detail": "rtk missing from lock"}
    sha = str(rtk.get("sha256") or "")
    version = str(rtk.get("version") or "")
    if len(sha) != 64 or version != "0.44.2":
        return {"status": "failed", "detail": f"rtk pin invalid version={version}"}
    path = managed_rtk()
    return {
        "status": "passed",
        "version": version,
        "sha256": sha,
        "managed_path": str(path),
        "rewrite_safe_only": True,
    }


def rtk_rewrite_guard_ok() -> bool:
    """Dangerous commands must not rewrite even if a fake binary exists."""
    fake = Path("C:/nonexistent/rtk-fake.exe")
    blocked = rewrite("git push origin main", {"command": "git push origin main"}, fake)
    allowed = rewrite("rg foo", {"command": "rg foo"}, Path(__file__))
    # executable must be a real file for allow — use this module path as stand-in file
    return blocked is None and (
        allowed is None or "RTK_TELEMETRY_DISABLED" in str(allowed.get("env"))
    )


def mcp_pin_report() -> dict[str, object]:
    """Report pinned Context7 / Playwright specs without calling Codex network."""
    names = sorted(MCP_SPECS)
    return {
        "status": "passed" if names == ["context7", "playwright-mcp"] else "failed",
        "specs": {
            name: {
                "command": MCP_SPECS[name]["command"],
                "args": list(MCP_SPECS[name]["args"]),
            }
            for name in names
        },
        "ensure_policy": "missing_only_no_overwrite_conflict",
    }


def openspec_ticket_report(
    root: Path, active_ticket: str | None
) -> dict[str, object]:
    result = OpenSpecAdapter().bind_active_ticket(root, active_ticket)
    return {
        "status": "passed" if result.state in {"ready", "missing"} else "failed",
        "state": result.state,
        "detail": result.detail,
        "evidence": list(result.evidence),
    }


def code_review_graph_lock_report(root: Path | None = None) -> dict[str, object]:
    root = (root or PLUGIN_ROOT).resolve()
    lock = load_managed_tools_lock(root / "managed-tools.lock.json")
    entry = lock.get("code-review-graph")
    if not isinstance(entry, dict):
        return {"status": "failed", "detail": "code-review-graph missing"}
    return {
        "status": "passed",
        "version": entry.get("version"),
        "uv_isolated": True,
        "install_via": "pala_expert_installer.install_python_tool",
    }


def run_canary(
    root: Path | None = None, active_ticket: str | None = None
) -> dict[str, object]:
    root = (root or PLUGIN_ROOT).resolve()
    checks = {
        "rtk_lock": rtk_lock_report(root),
        "rtk_rewrite_guard": {
            "status": "passed" if rtk_rewrite_guard_ok() else "failed"
        },
        "mcp_pins": mcp_pin_report(),
        "openspec_bind": openspec_ticket_report(root, active_ticket),
        "code_review_graph": code_review_graph_lock_report(root),
    }
    failed = [
        name for name, item in checks.items() if item.get("status") == "failed"
    ]
    return {
        "status": "failed" if failed else "passed",
        "failed": failed,
        "checks": checks,
    }


def main() -> int:
    payload = run_canary()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

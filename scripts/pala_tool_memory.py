#!/usr/bin/env python3
"""Honest tool / extension memory statuses for Pala projects."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

TOOL_MEMORY_STATES = {
    "installed",
    "recommended",
    "installed_unverified",
    "not_installed",
    "unavailable",
}

ADAPTER_TO_TOOL = {
    "ready": "installed",
    "missing": "not_installed",
    "external_conflict": "installed_unverified",
    "unsupported": "unavailable",
    "failed": "installed_unverified",
}


def map_adapter_state(state: str) -> str:
    return ADAPTER_TO_TOOL.get(state, "unavailable")


def _which_status(name: str, *, recommended: bool = False) -> dict[str, object]:
    path = shutil.which(name)
    if path:
        return {
            "name": name,
            "status": "installed",
            "evidence": path,
            "detail": "on PATH",
        }
    if recommended:
        return {
            "name": name,
            "status": "recommended",
            "evidence": "",
            "detail": "not on PATH",
        }
    return {
        "name": name,
        "status": "not_installed",
        "evidence": "",
        "detail": "not on PATH",
    }


def _python_status() -> dict[str, object]:
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= (3, 10)
    return {
        "name": "python",
        "status": "installed" if ok else "installed_unverified",
        "evidence": sys.executable,
        "detail": f"{major}.{minor}",
    }


def _extension_probe(cli: str, extension_id: str) -> dict[str, object]:
    exe = shutil.which(cli)
    if not exe:
        return {
            "name": extension_id,
            "status": "unavailable",
            "evidence": "",
            "detail": f"{cli} CLI not found",
        }
    try:
        result = subprocess.run(
            [exe, "--list-extensions"],
            capture_output=True,
            text=True,
            check=False,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {
            "name": extension_id,
            "status": "installed_unverified",
            "evidence": exe,
            "detail": "list-extensions failed",
        }
    if result.returncode != 0:
        return {
            "name": extension_id,
            "status": "installed_unverified",
            "evidence": exe,
            "detail": "list-extensions non-zero",
        }
    names = {line.strip().casefold() for line in result.stdout.splitlines()}
    if extension_id.casefold() in names:
        return {
            "name": extension_id,
            "status": "installed",
            "evidence": f"{cli} --list-extensions",
            "detail": "extension present",
        }
    return {
        "name": extension_id,
        "status": "recommended",
        "evidence": f"{cli} --list-extensions",
        "detail": "extension absent",
    }


def probe_host_tools(profiles: list[str] | None = None) -> list[dict[str, object]]:
    profiles = profiles or []
    items = [
        _python_status(),
        _which_status("git"),
        _which_status("codex", recommended=True),
        _which_status("node", recommended=True),
        _which_status("uv", recommended=True),
        _which_status("gemini", recommended=False),
    ]
    # IDE extensions: only probe when backend/php-ish profile hints exist.
    if any("backend" in p or "php" in p for p in profiles):
        items.append(_extension_probe("code", "xdebug.php-debug"))
        items.append(_extension_probe("cursor", "xdebug.php-debug"))
    return items


def inventory_from_adapters(
    adapters: dict[str, dict[str, object]] | None,
) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    if not isinstance(adapters, dict):
        return result
    for name, entry in adapters.items():
        if not isinstance(entry, dict):
            continue
        state = str(entry.get("state", "missing"))
        result.append(
            {
                "name": name,
                "status": map_adapter_state(state),
                "evidence": str(entry.get("detail", ""))[:200],
                "detail": state,
            }
        )
    return result


def summarize(items: list[dict[str, object]]) -> dict[str, object]:
    counts = {key: 0 for key in TOOL_MEMORY_STATES}
    for item in items:
        status = str(item.get("status", "unavailable"))
        if status in counts:
            counts[status] += 1
    return {
        "counts": counts,
        "total": len(items),
        "items": items,
    }


def tool_memory_report(
    *,
    profiles: list[str] | None = None,
    adapters: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    items = probe_host_tools(profiles)
    items.extend(inventory_from_adapters(adapters))
    return summarize(items)


def short_hook_summary(report: dict[str, object]) -> str:
    counts = report.get("counts") if isinstance(report.get("counts"), dict) else {}
    installed = int(counts.get("installed", 0))
    gaps = int(counts.get("not_installed", 0)) + int(
        counts.get("installed_unverified", 0)
    ) + int(counts.get("recommended", 0))
    return f"tools={installed}ok/{gaps}gap"


def write_tooling_section(path: Path, report: dict[str, object]) -> None:
    """Refresh machine-local tooling table without secrets."""
    lines = [
        "# Tooling decisions",
        "",
        "| Tool | Status | Evidence | Notes |",
        "| --- | --- | --- | --- |",
    ]
    for item in report.get("items", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", ""))[:80]
        status = str(item.get("status", ""))[:40]
        evidence = str(item.get("evidence", "")).replace("|", "/")[:120]
        detail = str(item.get("detail", "")).replace("|", "/")[:120]
        lines.append(f"| {name} | {status} | {evidence} | {detail} |")
    lines.extend(
        [
            "",
            "Statuses: installed | recommended | installed_unverified | "
            "not_installed | unavailable",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

#!/usr/bin/env python3
"""Ownership-proven quarantine and rollback for retired Workbench helpers."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

RETIRED = ("graphify", "codebase-memory", "code-review-graph", "ollama", "rtk", "playwright-mcp", "serena")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _owned_versions(root: Path, name: str) -> tuple[bool, list[str], str]:
    capability = Path(root) / name
    if not capability.exists():
        return False, [], "absent"
    if not capability.is_dir():
        return False, [], "ambiguous"
    versions: list[str] = []
    for target in sorted(capability.iterdir()):
        if not target.is_dir():
            return False, versions, "ambiguous"
        marker_path = target / "install.json"
        payload = target / "payload.bin"
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return False, versions, "foreign"
        if not isinstance(marker, dict) or marker.get("name") != name or marker.get("version") != target.name:
            return False, versions, "foreign"
        if not payload.is_file() or marker.get("sha256") != _sha256(payload):
            return False, versions, "modified"
        versions.append(target.name)
    return bool(versions), versions, "pala-owned" if versions else "ambiguous"


def inventory_legacy(root: Path) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for name in RETIRED:
        owned, versions, state = _owned_versions(root, name)
        result.append(
            {
                "name": name,
                "state": state,
                "versions": versions,
                "decision": "quarantine" if owned else "preserve",
                "reason": "proven-pala-owned" if owned else state,
            }
        )
    return result


def quarantine_transaction(
    root: Path,
    quarantine: Path,
    *,
    workbench_health: bool,
    post_health=lambda: True,
) -> dict[str, object]:
    inventory = inventory_legacy(root)
    if not workbench_health:
        return {"status": "blocked", "changed": False, "inventory": inventory, "reason": "workbench-not-healthy"}
    source_root = Path(root).resolve()
    destination_root = Path(quarantine).resolve()
    destination_root.mkdir(parents=True, exist_ok=True)
    moved: list[tuple[Path, Path]] = []
    try:
        for item in inventory:
            if item["decision"] != "quarantine":
                continue
            source = source_root / str(item["name"])
            destination = destination_root / str(item["name"])
            if destination.exists():
                item["decision"] = "preserve"
                item["reason"] = "quarantine-target-occupied"
                continue
            os.replace(source, destination)
            moved.append((source, destination))
        if not post_health():
            raise RuntimeError("post-migration-workbench-health-failed")
    except Exception as exc:
        for source, destination in reversed(moved):
            if destination.exists() and not source.exists():
                os.replace(destination, source)
        return {
            "status": "rolled-back",
            "changed": False,
            "inventory": inventory,
            "reason": str(exc),
            "moved": [],
            "serena_profile": "legacy-preserved",
        }
    moved_names = [source.name for source, _destination in moved]
    return {
        "status": "passed",
        "changed": bool(moved),
        "inventory": inventory,
        "moved": moved_names,
        "preserved": [item["name"] for item in inventory if item["decision"] == "preserve"],
        "serena_profile": "lazy-absent" if "serena" in moved_names else "lazy-external-preserved",
        "rollback": "available-in-quarantine",
    }

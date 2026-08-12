#!/usr/bin/env python3
"""Read-only local release truth, drift lint, and remote preflight."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object: {path}")
    return payload


def release_truth(root: Path) -> dict[str, object]:
    identity = _json(root / "product-identity.json")
    return {
        "product": identity["product"],
        "product_version": identity["product_version"],
        "plugin_version": identity["plugin_version"],
        "artifact_name": identity["artifact_name"],
        "release_status": identity["release_status"],
        "remote_publish": "not-run",
        "real_remote_deploy": "not-run",
        "last_published_version": identity.get("last_published_version", ""),
        "authority": "product-identity.json",
    }


def publication_matrix(root: Path) -> dict[str, object]:
    truth = release_truth(root)
    return {
        "local_candidate": {"status": "configured-not-verified", "version": truth["product_version"], "artifact": truth["artifact_name"]},
        "public_release": {"status": "not-run", "version": truth["last_published_version"]},
        "remote_publish": "not-run",
        "real_remote_deploy": "not-run",
        "write_authority": "separate-explicit-authority-required",
    }


def drift_lint(root: Path) -> dict[str, object]:
    truth = release_truth(root)
    readme = (root / "README.md").read_text(encoding="utf-8")
    plugin = _json(root / ".codex-plugin" / "plugin.json")
    findings: list[str] = []
    if str(truth["product_version"]) not in readme:
        findings.append("README product version drift")
    if plugin.get("version") != truth["plugin_version"]:
        findings.append("plugin version drift")
    if str(truth["artifact_name"]) not in readme:
        findings.append("README artifact name drift")
    return {"status": "passed" if not findings else "blocked", "findings": findings, "authority": "local-files-only"}


def remote_preflight(_root: Path) -> dict[str, object]:
    """Return an honest preflight without network access or remote writes."""
    return {
        "status": "configured-not-verified",
        "network": "not-run",
        "permissions": "unknown",
        "visibility": "unknown",
        "remote_publish": "not-run",
        "real_remote_deploy": "not-run",
        "reason": "Remote connector and write authority were not invoked.",
    }

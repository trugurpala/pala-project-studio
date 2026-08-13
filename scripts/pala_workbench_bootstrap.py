#!/usr/bin/env python3
"""Bootstrap Pala's required Windows Workbench without global mutations."""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid
from pathlib import Path

from pala_codegraph import (
    CODEGRAPH_EXECUTABLE,
    CODEGRAPH_SHA256,
    artifact_spec,
    health_probe as codegraph_health_probe,
)
from pala_semgrep import (
    SEMGREP_VERSION,
    build_wheelhouse_manifest,
    install_transaction as install_semgrep,
    inventory as semgrep_inventory,
    render_requirements_lock,
)
from pala_workbench_doctor import doctor as workbench_doctor
from pala_workbench_install import install_zip_transaction

INSTALLATION_STATES = frozenset(
    {"ABSENT", "CURRENT", "OLD", "STALE", "FOREIGN", "OFFLINE", "BROKEN"}
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _default_pala_root() -> Path | None:
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "Pala" if local else None


def _research_root() -> Path | None:
    root = _default_pala_root()
    return root / "packages" / "workbench-research" if root is not None else None


def _codegraph_payload(state_root: Path) -> bytes:
    candidates = [
        state_root / "packages" / "workbench" / "codegraph" / "1.5.0" / "codegraph-win32-x64.zip",
    ]
    research = _research_root()
    if research is not None:
        candidates.append(research / "codegraph" / "1.5.0" / "codegraph-win32-x64.zip")
    for candidate in candidates:
        if candidate.is_file() and _sha256(candidate) == CODEGRAPH_SHA256:
            return candidate.read_bytes()
    request = urllib.request.Request(
        artifact_spec().source_url,
        headers={"User-Agent": "Pala-Workbench-Installer/1"},
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def _wheelhouse_matches(wheelhouse: Path, lock_path: Path) -> bool:
    try:
        observed = render_requirements_lock(build_wheelhouse_manifest(wheelhouse))
        return observed == lock_path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return False


def _resolve_wheelhouse(source: Path, state_root: Path) -> Path:
    lock_path = source / "workbench" / "semgrep" / "requirements-win-amd64.lock"
    cache = state_root / "packages" / "workbench" / "semgrep" / SEMGREP_VERSION / "wheelhouse"
    candidates = [cache]
    research = _research_root()
    if research is not None:
        candidates.append(research / "semgrep" / SEMGREP_VERSION / "wheelhouse")
    for candidate in candidates:
        if _wheelhouse_matches(candidate, lock_path):
            return candidate

    cache.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".wheelhouse.stage-", dir=cache.parent))
    try:
        command = (
            sys.executable,
            "-m",
            "pip",
            "download",
            "--disable-pip-version-check",
            "--no-input",
            "--only-binary",
            ":all:",
            "--require-hashes",
            "--dest",
            str(stage),
            "-r",
            str(lock_path),
        )
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
        )
        if completed.returncode != 0 or not _wheelhouse_matches(stage, lock_path):
            raise RuntimeError("Semgrep hash-locked wheelhouse download failed")
        if cache.exists():
            raise RuntimeError("Semgrep wheelhouse cache became ambiguous")
        os.replace(stage, cache)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return cache


def inventory_required_workbench(state_root: Path, project_root: Path) -> dict[str, object]:
    report = workbench_doctor(
        state_root,
        project_root,
        task_requires_browser=False,
    )
    return {
        "status": "ready" if report.get("healthy") else "attention_required",
        "healthy": bool(report.get("healthy")),
        "doctor": report,
        "capabilities": report.get("capabilities", {}),
    }


def ensure_required_workbench(
    source: Path,
    state_root: Path,
    *,
    dry_run: bool = False,
    repair: bool = False,
) -> dict[str, object]:
    """Ensure CodeGraph and Semgrep as one rollback-capable local transaction."""
    source = Path(source).resolve()
    state_root = Path(state_root).resolve()
    lock_path = source / "workbench" / "semgrep" / "requirements-win-amd64.lock"
    rule_manifest = source / "workbench" / "semgrep" / "rules" / "1.0.0" / "manifest.json"
    if not lock_path.is_file() or not rule_manifest.is_file():
        return {
            "status": "ready",
            "healthy": True,
            "changed": False,
            "state": "NOT_APPLICABLE_LEGACY_BUNDLE",
        }
    before = inventory_required_workbench(state_root, source)
    if before["healthy"] and not repair:
        return {**before, "changed": False, "state": "CURRENT"}
    if sys.platform != "win32" or platform.machine().casefold() not in {"amd64", "x86_64"}:
        return {**before, "changed": False, "state": "BROKEN", "reason": "unsupported-platform"}
    capabilities = before.get("capabilities")
    if isinstance(capabilities, dict) and any(
        isinstance(capabilities.get(name), dict)
        and capabilities[name].get("state") == "foreign"
        for name in ("code_intelligence", "security_static")
    ):
        return {**before, "changed": False, "state": "FOREIGN"}
    if dry_run:
        capability_states = {
            str(value.get("state"))
            for value in before.get("capabilities", {}).values()
            if isinstance(value, dict)
        }
        state = (
            "OLD"
            if "old" in capability_states
            else "ABSENT"
            if "absent" in capability_states
            else "STALE"
            if capability_states == {"exact"}
            else "BROKEN"
        )
        return {**before, "changed": False, "state": state, "status": "would_install"}

    workbench = state_root / "workbench"
    backup = workbench.parent / f".workbench.rollback-{uuid.uuid4().hex}"
    moved = False
    if workbench.exists():
        os.replace(workbench, backup)
        moved = True
    try:
        codegraph = install_zip_transaction(
            artifact_spec(),
            state_root,
            executable=CODEGRAPH_EXECUTABLE,
            fetch=lambda _url: _codegraph_payload(state_root),
            health_probe=codegraph_health_probe,
        )
        wheelhouse = _resolve_wheelhouse(source, state_root)
        semgrep = install_semgrep(
            wheelhouse,
            state_root,
            source / "workbench" / "semgrep" / "rules" / "1.0.0",
            source / "workbench" / "semgrep" / "requirements-win-amd64.lock",
        )
        after = inventory_required_workbench(state_root, source)
        if not after["healthy"]:
            raise RuntimeError("required Workbench Doctor health failed")
        if moved and backup.exists():
            shutil.rmtree(backup)
        return {
            **after,
            "changed": bool(codegraph.get("changed") or semgrep.get("changed")),
            "state": "CURRENT",
            "codegraph": codegraph,
            "semgrep": semgrep,
        }
    except Exception:
        if workbench.exists():
            shutil.rmtree(workbench)
        if moved and backup.exists():
            os.replace(backup, workbench)
        raise
    finally:
        if backup.exists():
            shutil.rmtree(backup)

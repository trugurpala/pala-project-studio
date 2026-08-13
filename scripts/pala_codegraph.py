#!/usr/bin/env python3
"""Bounded CodeGraph 1.5.0 contract for the Pala Professional Workbench."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from pala_workbench_install import ArtifactSpec, inventory

CODEGRAPH_VERSION = "1.5.0"
CODEGRAPH_SHA256 = "d6798622b4f44ee6757c94335f437ee27a9ff7d3537b554cb6a2b3baf11bc4a1"
CODEGRAPH_URL = (
    "https://github.com/colbymchenry/codegraph/releases/download/"
    "v1.5.0/codegraph-win32-x64.zip"
)
CODEGRAPH_EXECUTABLE = "codegraph-win32-x64/bin/codegraph.cmd"
CODEGRAPH_NODE = "codegraph-win32-x64/node.exe"
CODEGRAPH_ENTRY = "codegraph-win32-x64/lib/dist/bin/codegraph.js"
OWNER = "pala-project-studio"


def artifact_spec() -> ArtifactSpec:
    return ArtifactSpec(
        capability_id="code_intelligence",
        provider="CodeGraph",
        version=CODEGRAPH_VERSION,
        source_url=CODEGRAPH_URL,
        sha256=CODEGRAPH_SHA256,
        owner=OWNER,
    )


def default_state_root() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise RuntimeError("LOCALAPPDATA is required for Pala-owned Workbench state")
    return Path(local) / "Pala"


def codegraph_environment() -> dict[str, str]:
    """Return only upstream-supported switches that bound all CodeGraph processes."""
    return {
        "DO_NOT_TRACK": "1",
        "CODEGRAPH_TELEMETRY": "0",
        "CODEGRAPH_NO_UPDATE_CHECK": "1",
        "CODEGRAPH_NO_WATCH": "1",
    }


def runtime_paths(state_root: Path | None = None) -> dict[str, Path]:
    root = Path(state_root or default_state_root()).resolve()
    status = inventory(artifact_spec(), root, executable=CODEGRAPH_EXECUTABLE)
    if status.get("state") != "exact":
        raise RuntimeError(f"Pala CodeGraph runtime is not exact: {status.get('state')}")
    target = Path(str(status["path"]))
    paths = {
        "root": target,
        "executable": target / Path(CODEGRAPH_EXECUTABLE),
        "node": target / Path(CODEGRAPH_NODE),
        "entry": target / Path(CODEGRAPH_ENTRY),
    }
    if not all(path.is_file() for name, path in paths.items() if name != "root"):
        raise RuntimeError("Pala CodeGraph activation is missing runtime files")
    return paths


def health_probe(staged: Path) -> dict[str, object]:
    node = staged / Path(CODEGRAPH_NODE)
    entry = staged / Path(CODEGRAPH_ENTRY)
    if not node.is_file() or not entry.is_file():
        return {"status": "blocked", "version": "unknown", "reason": "runtime-files-missing"}
    environment = os.environ.copy()
    environment.update(codegraph_environment())
    try:
        completed = subprocess.run(
            (str(node), str(entry), "--version"),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "blocked", "version": "unknown", "reason": type(exc).__name__}
    observed = (completed.stdout or completed.stderr).strip().lstrip("v")
    return {
        "status": "passed" if completed.returncode == 0 and observed == CODEGRAPH_VERSION else "blocked",
        "version": observed or "unknown",
        "exit_code": completed.returncode,
        "telemetry": "disabled-via-supported-env",
        "update_check": "disabled-via-supported-env",
        "watcher": "configured-disabled-via-supported-env",
        "shared_daemon": "not-applicable-to-version-probe",
    }


def lifecycle_commands(
    executable: Path,
    project: Path,
    stage: str,
    *,
    query: str | None = None,
    symbol: str | None = None,
) -> tuple[tuple[str, ...], ...]:
    """Build fixed-argument manual lifecycle commands; never uses a shell."""
    executable_value = str(Path(executable))
    project_value = str(Path(project).resolve())
    init = (executable_value, "init", project_value)
    sync = (executable_value, "sync", project_value, "--quiet")
    status = (executable_value, "status", project_value, "--json")
    explore = (
        executable_value,
        "explore",
        query or "current task semantics",
        "--path",
        project_value,
    )
    impact = (
        executable_value,
        "impact",
        symbol or "changed-symbol",
        "--path",
        project_value,
        "--json",
    )
    stages = {
        "project-takeover": (init, sync, status),
        "pre-context": (sync, status, explore),
        "post-implementation": (sync, status, impact),
        "pre-quality": (sync, status),
    }
    try:
        return stages[stage]
    except KeyError as exc:
        raise ValueError(f"unsupported CodeGraph lifecycle stage: {stage}") from exc


def evaluate_freshness(
    status_payload: dict[str, object] | None, *, sync_exit_code: int
) -> dict[str, object]:
    """Fail closed: a stale graph routes to source and cannot prove Quality."""
    reasons: list[str] = []

    def nonzero(value: object) -> bool:
        try:
            return int(value or 0) != 0
        except (TypeError, ValueError):
            return True

    if sync_exit_code != 0:
        reasons.append(f"sync-exit-{sync_exit_code}")
    if not isinstance(status_payload, dict):
        reasons.append("status-unavailable")
    else:
        if status_payload.get("initialized") is not True:
            reasons.append("not-initialized")
        if status_payload.get("version") != CODEGRAPH_VERSION:
            reasons.append("version-not-exact")
        if not status_payload.get("lastIndexed"):
            reasons.append("last-indexed-missing")
        pending = status_payload.get("pendingChanges")
        if not isinstance(pending, dict) or any(
            nonzero(pending.get(name, 0)) for name in ("added", "modified", "removed")
        ):
            reasons.append("pending-changes")
        if status_payload.get("worktreeMismatch") is not None:
            reasons.append("worktree-mismatch")
        index = status_payload.get("index")
        if not isinstance(index, dict):
            reasons.append("index-status-missing")
        else:
            if index.get("state") != "complete":
                reasons.append(f"index-{index.get('state') or 'unknown'}")
            if nonzero(index.get("pendingRefs", 0)):
                reasons.append("pending-references")
            if index.get("reindexRecommended") is True:
                reasons.append("reindex-recommended")
    passed = not reasons
    return {
        "status": "passed" if passed else "blocked",
        "freshness": "current" if passed else "stale",
        "reasons": reasons,
        "fallback": "none" if passed else "direct-source",
        "quality_evidence_eligible": False,
        "authority": "advisory-code-intelligence",
    }


def parse_status(stdout: str, *, sync_exit_code: int) -> dict[str, object]:
    try:
        payload = json.loads(stdout)
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = None
    return evaluate_freshness(payload if isinstance(payload, dict) else None, sync_exit_code=sync_exit_code)


def run_lifecycle(
    project: Path,
    stage: str,
    *,
    query: str | None = None,
    symbol: str | None = None,
    state_root: Path | None = None,
    timeout_seconds: int = 180,
) -> dict[str, object]:
    """Run one bounded lifecycle stage and stop before advisory use on stale state."""
    runtime = runtime_paths(state_root)
    planned = lifecycle_commands(
        runtime["executable"], project, stage, query=query, symbol=symbol
    )
    environment = os.environ.copy()
    environment.update(codegraph_environment())
    results: list[dict[str, object]] = []
    status_payload: dict[str, object] | None = None
    sync_exit_code = 1
    for planned_command in planned:
        action = planned_command[1]
        command = (str(runtime["node"]), str(runtime["entry"]), *planned_command[1:])
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                timeout=timeout_seconds,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            results.append({"action": action, "exit_code": 1, "error": type(exc).__name__})
            return {
                "status": "blocked",
                "stage": stage,
                "results": results,
                "freshness": "stale",
                "fallback": "direct-source",
                "quality_evidence_eligible": False,
                "authority": "advisory-code-intelligence",
            }
        output = completed.stdout.strip()
        results.append(
            {
                "action": action,
                "exit_code": completed.returncode,
                "stdout": output[:4000],
                "stderr": completed.stderr.strip()[:1000],
            }
        )
        if action == "sync":
            sync_exit_code = completed.returncode
        if action == "status" and completed.returncode == 0:
            try:
                parsed = json.loads(output)
            except (ValueError, json.JSONDecodeError):
                parsed = None
            status_payload = parsed if isinstance(parsed, dict) else None
        if completed.returncode != 0:
            return {
                "status": "blocked",
                "stage": stage,
                "results": results,
                "freshness": "stale",
                "fallback": "direct-source",
                "quality_evidence_eligible": False,
                "authority": "advisory-code-intelligence",
            }
        if action == "status":
            freshness = evaluate_freshness(status_payload, sync_exit_code=sync_exit_code)
            if freshness["status"] != "passed":
                return {**freshness, "stage": stage, "results": results}
    freshness = evaluate_freshness(status_payload, sync_exit_code=sync_exit_code)
    return {**freshness, "stage": stage, "results": results}


def mcp_server_record(project: Path, state_root: Path | None = None) -> dict[str, object]:
    wrapper = Path(__file__).resolve().with_name("pala_codegraph_mcp.py")
    args = ["-3", str(wrapper), "--project", str(Path(project))]
    if state_root is not None:
        args.extend(("--state-root", str(Path(state_root))))
    return {
        "command": "py",
        "args": args,
        "env": codegraph_environment(),
        "tools": ["codegraph_explore"],
        "ui": "disabled",
        "authority": "advisory",
    }


def main(argv: list[str] | None = None) -> int:
    if argv == ["--print-mcp"]:
        print(json.dumps({"mcpServers": {"pala-codegraph": mcp_server_record(Path.cwd())}}, indent=2))
        return 0
    print(json.dumps(inventory(artifact_spec(), default_state_root(), executable=CODEGRAPH_EXECUTABLE), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

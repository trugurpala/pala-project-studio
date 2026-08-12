"""Secrets-free GitHub capability routing for Pala."""

from __future__ import annotations

import shutil
import subprocess
import json
import base64
import re
import os
from datetime import datetime, timezone
from pathlib import Path

from pala_redaction import redact_remote_url

READ_ONLY_TIMEOUT_SECONDS = 5
MAX_READ_OUTPUT = 1_000_000


class GitHubReadPolicy:
    """Explicit read-only argv policy; write commands are never accepted."""

    ALLOWED_GH = (
        ("api",),
        ("issue", "view"),
        ("issue", "list"),
        ("pr", "view"),
        ("pr", "checks"),
    )
    ALLOWED_GIT = (
        ("remote", "get-url"),
        ("rev-parse",),
        ("branch",),
        ("status",),
    )

    @classmethod
    def allowed(cls, executable: str, argv: list[str]) -> bool:
        command = tuple(argv)
        if Path(executable).name.casefold().startswith("gh"):
            if command[:1] == ("api",):
                return len(command) == 2 and bool(command[1]) and not command[1].startswith("-")
            return command in cls.ALLOWED_GH[1:]
        if Path(executable).name.casefold().startswith("git"):
            if command[:2] == ("remote", "get-url"):
                return len(command) == 3 and not command[2].startswith("-")
            if command[:1] == ("rev-parse",):
                return len(command) > 1
            if command[:1] == ("branch",):
                return command in (("branch",), ("branch", "--show-current"))
            if command[:1] == ("status",):
                return all(not value.casefold().startswith(("--porcelain=", "--short=")) for value in command[1:]) or command in (
                    ("status", "--porcelain"),
                    ("status", "--short"),
                )
        return False


def external_conflict(conflict_type: str, *, local_basis: object = None, remote_basis: object = None, resolution: str = "needs_decision") -> dict[str, object]:
    return {
        "type": conflict_type,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "local_basis": local_basis,
        "remote_basis": remote_basis,
        "resolution": resolution,
    }


class GitHubRouter:
    def __init__(self, connector_available: bool = False, gh_path: str | None = None) -> None:
        self.connector_available = connector_available
        self.gh_path = gh_path if gh_path is not None else shutil.which("gh")

    def inspect(self, root: Path) -> dict[str, object]:
        if self.connector_available:
            return {"route": "connector", "write_capability": "separate_authority"}
        if self.gh_path:
            return {"route": "gh", "write_capability": "separate_authority"}
        remote = self._remote(root)
        return {"route": "git", "write_capability": "none", "remote": self._redact(remote)}

    def read_only_snapshot(self, root: Path) -> dict[str, object]:
        """Read a bounded GitHub snapshot; never invokes a write-capable command."""
        remote = self._remote(root)
        repo = self._repo_slug(remote)
        if not repo:
            return {"status": "not-run", "route": "none", "reason": "repository remote unavailable"}
        if not self.gh_path:
            return {"status": "not-run", "route": "git", "repository": repo, "write_capability": "none"}
        payload: dict[str, object] = {"status": "passed", "route": "gh", "repository": repo, "write_capability": "none", "external_conflicts": []}
        for name, endpoint in (("issues", f"repos/{repo}/issues?state=open&per_page=20"), ("pulls", f"repos/{repo}/pulls?state=open&per_page=20"), ("checks", f"repos/{repo}/actions/runs?per_page=10")):
            code, value = self._gh_json(endpoint)
            if code != 0:
                payload["status"] = "not-run"
                payload[name] = []
                continue
            payload[name] = value if isinstance(value, list) else value.get("workflow_runs", []) if isinstance(value, dict) else []
        code, owners = self._gh_json(f"repos/{repo}/contents/.github/CODEOWNERS")
        if code == 0 and isinstance(owners, dict):
            encoded = owners.get("content")
            try:
                text = base64.b64decode(str(encoded or "")).decode("utf-8", errors="replace")
                payload["codeowners"] = {"status": "passed", "write_capability": "none", "rules": len([line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")])}
            except (ValueError, TypeError):
                payload["codeowners"] = {"status": "not-run", "write_capability": "none"}
        else:
            payload["codeowners"] = {"status": "not-run", "write_capability": "none"}
        return payload

    def _gh_json(self, endpoint: str) -> tuple[int, object]:
        executable = self.gh_path or "gh"
        if not GitHubReadPolicy.allowed(executable, ["api", endpoint]):
            return 2, None
        environment = os.environ.copy()
        environment.update({"GH_PROMPT_DISABLED": "1", "GIT_TERMINAL_PROMPT": "0", "NO_COLOR": "1"})
        try:
            result = subprocess.run([executable, "api", endpoint], capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False, timeout=READ_ONLY_TIMEOUT_SECONDS, check=False, env=environment)
        except (OSError, subprocess.TimeoutExpired):
            return 2, None
        if result.returncode != 0:
            return result.returncode, None
        try:
            return 0, json.loads(result.stdout[:MAX_READ_OUTPUT])
        except json.JSONDecodeError:
            return 2, None

    @staticmethod
    def _repo_slug(remote: str | None) -> str | None:
        if not remote:
            return None
        match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", remote.strip())
        return match.group(1) if match else None

    @staticmethod
    def _remote(root: Path) -> str | None:
        git_exe = shutil.which("git")
        if git_exe is None:
            return None
        try:
            result = subprocess.run(
                [git_exe, "remote", "get-url", "origin"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                shell=False,
                timeout=READ_ONLY_TIMEOUT_SECONDS,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    @staticmethod
    def _redact(remote: str | None) -> str | None:
        return redact_remote_url(remote) or None

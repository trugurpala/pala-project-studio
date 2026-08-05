"""Secrets-free GitHub capability routing for Pala."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


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

    @staticmethod
    def _remote(root: Path) -> str | None:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"], cwd=root, capture_output=True, text=True, check=False
        )
        return result.stdout.strip() if result.returncode == 0 else None

    @staticmethod
    def _redact(remote: str | None) -> str | None:
        if remote is None:
            return None
        if "@" in remote and "://" in remote:
            prefix, suffix = remote.split("@", 1)
            return prefix.split("://", 1)[0] + "://[redacted]@" + suffix
        return remote

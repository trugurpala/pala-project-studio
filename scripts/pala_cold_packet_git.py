"""Bounded, read-only Git observation for Pala cold-session packets."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

GIT_TIMEOUT_SECONDS = 5


def _run_git(root: Path, *args: str) -> str | None:
    git_exe = shutil.which("git")
    if git_exe is None:
        return None
    try:
        result = subprocess.run(
            [git_exe, *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def git_surface(root: Path) -> dict[str, object]:
    """Return a bounded Git snapshot without treating an unknown tree as clean."""
    head = _run_git(root, "rev-parse", "HEAD")
    branch = _run_git(root, "rev-parse", "--abbrev-ref", "HEAD")
    toplevel = _run_git(root, "rev-parse", "--show-toplevel")
    worktree = toplevel or str(root.resolve())
    dirty = _run_git(root, "status", "--porcelain=v1")
    changed: list[str] = []
    if dirty is not None:
        for line in dirty.splitlines():
            path = line[3:].strip().strip('"').replace("\\", "/")
            if path and path.casefold() != ".codex/pala-workflow.json":
                changed.append(path)
    return {
        "branch": branch or "unknown",
        "worktree": worktree,
        "base_commit": (head or "")[:40] or None,
        "dirty": bool(dirty and dirty.strip()) if dirty is not None else None,
        "worktree_status": "known" if dirty is not None else "unknown",
        "changed_files": changed[:12],
        "evidence_source": "source_git_test",
        "freshness": "live" if head and dirty is not None else ("partial" if head else "unknown"),
    }

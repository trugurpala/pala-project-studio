#!/usr/bin/env python3
"""Safe adapter for optional local code-review-graph integration."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SOURCE_FILE_THRESHOLD = 1000
CHANGED_FILE_THRESHOLD = 50
MODULE_ROOT_THRESHOLD = 4
READ_ONLY_TIMEOUT_SECONDS = 5
EXECUTION_TIMEOUT_SECONDS = 30

def graph_eligible(
    source_files: int, changed_files: int, module_roots: int, *, use_graph: bool = True
) -> bool:
    """Keep graph startup for work large enough to justify its cost."""
    if not use_graph:
        return False
    return (
        source_files >= SOURCE_FILE_THRESHOLD
        or changed_files >= CHANGED_FILE_THRESHOLD
        or module_roots >= MODULE_ROOT_THRESHOLD
    )


def find_executable() -> str | None:
    direct = shutil.which("code-review-graph")
    if direct is not None:
        return direct
    uv = shutil.which("uv")
    if uv is None:
        return None
    try:
        result = subprocess.run(
            [uv, "tool", "dir", "--bin"],
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=READ_ONLY_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    directory = Path(result.stdout.strip())
    for name in ("code-review-graph.exe", "code-review-graph"):
        candidate = directory / name
        if candidate.is_file():
            return str(candidate)
    return None


def git_root(cwd: Path) -> Path | None:
    git_exe = shutil.which("git")
    if git_exe is None:
        return None
    try:
        result = subprocess.run(
            [git_exe, "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=READ_ONLY_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


def status(root: Path | None) -> dict[str, object]:
    executable = find_executable()
    graph_exists = bool(root and (root / ".code-review-graph").is_dir())
    if executable is None:
        note = "Optional tool missing; continue with git diff, rg, and focused reads."
    elif not graph_exists:
        note = "Optional tool is available but no local graph exists; use git diff and rg."
    else:
        note = "Graph output narrows review context; verify findings against source."
    return {
        "available": executable is not None,
        "executable": executable,
        "repository": str(root) if root else None,
        "graph_exists": graph_exists,
        "local_first": True,
        "note": note,
    }


def run_graph(root: Path, action: str) -> int:
    executable = find_executable()
    if executable is None:
        print(json.dumps(status(root), ensure_ascii=False, indent=2))
        return 3
    if action == "review":
        command = [executable, "detect-changes", "--brief"]
    elif action == "update":
        command = [executable, "update", "--brief"]
    else:
        command = [executable, action]
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    try:
        return subprocess.run(
            command,
            cwd=root,
            env=environment,
            check=False,
            shell=False,
            timeout=EXECUTION_TIMEOUT_SECONDS,
        ).returncode
    except subprocess.TimeoutExpired:
        return 124


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("status", "build", "update", "review"))
    parser.add_argument("--cwd", default=".")
    args = parser.parse_args()
    root = git_root(Path(args.cwd).resolve())
    if args.action == "status":
        print(json.dumps(status(root), ensure_ascii=False, indent=2))
        return 0
    if root is None:
        print("code intelligence requires a Git repository", file=sys.stderr)
        return 2
    return run_graph(root, args.action)


if __name__ == "__main__":
    raise SystemExit(main())

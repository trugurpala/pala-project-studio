"""Bounded Git and checkpoint observation owned by Pala project state."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

GIT_TIMEOUT_SECONDS = 5
WORKFLOW_PATH = ".codex/pala-workflow.json"
PLUGIN_DATA_PREFIX = ".codex/plugin-data/"


def _run_git_process(
    root: Path, arguments: tuple[str, ...], *, text: bool
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str] | None:
    """Run a fixed Git query without a shell and with a bounded wait."""
    executable = shutil.which("git")
    if not executable:
        return None
    try:
        return subprocess.run(  # nosec B603 - fixed Git argv, shell=False
            [executable, *arguments],
            cwd=root,
            capture_output=True,
            text=text,
            check=False,
            shell=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def git_root(cwd: Path) -> Path:
    result = _run_git_process(cwd, ("rev-parse", "--show-toplevel"), text=True)
    output = result.stdout if result is not None and isinstance(result.stdout, str) else ""
    if result is not None and result.returncode == 0 and output.strip():
        return Path(output.strip()).resolve()
    return cwd.resolve()


def run_git(root: Path, *args: str) -> str | None:
    result = _run_git_process(root, tuple(args), text=True)
    if result is None or result.returncode != 0:
        return None
    output = result.stdout if isinstance(result.stdout, str) else ""
    return output.strip()


def run_git_bytes(root: Path, *args: str) -> bytes | None:
    result = _run_git_process(root, tuple(args), text=False)
    if result is None or result.returncode != 0:
        return None
    return result.stdout if isinstance(result.stdout, bytes) else None


def changed_git_paths(root: Path) -> list[str]:
    paths: set[str] = set()
    commands = (
        ("diff", "--name-only", "-z"),
        ("diff", "--cached", "--name-only", "-z"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    )
    for command in commands:
        output = run_git_bytes(root, *command)
        if output is None:
            continue
        for value in output.split(b"\0"):
            if value:
                paths.add(value.decode("utf-8", errors="surrogateescape"))
    return sorted(paths, key=str.casefold)


def worktree_entry_digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        elif path.is_file():
            digest.update(b"file\0")
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        elif path.exists():
            digest.update(b"non-file\0")
        else:
            digest.update(b"missing\0")
    except OSError as error:
        digest.update(f"unreadable:{error.errno}".encode("ascii", errors="replace"))
    return digest.hexdigest()


def git_paths_snapshot(root: Path, paths: list[str]) -> str:
    fingerprint = hashlib.sha256()
    for value in sorted(set(paths), key=str.casefold):
        normalized = value.replace("\\", "/")
        fingerprint.update(b"\0path\0")
        fingerprint.update(normalized.encode("utf-8", errors="surrogateescape"))
        fingerprint.update(b"\0content\0")
        fingerprint.update(worktree_entry_digest(root / value).encode("ascii"))
    return fingerprint.hexdigest()


def _is_state_noise(value: str) -> bool:
    normalized = value.replace("\\", "/").casefold()
    return normalized == WORKFLOW_PATH or normalized.startswith(PLUGIN_DATA_PREFIX)


def git_checkpoint(root: Path) -> dict[str, object]:
    head = run_git(root, "rev-parse", "HEAD")
    status = run_git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status is None:
        return {
            "head": head,
            "worktree_sha256": None,
            "changed_count": None,
            "changed_snapshot_sha256": None,
        }
    filtered = [line for line in status.splitlines() if not _is_state_noise(line[3:].strip().strip('"'))]
    changed_paths = [value for value in changed_git_paths(root) if not _is_state_noise(value)]
    changed_snapshot = git_paths_snapshot(root, changed_paths)
    fingerprint = hashlib.sha256()
    fingerprint.update("\n".join(filtered).encode("utf-8", errors="surrogateescape"))
    fingerprint.update(b"\0snapshot\0")
    fingerprint.update(changed_snapshot.encode("ascii"))
    return {
        "head": head,
        "worktree_sha256": fingerprint.hexdigest(),
        "changed_count": len(changed_paths),
        "changed_snapshot_sha256": changed_snapshot,
    }


def git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = _run_git_process(
        root, ("merge-base", "--is-ancestor", ancestor, descendant), text=False
    )
    return result is not None and result.returncode == 0


def git_diff_paths(root: Path, before: str, after: str) -> list[str] | None:
    output = run_git_bytes(root, "diff", "--name-only", "-z", f"{before}..{after}")
    if output is None:
        return None
    paths = []
    for value in output.split(b"\0"):
        if not value:
            continue
        decoded = value.decode("utf-8", errors="surrogateescape")
        if not _is_state_noise(decoded):
            paths.append(decoded)
    return paths


def checkpoint_commit_materialized(
    root: Path,
    previous: dict[str, object],
    current: dict[str, object],
) -> bool:
    previous_head = previous.get("head")
    current_head = current.get("head")
    previous_count = previous.get("changed_count")
    previous_snapshot = previous.get("changed_snapshot_sha256")
    if not (
        isinstance(previous_head, str)
        and isinstance(current_head, str)
        and isinstance(previous_count, int)
        and isinstance(previous_snapshot, str)
        and current.get("changed_count") == 0
        and git_is_ancestor(root, previous_head, current_head)
    ):
        return False
    committed_paths = git_diff_paths(root, previous_head, current_head)
    if committed_paths is None or len(committed_paths) != previous_count:
        return False
    return git_paths_snapshot(root, committed_paths) == previous_snapshot

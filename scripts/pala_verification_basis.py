"""Bounded workspace fingerprint used to invalidate stale verification."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pala_state_git import changed_git_paths, git_checkpoint, git_paths_snapshot, run_git, run_git_bytes


def _digest(value: bytes | None) -> str | None:
    return hashlib.sha256(value or b"").hexdigest() if value is not None else None


def capture_basis(root: Path, paths: list[str] | None = None) -> dict[str, object]:
    root = Path(root).resolve()
    selected = sorted(set(paths or changed_git_paths(root)), key=str.casefold)
    checkpoint = git_checkpoint(root)
    return {
        "head_sha": run_git(root, "rev-parse", "HEAD"),
        "index_digest": _digest(run_git_bytes(root, "diff", "--cached", "--binary")),
        "worktree_digest": checkpoint.get("worktree_sha256"),
        "surface_digest": git_paths_snapshot(root, selected),
        "changed_files": selected[:500],
    }


def basis_matches(expected: dict[str, object], current: dict[str, object]) -> bool:
    keys = ("head_sha", "index_digest", "worktree_digest", "surface_digest")
    return all(expected.get(key) == current.get(key) for key in keys)

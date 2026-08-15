#!/usr/bin/env python3
"""M76 contracts for pure, worktree-aware canonical project observation."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_project_snapshot import (  # noqa: E402 - local scripts import root
    GitResult,
    capture_project_snapshot,
    path_identity_digest,
    select_project_snapshot,
)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        shell=False,
    )


def _repository(root: Path, *, commit: bool = True) -> None:
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "pala@example.invalid")
    _git(root, "config", "user.name", "Pala Contract")
    if commit:
        (root / "README.md").write_text("fixture\n", encoding="utf-8")
        _git(root, "add", "README.md")
        _git(root, "commit", "-qm", "fixture")


class ProjectSnapshotContractTests(unittest.TestCase):
    def test_two_worktrees_share_repository_identity_but_have_distinct_worktree_identity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m76-worktrees-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            linked = fixture / "linked"
            _repository(repository)
            _git(repository, "worktree", "add", "-q", "-b", "linked", str(linked))

            primary = capture_project_snapshot(repository)
            secondary = capture_project_snapshot(linked)

            self.assertEqual(primary.repository_id, secondary.repository_id)
            self.assertNotEqual(primary.worktree_id, secondary.worktree_id)
            self.assertEqual(primary.git_state, "clean")
            self.assertEqual(secondary.git_state, "clean")

            selection = select_project_snapshot([primary, secondary])
            self.assertEqual(selection.status, "needs_decision")
            self.assertEqual(selection.finding["code"], "PROJECT_SNAPSHOT_WORKTREE_AMBIGUOUS")
            self.assertEqual(len(selection.candidates), 2)

    def test_requested_worktree_identity_selects_exact_candidate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m76-selection-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            linked = fixture / "linked"
            _repository(repository)
            _git(repository, "worktree", "add", "-q", "-b", "linked", str(linked))
            snapshots = [capture_project_snapshot(repository), capture_project_snapshot(linked)]

            selection = select_project_snapshot(
                snapshots, requested_worktree_id=snapshots[1].worktree_id
            )

            self.assertEqual(selection.status, "selected")
            self.assertEqual(selection.snapshot, snapshots[1])
            self.assertIsNone(selection.finding)

    def test_dirty_state_and_digest_are_current_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m76-dirty-") as value:
            repository = Path(value) / "repository"
            _repository(repository)
            clean = capture_project_snapshot(repository)
            (repository / "change.txt").write_text("one\n", encoding="utf-8")
            first = capture_project_snapshot(repository)
            second = capture_project_snapshot(repository)
            (repository / "change.txt").write_text("two\n", encoding="utf-8")
            changed = capture_project_snapshot(repository)

            self.assertEqual(first.git_state, "dirty")
            self.assertEqual(first.changed_digest, second.changed_digest)
            self.assertNotEqual(clean.changed_digest, first.changed_digest)
            self.assertNotEqual(first.changed_digest, changed.changed_digest)

    def test_git_timeout_is_unknown_and_never_clean(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m76-timeout-") as value:
            repository = Path(value) / "repository"
            _repository(repository)

            from pala_project_snapshot import run_git as real_run_git

            def timeout_status(root: Path, *args: str, timeout_seconds: float = 5) -> GitResult:
                if args[:2] == ("status", "--porcelain=v1"):
                    return GitResult(None, "", "", "timeout")
                return real_run_git(root, *args, timeout_seconds=timeout_seconds)

            snapshot = capture_project_snapshot(repository, git_runner=timeout_status)

            self.assertEqual(snapshot.git_state, "unknown")
            self.assertIn("PROJECT_SNAPSHOT_GIT_STATUS_TIMEOUT", snapshot.finding_codes)

    def test_snapshot_is_repeatable_and_does_not_create_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m76-pure-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            local_state = fixture / "local-state"
            _repository(repository)

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_state)}):
                first = capture_project_snapshot(repository).to_dict()
                second = capture_project_snapshot(repository).to_dict()

            self.assertEqual(first, second)
            self.assertFalse(local_state.exists())

    def test_detached_and_unborn_heads_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m76-head-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            unborn = fixture / "unborn"
            _repository(repository)
            _git(repository, "checkout", "--detach", "-q")
            _repository(unborn, commit=False)

            self.assertEqual(capture_project_snapshot(repository).head_state, "detached")
            self.assertEqual(capture_project_snapshot(unborn).head_state, "unborn")

    def test_serialized_snapshot_redacts_remote_credentials_and_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m76-privacy-") as value:
            repository = Path(value) / "repository"
            _repository(repository)
            _git(
                repository,
                "remote",
                "add",
                "origin",
                "https://token:secret@github.com/acme/demo.git",
            )

            payload = capture_project_snapshot(repository).to_dict()
            serialized = json.dumps(payload, sort_keys=True)

            self.assertEqual(payload["remote"], "https://github.com/acme/demo.git")
            self.assertNotIn("token", serialized)
            self.assertNotIn("secret", serialized)
            self.assertNotIn(str(repository), serialized)

    def test_windows_path_identity_is_case_and_separator_stable(self) -> None:
        upper = path_identity_digest(r"C:\\Users\\PALA\\Project", platform="Windows")
        lower = path_identity_digest("c:/users/pala/project", platform="Windows")

        self.assertEqual(upper, lower)

    def test_repository_identity_survives_directory_move(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m76-move-") as value:
            fixture = Path(value)
            repository = fixture / "before"
            moved = fixture / "after"
            _repository(repository)
            before = capture_project_snapshot(repository)

            repository.rename(moved)
            after = capture_project_snapshot(moved)

            self.assertEqual(before.repository_id, after.repository_id)
            self.assertNotEqual(before.worktree_id, after.worktree_id)


if __name__ == "__main__":
    unittest.main()

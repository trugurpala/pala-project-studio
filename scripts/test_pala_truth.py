#!/usr/bin/env python3
"""Truth Core contract tests for repository and project state."""

from __future__ import annotations

import json
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


class TruthIdentityTests(unittest.TestCase):
    def make_repository(self, root: Path) -> None:
        root.mkdir()
        git(root, "init", "-b", "main")
        (root / "tracked.txt").write_text("fixture\n", encoding="utf-8")
        git(root, "add", ".")
        git(
            root,
            "-c",
            "user.name=Pala Tests",
            "-c",
            "user.email=pala-tests@example.invalid",
            "commit",
            "-m",
            "fixture",
        )

    def snapshot_module(self):
        try:
            import pala_snapshot
        except ModuleNotFoundError:
            self.fail("pala_snapshot must provide Truth Core Git identities")
        return pala_snapshot

    def test_linked_worktrees_share_repo_identity_but_not_worktree_identity(self) -> None:
        """Catches using a checkout root as the shared repository identity."""
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            main = parent / "main"
            linked = parent / "linked"
            self.make_repository(main)
            git(main, "worktree", "add", "-b", "feature", str(linked))

            pala_snapshot = self.snapshot_module()
            main_repo, main_tree = pala_snapshot.git_identity(main)
            linked_repo, linked_tree = pala_snapshot.git_identity(linked)

            self.assertEqual(
                main_repo.common_dir_digest, linked_repo.common_dir_digest
            )
            self.assertNotEqual(main_tree.git_dir_digest, linked_tree.git_dir_digest)
            self.assertEqual(
                {item.branch for item in pala_snapshot.list_worktrees(main)},
                {"main", "feature"},
            )

    def test_detached_head_has_no_branch_and_preserves_head(self) -> None:
        """Catches inventing a branch name for a detached checkout."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.make_repository(root)
            expected_head = git(root, "rev-parse", "HEAD")
            git(root, "checkout", "--detach", expected_head)

            pala_snapshot = self.snapshot_module()
            _, tree = pala_snapshot.git_identity(root)

            self.assertIsNone(tree.branch)
            self.assertEqual(tree.head, expected_head)


class SnapshotSelectionTests(unittest.TestCase):
    def identities(self):
        try:
            from pala_models import WorktreeIdentity
            from pala_snapshot import select_worktree
        except ImportError:
            self.fail("Truth Core must expose deterministic worktree selection")
        main = WorktreeIdentity("C:/repo", "main-id", "main", "1" * 40)
        feature = WorktreeIdentity(
            "C:/repo-feature", "feature-id", "feature", "2" * 40
        )
        return select_worktree, main, feature

    def test_explicit_worktree_precedes_owned_session(self) -> None:
        """Catches allowing session state to override an explicit checkout."""
        select, main, feature = self.identities()
        selected, findings = select(
            (main, feature),
            explicit_git_dir="feature-id",
            current_git_dir="main-id",
            owned_git_dir="main-id",
            active_git_dirs=("main-id",),
            checkpoint_git_dir="main-id",
        )
        self.assertEqual(selected, feature)
        self.assertEqual(findings, ())

    def test_owned_dirty_session_precedes_single_active_ticket(self) -> None:
        """Catches resuming another ticket while this session owns dirty work."""
        select, main, feature = self.identities()
        selected, findings = select(
            (main, feature),
            explicit_git_dir=None,
            current_git_dir=None,
            owned_git_dir="feature-id",
            active_git_dirs=("main-id",),
            checkpoint_git_dir="main-id",
        )
        self.assertEqual(selected, feature)
        self.assertEqual(findings, ())

    def test_two_independent_active_candidates_are_not_guessed(self) -> None:
        """Catches choosing an ambiguous worktree by ordering or mtime."""
        select, main, feature = self.identities()
        selected, findings = select(
            (main, feature),
            explicit_git_dir=None,
            current_git_dir=None,
            owned_git_dir=None,
            active_git_dirs=("main-id", "feature-id"),
            checkpoint_git_dir=None,
        )
        self.assertIsNone(selected)
        self.assertEqual([item.code for item in findings], ["WORKTREE_AMBIGUOUS"])

    def test_snapshot_is_immutable_and_uses_registered_documents(self) -> None:
        """Catches readers rebuilding document/state truth independently."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            TruthIdentityTests().make_repository(root)
            (root / ".codex").mkdir()
            for name in ("PROJECT.md", "PLAN.md", "STATUS.md"):
                (root / name).write_text(f"# {name}\n", encoding="utf-8")
            (root / ".codex" / "pala-project.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "managed_by": "pala-project-finisher",
                        "documents": {
                            "project": "PROJECT.md",
                            "plan": "PLAN.md",
                            "status": "STATUS.md",
                        },
                    }
                ),
                encoding="utf-8",
            )
            try:
                from pala_snapshot import build_snapshot
            except ImportError:
                self.fail("Truth Core must build one immutable project snapshot")

            snapshot = build_snapshot(root)

            self.assertEqual(snapshot.schema_version, 1)
            self.assertEqual(snapshot.selected_worktree.branch, "main")
            self.assertEqual(
                dict(snapshot.documents),
                {
                    "plan": "PLAN.md",
                    "project": "PROJECT.md",
                    "status": "STATUS.md",
                },
            )
            with self.assertRaises(AttributeError):
                snapshot.schema_version = 2


class MigrationTests(unittest.TestCase):
    def legacy_fixture(self, root: Path) -> Path:
        path = root / ".codex" / "pala-workflow.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(
            b'{"schema_version":2,"active_ticket":"A","dirty":true}\n'
        )
        return path

    def migrate(self, store, *, apply: bool):
        try:
            return store.migrate_v2(apply=apply)
        except TypeError:
            self.fail("migration must expose explicit dry-run/apply behavior")

    def test_migration_dry_run_preserves_bytes_and_mtimes(self) -> None:
        """Catches a preview that mutates legacy or creates v3 state."""
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = self.legacy_fixture(root)
            before_bytes = legacy.read_bytes()
            before_mtime = legacy.stat().st_mtime_ns

            result = self.migrate(WorkflowStore(root), apply=False)

            self.assertEqual(result.status, "would_migrate")
            self.assertEqual(legacy.read_bytes(), before_bytes)
            self.assertEqual(legacy.stat().st_mtime_ns, before_mtime)
            self.assertFalse(
                (root / ".codex/plugin-data/pala/v3/migration-v2.json").exists()
            )

    def test_migration_apply_is_byte_stable_and_preserves_legacy(self) -> None:
        """Catches rewriting a marker or the audit source on repeated apply."""
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = self.legacy_fixture(root)
            legacy_bytes = legacy.read_bytes()
            store = WorkflowStore(root)

            first = self.migrate(store, apply=True)
            marker_path = root / ".codex/plugin-data/pala/v3/migration-v2.json"
            marker_bytes = marker_path.read_bytes()
            marker_mtime = marker_path.stat().st_mtime_ns
            second = self.migrate(store, apply=True)

            self.assertEqual((first.status, second.status), ("migrated", "already_migrated"))
            self.assertEqual(legacy.read_bytes(), legacy_bytes)
            self.assertEqual(marker_path.read_bytes(), marker_bytes)
            self.assertEqual(marker_path.stat().st_mtime_ns, marker_mtime)
            self.assertEqual(first.record["legacy_sha256"], second.record["legacy_sha256"])

    def test_marker_makes_v2_audit_only_while_active_v3_wins(self) -> None:
        """Catches selecting an obsolete v2 ticket over live v3 state."""
        from pala_snapshot import build_snapshot, git_identity
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            TruthIdentityTests().make_repository(root)
            legacy = self.legacy_fixture(root)
            legacy.write_text(
                json.dumps({"schema_version": 2, "active_ticket": "A"}),
                encoding="utf-8",
            )
            store = WorkflowStore(root)
            _, identity = git_identity(root)
            for ticket, lifecycle, dirty in (("A", "completed", False), ("B", "active", True)):
                record = {
                    "schema_version": 3,
                    "ticket": ticket,
                    "goal": ticket,
                    "lifecycle": lifecycle,
                    "dirty": dirty,
                    "owner": "a" * 24 if lifecycle == "active" else None,
                    "worktree_git_dir_digest": identity.git_dir_digest,
                }
                store._write(store._ticket_path(ticket), record)
            store.migrate_v2(apply=True)

            snapshot = build_snapshot(root)

            self.assertEqual(snapshot.active_ticket.ticket, "B")
            self.assertIn("LEGACY_V2_OBSOLETE", {item.code for item in snapshot.findings})

    def test_unmigrated_v2_is_snapshot_fallback(self) -> None:
        """Catches readers disagreeing before the explicit migration marker exists."""
        from pala_snapshot import build_snapshot

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            TruthIdentityTests().make_repository(root)
            (root / ".codex").mkdir()
            (root / ".codex/pala-workflow.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "active_ticket": "A",
                        "goal": "legacy fallback",
                        "dirty": False,
                    }
                ),
                encoding="utf-8",
            )

            snapshot = build_snapshot(root)

            self.assertIsNotNone(snapshot.active_ticket)
            self.assertEqual(snapshot.active_ticket.ticket, "A")
            self.assertEqual(snapshot.active_ticket.lifecycle, "checkpointed")

    def test_legacy_document_basis_shape_does_not_create_false_drift(self) -> None:
        """Catches comparing legacy {path, sha256} objects to plain hashes."""
        from pala_snapshot import build_snapshot

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            TruthIdentityTests().make_repository(root)
            (root / ".codex").mkdir()
            status = root / "STATUS.md"
            status.write_text("# Status\n- Aktif ticket: A\n", encoding="utf-8")
            digest = __import__("hashlib").sha256(status.read_bytes()).hexdigest()
            (root / ".codex/pala-project.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "managed_by": "pala-project-finisher",
                        "documents": {"status": "STATUS.md"},
                    }
                ),
                encoding="utf-8",
            )
            (root / ".codex/pala-workflow.json").write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "active_ticket": "A",
                        "dirty": False,
                        "checkpoint_basis": {
                            "documents": {
                                "status": {"path": "STATUS.md", "sha256": digest}
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            snapshot = build_snapshot(root)

            self.assertNotIn("DOCUMENT_CHANGED", {item.code for item in snapshot.findings})


class CheckpointTruthTests(unittest.TestCase):
    def clean_fixture(self, root: Path) -> None:
        TruthIdentityTests().make_repository(root)
        (root / ".codex").mkdir()
        for name in ("PROJECT.md", "PLAN.md", "STATUS.md"):
            (root / name).write_text(f"# {name}\n", encoding="utf-8")
        (root / ".codex/pala-project.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "managed_by": "pala-project-finisher",
                    "documents": {
                        "project": "PROJECT.md",
                        "plan": "PLAN.md",
                        "status": "STATUS.md",
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_session_begin_writes_non_null_git_and_worktree_basis(self) -> None:
        """Catches creating uncheckable active tickets with a null basis."""
        from pala_state import begin_work
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)

            begin_work(root, "B", "truth", session="session-b")
            record = WorkflowStore(root).record("B")

            self.assertIn("basis", record)
            self.assertIsInstance(record["basis"], dict)
            self.assertRegex(record["basis"]["head"], r"^[0-9a-f]{40}$")
            self.assertRegex(record["worktree_git_dir_digest"], r"^[0-9a-f]{24}$")

    def test_session_checkpoint_refuses_missing_verification(self) -> None:
        """Catches releasing ownership while no success evidence exists."""
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            store = WorkflowStore(root)
            store.claim("B", "truth", "session-b")

            result = store.checkpoint("B", "session-b", "continue")

            self.assertEqual(result.status, "verification_required")
            self.assertTrue(result.record["dirty"])

    def test_checkpoint_rejects_negated_pass_and_persists_blockers(self) -> None:
        """Catches substring-based success and lost blocker evidence."""
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            store = WorkflowStore(root)
            store.claim("B", "truth", "session-b")

            negated = store.checkpoint(
                "B", "session-b", "continue", ["tests not passed"], "ticket", []
            )
            blocked = store.checkpoint(
                "B",
                "session-b",
                "continue",
                ["unit: passed"],
                "ticket",
                ["external dependency unavailable"],
            )

            self.assertEqual(negated.status, "verification_required")
            self.assertEqual(blocked.status, "blocked")
            self.assertEqual(blocked.record["verification"], ["unit: passed"])
            self.assertEqual(blocked.record["verification_tier"], "ticket")
            self.assertEqual(blocked.record["blockers"], ["external dependency unavailable"])
            self.assertTrue(blocked.record["dirty"])

    def test_checkpoint_rejects_mixed_failure_and_pass_evidence(self) -> None:
        """Catches accepting a trailing pass after an explicit failure."""
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            store = WorkflowStore(root)
            store.claim("B", "truth", "session-b")

            result = store.checkpoint(
                "B",
                "session-b",
                "continue",
                ["unit failed; retry: passed"],
                "ticket",
                [],
            )

            self.assertEqual(result.status, "verification_required")
            self.assertTrue(result.record["dirty"])

    def test_session_checkpoint_persists_evidence_tier_blockers_and_basis(self) -> None:
        """Catches CLI evidence being discarded before durable checkpoint."""
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            store = WorkflowStore(root)
            store.claim("B", "truth", "session-b")

            try:
                result = store.checkpoint(
                    "B",
                    "session-b",
                    "continue",
                    verification=["unit: passed"],
                    tier="ticket",
                    blockers=[],
                )
            except TypeError:
                self.fail("session checkpoint must accept evidence, tier, and blockers")

            self.assertEqual(result.status, "checkpointed")
            self.assertEqual(result.record["verification"], ["unit: passed"])
            self.assertEqual(result.record["verification_tier"], "ticket")
            self.assertEqual(result.record["blockers"], [])
            self.assertIsInstance(result.record["basis"], dict)

    def test_checkpoint_refreshes_basis_and_reports_later_document_and_git_drift(self) -> None:
        """Catches dropping clean checkpoints from snapshot reconciliation."""
        from pala_snapshot import build_snapshot
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            store = WorkflowStore(root)
            store.claim("B", "truth", "session-b")
            (root / "PLAN.md").write_text("# checkpointed\n", encoding="utf-8")
            store.checkpoint(
                "B", "session-b", "continue", ["unit: passed"], "ticket", []
            )
            (root / "PLAN.md").write_text("# later drift\n", encoding="utf-8")
            (root / "after.txt").write_text("later\n", encoding="utf-8")
            git(root, "add", ".")
            git(
                root,
                "-c",
                "user.name=Pala Tests",
                "-c",
                "user.email=pala-tests@example.invalid",
                "commit",
                "-m",
                "later",
            )

            snapshot = build_snapshot(root)
            codes = {item.code for item in snapshot.findings}

            self.assertIsNotNone(snapshot.active_ticket)
            self.assertEqual(snapshot.active_ticket.ticket, "B")
            self.assertEqual(snapshot.active_ticket.lifecycle, "checkpointed")
            self.assertIn("DOCUMENT_CHANGED", codes)
            self.assertIn("GIT_HEAD_CHANGED", codes)

    def test_missing_checkpoint_basis_is_typed_error(self) -> None:
        """Catches treating an unverifiable checkpoint as clean."""
        from pala_snapshot import build_snapshot, git_identity
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            _, identity = git_identity(root)
            store = WorkflowStore(root)
            store._write(
                store._ticket_path("B"),
                {
                    "schema_version": 3,
                    "ticket": "B",
                    "goal": "truth",
                    "lifecycle": "checkpointed",
                    "dirty": False,
                    "owner": None,
                    "worktree_git_dir_digest": identity.git_dir_digest,
                },
            )

            snapshot = build_snapshot(root)

            self.assertIn(
                "CHECKPOINT_BASIS_MISSING", {item.code for item in snapshot.findings}
            )

    def test_snapshot_reports_typed_status_plan_and_document_drift(self) -> None:
        """Catches collapsing distinct state contradictions into one boolean."""
        from pala_snapshot import build_snapshot
        from pala_state import begin_work

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            (root / "STATUS.md").write_text(
                "# Status\n\n- Aktif ticket: A — old\n", encoding="utf-8"
            )
            (root / "PLAN.md").write_text(
                "# Plan\n\n- [ ] A: old\n", encoding="utf-8"
            )
            begin_work(root, "B", "truth", session="session-b")
            (root / "PLAN.md").write_text(
                "# Plan\n\n- [ ] C: changed\n", encoding="utf-8"
            )

            snapshot = build_snapshot(root, session="session-b")
            codes = {item.code for item in snapshot.findings}

            self.assertIn("STATUS_ACTIVE_MISMATCH", codes)
            self.assertIn("PLAN_STATUS_MISMATCH", codes)
            self.assertIn("DOCUMENT_CHANGED", codes)

    def test_begin_refuses_unresolved_error_findings_before_claim(self) -> None:
        """Catches claiming a second ticket on top of known project drift."""
        from pala_state import begin_work
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            begin_work(root, "A", "first", session="session-b")
            (root / "PLAN.md").write_text("# changed\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "DOCUMENT_CHANGED"):
                begin_work(root, "B", "second", session="session-b")

            self.assertIsNone(WorkflowStore(root).record("B"))

    def test_begin_refuses_corrupt_v3_state(self) -> None:
        """Catches silently skipping unreadable coordination records."""
        from pala_state import begin_work
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            store = WorkflowStore(root)
            corrupt = store._state_root() / "tickets" / "corrupt.json"
            corrupt.parent.mkdir(parents=True, exist_ok=True)
            corrupt.write_text("{not-json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "STATE_RECORD_INVALID"):
                begin_work(root, "B", "truth", session="session-b")

            self.assertIsNone(store.record("B"))

    def test_sessionless_begin_refuses_corrupt_shared_v3_state(self) -> None:
        """Catches bypassing snapshot integrity when no session key is supplied."""
        from pala_state import begin_work
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            store = WorkflowStore(root)
            corrupt = store._state_root() / "tickets" / "corrupt.json"
            corrupt.parent.mkdir(parents=True, exist_ok=True)
            corrupt.write_text("{not-json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "STATE_RECORD_INVALID"):
                begin_work(root, "B", "truth")

            self.assertFalse((root / ".codex/pala-workflow.json").exists())

    def test_begin_refuses_schema_invalid_v3_state(self) -> None:
        """Catches structurally corrupt but syntactically valid coordination records."""
        from pala_state import begin_work
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            store = WorkflowStore(root)
            invalid = store._state_root() / "tickets" / "invalid.json"
            invalid.parent.mkdir(parents=True, exist_ok=True)
            invalid.write_text("{}\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "STATE_RECORD_INVALID"):
                begin_work(root, "B", "truth")

            self.assertFalse((root / ".codex/pala-workflow.json").exists())

    def test_begin_refuses_lifecycle_inconsistent_v3_state(self) -> None:
        """Catches checkpointed records that still claim dirty ownership."""
        from pala_state import begin_work
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            store = WorkflowStore(root)
            invalid = {
                "schema_version": 3,
                "ticket": "A",
                "goal": "truth",
                "lifecycle": "checkpointed",
                "dirty": True,
                "owner": "a" * 24,
                "worktree_git_dir_digest": "b" * 24,
            }
            store._write(store._ticket_path("A"), invalid)

            with self.assertRaisesRegex(ValueError, "STATE_RECORD_INVALID"):
                begin_work(root, "B", "truth")

            self.assertIsNone(store.record("B"))

    def test_checkpoint_reports_working_tree_source_drift(self) -> None:
        """Catches source edits hidden behind an unchanged Git HEAD."""
        from pala_snapshot import build_snapshot
        from pala_state import begin_work
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.clean_fixture(root)
            source = root / "source.py"
            source.write_text("value = 1\n", encoding="utf-8")
            git(root, "add", "source.py")
            git(
                root,
                "-c",
                "user.name=Pala Tests",
                "-c",
                "user.email=pala-tests@example.invalid",
                "commit",
                "-m",
                "source",
            )
            begin_work(root, "A", "truth", session="session-a")
            result = WorkflowStore(root).checkpoint(
                "A", "session-a", "continue", ["unit: passed"]
            )
            self.assertEqual(result.status, "checkpointed")

            source.write_text("value = 2\n", encoding="utf-8")
            snapshot = build_snapshot(root)

            self.assertIn("WORKTREE_CONTENT_CHANGED", {item.code for item in snapshot.findings})


class SessionIsolationTests(unittest.TestCase):
    def test_lifecycle_event_never_mutates_another_session_ticket(self) -> None:
        """Catches broadcasting lifecycle events across session ownership."""
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            store = WorkflowStore(Path(temp))
            store.claim("A", "a", "session-a")
            store.claim("B", "b", "session-b")
            before_b = json.dumps(store.record("B"), sort_keys=True)

            try:
                result = store.handle_event("session-a", "pre_compact")
            except AttributeError:
                self.fail("WorkflowStore must expose owner-scoped handle_event")

            self.assertEqual(result.status, "updated")
            self.assertEqual(json.dumps(store.record("B"), sort_keys=True), before_b)
            self.assertEqual(store.record("A")["last_event"], "pre_compact")
            self.assertNotIn("session-a", json.dumps(store.list_records()))

    def test_stop_blocks_only_the_event_sessions_dirty_ticket(self) -> None:
        """Catches Stop blocking or releasing work owned by another session."""
        import pala_hook
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            (root / pala_hook.MANIFEST).write_text(
                json.dumps(
                    {
                        "managed_by": "pala-project-finisher",
                        "documents": {"status": "STATUS.md"},
                    }
                ),
                encoding="utf-8",
            )
            WorkflowStore(root).claim("A", "a", "session-a")

            def stop(session: str) -> dict[str, object]:
                output = io.StringIO()
                event = {
                    "cwd": temp,
                    "hook_event_name": "Stop",
                    "stop_hook_active": False,
                    "session_id": session,
                }
                with (
                    patch("sys.stdin", io.StringIO(json.dumps(event))),
                    patch("sys.stdout", output),
                    patch.object(pala_hook, "git_root", return_value=root),
                ):
                    self.assertEqual(pala_hook.main(), 0)
                return json.loads(output.getvalue())

            owned_stop = stop("session-a")
            self.assertIn("decision", owned_stop)
            self.assertEqual(owned_stop["decision"], "block")
            self.assertEqual(stop("session-b"), {})

    def test_linked_worktrees_share_ticket_ownership_store(self) -> None:
        """Catches two worktrees claiming the same ticket independently."""
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            main = parent / "main"
            linked = parent / "linked"
            TruthIdentityTests().make_repository(main)
            git(main, "worktree", "add", "-b", "feature", str(linked))

            first = WorkflowStore(main).claim("A", "truth", "session-a")
            second = WorkflowStore(linked).claim("A", "truth", "session-b")

            self.assertEqual(first.status, "claimed")
            self.assertEqual(second.status, "owned_by_other")
            self.assertEqual(
                [record["ticket"] for record in WorkflowStore(linked).list_records()],
                ["A"],
            )

    def test_checkpoint_from_other_worktree_emits_worktree_changed(self) -> None:
        """Catches filtering out the only checkpoint before worktree comparison."""
        from pala_snapshot import build_snapshot
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            main = parent / "main"
            linked = parent / "linked"
            CheckpointTruthTests().clean_fixture(main)
            git(main, "worktree", "add", "-b", "feature", str(linked))
            store = WorkflowStore(main)
            store.claim("A", "truth", "session-a")
            store.checkpoint("A", "session-a", "continue", ["unit: passed"], "ticket", [])

            snapshot = build_snapshot(linked)

            self.assertIsNotNone(snapshot.active_ticket)
            self.assertEqual(snapshot.active_ticket.ticket, "A")
            self.assertIn("WORKTREE_CHANGED", {item.code for item in snapshot.findings})

    def test_session_start_does_not_retain_legacy_ticket_after_migration(self) -> None:
        """Catches hook fallback to v2 when snapshot explicitly has no ticket."""
        import pala_hook
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            (root / pala_hook.MANIFEST).write_text(
                json.dumps(
                    {
                        "managed_by": "pala-project-finisher",
                        "documents": {"status": "STATUS.md"},
                    }
                ),
                encoding="utf-8",
            )
            (root / pala_hook.WORKFLOW).write_text(
                json.dumps({"schema_version": 2, "active_ticket": "A", "dirty": True}),
                encoding="utf-8",
            )
            WorkflowStore(root).migrate_v2(apply=True)
            output = io.StringIO()
            event = {"cwd": temp, "hook_event_name": "SessionStart"}
            with (
                patch("sys.stdin", io.StringIO(json.dumps(event))),
                patch("sys.stdout", output),
                patch.object(pala_hook, "git_root", return_value=root),
            ):
                self.assertEqual(pala_hook.main(), 0)

            message = json.loads(output.getvalue())["hookSpecificOutput"]["additionalContext"]
            self.assertIn("active=none", message)
            self.assertNotIn("active=A", message)


class ReaderParityTests(unittest.TestCase):
    def registered_repository(self, root: Path) -> None:
        CheckpointTruthTests().clean_fixture(root)

    def test_discover_context_doctor_and_hook_share_snapshot(self) -> None:
        """Catches any reader independently choosing a different project truth."""
        import pala_hook
        import pala_state

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.registered_repository(root)

            discovery = pala_state.discover(root)
            self.assertIn("snapshot", discovery)
            discover_snapshot = discovery["snapshot"]
            context = pala_state.context_report(root)
            self.assertIn("snapshot", context)
            context_snapshot = context["snapshot"]
            doctor = pala_state.doctor_report(root)
            self.assertIn("snapshot", doctor)
            doctor_snapshot = doctor["snapshot"]
            try:
                hook_snapshot = pala_hook.snapshot_report(root)
            except AttributeError:
                self.fail("hook must expose the shared snapshot report")

            self.assertEqual(discover_snapshot, context_snapshot)
            self.assertEqual(context_snapshot, doctor_snapshot)
            self.assertEqual(doctor_snapshot, hook_snapshot)

    def test_compatibility_fields_derive_from_v3_snapshot_not_legacy_v2(self) -> None:
        """Catches nested snapshot B while top-level readers still report v2 A."""
        import pala_state
        from pala_store import WorkflowStore

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.registered_repository(root)
            (root / ".codex/pala-workflow.json").write_text(
                json.dumps(
                    {"schema_version": 2, "active_ticket": "A", "dirty": True}
                ),
                encoding="utf-8",
            )
            WorkflowStore(root).claim("B", "v3 truth", "session-b")

            context = pala_state.context_report(root, session="session-b")
            doctor = pala_state.doctor_report(root, session="session-b")

            self.assertEqual(context["active_ticket"], "B")
            self.assertEqual(context["active_ticket"], context["snapshot"]["active_ticket"]["ticket"])
            self.assertEqual(doctor["hook_discovery"]["active_ticket"], "B")
            self.assertEqual(doctor["hook_discovery"]["active_ticket"], doctor["snapshot"]["active_ticket"]["ticket"])

    def test_doctor_separates_installation_from_project_health(self) -> None:
        """Catches treating an application checkout as the installed plugin."""
        import pala_state

        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            project = parent / "app"
            plugin = parent / "plugin"
            self.registered_repository(project)
            (plugin / ".codex-plugin").mkdir(parents=True)
            (plugin / "hooks").mkdir()
            (plugin / ".codex-plugin/plugin.json").write_text("{}", encoding="utf-8")
            (plugin / "hooks/hooks.json").write_text("{}", encoding="utf-8")

            try:
                report = pala_state.doctor_report(project, plugin_root=plugin)
            except TypeError:
                self.fail("doctor must accept a plugin root separate from project root")

            self.assertEqual(report["installation_health"]["status"], "ready")
            self.assertEqual(report["project_health"]["status"], "ready")

    def test_doctor_flags_tracked_dynamic_v3_state_without_deleting_it(self) -> None:
        """Catches silently treating tracked session records as healthy."""
        import pala_state

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            self.registered_repository(root)
            dynamic = root / ".codex/plugin-data/pala/v3/tickets/leak.json"
            dynamic.parent.mkdir(parents=True)
            dynamic.write_text("{}\n", encoding="utf-8")
            git(root, "add", "-f", ".codex/plugin-data/pala/v3/tickets/leak.json")

            report = pala_state.doctor_report(root)

            self.assertIn("project_health", report)
            self.assertEqual(report["project_health"]["status"], "attention_required")
            self.assertIn(
                "TRACKED_DYNAMIC_STATE",
                {item["code"] for item in report["project_health"]["findings"]},
            )
            self.assertTrue(dynamic.is_file())

    def test_doctor_cli_resolves_plugin_root_separately_from_project(self) -> None:
        """Catches the CLI treating an application checkout as Pala's install."""
        import pala_state

        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "app"
            self.registered_repository(project)
            output = io.StringIO()
            with (
                patch("sys.argv", ["pala_state.py", "doctor", "--cwd", str(project)]),
                patch("sys.stdout", output),
            ):
                self.assertEqual(pala_state.main(), 0)
            report = json.loads(output.getvalue())

            self.assertEqual(
                Path(report["installation_health"]["root"]),
                SCRIPT_DIR.parent,
            )
            self.assertEqual(Path(report["project_health"]["root"]), project)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Mandatory M29 cold-packet / budget / capability contract tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pala_cmd_memory
import pala_cold_packet
import pala_db
import pala_state

_ENV_TMP: tempfile.TemporaryDirectory | None = None
_ENV_PREV: dict[str, str | None] = {}


def setUpModule() -> None:
    global _ENV_TMP
    _ENV_TMP = tempfile.TemporaryDirectory()
    for name in ("PALA_CATALOG_ROOT", "PALA_DB_PATH"):
        _ENV_PREV[name] = os.environ.get(name)
    os.environ["PALA_CATALOG_ROOT"] = _ENV_TMP.name
    os.environ["PALA_DB_PATH"] = str(Path(_ENV_TMP.name) / "pala.sqlite")


def tearDownModule() -> None:
    global _ENV_TMP
    for name, value in _ENV_PREV.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
    if _ENV_TMP is not None:
        _ENV_TMP.cleanup()
        _ENV_TMP = None


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> str:
    _git(root, "init")
    _git(root, "config", "user.email", "pala@example.com")
    _git(root, "config", "user.name", "Pala Test")
    (root / "README.md").write_text("demo\n", encoding="utf-8", newline="\n")
    (root / ".codex").mkdir(parents=True, exist_ok=True)
    (root / "STATUS.md").write_text(
        "# Status\n\n## Şu an tek sonraki iş\n\nFinish M29-T1 cold packet.\n",
        encoding="utf-8",
        newline="\n",
    )
    (root / ".codex" / "pala-project.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "managed_by": "pala-project-finisher",
                "documents": {
                    "status": "STATUS.md",
                    "plan": "PLAN.md",
                    "debugging": "DEBUGGING.md",
                    "project": "PROJECT.md",
                    "decisions": "DECISIONS.md",
                    "instructions": "AGENTS.md",
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _git(root, "add", ".")
    _git(root, "commit", "-m", "init")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return head


class ColdSessionFindsActiveWorkTests(unittest.TestCase):
    def test_01_cold_session2_finds_active_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            head = _init_repo(root)
            pala_state.begin_work(root, "M29-T1", "Ship cold packet")
            # Session 2: no chat history — only files + workflow.
            packet = pala_cold_packet.build_cold_packet(
                root,
                profile="minimal",
                documents={"status": "STATUS.md"},
            )
            self.assertEqual(packet.get("active_ticket"), "M29-T1")
            self.assertEqual(packet.get("goal"), "Ship cold packet")
            self.assertTrue(packet.get("base_commit"))
            self.assertTrue(str(packet.get("base_commit")).startswith(head[:7]))
            self.assertIn("next_action", packet)
            self.assertTrue(packet.get("within_budget"))


class PathMemoryNewSessionTests(unittest.TestCase):
    def test_02_wrong_script_path_then_do_not_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "cmd.sqlite"
            root = Path(temp) / "proj"
            root.mkdir()
            _init_repo(root)
            pala_cmd_memory.record_failure(
                command="py -3 ../../scripts/pala_report.py --cwd .",
                exit_code=2,
                stderr="No such file: ../../scripts/pala_report.py",
                cwd=str(root),
                path=db,
            )
            decision = pala_cmd_memory.guard_retry(
                command="py -3 ../../scripts/pala_report.py --cwd .",
                path=db,
            )
            self.assertFalse(decision.get("allowed"))
            self.assertTrue(decision.get("do_not_retry"))
            # New session packet surfaces do-not-retry + correct launcher hint.
            os.environ["PALA_DB_PATH"] = str(db)
            try:
                packet = pala_cold_packet.build_cold_packet(root, profile="minimal")
            finally:
                os.environ["PALA_DB_PATH"] = str(
                    Path(_ENV_TMP.name) / "pala.sqlite"  # type: ignore[union-attr]
                )
            blocks = packet.get("do_not_retry") or []
            self.assertTrue(blocks)
            text = str(packet.get("text") or "")
            self.assertIn("do-not-retry", text.casefold().replace(" ", ""))
            caps = packet.get("capability") or {}
            self.assertEqual(caps.get("launcher"), "pala_paths")


class BrowserFallbackTests(unittest.TestCase):
    def test_03_no_browser_fallback_honest_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _init_repo(root)
            # Force missing playwright by clearing PATH temporarily for which().
            old_path = os.environ.get("PATH")
            try:
                os.environ["PATH"] = str(root)  # empty of tools except none
                caps = pala_cold_packet.capability_manifest(root)
            finally:
                if old_path is None:
                    os.environ.pop("PATH", None)
                else:
                    os.environ["PATH"] = old_path
            self.assertIn(caps.get("browser"), {"not-run", "blocked", "configured-not-verified"})
            self.assertNotEqual(caps.get("browser"), "passed")
            packet = pala_cold_packet.build_cold_packet(
                root,
                profile="minimal",
                workflow={
                    "active_ticket": "M29-T3",
                    "next_action": "run browser screenshot proof",
                    "verification_tier": "not-run",
                },
            )
            verified = packet.get("last_verified") or {}
            # Browser-related next action gets honest fallback marker when unavailable.
            if (packet.get("capability") or {}).get("browser") != "passed":
                self.assertTrue(
                    verified.get("browser_fallback") in {None, "not-run"}
                    or verified.get("status") in {"not-run", "configured-not-verified"}
                )


class PermissionDenyNoRetryTests(unittest.TestCase):
    def test_04_permission_deny_same_op_not_retried(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "perm.sqlite"
            recorded = pala_cmd_memory.record_failure(
                command="rm -rf /protected/path",
                exit_code=1,
                stderr="Permission denied / Access is denied",
                failure_class="permission_policy",
                path=db,
            )
            self.assertEqual(recorded.get("failure_class"), "permission_policy")
            decision = pala_cmd_memory.guard_retry(
                command="rm -rf /protected/path",
                failure_class="permission_policy",
                path=db,
            )
            self.assertFalse(decision.get("allowed"))
            self.assertTrue(decision.get("do_not_retry"))


class TimeoutInProgressTests(unittest.TestCase):
    def test_05_timeout_state_blocks_continue_without_verify(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _init_repo(root)
            packet = pala_cold_packet.build_cold_packet(
                root,
                profile="minimal",
                workflow={
                    "active_ticket": "M29-T4",
                    "goal": "finish",
                    "lifecycle": "in-progress",
                    "verification_tier": "not-run",
                    "verification_evidence": [
                        {"name": "hook", "status": "timeout"},
                    ],
                },
            )
            self.assertFalse(packet.get("continue_without_verify"))
            self.assertIn("verify", str(packet.get("next_action") or "").casefold())


class StaleContextGitTests(unittest.TestCase):
    def test_06_stale_state_vs_new_git_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            head1 = _init_repo(root)
            pala_state.begin_work(root, "M29-T1", "old goal")
            pala_state.checkpoint_work(
                root,
                "continue after commit",
                ["unittest=passed"],
                [],
            )
            # New commit after checkpoint.
            (root / "extra.txt").write_text("x\n", encoding="utf-8", newline="\n")
            _git(root, "add", "extra.txt")
            _git(root, "commit", "-m", "second")
            # Mark dirty again with old checkpoint basis still pointing at head1.
            wf = pala_state.load_workflow(root)
            wf["dirty"] = True
            wf["active_ticket"] = "M29-T1"
            # Force stored head to head1 while live is head2.
            basis = wf.get("checkpoint_basis") if isinstance(wf.get("checkpoint_basis"), dict) else {}
            git_basis = basis.get("git") if isinstance(basis.get("git"), dict) else {}
            # After second commit, basis may already be head1 from checkpoint before commit.
            # Ensure mismatch: set basis head to head1 explicitly.
            git_basis = dict(git_basis)
            git_basis["head"] = head1
            basis = dict(basis)
            basis["git"] = git_basis
            wf["checkpoint_basis"] = basis
            pala_state.write_json(root / pala_state.WORKFLOW, wf)

            packet = pala_cold_packet.build_cold_packet(root, profile="minimal", workflow=wf)
            self.assertTrue(packet.get("stale_context"))
            self.assertFalse(packet.get("apply_state"))
            self.assertIsNone(packet.get("active_ticket"))
            text = str(packet.get("text") or "")
            self.assertIn("STALE-CONTEXT", text)


class TwoWorktreeConflictTests(unittest.TestCase):
    def test_07_two_worktrees_same_ticket_reconcile(self) -> None:
        conflict = pala_cold_packet.detect_worktree_conflict(
            ticket="M29-T1",
            this_worktree=r"C:\wt\a",
            other_worktree=r"C:\wt\b",
            this_branch="feat-a",
            other_branch="feat-b",
        )
        self.assertTrue(conflict.get("conflict"))
        self.assertTrue(conflict.get("reconcile_required"))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _init_repo(root)
            packet = pala_cold_packet.build_cold_packet(
                root,
                profile="minimal",
                workflow={
                    "active_ticket": "M29-T1",
                    "goal": "parallel",
                    "parallel": {
                        "session_id": "other-session",
                        "worktree": str(Path(temp) / "other-tree"),
                        "branch": "other",
                        "base_commit": "abc123",
                        "file_scope": ["x.py"],
                    },
                },
            )
            self.assertTrue((packet.get("worktree_conflict") or {}).get("reconcile_required"))
            self.assertIn("reconcile", str(packet.get("next_action") or "").casefold())


class MinimalBudgetTests(unittest.TestCase):
    def test_08_minimal_profile_packet_within_2kb(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _init_repo(root)
            # Inflate STATUS so budget trim matters for docs; packet text still ≤2KB.
            (root / "STATUS.md").write_text(
                "# Status\n\n" + ("noise line\n" * 400) + "\n## Şu an tek sonraki iş\n\nKeep going.\n",
                encoding="utf-8",
                newline="\n",
            )
            pala_state.begin_work(root, "M29-T1", "budget")
            packet = pala_cold_packet.build_cold_packet(
                root,
                profile="minimal",
                documents={"status": "STATUS.md", "plan": "PLAN.md", "progress": "PROGRESS.md"},
            )
            self.assertLessEqual(int(packet.get("bytes") or 99999), pala_cold_packet.MINIMAL_MAX_BYTES)
            self.assertTrue(packet.get("within_budget"))
            # Minimal must not auto-load full AGENTS+PLAN+PROGRESS set.
            names = {r.get("scope") for r in (packet.get("context_records") or [])}
            self.assertNotIn("plan", names)
            self.assertNotIn("progress", names)
            # Protected fields present.
            scopes = {r.get("scope") for r in (packet.get("context_records") or [])}
            self.assertIn("test_evidence", scopes)

    def test_budget_never_drops_blocker(self) -> None:
        records = [
            pala_cold_packet.context_record(
                name="old_log",
                scope="progress",
                text="x" * 4000,
                confidence="low",
            ),
            pala_cold_packet.context_record(
                name="blocker",
                scope="open_blocker",
                text="INC open",
                confidence="high",
                protected=True,
            ),
        ]
        trimmed = pala_cold_packet.apply_doc_budget(records, max_tokens=50)
        blocker = next(r for r in trimmed if r.get("scope") == "open_blocker")
        self.assertEqual(blocker.get("text"), "INC open")
        self.assertNotEqual(blocker.get("freshness"), "trimmed")


class WindowsTempProfileSmokeTests(unittest.TestCase):
    def test_09_p0_smoke_artifact_still_passed(self) -> None:
        artifact = PLUGIN_ROOT / "artifacts" / "codex-compat" / "p0-smoke.json"
        self.assertTrue(artifact.is_file(), "Gate0 artifact missing")
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertEqual(payload.get("status"), "passed")
        self.assertEqual(payload.get("exit_code"), 0)
        rows = payload.get("rows") or []
        self.assertGreaterEqual(len(rows), 9)
        self.assertTrue(all(r.get("status") == "passed" for r in rows if isinstance(r, dict)))


class FullLifecycleIntegrityTests(unittest.TestCase):
    def test_10_full_lifecycle_complete_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _init_repo(root)
            for name, body in (
                ("PLAN.md", "# Plan\n\n#### M29-LIFE — lifecycle\n"),
                ("AGENTS.md", "# Agents\n"),
                ("DECISIONS.md", "# Decisions\n"),
                (
                    "DEBUGGING.md",
                    "# Debugging log\n\n## Format\n\n"
                    "Symptoms, Root cause, Fix criteria, Proved by, "
                    "Related files, Date, Status.\n\n## Incidents\n\n",
                ),
                ("PROJECT.md", "# Project\n"),
            ):
                (root / name).write_text(body, encoding="utf-8", newline="\n")
            # Refresh manifest docs for register-style mapping already present.
            pala_state.begin_work(root, "M29-LIFE", "lifecycle integrity")
            pala_state.checkpoint_work(
                root,
                "complete after verify",
                ["unittest=passed"],
                [],
                changed_files=["scripts/pala_cold_packet.py"],
                session_id="sess-life-1",
            )
            wf = pala_state.load_workflow(root)
            parallel = wf.get("parallel") or {}
            self.assertEqual(parallel.get("session_id"), "sess-life-1")
            self.assertTrue(parallel.get("worktree"))
            self.assertTrue(parallel.get("branch"))
            self.assertTrue(parallel.get("base_commit"))
            self.assertIn("file_scope", parallel)
            ctx = pala_state.context_report(root)
            self.assertIsInstance(ctx.get("cold_packet"), dict)
            cold = ctx["cold_packet"]
            self.assertTrue(cold.get("within_budget"))

            from pala_store import WorkflowStore

            store = WorkflowStore(root)
            # begin without --session-key owns DEFAULT_LOCAL_SESSION (pala-local).
            store.record_verification(
                "M29-LIFE",
                pala_state.DEFAULT_LOCAL_SESSION,
                "passed",
                "py -3 -m unittest scripts.test_pala_cold_packet",
            )
            done = store.complete("M29-LIFE", pala_state.DEFAULT_LOCAL_SESSION)
            self.assertEqual(done.status, "completed")
            self.assertEqual(done.record.get("lifecycle"), "completed")
            self.assertFalse(done.record.get("dirty"))


class CapabilityHonestLabelsTests(unittest.TestCase):
    def test_capability_missing_tools_never_fake_passed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _init_repo(root)
            old = os.environ.get("PATH")
            try:
                os.environ["PATH"] = str(root)
                caps = pala_cold_packet.capability_manifest(root)
            finally:
                if old is None:
                    os.environ.pop("PATH", None)
                else:
                    os.environ["PATH"] = old
            for key in ("git", "node", "test_runner", "browser"):
                self.assertIn(
                    caps.get(key),
                    {"not-run", "blocked", "configured-not-verified", "passed"},
                )
            # With empty PATH, git/node/browser should not be passed.
            self.assertNotEqual(caps.get("node"), "passed")
            self.assertNotEqual(caps.get("browser"), "passed")
            auth = caps.get("authority") or {}
            self.assertFalse(auth.get("push"))
            self.assertFalse(auth.get("commit"))


class ContextBudgetProfileTests(unittest.TestCase):
    def test_profiles_expand_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _init_repo(root)
            (root / "PLAN.md").write_text("# Plan\n", encoding="utf-8", newline="\n")
            (root / "DECISIONS.md").write_text("# Dec\n", encoding="utf-8", newline="\n")
            (root / "PROGRESS.md").write_text("# Progress\n", encoding="utf-8", newline="\n")
            (root / "DEBUGGING.md").write_text(
                "# Debugging log\n\n## Format\n\nx\n\n## Incidents\n\n",
                encoding="utf-8",
                newline="\n",
            )
            docs = {
                "status": "STATUS.md",
                "plan": "PLAN.md",
                "decisions": "DECISIONS.md",
                "progress": "PROGRESS.md",
                "debugging": "DEBUGGING.md",
            }
            minimal = pala_cold_packet.select_documents_for_profile(root, docs, "minimal")
            standard = pala_cold_packet.select_documents_for_profile(root, docs, "standard")
            milestone = pala_cold_packet.select_documents_for_profile(root, docs, "milestone")
            self.assertEqual([r["scope"] for r in minimal], ["status"])
            self.assertIn("decisions", [r["scope"] for r in standard])
            self.assertIn("plan", [r["scope"] for r in milestone])
            for record in minimal + standard + milestone:
                for key in (
                    "freshness",
                    "scope",
                    "confidence",
                    "superseded_by",
                    "estimated_token_cost",
                ):
                    self.assertIn(key, record)


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from pala_artifact import REQUIRED_FILES, artifact_contract
from pala_dependencies import dependency_ready, validate_dependency_graph
from pala_knowledge import lint_markdown_links
from pala_store import WorkflowStore
from pala_task_contract import Evidence, TaskContract, scope_violations
from pala_verification_basis import basis_matches


class TaskContractHardeningTests(unittest.TestCase):
    def test_v4_contract_separates_assignee_lease_and_workspace_basis(self):
        task = TaskContract(
            id="T-1",
            project_id="p",
            title="Hardening",
            goal="finish",
            acceptance=[{"id": "AC-1", "text": "gate", "status": "not-run", "evidence_refs": []}],
            write_scope=["scripts/**"],
            deny_scope=[".github/**"],
        )
        task.claim("agent", "raw-session")
        payload = task.to_dict()
        self.assertEqual(payload["schema_version"], 4)
        self.assertEqual(payload["assignee"]["id"], "agent")
        self.assertEqual(payload["lease"]["status"], "claimed")
        self.assertNotIn("raw-session", json.dumps(payload))
        task.set_verification_basis("abc", "index", "worktree", "surface")
        self.assertEqual(task.to_dict()["verification_basis"]["head_sha"], "abc")

    def test_acceptance_item_must_reference_passed_evidence(self):
        task = TaskContract(
            id="T-2", project_id="p", title="Acceptance", goal="finish",
            acceptance=[{"id": "AC-1", "text": "gate", "status": "not-run", "evidence_refs": []}],
        )
        task.claim("agent", "session")
        for state in ("IN_PROGRESS", "REVIEW", "VERIFYING"):
            task.transition(state)
        task.record_evidence(Evidence("test", "pytest", 0, "passed", sha="abc"))
        with self.assertRaises(ValueError):
            task.complete()
        task.acceptance[0]["status"] = "passed"
        task.acceptance[0]["evidence_refs"] = [task.evidence[0]["id"]]
        task.complete()
        self.assertEqual(task.status, "DONE")

    def test_recovery_transitions_and_cancelled_are_explicit(self):
        task = TaskContract(id="T-3", project_id="p", title="Recovery", goal="finish")
        task.claim("agent", "session")
        task.transition("IN_PROGRESS")
        task.transition("REVIEW")
        task.transition("VERIFYING")
        task.transition("BLOCKED")
        task.transition("NEEDS_DECISION")
        task.transition("READY")
        task.transition("CLAIMED")
        self.assertIn("CANCELLED", task.to_dict()["allowed_states"])

    def test_write_boundary_is_policy_not_claimed_as_hard_sandbox(self):
        self.assertEqual(scope_violations(["scripts/a.py"], ["scripts/**"], [".github/**"]), [])
        self.assertEqual(scope_violations([".github/workflows/x.yml"], ["scripts/**"], [".github/**"]), [".github/workflows/x.yml"])

    def test_workspace_basis_match_is_stale_safe(self):
        basis = {"head_sha": "a", "index_digest": "b", "worktree_digest": "c", "surface_digest": "d"}
        self.assertTrue(basis_matches(basis, dict(basis)))
        changed = dict(basis)
        changed["surface_digest"] = "e"
        self.assertFalse(basis_matches(basis, changed))


class DependencyAndKnowledgeTests(unittest.TestCase):
    def test_dependency_graph_rejects_cycles_and_blocks_unfinished_parent(self):
        tasks = {
            "T1": {"id": "T1", "status": "IN_PROGRESS", "dependencies": []},
            "T2": {"id": "T2", "status": "READY", "dependencies": ["T1"]},
        }
        self.assertEqual(dependency_ready(tasks, "T2")["status"], "blocked")
        self.assertEqual(validate_dependency_graph({"T1": {"dependencies": ["T2"]}, "T2": {"dependencies": ["T1"]}})["status"], "blocked")

    def test_artifact_link_lint_fails_missing_relative_markdown_target(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            (root / "README.md").write_text("[missing](docs/nope.md)\n", encoding="utf-8")
            report = lint_markdown_links(root)
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["missing"][0]["target"], "docs/nope.md")

    def test_artifact_link_lint_ignores_project_local_dev_environment(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            (root / "README.md").write_text("source\n", encoding="utf-8")
            environment = root / ".venv"
            environment.mkdir()
            (environment / "README.md").write_text(
                "[third party](missing-tooling-doc.md)\n", encoding="utf-8"
            )
            report = lint_markdown_links(root)
            self.assertEqual(report["status"], "passed")

    def test_artifact_contract_ignores_project_local_dev_environment(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            for relative in REQUIRED_FILES:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")
            (root / "product-identity.json").write_text(
                json.dumps(
                    {
                        "product_version": "1.0.0-local-rc",
                        "plugin_version": "1.0.0-local-rc+codex.test",
                    }
                ),
                encoding="utf-8",
            )
            environment = root / ".venv" / "Lib" / "site-packages" / "certifi"
            environment.mkdir(parents=True)
            (environment / "cacert.pem").write_text("fixture\n", encoding="utf-8")
            report = artifact_contract(root)
            self.assertEqual(report["status"], "passed")


class SharedLeaseTests(unittest.TestCase):
    def test_git_common_dir_is_shared_claim_authority_for_two_worktrees(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "README.md").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(["git", "-c", "user.email=pala@example.com", "-c", "user.name=Pala", "commit", "-qm", "init"], cwd=root, check=True)
            shared = root / "shared-worktree"
            subprocess.run(["git", "worktree", "add", "-q", "-b", "lease-test", str(shared)], cwd=root, check=True)
            first = WorkflowStore(root).claim("T-SHARED", "shared", "session-a")
            second = WorkflowStore(shared).claim("T-SHARED", "shared", "session-b")
            self.assertEqual(first.status, "claimed")
            self.assertEqual(second.status, "owned_by_other")

    def test_stale_lease_is_orphaned_not_auto_taken_over(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            store = WorkflowStore(root)
            store.claim("T-STALE", "stale", "session-a")
            path = store._ticket_path("T-STALE")
            record = store._read(path)
            record["lease"]["heartbeat_at"] = "2000-01-01T00:00:00+00:00"
            store._write(path, record)
            result = store.claim("T-STALE", "stale", "session-b")
            self.assertEqual(result.status, "orphaned")


if __name__ == "__main__":
    unittest.main()

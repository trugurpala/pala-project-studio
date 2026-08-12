import subprocess
import tempfile
import unittest
from pathlib import Path

import pala_quality
import pala_state_core
from pala_handoff import make_handoff
from pala_knowledge import build_index, lint_task_references
from pala_store import WorkflowStore
from pala_task_contract import Evidence, TaskContract


class TaskContractTests(unittest.TestCase):
    def make_task(self):
        return TaskContract(id="T-1", project_id="p", title="Atomic task", goal="finish", acceptance=["test passes"], verification_commands=["test"])
    def test_claim_is_owner_bound_and_done_requires_evidence(self):
        task=self.make_task(); task.claim("agent", "session"); self.assertEqual(task.status, "CLAIMED")
        with self.assertRaises(ValueError): task.claim("other", "session-2")
        task.transition("IN_PROGRESS"); task.transition("REVIEW"); task.transition("VERIFYING")
        task.record_evidence(Evidence("test", "test", 0, "passed", sha="abc")); task.complete()
        self.assertEqual(task.status, "DONE"); self.assertIsNone(task.owner)
    def test_missing_evidence_and_blocker_refuse_done(self):
        task=self.make_task(); task.claim("agent", "session"); task.transition("IN_PROGRESS"); task.transition("REVIEW"); task.transition("VERIFYING")
        with self.assertRaises(ValueError): task.complete()
        task.blocker="needs review"
        task.record_evidence(Evidence("test", "test", 0, "passed"))
        with self.assertRaises(ValueError): task.complete()
    def test_invalid_transition_is_rejected(self):
        with self.assertRaises(ValueError): self.make_task().transition("DONE")

    def test_workflow_store_refuses_a_legacy_pass_without_structured_acceptance(self):
        with tempfile.TemporaryDirectory() as value:
            store = WorkflowStore(Path(value))
            store.claim("R6-M1", "Bridge task semantics", "session-alpha")
            store.record_verification("R6-M1", "session-alpha", "passed", "py -3 -m unittest")

            result = store.complete("R6-M1", "session-alpha")

        self.assertEqual(result.status, "verification_required")

    def test_begin_persists_explicit_structured_acceptance_in_task_contract(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            pala_state_core.begin_work(
                root, "R6-M1", "Bridge task semantics", session="session-alpha",
                acceptance=["contract is persisted"],
            )
            record = WorkflowStore(root)._read_ticket("R6-M1")

        self.assertEqual(record["task_contract"]["acceptance"][0]["status"], "not-run")
        self.assertEqual(record["task_contract"]["acceptance"][0]["text"], "contract is persisted")

    def test_quality_evidence_maps_required_check_to_acceptance_before_done(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            store = WorkflowStore(root)
            store.claim("R6-M2", "Map quality evidence", "session-alpha", acceptance=[{
                "id": "AC-01", "text": "unit passes", "quality_check_ids": ["unit:test"],
            }])
            pala_quality.write_ledger(root, "R6-M2", {"checks": [{
                "id": "unit:test", "kind": "unit", "required": True,
                "status": "not-run", "command": "py -3 -m unittest",
            }]})
            pala_quality.record_result(root, "R6-M2", "unit:test", status="passed", command="py -3 -m unittest", exit_code=0)

            mapped = store.sync_quality_evidence("R6-M2", "session-alpha", "R6-M2")
            done = store.complete("R6-M2", "session-alpha")

        self.assertEqual(mapped.status, "mapped")
        self.assertEqual(done.status, "completed")
        self.assertEqual(done.record["task_contract"]["acceptance"][0]["status"], "passed")

    def test_quality_evidence_uses_complete_git_basis_before_done(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.email", "pala@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Pala Test"],
                cwd=root,
                check=True,
            )
            (root / "README.md").write_text("# fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-m", "fixture"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            store = WorkflowStore(root)
            store.claim(
                "R6-GIT",
                "Map complete Git basis",
                "session-alpha",
                acceptance=[{
                    "id": "AC-01",
                    "text": "unit passes",
                    "quality_check_ids": ["unit:test"],
                }],
            )
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            pala_quality.write_ledger(root, "R6-GIT", {
                "git": {"head": head},
                "checks": [{
                    "id": "unit:test",
                    "kind": "unit",
                    "required": True,
                    "status": "not-run",
                    "command": "py -3 -m unittest",
                }],
            })
            pala_quality.record_result(
                root,
                "R6-GIT",
                "unit:test",
                status="passed",
                command="py -3 -m unittest",
                exit_code=0,
            )

            mapped = store.sync_quality_evidence(
                "R6-GIT", "session-alpha", "R6-GIT"
            )
            done = store.complete("R6-GIT", "session-alpha")

        self.assertEqual(mapped.status, "mapped")
        self.assertEqual(done.status, "completed")

    def test_completion_refuses_unfinished_taskcontract_dependency(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            store = WorkflowStore(root)
            store.claim("DEP-1", "dependency", "dependency-session", acceptance=[])
            store.claim("R6-M4", "dependent", "session-alpha", acceptance=[{
                "id": "AC-01", "text": "unit passes", "quality_check_ids": ["unit:test"],
            }])
            record = store._read_ticket("R6-M4")
            record["task_contract"]["dependencies"] = ["DEP-1"]
            store._write(store._ticket_path("R6-M4"), record)
            pala_quality.write_ledger(root, "R6-M4", {"checks": [{"id": "unit:test", "kind": "unit", "required": True, "status": "not-run", "command": "py -3 -m unittest"}]})
            pala_quality.record_result(root, "R6-M4", "unit:test", status="passed", command="py -3 -m unittest", exit_code=0)
            store.sync_quality_evidence("R6-M4", "session-alpha", "R6-M4")
            result = store.complete("R6-M4", "session-alpha")

        self.assertEqual(result.status, "dependency_required")

    def test_completion_refuses_taskcontract_scope_violation(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            store = WorkflowStore(root)
            store.claim("R6-SCOPE", "scoped", "session-alpha", acceptance=[{
                "id": "AC-01", "text": "unit passes", "quality_check_ids": ["unit:test"],
            }])
            record = store._read_ticket("R6-SCOPE")
            record["task_contract"]["write_scope"] = ["scripts/**"]
            record["task_contract"]["deny_scope"] = ["scripts/secrets/**"]
            record["changed_files"] = ["README.md"]
            store._write(store._ticket_path("R6-SCOPE"), record)
            pala_quality.write_ledger(root, "R6-SCOPE", {"checks": [{"id": "unit:test", "kind": "unit", "required": True, "status": "not-run", "command": "py -3 -m unittest"}]})
            pala_quality.record_result(root, "R6-SCOPE", "unit:test", status="passed", command="py -3 -m unittest", exit_code=0)
            store.sync_quality_evidence("R6-SCOPE", "session-alpha", "R6-SCOPE")
            result = store.complete("R6-SCOPE", "session-alpha")

        self.assertEqual(result.status, "scope_required")

    def test_handoff_derives_active_task_from_canonical_store_when_not_supplied(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            WorkflowStore(root).claim("R6-M5", "canonical projection", "session-alpha", acceptance=[])
            handoff = make_handoff(root)

        self.assertEqual(handoff["active_task"], "R6-M5")
        self.assertEqual(handoff["status"], "IN_PROGRESS")

    def test_workflow_projection_falls_back_to_canonical_active_task(self):
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            WorkflowStore(root).claim("R6-M5", "canonical workflow", "session-alpha", acceptance=[])
            workflow = pala_state_core.load_workflow(root)

        self.assertEqual(workflow["active_ticket"], "R6-M5")
        self.assertEqual(workflow["goal"], "canonical workflow")

class KnowledgeHandoffTests(unittest.TestCase):
    def test_index_and_redacted_handoff(self):
        with tempfile.TemporaryDirectory() as value:
            root=Path(value); (root/"ARCHITECTURE.md").write_text("# map", encoding="utf-8")
            index=build_index(root); self.assertEqual(index["entries"][0]["status"], "present")
            task={"id":"T-1","status":"IN_PROGRESS","owner":"agent","worktree":"C:/secret/project","next_action":"test","evidence":[]}
            handoff=make_handoff(root, task); self.assertEqual(handoff["active_task"], "T-1"); self.assertEqual(handoff["worktree"], "redacted")
    def test_reference_lint_requires_acceptance_and_existing_refs(self):
        with tempfile.TemporaryDirectory() as value:
            root=Path(value); (root/"ADR.md").write_text("# adr", encoding="utf-8")
            self.assertEqual(lint_task_references(root,{"architecture_refs":["ADR.md"],"acceptance":["x"]})["status"],"passed")
            self.assertEqual(lint_task_references(root,{"architecture_refs":["missing.md"],"acceptance":["x"]})["status"],"blocked")

if __name__ == "__main__": unittest.main()

import os
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pala_authority import RuntimeMigrationConflict, repository_instance, shared_state_root
from pala_quality import quality_ledger_path
import pala_hook
import pala_db
import pala_cold_packet
import pala_report
import pala_state_core
from pala_store import WorkflowStore


class RuntimeRootContractTests(unittest.TestCase):
    def test_two_worktrees_share_external_runtime_root_outside_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-runtime-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            (repository / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repository, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.email=pala@example.com",
                    "-c",
                    "user.name=Pala",
                    "commit",
                    "-qm",
                    "fixture",
                ],
                cwd=repository,
                check=True,
            )
            worktree = fixture / "worktree"
            subprocess.run(
                ["git", "worktree", "add", "-q", "-b", "runtime-test", str(worktree)],
                cwd=repository,
                check=True,
            )
            local_app_data = fixture / "local-app-data"
            expected = (
                local_app_data
                / "Pala"
                / "runtime"
                / "repositories"
                / repository_instance(repository)
            )

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                primary_root = shared_state_root(repository)
                worktree_root = shared_state_root(worktree)

            self.assertEqual(primary_root, expected)
            self.assertEqual(worktree_root, expected)
            self.assertNotIn(".git", expected.parts)
            self.assertNotIn(".codex", expected.parts)

    def test_ticket_records_live_in_runtime_tasks_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-tasks-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                store = WorkflowStore(repository)
                ticket_path = store._ticket_path("R6-M0")
                authority_root = shared_state_root(repository)

            self.assertIsNotNone(authority_root)
            self.assertEqual(ticket_path.parent, authority_root / "tasks")

    def test_external_runtime_active_task_supersedes_stale_legacy_dirty_copy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-active-read-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                authority_root = shared_state_root(repository)
                runtime_task = authority_root / "tasks" / "current.json"
                runtime_task.write_text(
                    json.dumps(
                        {
                            "dirty": True,
                            "task_contract": {"id": "M80-T4", "status": "IN_PROGRESS"},
                        }
                    ),
                    encoding="utf-8",
                )
                projection = authority_root / "generated" / "pala-workflow.json"
                projection.write_text(
                    json.dumps(
                        {
                            "schema_version": 2,
                            "active_ticket": None,
                            "goal": "stale projection",
                            "next_action": "stale next action",
                            "dirty": False,
                        }
                    ),
                    encoding="utf-8",
                )
                legacy_task = (
                    repository
                    / ".codex"
                    / "plugin-data"
                    / "pala"
                    / "v3"
                    / "tickets"
                    / "stale.json"
                )
                legacy_task.parent.mkdir(parents=True)
                legacy_task.write_text(
                    json.dumps(
                        {
                            "dirty": True,
                            "task_contract": {"id": "M44-T1", "status": "IN_PROGRESS"},
                        }
                    ),
                    encoding="utf-8",
                )

                active = WorkflowStore(repository).active_task_contract()
                workflow = pala_state_core.load_workflow(repository)

            self.assertEqual(active, {"id": "M80-T4", "status": "IN_PROGRESS"})
            self.assertEqual(workflow["active_ticket"], "M80-T4")
            self.assertTrue(workflow["dirty"])

    def test_runtime_root_materializes_declared_layout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-layout-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                authority_root = shared_state_root(repository)

            for name in ("tasks", "leases", "quality", "events", "generated", "cache", "migration"):
                with self.subTest(name=name):
                    self.assertTrue((authority_root / name).is_dir())

    def test_ticket_leases_live_in_runtime_leases_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-leases-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                store = WorkflowStore(repository)
                ticket_path = store._ticket_path("R6-M0")
                authority_root = shared_state_root(repository)
                lock_path = store._acquire_lock(ticket_path)
                try:
                    self.assertIsNotNone(authority_root)
                    self.assertIsNotNone(lock_path)
                    self.assertEqual(lock_path.parent, authority_root / "leases")
                finally:
                    if lock_path is not None:
                        store._release_lock(lock_path)

    def test_quality_ledger_uses_runtime_quality_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-quality-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                authority_root = shared_state_root(repository)
                ledger_path = quality_ledger_path(repository, "R6-M0")

            self.assertIsNotNone(authority_root)
            self.assertEqual(ledger_path, authority_root / "quality" / "R6-M0.json")

    def test_migration_marker_uses_runtime_migration_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-migration-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                store = WorkflowStore(repository)
                authority_root = shared_state_root(repository)
                marker_path = store._migration_path()

            self.assertIsNotNone(authority_root)
            self.assertEqual(marker_path, authority_root / "migration" / "v2-observed.json")

    def test_generated_report_is_written_outside_repository_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-report-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"

            with (
                patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}),
                patch.object(pala_report, "render_html", return_value="<html></html>"),
            ):
                authority_root = shared_state_root(repository)
                report_path = pala_report.write_report(repository)

            self.assertIsNotNone(authority_root)
            self.assertEqual(report_path, authority_root / "generated" / "pala-status.html")
            self.assertTrue(report_path.is_file())

    def test_workflow_projection_path_uses_runtime_generated_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-workflow-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                authority_root = shared_state_root(repository)
                workflow_path = pala_state_core.workflow_path(repository)

            self.assertIsNotNone(authority_root)
            self.assertEqual(
                workflow_path,
                authority_root / "generated" / "pala-workflow.json",
            )

    def test_begin_writes_workflow_projection_to_runtime_generated_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-begin-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"

            with (
                patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}),
                patch.object(pala_state_core, "_record_store_event"),
            ):
                pala_state_core.begin_work(repository, "R6-M0", "runtime authority")
                projection = pala_state_core.workflow_path(repository)

            self.assertTrue(projection.is_file())
            self.assertFalse((repository / ".codex" / "pala-workflow.json").exists())

    def test_hook_updates_runtime_workflow_projection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-hook-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"
            payload = {"schema_version": 2, "active_ticket": "R6-M0"}

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                projection = pala_state_core.workflow_path(repository)
                pala_hook.save_workflow(repository, payload)
                loaded = pala_hook.load_workflow(repository)

            self.assertEqual(loaded, payload)
            self.assertTrue(projection.is_file())
            self.assertFalse((repository / ".codex" / "pala-workflow.json").exists())

    def test_runtime_events_use_single_machine_local_catalog_database(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-events-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"
            event_db = fixture / "catalog" / "pala.sqlite"

            with (
                patch.dict(
                    os.environ,
                    {
                        "LOCALAPPDATA": str(local_app_data),
                        "PALA_DB_PATH": str(event_db),
                    },
                ),
                patch.object(pala_db, "add_event") as add_event,
            ):
                pala_state_core._record_store_event(
                    repository,
                    "begin",
                    detail="R6-M0: runtime authority",
                )

            self.assertEqual(
                add_event.call_args.kwargs["path"],
                event_db,
            )

    def test_cold_packet_updates_runtime_workflow_projection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-cold-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"
            payload = {
                "schema_version": 2,
                "active_ticket": "R6-M0",
                "dirty": False,
            }
            git_surface = {
                "worktree": str(repository),
                "branch": "detached",
                "base_commit": "a" * 40,
                "changed_files": [],
            }

            with (
                patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}),
                patch.object(pala_cold_packet, "git_surface", return_value=git_surface),
            ):
                projection = pala_state_core.workflow_path(repository)
                pala_state_core.write_json(projection, payload)
                result = pala_cold_packet.stamp_workflow_parallel(repository)
                stored = pala_state_core.load_workflow(repository)

            self.assertTrue(result["written"])
            self.assertEqual(stored["parallel"]["branch"], "detached")
            self.assertFalse((repository / ".codex" / "pala-workflow.json").exists())

    def test_legacy_runtime_data_is_copied_idempotently_without_deletion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-legacy-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"
            ticket_name = "ticket-hash.json"
            ticket_payload = {"schema_version": 4, "ticket": "R6-M0", "dirty": False}
            quality_payload = {"schema_version": 1, "ticket": "R6-M0", "checks": []}
            workflow_payload = {"schema_version": 2, "active_ticket": "R6-M0"}
            legacy_ticket = (
                repository
                / ".codex"
                / "plugin-data"
                / "pala"
                / "v3"
                / "tickets"
                / ticket_name
            )
            legacy_quality = (
                repository
                / ".codex"
                / "plugin-data"
                / "pala"
                / "v3"
                / "quality"
                / "R6-M0.json"
            )
            legacy_workflow = repository / ".codex" / "pala-workflow.json"
            for path, payload in (
                (legacy_ticket, ticket_payload),
                (legacy_quality, quality_payload),
                (legacy_workflow, workflow_payload),
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(payload), encoding="utf-8")

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                authority_root = shared_state_root(repository)
                second_root = shared_state_root(repository)

            self.assertEqual(second_root, authority_root)
            self.assertEqual(
                json.loads((authority_root / "tasks" / ticket_name).read_text(encoding="utf-8")),
                ticket_payload,
            )
            self.assertEqual(
                json.loads((authority_root / "quality" / "R6-M0.json").read_text(encoding="utf-8")),
                quality_payload,
            )
            self.assertEqual(
                json.loads(
                    (authority_root / "generated" / "pala-workflow.json").read_text(encoding="utf-8")
                ),
                workflow_payload,
            )
            self.assertTrue((authority_root / "migration" / "runtime-v1.json").is_file())
            self.assertTrue(legacy_ticket.is_file())
            self.assertTrue(legacy_quality.is_file())
            self.assertTrue(legacy_workflow.is_file())

    def test_divergent_legacy_runtime_data_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-conflict-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"
            authority_root = (
                local_app_data
                / "Pala"
                / "runtime"
                / "repositories"
                / repository_instance(repository)
            )
            legacy = (
                repository
                / ".codex"
                / "plugin-data"
                / "pala"
                / "v3"
                / "tickets"
                / "ticket.json"
            )
            destination = authority_root / "tasks" / "ticket.json"
            legacy.parent.mkdir(parents=True)
            destination.parent.mkdir(parents=True)
            legacy.write_text(json.dumps({"ticket": "legacy"}), encoding="utf-8")
            destination.write_text(json.dumps({"ticket": "runtime"}), encoding="utf-8")

            with (
                patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}),
                self.assertRaises(RuntimeMigrationConflict),
            ):
                shared_state_root(repository)

            marker = json.loads(
                (authority_root / "migration" / "runtime-v1.json").read_text(encoding="utf-8")
            )
            self.assertEqual(marker["status"], "needs_decision")
            self.assertEqual(json.loads(destination.read_text(encoding="utf-8")), {"ticket": "runtime"})
            self.assertTrue(legacy.is_file())

    def test_r5_git_metadata_ticket_is_migrated_to_external_tasks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-r5git-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"
            ticket_name = "r5-ticket.json"
            legacy = (
                repository
                / ".git"
                / "pala"
                / repository_instance(repository)
                / "v3"
                / "tickets"
                / ticket_name
            )
            legacy.parent.mkdir(parents=True)
            legacy.write_text(json.dumps({"ticket": "R6-M0"}), encoding="utf-8")

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                authority_root = shared_state_root(repository)

            copied = authority_root / "tasks" / ticket_name
            self.assertEqual(json.loads(copied.read_text(encoding="utf-8")), {"ticket": "R6-M0"})
            self.assertTrue(legacy.is_file())

    def test_legacy_completed_ticket_without_structured_acceptance_becomes_needs_decision(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-legacy-decision-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"
            legacy = repository / ".codex" / "plugin-data" / "pala" / "v3" / "tickets" / "legacy.json"
            legacy_payload = {"schema_version": 4, "ticket": "LEGACY-1", "goal": "old completion", "lifecycle": "completed", "acceptance": []}
            legacy.parent.mkdir(parents=True)
            legacy.write_text(json.dumps(legacy_payload), encoding="utf-8")

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                authority_root = shared_state_root(repository)
                shared_state_root(repository)

            migrated = json.loads((authority_root / "tasks" / "legacy.json").read_text(encoding="utf-8"))
            self.assertEqual(json.loads(legacy.read_text(encoding="utf-8")), legacy_payload)
            self.assertEqual(migrated["lifecycle"], "needs_decision")
            self.assertEqual(migrated["external_conflict"]["type"], "legacy-completed-without-structured-acceptance")
            self.assertEqual(migrated["task_contract"]["status"], "NEEDS_DECISION")

    def test_detached_head_keeps_repository_authority_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-detached-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            (repository / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repository, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.email=pala@example.com",
                    "-c",
                    "user.name=Pala",
                    "commit",
                    "-qm",
                    "fixture",
                ],
                cwd=repository,
                check=True,
            )
            before = repository_instance(repository)
            subprocess.run(["git", "checkout", "--detach", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                authority_root = shared_state_root(repository)

            self.assertEqual(repository_instance(repository), before)
            self.assertEqual(authority_root.name, before)

    def test_second_session_cannot_claim_same_runtime_task(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-claim-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            local_app_data = fixture / "local-app-data"

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                store = WorkflowStore(repository)
                first = store.claim("R6-M0", "runtime authority", "session-one")
                second = store.claim("R6-M0", "runtime authority", "session-two")

            self.assertEqual(first.status, "claimed")
            self.assertEqual(second.status, "owned_by_other")

    def test_migration_started_from_secondary_worktree_finds_primary_legacy_data(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-r6-worktree-migration-") as value:
            fixture = Path(value)
            repository = fixture / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
            (repository / "README.md").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repository, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.email=pala@example.com",
                    "-c",
                    "user.name=Pala",
                    "commit",
                    "-qm",
                    "fixture",
                ],
                cwd=repository,
                check=True,
            )
            worktree = fixture / "worktree"
            subprocess.run(
                ["git", "worktree", "add", "-q", "-b", "migration-test", str(worktree)],
                cwd=repository,
                check=True,
            )
            legacy_quality = (
                repository
                / ".codex"
                / "plugin-data"
                / "pala"
                / "v3"
                / "quality"
                / "R6-M0.json"
            )
            legacy_quality.parent.mkdir(parents=True)
            legacy_quality.write_text(
                json.dumps({"schema_version": 1, "ticket": "R6-M0"}),
                encoding="utf-8",
            )
            local_app_data = fixture / "local-app-data"

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_app_data)}):
                authority_root = shared_state_root(worktree)

            copied = authority_root / "quality" / "R6-M0.json"
            self.assertEqual(
                json.loads(copied.read_text(encoding="utf-8"))["ticket"],
                "R6-M0",
            )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Production adapter contracts for M80 continuity wiring."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pala_state_core  # noqa: E402
import pala_state_cli  # noqa: E402
import pala_state_documents  # noqa: E402
from pala_task_contract import TaskContract  # noqa: E402
from test_pala_project_profile import profile_payload  # noqa: E402


def _git(root: Path, *args: str) -> None:
    completed = subprocess.run(
        ["git", *args], cwd=root, check=False, capture_output=True, text=True
    )
    if completed.returncode:
        raise AssertionError(completed.stderr)


class ContinuityProductionIntegrationTests(unittest.TestCase):
    def _repository(self, base: Path) -> tuple[Path, dict[str, object]]:
        root = base / "repo"
        root.mkdir()
        _git(root, "init")
        _git(root, "config", "user.email", "pala@example.invalid")
        _git(root, "config", "user.name", "Pala Test")
        (root / "PROJECT.md").write_text("# Project\n", encoding="utf-8")
        (root / "PLAN.md").write_text("# Plan\n", encoding="utf-8")
        (root / "DECISIONS.md").write_text("# Decisions\n", encoding="utf-8")
        profile = profile_payload()
        profile_dir = root / ".pala"
        profile_dir.mkdir()
        (profile_dir / "project-profile.json").write_text(
            json.dumps(profile), encoding="utf-8"
        )
        _git(root, "add", ".")
        _git(root, "commit", "-m", "fixture")
        return root, profile

    def test_refresh_persists_only_on_mutating_lifecycle_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, _profile = self._repository(Path(temp))
            manifest = {
                "schema_version": 1,
                "managed_by": "pala-project-finisher",
                "project_profile": ".pala/project-profile.json",
                "documents": {
                    "project": "PROJECT.md",
                    "plan": "PLAN.md",
                    "decisions": "DECISIONS.md",
                },
            }
            (root / ".codex").mkdir()
            (root / ".codex" / "pala-project.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            task = TaskContract(
                id="M80-T2",
                project_id="local",
                title="Continuity",
                goal="Wire continuity",
                status="IN_PROGRESS",
                next_action="run-quality",
            ).to_dict()
            db = Path(temp) / "catalog" / "pala.sqlite"

            read_only = pala_state_core.refresh_continuity(
                root, task_contract=task, persist=False, db_path=db
            )
            self.assertEqual(read_only["receipt"]["validation_status"], "passed")
            self.assertFalse(read_only["receipt"]["can_complete"])
            self.assertFalse(db.exists())

            written = pala_state_core.refresh_continuity(
                root, task_contract=task, persist=True, db_path=db
            )
            self.assertEqual(written["continuity"]["validation_status"], "passed")
            self.assertTrue(db.is_file())
            raw = db.read_bytes()
            self.assertNotIn(b"PROJECT.md", raw)
            self.assertNotIn(b"Wire continuity", raw)

            before = db.read_bytes()
            (root / "PLAN.md").write_text("# Changed plan\n", encoding="utf-8")
            stale = pala_state_core.refresh_continuity(
                root, task_contract=task, persist=False, db_path=db
            )
            self.assertEqual(
                stale["continuity"]["validation_status"], "blocked"
            )
            self.assertEqual(
                stale["continuity"]["finding"]["code"],
                "CONTINUITY_RECEIPT_STALE",
            )
            self.assertEqual(db.read_bytes(), before)

    def test_cold_packet_has_no_state_core_import_cycle(self) -> None:
        source = (SCRIPTS / "pala_cold_packet.py").read_text(encoding="utf-8")
        self.assertNotIn("from pala_state_core import", source)

    def test_register_binds_an_explicit_validated_profile_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root, _profile = self._repository(Path(temp))
            args = pala_state_cli.parser().parse_args(
                [
                    "register",
                    "--cwd",
                    str(root),
                    "--project-profile",
                    ".pala/project-profile.json",
                ]
            )
            self.assertEqual(pala_state_documents.register(args, root), 0)
            manifest = pala_state_core.load_manifest(root)
            self.assertEqual(
                manifest["project_profile"], ".pala/project-profile.json"
            )
            discovered = pala_state_documents.discover(root)
            self.assertEqual(
                discovered["project_profile"]["validation_status"], "passed"
            )
            self.assertFalse(discovered["project_profile"]["can_complete"])

    def test_begin_and_checkpoint_refresh_persisted_continuity(self) -> None:
        task = TaskContract(
            id="M80-T2",
            project_id="local",
            title="Continuity",
            goal="Wire continuity",
            status="IN_PROGRESS",
        ).to_dict()
        claimed = SimpleNamespace(status="claimed", record={"task_contract": task})
        checkpointed = SimpleNamespace(
            status="checkpointed", record={"task_contract": task}
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with (
                patch("pala_store.WorkflowStore") as store_type,
                patch("pala_state_core._emit_debug_gate"),
                patch("pala_state_core._record_store_event"),
                patch("pala_state_core.refresh_continuity") as refresh,
            ):
                store_type.return_value.claim.return_value = claimed
                store_type.return_value.checkpoint.return_value = checkpointed
                pala_state_core.begin_work(
                    root,
                    "M80-T2",
                    "Wire continuity",
                    session="session",
                    acceptance=["context is current"],
                )
                refresh.assert_called_once_with(
                    root, task_contract=task, persist=True
                )

                refresh.reset_mock()
                args = SimpleNamespace(
                    quality_ticket=None,
                    session_key="session",
                    ticket="M80-T2",
                    next_action="run-quality",
                    verification=[],
                    blocker=[],
                    tier="ticket",
                )
                self.assertEqual(pala_state_cli._checkpoint_command(args, root), 0)
                refresh.assert_called_once_with(
                    root, task_contract=task, persist=True
                )

    def test_explicit_project_close_and_reopen_cli_call_lifecycle_owners(self) -> None:
        parser = pala_state_cli.parser()
        close_args = parser.parse_args(
            [
                "close-project",
                "--ticket",
                "M80-T2",
                "--summary",
                "Release candidate closed",
                "--final-commit",
                "c" * 40,
                "--authority-ref",
                "quality/m80-t2",
            ]
        )
        reopen_args = parser.parse_args(
            [
                "reopen-project",
                "--ticket",
                "M80-T3",
                "--closure-id",
                "d" * 64,
                "--authority-ref",
                "task/m80-t3",
            ]
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "pala.sqlite"
            context = SimpleNamespace(profile=SimpleNamespace(project_id="pala"))
            with (
                patch("pala_store.WorkflowStore") as store_type,
                patch(
                    "pala_state_core.build_registered_continuity_context",
                    return_value=context,
                ),
                patch("pala_state_core._continuity_db_path", return_value=db),
                patch("pala_continuity.close_context") as close_context,
                patch("pala_continuity.reopen_context") as reopen_context,
            ):
                store_type.return_value.ticket_record.return_value = {
                    "task_contract": {"status": "DONE"}
                }
                close_context.return_value = {
                    "history_id": "d" * 64,
                    "lifecycle": "project-closed",
                    "can_complete": False,
                }
                self.assertEqual(
                    pala_state_cli._project_lifecycle_command(close_args, root), 0
                )
                close_context.assert_called_once()

                store_type.return_value.ticket_record.return_value = {
                    "task_contract": {"status": "IN_PROGRESS"}
                }
                reopen_context.return_value = {
                    "history_id": "e" * 64,
                    "lifecycle": "project-reopened",
                    "can_complete": False,
                }
                self.assertEqual(
                    pala_state_cli._project_lifecycle_command(reopen_args, root), 0
                )
                reopen_context.assert_called_once()


if __name__ == "__main__":
    unittest.main()

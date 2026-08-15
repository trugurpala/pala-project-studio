#!/usr/bin/env python3
"""Contracts for the downward-only continuity orchestration boundary."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_context_receipt import ContextReceipt  # noqa: E402
from pala_project_snapshot import ProjectSnapshot  # noqa: E402
from pala_task_contract import TaskContract  # noqa: E402
from test_pala_context_receipt import snapshot  # noqa: E402
from test_pala_project_profile import profile_payload  # noqa: E402

from pala_continuity import (  # noqa: E402
    build_context,
    close_context,
    persist_context,
    read_models,
    reopen_context,
)


def task_payload() -> dict[str, object]:
    return TaskContract(
        id="M80-T2",
        project_id="local",
        title="Continuity wiring",
        goal="Wire bounded context",
        status="IN_PROGRESS",
    ).to_dict()


class ContinuityContractTests(unittest.TestCase):
    def test_build_is_deterministic_snapshot_bound_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repository"
            root.mkdir()
            database = Path(temp) / "pala.sqlite"
            observed: ProjectSnapshot = snapshot()
            with patch("pala_continuity.capture_project_snapshot", return_value=observed):
                first = build_context(
                    root,
                    profile_payload=profile_payload(),
                    task_contract=task_payload(),
                    source_refs=[{"path": "PLAN.md", "digest": "1" * 64}],
                    capabilities=[
                        {"name": "python", "status": "passed", "evidence_ref": "quality/python"}
                    ],
                    verifications=[
                        {
                            "check_id": "unit:m80-t2",
                            "status": "passed",
                            "exit_code": 0,
                            "evidence_ref": "quality/m80-t2",
                        }
                    ],
                    risk_codes=["continuity-not-persisted"],
                    next_action="persist-context",
                )
                second = build_context(
                    root,
                    profile_payload=profile_payload(),
                    task_contract=task_payload(),
                    source_refs=[{"path": "PLAN.md", "digest": "1" * 64}],
                    capabilities=[
                        {"name": "python", "status": "passed", "evidence_ref": "quality/python"}
                    ],
                    verifications=[
                        {
                            "check_id": "unit:m80-t2",
                            "status": "passed",
                            "exit_code": 0,
                            "evidence_ref": "quality/m80-t2",
                        }
                    ],
                    risk_codes=["continuity-not-persisted"],
                    next_action="persist-context",
                )
            self.assertIsInstance(first.receipt, ContextReceipt)
            self.assertEqual(first.receipt.receipt_id, second.receipt.receipt_id)
            self.assertEqual(first.expectation.project.worktree_id, observed.worktree_id)
            self.assertFalse(database.exists())

    def test_persist_keeps_only_safe_scalar_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repository"
            root.mkdir()
            db = Path(temp) / "pala.sqlite"
            with patch("pala_continuity.capture_project_snapshot", return_value=snapshot()):
                context = build_context(
                    root,
                    profile_payload=profile_payload(),
                    task_contract=task_payload(),
                    source_refs=[{"path": "PLAN.md", "digest": "1" * 64}],
                    capabilities=[],
                    verifications=[],
                    risk_codes=[],
                    next_action="persist-context",
                )
            result = persist_context(context, db_path=db)
            raw = db.read_bytes()
            self.assertEqual(result["validation_status"], "passed")
            self.assertFalse(result["can_complete"])
            self.assertNotIn(b"Local software delivery operating system", raw)
            self.assertNotIn(b"PLAN.md", raw)
            self.assertNotIn(b"Wire bounded context", raw)

    def test_absent_database_read_model_is_not_run_and_does_not_create_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "missing.sqlite"
            model = read_models(
                project_id="pala-project-studio",
                repository_id="a" * 24,
                db_path=db,
            )
            self.assertEqual(model["continuity"]["validation_status"], "not-run")
            self.assertEqual(model["history"]["validation_status"], "passed")
            self.assertFalse(model["continuity"]["can_complete"])
            self.assertFalse(model["history"]["can_complete"])
            self.assertFalse(db.exists())

    def test_close_and_reopen_are_explicit_context_lifecycle_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repository"
            root.mkdir()
            db = Path(temp) / "pala.sqlite"
            with patch("pala_continuity.capture_project_snapshot", return_value=snapshot()):
                context = build_context(
                    root,
                    profile_payload=profile_payload(),
                    task_contract=task_payload(),
                    source_refs=[],
                    capabilities=[],
                    verifications=[],
                    risk_codes=[],
                    next_action="close-project",
                )
            closed = close_context(
                context,
                summary="Continuity release candidate closed",
                final_commit="c" * 40,
                release_ref=None,
                risk_codes=[],
                lessons=["keep-context-bounded"],
                authority_ref="quality/m80-t2",
                db_path=db,
            )
            reopened = reopen_context(
                context,
                closure_id=closed["history_id"],
                authority_ref="task/m80-t3",
                db_path=db,
            )
            self.assertEqual(closed["lifecycle"], "project-closed")
            self.assertEqual(reopened["lifecycle"], "project-reopened")
            self.assertFalse(closed["can_complete"])
            self.assertFalse(reopened["can_complete"])


if __name__ == "__main__":
    unittest.main()

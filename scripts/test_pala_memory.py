#!/usr/bin/env python3
"""Contract tests for Pala 0.5 Project Memory Contract."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pala_catalog
import pala_hook
import pala_memory
import pala_state
import pala_tool_memory


class MemoryContractTests(unittest.TestCase):
    def test_discover_splits_progress_from_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "reports").mkdir()
            (root / "PROGRESS.md").write_text("# Progress\n", encoding="utf-8")
            (root / "reports" / "CURRENT_STATUS.md").write_text(
                "# Status\n", encoding="utf-8"
            )
            (root / "README.md").write_text("# P\n", encoding="utf-8")
            (root / "TASKS.md").write_text("# Plan\n", encoding="utf-8")
            result = pala_state.discover(root)
            self.assertEqual(
                result["documents"]["status"], "reports/CURRENT_STATUS.md"
            )
            self.assertEqual(result["documents"]["progress"], "PROGRESS.md")

    def test_read_order_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = {
                "instructions": "AGENTS.md",
                "status": "reports/CURRENT_STATUS.md",
                "progress": "PROGRESS.md",
                "plan": "PLAN.md",
                "tooling": "TOOLING_DECISIONS.md",
                "debugging": "DEBUGGING.md",
            }
            for rel in docs.values():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# x\n", encoding="utf-8")
            ordered = pala_memory.resolve_read_order(root, docs)
            purposes = [item["purpose"] for item in ordered]
            self.assertEqual(
                purposes,
                [
                    "instructions",
                    "status",
                    "progress",
                    "plan",
                    "tooling",
                    "debugging",
                    "git",
                ],
            )

    def test_ticket_coherence_detects_mismatch(self) -> None:
        report = pala_memory.ticket_coherence_report(
            {"active_ticket": "F2-T1", "next_action": "Start F2-T2 domain tests"},
            status_text="- Next: F2-T2 write failing test\n",
        )
        self.assertTrue(report["mismatch"])
        self.assertFalse(report["ok"])

    def test_checkpoint_rejects_soft_done(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            pala_state.begin_work(root, "T-1", "Do work")
            with self.assertRaises(ValueError):
                pala_state.checkpoint_work(
                    root,
                    next_action="Next ticket",
                    verification=["done"],
                    blockers=[],
                )

    def test_checkpoint_accepts_structured_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            pala_state.begin_work(root, "T-1", "Do work")
            pala_state.checkpoint_work(
                root,
                next_action="Continue T-2",
                verification=["unittest=passed", "e2e=not-run"],
                blockers=[],
            )
            payload = pala_state.load_workflow(root)
            self.assertFalse(payload["dirty"])
            self.assertEqual(len(payload["verification_evidence"]), 2)

    def test_tool_memory_maps_adapter_states(self) -> None:
        self.assertEqual(pala_tool_memory.map_adapter_state("ready"), "installed")
        self.assertEqual(pala_tool_memory.map_adapter_state("missing"), "not_installed")
        self.assertEqual(
            pala_tool_memory.map_adapter_state("external_conflict"),
            "installed_unverified",
        )

    def test_catalog_upsert_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "README.md").write_text("# demo\n", encoding="utf-8")
            cdir = Path(temp) / "Codex"
            first = pala_catalog.upsert_project(
                root, catalog_dir=cdir, next_action="A", phase="F2-T1"
            )
            second = pala_catalog.upsert_project(
                root, catalog_dir=cdir, next_action="B", phase="F2-T2"
            )
            self.assertEqual(first["id"], second["id"])
            projects = pala_catalog.list_projects(cdir)
            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0]["next_action"], "B")

    def test_session_context_includes_memory_flags_under_limit(self) -> None:
        result = pala_hook.session_context(
            {
                "project": "docs/SCOPE.md",
                "plan": "docs/IMPLEMENTATION_PLAN.md",
                "status": "reports/CURRENT_STATUS.md",
            },
            {
                "active_ticket": "F2-T1",
                "next_action": "Write failing test",
                "dirty": False,
                "blockers": [],
            },
            compacted=False,
            project_kind="existing",
            reconciliation={"needed": False, "reasons": []},
            health={
                "plugin": "loaded",
                "python": "ready",
                "git": "ready",
                "hook": "running",
            },
            memory={
                "ticket_coherence": {
                    "mismatch": True,
                    "note": "active=F2-T1 but next is F2-T2",
                }
            },
            tools_summary="tools=3ok/2gap",
        )
        message = result["hookSpecificOutput"]["additionalContext"]
        self.assertLessEqual(len(message), 800)
        self.assertIn("Read status first", message)
        self.assertIn("ticket_mismatch=true", message)
        self.assertIn("tools=3ok/2gap", message)
        self.assertIn("read_order=", message)

    def test_register_creates_memory_stubs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("README.md", "TASKS.md", "PROJECT_STATE.md"):
                (root / name).write_text("# Existing\n", encoding="utf-8")
            args = Namespace(
                instructions=None,
                project=None,
                plan=None,
                status=None,
                progress=None,
                tooling=None,
                debugging=None,
                decisions=None,
                open_source=None,
                demo=None,
            )
            self.assertEqual(pala_state.register(args, root), 0)
            self.assertTrue((root / "PROGRESS.md").is_file())
            self.assertTrue((root / "TOOLING_DECISIONS.md").is_file())
            self.assertTrue((root / "DEBUGGING.md").is_file())


if __name__ == "__main__":
    unittest.main()

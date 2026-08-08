#!/usr/bin/env python3
"""Contract tests for Wave B pala_debug_gate (Memory-as-Governance)."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pala_db
import pala_debug_gate
import pala_hook
import pala_memory
import pala_state


OPEN_BRAIN = """# Debugging log

## Format

Each `### INC-...` entry must include:
Symptoms, Root cause, Fix criteria, Proved by, Related files, Date, Status.
Optional: Attempts (append-only attempt notes). Soft done/ok is not evidence.

## Incidents

### INC-20260808-repeat-fix
- **Symptoms:** Same broken import kept returning
- **Root cause:** Agents ignored open INC Fix criteria
- **Fix criteria:** Import pathlib.Path explicitly; do not patch sys.path twice
- **Proved by:** not-run
- **Attempts:** none yet
- **Related files:** `scripts/broken_mod.py`, `scripts/pala_debug_gate.py`
- **Date:** 2026-08-08
- **Status:** open
"""


def _write_registered_project(root: Path, brain: str = OPEN_BRAIN) -> None:
    (root / ".codex").mkdir(parents=True, exist_ok=True)
    (root / "STATUS.md").write_text(
        "# Status\n\n- Active ticket: M28-T1\n- Next action: gate\n",
        encoding="utf-8",
        newline="\n",
    )
    (root / "PLAN.md").write_text("# Plan\n\n#### M28-T1 — gate\n", encoding="utf-8")
    (root / "DEBUGGING.md").write_text(brain, encoding="utf-8", newline="\n")
    manifest = {
        "managed_by": "pala-project-finisher",
        "documents": {
            "status": "STATUS.md",
            "plan": "PLAN.md",
            "debugging": "DEBUGGING.md",
        },
        "project_kind": "existing",
        "profiles": [],
    }
    (root / ".codex" / "pala-project.json").write_text(
        json.dumps(manifest), encoding="utf-8", newline="\n"
    )
    (root / ".codex" / "pala-workflow.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "active_ticket": "M28-T1",
                "next_action": "implement gate",
                "dirty": False,
                "blockers": [],
            }
        ),
        encoding="utf-8",
        newline="\n",
    )


class DebugGateWarningTests(unittest.TestCase):
    def test_open_inc_produces_gate_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_registered_project(root)
            report = pala_debug_gate.evaluate_gate(
                root, {"debugging": "DEBUGGING.md"}, surface="begin"
            )
            self.assertTrue(report["warn"])
            self.assertGreaterEqual(int(report["open"]), 1)
            message = str(report["message"])
            self.assertIn("INC-20260808-repeat-fix", message)
            self.assertRegex(message, r"(?i)fix criteria|do not repeat")

    def test_no_open_inc_skips_warning(self) -> None:
        closed = OPEN_BRAIN.replace("**Status:** open", "**Status:** fixed (`passed`)")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_registered_project(root, brain=closed)
            report = pala_debug_gate.evaluate_gate(
                root, {"debugging": "DEBUGGING.md"}, surface="checkpoint"
            )
            self.assertFalse(report["warn"])
            self.assertEqual(int(report["open"]), 0)

    def test_session_start_includes_gate_when_debug_open(self) -> None:
        result = pala_hook.session_context(
            {"status": "STATUS.md", "plan": "PLAN.md", "debugging": "DEBUGGING.md"},
            {"active_ticket": "M28-T1", "next_action": "gate", "dirty": False},
            compacted=False,
            memory={
                "ticket_coherence": {"mismatch": False},
                "debugging_brain": {"ok": True, "open": 1, "fixed": 0, "total": 1},
                "debug_gate": {
                    "warn": True,
                    "open": 1,
                    "message": (
                        "DEBUG GATE: read INC-20260808-repeat-fix; "
                        "do not repeat same Fix criteria."
                    ),
                },
            },
        )
        message = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("DEBUG GATE", message)
        self.assertIn("INC-20260808-repeat-fix", message)
        self.assertIn("debug_open=1", message)
        self.assertLessEqual(len(message), pala_hook.SESSION_CONTEXT_LIMIT)

    def test_cli_debug_gate_prints_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_registered_project(root)
            code = pala_debug_gate.main(["--cwd", str(root), "--surface", "begin"])
            self.assertEqual(code, 0)


class DebugAttemptTests(unittest.TestCase):
    def test_debug_attempt_event_kind_is_accepted(self) -> None:
        self.assertIn("debug_attempt", pala_db.EVENT_KINDS)
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            event_id = pala_db.add_event(
                "debug_attempt",
                project_name="gate",
                detail="INC-20260808-repeat-fix attempt",
                evidence="surface=begin",
                path=db,
            )
            self.assertGreater(event_id, 0)
            recent = pala_db.recent_events(limit=1, path=db)[0]
            self.assertEqual(recent["kind"], "debug_attempt")

    def test_record_debug_attempt_writes_store_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_registered_project(root)
            db = Path(temp) / "pala.sqlite"
            os.environ["PALA_DB_PATH"] = str(db)
            try:
                event_id = pala_debug_gate.record_debug_attempt(
                    root,
                    "INC-20260808-repeat-fix",
                    detail="tried same import patch",
                    evidence="surface=checkpoint",
                    path=db,
                )
                self.assertIsNotNone(event_id)
                kinds = [item["kind"] for item in pala_db.recent_events(limit=5, path=db)]
                self.assertIn("debug_attempt", kinds)
            finally:
                os.environ.pop("PALA_DB_PATH", None)

    def test_parser_keeps_optional_attempts_field(self) -> None:
        parsed = pala_memory.parse_debugging_brain(OPEN_BRAIN)
        self.assertTrue(parsed["ok"], parsed)
        fields = parsed["incidents"][0]["fields"]
        self.assertIn("Attempts", fields)
        self.assertTrue(str(fields["Attempts"]).strip())


class CompleteFailClosedTests(unittest.TestCase):
    def test_complete_refuses_passed_on_open_inc_related_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_registered_project(root)
            decision = pala_debug_gate.complete_fail_closed(
                root,
                documents={"debugging": "DEBUGGING.md"},
                changed_files=["scripts/broken_mod.py"],
                verification=[{"name": "unittest", "status": "passed"}],
                enabled=True,
            )
            self.assertFalse(decision["allowed"])
            self.assertIn("INC-20260808-repeat-fix", decision["reason"])

    def test_complete_allows_when_fail_closed_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_registered_project(root)
            decision = pala_debug_gate.complete_fail_closed(
                root,
                documents={"debugging": "DEBUGGING.md"},
                changed_files=["scripts/broken_mod.py"],
                verification=[{"name": "unittest", "status": "passed"}],
                enabled=False,
            )
            self.assertTrue(decision["allowed"])

    def test_complete_allows_when_related_files_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_registered_project(root)
            decision = pala_debug_gate.complete_fail_closed(
                root,
                documents={"debugging": "DEBUGGING.md"},
                changed_files=["README.md"],
                verification=[{"name": "unittest", "status": "passed"}],
                enabled=True,
            )
            self.assertTrue(decision["allowed"])


class MemoryHitRateTests(unittest.TestCase):
    def test_memory_hit_rate_proxy_counts_inc_read(self) -> None:
        miss = pala_debug_gate.session_memory_hit(debug_open=2, debugging_read=False)
        hit = pala_debug_gate.session_memory_hit(debug_open=2, debugging_read=True)
        idle = pala_debug_gate.session_memory_hit(debug_open=0, debugging_read=True)
        self.assertTrue(miss["opportunity"])
        self.assertFalse(miss["hit"])
        self.assertTrue(hit["hit"])
        self.assertFalse(idle["opportunity"])
        aggregate = pala_debug_gate.memory_hit_rate(opportunities=2, hits=1)
        self.assertEqual(aggregate["opportunities"], 2)
        self.assertEqual(aggregate["hits"], 1)
        self.assertEqual(aggregate["memory_hit_rate"], 0.5)
        blob = json.dumps(aggregate)
        self.assertNotIn("%", blob)

    def test_begin_surfaces_gate_warning_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_registered_project(root)
            warning = pala_debug_gate.surface_warning(
                root, {"debugging": "DEBUGGING.md"}, surface="begin"
            )
            self.assertIsNotNone(warning)
            self.assertIn("DEBUG GATE", warning or "")


class StopConditionContractTests(unittest.TestCase):
    """Fill feature-matrix stop rows that were N/A where harness can prove them."""

    def test_stop_unregistered_project_emits_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            event = json.dumps({"cwd": temp, "hook_event_name": "SessionStart"})
            output = io.StringIO()
            with (
                patch("sys.stdin", io.StringIO(event)),
                patch("sys.stdout", output),
                patch.object(pala_hook, "git_root", return_value=Path(temp)),
            ):
                self.assertEqual(pala_hook.main(), 0)
            self.assertEqual(output.getvalue(), "")

    def test_stop_invalid_evidence_soft_done_refused(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            pala_state._normalize_evidence_entries(["done"])
        self.assertIn("soft done", str(ctx.exception).casefold())

    def test_stop_insufficient_evidence_shape_refused(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            pala_state._normalize_evidence_entries(["looks fine"])
        self.assertIn("evidence must look like", str(ctx.exception))

    def test_stop_hooks_untrusted_stays_configured_not_verified(self) -> None:
        """UI hook trust is never claimed passed from Doctor/file safety alone."""
        report = pala_state.hook_safety_report(PLUGIN_ROOT)
        # File-level safety may pass; product UI trust remains separate.
        self.assertIn(report.get("status"), {"passed", "blocked", "failed", "unknown"})
        # Contract: no API on this surface returns hooks UI trust = passed.
        self.assertNotEqual(
            report.get("ui_trust"),
            "passed",
            "hooks UI trust must not be claimed passed here",
        )
        label = pala_debug_gate.hooks_ui_trust_label()
        self.assertEqual(label, "configured-not-verified")


class BeginCheckpointIntegrationTests(unittest.TestCase):
    def test_begin_work_emits_debug_gate_on_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write_registered_project(root)
            err = io.StringIO()
            with patch("sys.stderr", err):
                pala_state.begin_work(root, "M28-T1", "ship debug gate")
            text = err.getvalue()
            self.assertIn("DEBUG GATE", text)
            self.assertIn("INC-20260808-repeat-fix", text)


if __name__ == "__main__":
    unittest.main()

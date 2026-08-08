#!/usr/bin/env python3
"""Contract tests for durable DEBUGGING.md error-brain format (STAB-001)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

PLUGIN_ROOT = SCRIPTS.parent

import pala_memory
import pala_self_audit


VALID_BRAIN = """# Debugging log

## Format

Each `### INC-...` entry must include:
Symptoms, Root cause, Fix criteria, Proved by, Related files, Date, Status.
No secrets, transcripts, or tokens. Soft done/ok is not evidence.

## Incidents

### INC-20260808-soft-done
- **Symptoms:** Agent marked work complete with bare "done"
- **Root cause:** Soft completion words were treated as evidence
- **Fix criteria:** Evidence labels passed|not-run|blocked|configured-not-verified
- **Proved by:** `py -3 -m unittest scripts.test_pala_debugging -v`
- **Related files:** `DEBUGGING.md`, `AGENTS.md`
- **Date:** 2026-08-08
- **Status:** fixed (`passed` contract)
"""


class DebuggingBrainContractTests(unittest.TestCase):
    def test_parser_rejects_missing_format_section(self) -> None:
        result = pala_memory.parse_debugging_brain("# Debugging log\n\nNo format.\n")
        self.assertFalse(result["ok"])
        self.assertIn("format", result["detail"].casefold())

    def test_parser_accepts_format_without_incidents(self) -> None:
        text = (
            "# Debugging log\n\n## Format\n\n"
            "Required fields: Symptoms, Root cause, Fix criteria, "
            "Proved by, Related files, Date, Status.\n\n"
            "## Incidents\n\n(none yet)\n"
        )
        result = pala_memory.parse_debugging_brain(text)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["incidents"], [])

    def test_parser_requires_all_fields_on_incident(self) -> None:
        text = (
            "# Debugging log\n\n## Format\n\n"
            "Symptoms, Root cause, Fix criteria, Proved by, "
            "Related files, Date, Status.\n\n"
            "## Incidents\n\n### INC-20260808-broken\n"
            "- **Symptoms:** x\n"
            "- **Root cause:** y\n"
        )
        result = pala_memory.parse_debugging_brain(text)
        self.assertFalse(result["ok"])
        self.assertIn("INC-20260808-broken", result["detail"])

    def test_parser_accepts_valid_incident(self) -> None:
        result = pala_memory.parse_debugging_brain(VALID_BRAIN)
        self.assertTrue(result["ok"], result)
        self.assertEqual(len(result["incidents"]), 1)
        entry = result["incidents"][0]
        self.assertEqual(entry["id"], "INC-20260808-soft-done")
        self.assertIn("Symptoms", entry["fields"])
        self.assertTrue(entry["fields"]["Proved by"].strip())

    def test_stub_body_includes_format_contract(self) -> None:
        body = pala_memory.STUB_BODIES["debugging"]
        parsed = pala_memory.parse_debugging_brain(body)
        self.assertTrue(parsed["ok"], parsed)

    def test_repo_debugging_md_passes_contract(self) -> None:
        path = PLUGIN_ROOT / "DEBUGGING.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        result = pala_memory.parse_debugging_brain(text)
        self.assertTrue(result["ok"], result)

    def test_self_audit_includes_debugging_brain(self) -> None:
        payload = pala_self_audit.run_audit(PLUGIN_ROOT)
        names = {item["name"] for item in payload["checks"]}
        self.assertIn("debugging_brain", names)
        brain = next(item for item in payload["checks"] if item["name"] == "debugging_brain")
        self.assertEqual(brain["status"], "passed", brain)

    def test_debugging_brain_summary_counts_open_and_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "DEBUGGING.md").write_text(
                VALID_BRAIN
                + "\n### INC-20260808-still-open\n"
                "- **Symptoms:** open bug\n"
                "- **Root cause:** unknown\n"
                "- **Fix criteria:** close it\n"
                "- **Proved by:** not-run\n"
                "- **Related files:** `DEBUGGING.md`\n"
                "- **Date:** 2026-08-08\n"
                "- **Status:** open\n",
                encoding="utf-8",
                newline="\n",
            )
            summary = pala_memory.debugging_brain_summary(
                root, {"debugging": "DEBUGGING.md"}
            )
            self.assertTrue(summary["ok"], summary)
            self.assertEqual(summary["open"], 1)
            self.assertEqual(summary["fixed"], 1)
            self.assertEqual(summary["total"], 2)

    def test_session_context_includes_debug_open(self) -> None:
        import pala_hook

        result = pala_hook.session_context(
            {"status": "STATUS.md", "plan": "PLAN.md"},
            {"active_ticket": "M22-B", "next_action": "surface brain", "dirty": False},
            compacted=False,
            memory={
                "ticket_coherence": {"mismatch": False},
                "debugging_brain": {"ok": True, "open": 2, "fixed": 1, "total": 3},
            },
        )
        message = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("debug_open=2", message)
        self.assertLessEqual(len(message), pala_hook.SESSION_CONTEXT_LIMIT)


if __name__ == "__main__":
    unittest.main()

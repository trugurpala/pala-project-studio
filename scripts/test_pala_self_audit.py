#!/usr/bin/env python3
"""Contract tests for pala_self_audit (M21)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

PLUGIN_ROOT = SCRIPTS.parent

import pala_self_audit


class SelfAuditUnitTests(unittest.TestCase):
    def test_presence_check_passes_on_repo(self) -> None:
        result = pala_self_audit.audit_presence(PLUGIN_ROOT)
        self.assertEqual(result["status"], "passed")

    def test_hook_safety_passes_on_repo(self) -> None:
        result = pala_self_audit.audit_hook_safety(PLUGIN_ROOT)
        self.assertEqual(result["status"], "passed")

    def test_demo_seed_dry_run(self) -> None:
        result = pala_self_audit.audit_demo_seed(PLUGIN_ROOT)
        self.assertEqual(result["status"], "passed")

    def test_run_audit_reports_labeled_checks(self) -> None:
        # Full audit may fail until fork docs + 0.8.0 bump land; shape is stable.
        payload = pala_self_audit.run_audit(PLUGIN_ROOT)
        self.assertIn(payload["status"], {"passed", "failed"})
        names = {item["name"] for item in payload["checks"]}
        self.assertTrue(
            {
                "presence",
                "hook_safety",
                "fork_pack",
                "demo_seed",
                "soft_claims",
                "debugging_brain",
                "agent_tasks",
                "shared_memory",
                "manifest",
            }.issubset(names)
        )
        for item in payload["checks"]:
            self.assertIn(item["status"], {"passed", "failed", "not-run"})

    def test_agent_tasks_passes_on_repo(self) -> None:
        result = pala_self_audit.audit_agent_tasks(PLUGIN_ROOT)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result.get("detail"), "cards=7")

    def test_runtime_profile_passes_on_copied_bundle(self) -> None:
        from pala_installer import copy_bundle

        with tempfile.TemporaryDirectory(prefix="pala-runtime-audit-") as temp:
            dest = Path(temp) / "install"
            copy_bundle(PLUGIN_ROOT, dest)
            payload = pala_self_audit.run_audit(dest, profile="runtime")
            self.assertEqual(payload["status"], "passed", payload)
            names = {c["name"] for c in payload["checks"]}
            self.assertIn("presence", names)
            self.assertIn("hook_safety", names)
            self.assertNotIn("fork_pack", names)

    def test_cli_emits_json(self) -> None:
        code, text = pala_self_audit.run_cli(["--root", str(PLUGIN_ROOT)])
        self.assertIn(code, (0, 1))
        # First JSON object in stdout
        start = text.index("{")
        end = text.rindex("}") + 1
        payload = json.loads(text[start:end])
        self.assertIn("summary_tr", payload)


if __name__ == "__main__":
    unittest.main()

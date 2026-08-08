#!/usr/bin/env python3
"""Contract tests for M10 managed-tools canary."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

PLUGIN_ROOT = SCRIPTS.parent

import pala_m10
import pala_openspec


class M10CanaryTests(unittest.TestCase):
    def test_run_canary_passes_on_repo(self) -> None:
        payload = pala_m10.run_canary(PLUGIN_ROOT)
        self.assertEqual(payload["status"], "passed", payload)
        self.assertEqual(payload["checks"]["rtk_lock"]["version"], "0.44.2")
        self.assertIn("context7", payload["checks"]["mcp_pins"]["specs"])
        self.assertIn("playwright-mcp", payload["checks"]["mcp_pins"]["specs"])

    def test_openspec_binds_ticket_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "openspec" / "specs").mkdir(parents=True)
            result = pala_openspec.OpenSpecAdapter().bind_active_ticket(root, "M10-T1")
            self.assertEqual(result.state, "ready")
            self.assertIn("ticket:M10-T1", result.evidence)

    def test_code_review_graph_marked_uv_isolated(self) -> None:
        report = pala_m10.code_review_graph_lock_report(PLUGIN_ROOT)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(report["uv_isolated"])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contract tests for pala_cold_start cold-start timing report."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pala_cold_start


class ColdStartTests(unittest.TestCase):
    def test_cold_start_report_has_median_ms(self) -> None:
        report = pala_cold_start.run_benchmark(n=1, root=PLUGIN_ROOT)
        self.assertIn("median_ms", report)
        self.assertIsInstance(report["median_ms"], int)
        self.assertNotIn("%", json.dumps(report))

    def test_cold_start_includes_memory_hit_rate_field(self) -> None:
        report = pala_cold_start.run_benchmark(n=1, root=PLUGIN_ROOT)
        self.assertIn("memory_hit_rate", report)
        self.assertIn("memory_hit", report)
        self.assertNotIn("%", json.dumps(report["memory_hit"]))


if __name__ == "__main__":
    unittest.main()

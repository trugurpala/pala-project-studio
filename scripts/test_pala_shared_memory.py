#!/usr/bin/env python3
"""Contract tests for shared-memory surface (M25) + Wave E hit/miss + drift."""

from __future__ import annotations

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

import pala_shared_memory


class SharedMemoryContractTests(unittest.TestCase):
    def test_hit_path_same_db_for_all_hosts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.dict(os.environ, {"PALA_DB_PATH": str(root / "one.sqlite")}, clear=False):
                reports = {
                    host: pala_shared_memory.surface_report(host)
                    for host in ("codex", "cursor", "cli")
                }
            paths = {item["db_path"] for item in reports.values()}
            self.assertEqual(len(paths), 1)
            self.assertTrue(str(paths.pop()).endswith("one.sqlite"))
            for host, item in reports.items():
                self.assertEqual(item["host"], host)
                self.assertEqual(item["access"], "hit")
                self.assertEqual(
                    pala_shared_memory.classify_host_access(host)["access"], "hit"
                )
                self.assertEqual(item["sync_model"], "single_machine_file")
                self.assertFalse(item["cloud_sync"])
                never = " ".join(item["never_store"]).casefold()
                self.assertIn("secrets", never)
                self.assertIn("transcripts", never)

    def test_hit_path_explicit_catalog_root_shared(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog = Path(temp) / "catalog"
            catalog.mkdir()
            paths = {
                pala_shared_memory.surface_report(host, catalog_root=catalog)["db_path"]
                for host in pala_shared_memory.HOSTS
            }
            self.assertEqual(len(paths), 1)
            self.assertTrue(paths.pop().endswith("pala.sqlite"))

    def test_miss_path_unknown_host(self) -> None:
        verdict = pala_shared_memory.classify_host_access("chatgpt-plus")
        self.assertEqual(verdict["access"], "miss")
        with self.assertRaises(ValueError):
            pala_shared_memory.surface_report("chatgpt-plus")

    def test_cursor_host_does_not_claim_codex_hooks(self) -> None:
        report = pala_shared_memory.surface_report("cursor")
        self.assertEqual(report["hooks"], "not_applicable")
        self.assertIn("codex", report["primary_product"].casefold())
        self.assertFalse(report["claims_cursor_install"])

    def test_codex_host_marks_hooks_as_codex_only(self) -> None:
        report = pala_shared_memory.surface_report("codex")
        self.assertEqual(report["hooks"], "codex_hooks_json")
        self.assertTrue(report["claims_codex_plugin"])

    def test_shared_fields_are_documented(self) -> None:
        fields = pala_shared_memory.SHARED_FIELDS
        self.assertIn("pala.sqlite path", fields)
        self.assertIn("memory contract", fields)
        self.assertNotIn("transcripts", fields)

    def test_doctor_store_block_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "doctor.sqlite"
            with patch.dict(os.environ, {"PALA_DB_PATH": str(db)}, clear=False):
                block = pala_shared_memory.doctor_store_block()
            self.assertEqual(block["db_path"], str(db))
            self.assertFalse(block["cloud_sync"])
            self.assertEqual(block["agents_source"], "AGENTS.md")
            self.assertIn("codex", block["hosts"])
            self.assertIn("cursor", block["hosts"])
            self.assertIn("cli", block["hosts"])
            self.assertEqual(block["hosts"]["cursor"]["hooks"], "not_applicable")
            self.assertIn("not a codex plugin", block["hosts"]["cursor"]["install"].casefold())

    def test_portable_skill_has_no_wave_e_drift(self) -> None:
        skill = (PLUGIN_ROOT / "portable" / "cursor" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        missing = pala_shared_memory.portable_skill_drift(skill)
        self.assertEqual(missing, [], f"portable skill drift markers missing: {missing}")
        folded = skill.casefold()
        self.assertIn("hooks", folded)
        self.assertIn("pala_report.py", folded)

    def test_cursor_rule_stays_thin_and_points_at_agents(self) -> None:
        rule = (PLUGIN_ROOT / ".cursor" / "rules" / "pala-memory.mdc").read_text(
            encoding="utf-8"
        )
        body = pala_shared_memory.cursor_rule_body_lines(rule)
        self.assertLessEqual(
            len(body),
            pala_shared_memory.CURSOR_RULE_MAX_BODY_LINES,
            f"cursor rule too thick ({len(body)} lines)",
        )
        folded = rule.casefold()
        self.assertIn("agents.md", folded)
        self.assertNotIn("hooks.json", folded)
        self.assertNotIn("sessionstart", folded)


if __name__ == "__main__":
    unittest.main()

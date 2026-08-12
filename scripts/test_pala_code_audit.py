#!/usr/bin/env python3
"""Contract tests for Pala's dependency-free code audit."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "pala_code_audit.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pala_code_audit", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("pala_code_audit.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pala_code_audit"] = module
    spec.loader.exec_module(module)
    return module


class CodeAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = load_module()

    def test_real_pala_source_has_no_hard_security_finding(self) -> None:
        result = self.audit.run_audit(ROOT)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["security"]["status"], "passed")
        self.assertGreater(result["files_scanned"], 10)

    def test_status_renderer_no_longer_trips_the_module_review_budget(self) -> None:
        result = self.audit.run_audit(ROOT)
        oversized = {
            item["path"]
            for item in result["maintainability"]["modules"]
            if isinstance(item, dict)
        }
        self.assertNotIn("scripts/pala_view.py", oversized)

    def test_quality_engine_keeps_discovery_out_of_the_orchestrator_budget(self) -> None:
        result = self.audit.run_audit(ROOT)
        oversized = {
            item["path"]
            for item in result["maintainability"]["modules"]
            if isinstance(item, dict)
        }
        self.assertNotIn("scripts/pala_quality.py", oversized)

        unbounded = {
            item["path"]
            for item in result["process_hygiene"]["without_timeout"]
            if isinstance(item, dict)
        }
        self.assertNotIn("scripts/pala_quality.py", unbounded)

    def test_quality_policy_split_removes_the_large_plan_function_candidate(self) -> None:
        core = ROOT / "scripts" / "pala_quality.py"
        policy = ROOT / "scripts" / "pala_quality_policy.py"
        self.assertTrue(policy.is_file())
        self.assertIn("from pala_quality_policy import", core.read_text(encoding="utf-8"))

        result = self.audit.run_audit(ROOT)
        oversized = {
            (item["path"], item["name"])
            for item in result["maintainability"]["functions"]
            if isinstance(item, dict)
        }
        self.assertNotIn(("scripts/pala_quality.py", "build_quality_plan"), oversized)
        self.assertNotIn(("scripts/pala_quality_policy.py", "build_quality_plan"), oversized)

    def test_state_git_observation_has_no_unbounded_process(self) -> None:
        result = self.audit.run_audit(ROOT)
        unbounded = {
            item["path"]
            for item in result["process_hygiene"]["without_timeout"]
            if isinstance(item, dict)
        }
        self.assertNotIn("scripts/pala_state.py", unbounded)

    def test_cold_packet_keeps_git_observation_small_and_time_bounded(self) -> None:
        result = self.audit.run_audit(ROOT)
        oversized = {
            item["path"]
            for item in result["maintainability"]["modules"]
            if isinstance(item, dict)
        }
        unbounded = {
            item["path"]
            for item in result["process_hygiene"]["without_timeout"]
            if isinstance(item, dict)
        }
        self.assertNotIn("scripts/pala_cold_packet.py", oversized)
        self.assertNotIn("scripts/pala_cold_packet_git.py", unbounded)

    def test_t6_packet_and_hook_session_owners_stay_within_review_budget(self) -> None:
        owners = {
            "scripts/pala_cold_packet_packet.py",
            "scripts/pala_hook_session.py",
        }
        for relative in owners:
            self.assertTrue((ROOT / relative).is_file())
            self.assertLessEqual(
                len((ROOT / relative).read_text(encoding="utf-8").splitlines()),
                800,
            )
        result = self.audit.run_audit(ROOT)
        candidates = {
            (item["path"], item["name"])
            for item in result["maintainability"]["functions"]
            if isinstance(item, dict)
        }
        self.assertFalse(
            {
                ("scripts/pala_cold_packet.py", "build_cold_packet"),
                ("scripts/pala_hook.py", "session_context"),
                ("scripts/pala_hook.py", "main"),
            }.intersection(candidates)
        )

    def test_t7_view_css_and_document_owners_stay_within_review_budget(self) -> None:
        owners = {
            "scripts/pala_view.py",
            "scripts/pala_view_styles.py",
            "scripts/pala_view_layout.py",
        }
        for relative in owners:
            self.assertTrue((ROOT / relative).is_file())
            self.assertLessEqual(
                len((ROOT / relative).read_text(encoding="utf-8").splitlines()),
                800,
            )
        result = self.audit.run_audit(ROOT)
        candidates = {
            (item["path"], item["name"])
            for item in result["maintainability"]["functions"]
            if isinstance(item, dict)
        }
        self.assertFalse(
            {
                ("scripts/pala_view.py", "_css"),
                ("scripts/pala_view.py", "render"),
                ("scripts/pala_view_styles.py", "render_css"),
                ("scripts/pala_view_layout.py", "render"),
            }.intersection(candidates)
        )

    def test_state_moves_git_checkpoint_observation_to_a_bounded_owner(self) -> None:
        state = ROOT / "scripts" / "pala_state.py"
        owner = ROOT / "scripts" / "pala_state_git.py"
        self.assertTrue(owner.is_file())
        self.assertIn("from pala_state_git import", state.read_text(encoding="utf-8"))
        self.assertLessEqual(len(state.read_text(encoding="utf-8").splitlines()), 1_550)

    def test_t3_process_owners_are_all_time_bounded(self) -> None:
        result = self.audit.run_audit(ROOT)
        unbounded = {
            item["path"]
            for item in result["process_hygiene"]["without_timeout"]
            if isinstance(item, dict)
        }
        self.assertFalse(
            {
                "scripts/pala_code_intel.py",
                "scripts/pala_cold_start.py",
                "scripts/pala_p0_smoke.py",
                "scripts/verify.py",
            }.intersection(unbounded)
        )

    def test_t3_smoke_orchestrator_stays_within_the_review_budget(self) -> None:
        result = self.audit.run_audit(ROOT)
        oversized = {
            (item["path"], item["name"])
            for item in result["maintainability"]["functions"]
            if isinstance(item, dict)
        }
        self.assertNotIn(("scripts/pala_p0_smoke.py", "run_smoke"), oversized)

    def test_installer_moves_external_codex_bridge_to_a_bounded_owner(self) -> None:
        installer = ROOT / "scripts" / "pala_installer.py"
        owner = ROOT / "scripts" / "pala_installer_codex.py"
        self.assertTrue(owner.is_file())
        self.assertIn("_load_codex_bridge", installer.read_text(encoding="utf-8"))
        owners = {
            "scripts/pala_installer.py",
            "scripts/pala_installer_core.py",
            "scripts/pala_installer_integrity.py",
            "scripts/pala_installer_transaction.py",
        }
        self.assertIn("pala_installer_integrity", installer.read_text(encoding="utf-8"))
        self.assertIn("pala_installer_transaction", installer.read_text(encoding="utf-8"))
        for relative in owners:
            self.assertTrue((ROOT / relative).is_file())
            self.assertLessEqual(
                len((ROOT / relative).read_text(encoding="utf-8").splitlines()),
                800,
            )

        result = self.audit.run_audit(ROOT)
        oversized = {
            item["path"]
            for item in result["maintainability"]["modules"]
            if isinstance(item, dict)
        }
        self.assertFalse(owners.intersection(oversized))

    def test_subprocess_shell_true_is_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "risky.py").write_text(
                "import subprocess\nsubprocess.run(['ok'], shell=True)\n",
                encoding="utf-8",
            )
            result = self.audit.run_audit(root)
        self.assertEqual(result["status"], "failed")
        finding = result["security"]["findings"][0]
        self.assertEqual(finding["rule"], "subprocess-shell")
        self.assertEqual(finding["path"], "scripts/risky.py")

    def test_hook_network_import_is_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "pala_hook.py").write_text(
                "import urllib.request\n", encoding="utf-8"
            )
            result = self.audit.run_audit(root, profile="runtime")
        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "hook-network-import",
            {item["rule"] for item in result["security"]["findings"]},
        )

    def test_large_module_is_explicit_advisory_not_false_security_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "large.py").write_text("pass\n" * 801, encoding="utf-8")
            result = self.audit.run_audit(root)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["maintainability"]["status"], "attention_required")


if __name__ == "__main__":
    unittest.main()

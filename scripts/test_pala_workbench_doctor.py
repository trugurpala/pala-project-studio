from __future__ import annotations

import unittest
from unittest.mock import patch
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_workbench_doctor import codegraph_inventory, doctor


class WorkbenchDoctorTests(unittest.TestCase):
    def test_codegraph_inventory_uses_the_pinned_provider_contract(self) -> None:
        with patch(
            "pala_workbench_doctor.codegraph_inventory_raw",
            return_value={"state": "exact"},
        ) as raw:
            result = codegraph_inventory(Path("C:/Pala"))
        self.assertEqual(result["state"], "exact")
        spec, state_root = raw.call_args.args
        self.assertEqual(spec.version, "1.5.0")
        self.assertEqual(state_root, Path("C:/Pala"))
        self.assertEqual(
            raw.call_args.kwargs["executable"], "codegraph-win32-x64/bin/codegraph.cmd"
        )

    def test_required_provider_failure_blocks_core(self) -> None:
        with (
            patch("pala_workbench_doctor.codegraph_inventory", return_value={"state": "exact", "health": "passed", "version": "1.5.0"}),
            patch("pala_workbench_doctor.semgrep_probe", return_value={"state": "exact", "status": "blocked", "version": "1.172.0"}),
        ):
            result = doctor(Path("C:/Pala"), Path("C:/project"), task_requires_browser=False)
        self.assertFalse(result["healthy"])
        self.assertIn("security_static", result["problems"])

    def test_optional_and_lazy_absence_never_blocks_core(self) -> None:
        with (
            patch("pala_workbench_doctor.codegraph_inventory", return_value={"state": "exact", "health": "passed", "version": "1.5.0"}),
            patch("pala_workbench_doctor.semgrep_probe", return_value={"state": "exact", "status": "passed", "version": "1.172.0", "integrity": "sha256:y", "ownership": "pala-project-studio", "provenance": "official-wheel"}),
        ):
            result = doctor(Path("C:/Pala"), Path("C:/project"), task_requires_browser=False)
        self.assertTrue(result["healthy"])
        self.assertEqual(result["capabilities"]["symbol_precision"]["state"], "absent")
        self.assertEqual(result["capabilities"]["current_docs"]["state"], "absent")

    def test_playwright_affects_health_only_when_selected(self) -> None:
        with (
            patch("pala_workbench_doctor.codegraph_inventory", return_value={"state": "exact", "health": "passed", "version": "1.5.0"}),
            patch("pala_workbench_doctor.semgrep_probe", return_value={"state": "exact", "status": "passed", "version": "1.172.0", "integrity": "sha256:y", "ownership": "pala-project-studio", "provenance": "official-wheel"}),
            patch("pala_workbench_doctor.inspect_project_profile", return_value={"status": "blocked"}),
        ):
            ignored = doctor(Path("C:/Pala"), Path("C:/project"), task_requires_browser=False)
            required = doctor(Path("C:/Pala"), Path("C:/project"), task_requires_browser=True)
        self.assertTrue(ignored["healthy"])
        self.assertFalse(required["healthy"])

    def test_advanced_has_integrity_freshness_offline_and_remnant_controls(self) -> None:
        with (
            patch("pala_workbench_doctor.codegraph_inventory", return_value={"state": "exact", "health": "passed", "version": "1.5.0", "integrity": "sha256:x", "provenance": "official"}),
            patch("pala_workbench_doctor.semgrep_probe", return_value={"state": "exact", "status": "passed", "version": "1.172.0", "integrity": "sha256:y", "ownership": "pala-project-studio", "provenance": "official-wheel"}),
        ):
            result = doctor(Path("C:/Pala"), Path("C:/project"), task_requires_browser=False)
        for key in ("ownership", "version_integrity_provenance", "freshness_offline", "forbidden_runtime", "retired_remnants"):
            self.assertIn(key, result["advanced"])
        self.assertEqual(result["advanced"]["ownership"]["security_static"], "pala-project-studio")
        self.assertEqual(
            result["advanced"]["version_integrity_provenance"]["semgrep"]["provenance"],
            "official-wheel",
        )

    def test_normal_view_separates_security_engine_from_project_coverage(self) -> None:
        with (
            patch("pala_workbench_doctor.codegraph_inventory", return_value={"state": "exact", "health": "passed", "version": "1.5.0"}),
            patch("pala_workbench_doctor.semgrep_probe", return_value={"state": "exact", "status": "passed", "version": "1.172.0"}),
            patch(
                "pala_workbench_doctor.language_coverage",
                return_value={
                    "status": "configured-not-verified",
                    "project_languages": ["python", "rust"],
                    "covered_languages": ["python"],
                    "uncovered_languages": ["rust"],
                },
            ),
        ):
            result = doctor(Path("C:/Pala"), Path("C:/project"), task_requires_browser=False)
        self.assertTrue(result["healthy"])
        self.assertEqual(result["normal"]["Guvenlik"]["motor"], "hazir")
        self.assertEqual(
            result["normal"]["Guvenlik"]["proje_kapsami"],
            "configured-not-verified",
        )
        self.assertTrue(result["security_truth"]["engine_ready"])
        self.assertFalse(result["security_truth"]["coverage_verified"])

    def test_retired_remnant_audit_includes_all_retired_helper_names(self) -> None:
        with (
            patch("pala_workbench_doctor.codegraph_inventory", return_value={"state": "exact", "health": "passed", "version": "1.5.0"}),
            patch("pala_workbench_doctor.semgrep_probe", return_value={"state": "exact", "status": "passed", "version": "1.172.0"}),
            patch("pala_workbench_doctor.language_coverage", return_value={"status": "passed"}),
        ):
            result = doctor(Path("C:/Pala"), Path("C:/project"), task_requires_browser=False)
        self.assertEqual(
            set(result["advanced"]["retired_remnants"]),
            {"graphify", "codebase-memory", "code-review-graph", "ollama", "rtk", "playwright-mcp", "serena"},
        )


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_playwright import (
    CLI_VERSION,
    TEST_VERSION,
    browser_environment,
    inspect_project_profile,
    validate_browser_evidence,
)


class PlaywrightProfileTests(unittest.TestCase):
    def test_exact_project_test_dependency_is_reused_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "package.json").write_text(
                json.dumps({"devDependencies": {"@playwright/test": "1.62.1"}}), encoding="utf-8"
            )
            result = inspect_project_profile(root, task_requires_browser=True)
        self.assertEqual(TEST_VERSION, "1.62.1")
        self.assertEqual(result["browser_e2e"]["state"], "exact")
        self.assertEqual(result["action"], "reuse-project-dependency")
        self.assertFalse(result["mutation_authorized"])

    def test_missing_or_range_dependency_never_silently_installs_or_upgrades(self) -> None:
        for dependency in (None, "^1.62.1", "1.61.0"):
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                package = {"devDependencies": {}} if dependency is None else {
                    "devDependencies": {"@playwright/test": dependency}
                }
                (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
                result = inspect_project_profile(root, task_requires_browser=True)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["action"], "explicit-taskcontract-change-required")
            self.assertFalse(result["mutation_authorized"])

    def test_project_profile_is_not_core_health_when_not_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "package.json").write_text("{}", encoding="utf-8")
            result = inspect_project_profile(root, task_requires_browser=False)
        self.assertEqual(result["status"], "not-run")
        self.assertFalse(result["affects_core_health"])

    def test_cli_and_test_contracts_are_separate_and_no_mcp_is_default(self) -> None:
        self.assertEqual(CLI_VERSION, "0.1.18")
        self.assertEqual(TEST_VERSION, "1.62.1")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "package.json").write_text(
                json.dumps({"devDependencies": {"@playwright/test": TEST_VERSION}}), encoding="utf-8"
            )
            result = inspect_project_profile(root, task_requires_browser=True)
        self.assertEqual(result["browser_exploration"]["provider"], "@playwright/cli")
        self.assertEqual(result["browser_e2e"]["provider"], "@playwright/test")
        self.assertFalse(result["default_mcp_registered"])
        mcp_path = SCRIPTS.parent / ".mcp.json"
        if mcp_path.is_file():
            mcp = json.loads(mcp_path.read_text(encoding="utf-8"))
            self.assertNotIn("playwright", json.dumps(mcp).casefold())

    def test_evidence_requires_trace_screenshot_console_network_and_browser_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("trace.zip", "page.png", "console.json", "network.har"):
                (root / name).write_bytes(b"evidence")
            record = {
                "trace": "trace.zip",
                "screenshot": "page.png",
                "console": "console.json",
                "network": "network.har",
                "browser_version": "Chromium 140.0",
                "ui_opened": False,
                "trace_viewer_opened": False,
            }
            passed = validate_browser_evidence(root, record)
            record["trace_viewer_opened"] = True
            blocked = validate_browser_evidence(root, record)
        self.assertEqual(passed["status"], "passed")
        self.assertEqual(blocked["status"], "blocked")

    def test_browser_cache_is_pala_controlled_and_ui_is_never_auto_opened(self) -> None:
        environment = browser_environment(Path("C:/Pala/workbench/browser-cache"))
        self.assertIn("PLAYWRIGHT_BROWSERS_PATH", environment)
        self.assertEqual(environment["CI"], "1")
        self.assertEqual(environment["PW_TEST_HTML_REPORT_OPEN"], "never")


if __name__ == "__main__":
    unittest.main()

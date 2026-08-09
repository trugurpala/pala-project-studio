#!/usr/bin/env python3
"""Contract tests for Pala's local, evidence-first Delivery Quality Engine."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def load_quality():
    spec = importlib.util.spec_from_file_location("pala_quality", SCRIPTS / "pala_quality.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("pala_quality.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_state():
    spec = importlib.util.spec_from_file_location("pala_state_quality_test", SCRIPTS / "pala_state.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("pala_state.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QualityPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.quality = load_quality()

    def test_node_project_derives_native_quality_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "scripts": {
                            "test": "vitest run",
                            "lint": "eslint .",
                            "typecheck": "tsc --noEmit",
                            "build": "vite build",
                            "test:integration": "node integration.mjs",
                            "smoke": "node smoke.mjs",
                        },
                        "dependencies": {"react": "1"},
                    }
                ),
                encoding="utf-8",
            )
            plan = self.quality.build_quality_plan(root, tier="ticket")

            kinds = {item["kind"] for item in plan["checks"]}
            self.assertTrue({"unit", "lint", "typecheck", "build", "integration", "runtime-smoke"}.issubset(kinds))
            self.assertEqual(plan["risk"]["level"], "medium")
            self.assertTrue(all(item["status"] == "not-run" for item in plan["checks"]))

    def test_browser_is_required_only_for_existing_playwright_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            (root / "package.json").write_text(
                json.dumps(
                    {"scripts": {"test:e2e": "playwright test"}, "dependencies": {"react": "1"}}
                ),
                encoding="utf-8",
            )
            (root / "playwright.config.ts").write_text("export default {};\n", encoding="utf-8")
            plan = self.quality.build_quality_plan(root, tier="ticket")
            browser = next(item for item in plan["checks"] if item["kind"] == "browser")

            self.assertTrue(browser["required"])
            self.assertEqual(browser["command"], "npm run test:e2e")

    def test_non_ui_project_does_not_gain_a_browser_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            (root / "package.json").write_text(
                json.dumps({"scripts": {"test:e2e": "playwright test"}}),
                encoding="utf-8",
            )
            (root / "playwright.config.ts").write_text("export default {};\n", encoding="utf-8")
            plan = self.quality.build_quality_plan(root, tier="ticket")
            self.assertFalse(any(item["kind"] == "browser" for item in plan["checks"]))

    def test_unavailable_optional_scanner_is_not_claimed_passed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            workflow = root / ".github" / "workflows"
            workflow.mkdir(parents=True)
            (workflow / "security.yml").write_text("- run: gitleaks detect\n", encoding="utf-8")
            plan = self.quality.build_quality_plan(root, tier="release", which=lambda _: None)
            security = next(item for item in plan["checks"] if item["kind"] == "security")

            self.assertEqual(security["status"], "configured-not-verified")
            self.assertTrue(security["required"])

    def test_risk_marks_auth_and_migration_changes_high(self) -> None:
        plan = self.quality.build_quality_plan(
            ROOT, changed_files=["src/auth/session.ts", "db/migrations/001.sql"]
        )
        self.assertEqual(plan["risk"]["level"], "high")
        self.assertIn("authentication", plan["risk"]["reasons"])
        self.assertIn("migration", plan["risk"]["reasons"])
        self.assertIn("git", plan)
        migration = next(item for item in plan["checks"] if item["kind"] == "migration")
        security = next(item for item in plan["checks"] if item["kind"] == "security")
        self.assertEqual(migration["status"], "blocked")
        self.assertEqual(security["status"], "blocked")

    def test_dangerous_configured_script_is_blocked_not_normalized(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            (root / "package.json").write_text(
                json.dumps({"scripts": {"lint": "rm -rf generated && eslint ."}}),
                encoding="utf-8",
            )

            plan = self.quality.build_quality_plan(root)
            lint = next(item for item in plan["checks"] if item["kind"] == "lint")

            self.assertEqual(lint["status"], "blocked")
            self.assertIsNone(lint["command"])


class QualityLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.quality = load_quality()

    def test_gate_blocks_until_every_required_check_is_passed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            plan = {
                "schema_version": 1,
                "ticket": "Q1",
                "checks": [
                    {"id": "unit:test", "kind": "unit", "required": True, "status": "not-run", "command": "py -3 -m unittest"},
                    {"id": "lint:ruff", "kind": "lint", "required": False, "status": "not-run", "command": "ruff check ."},
                ],
            }
            self.quality.write_ledger(root, "Q1", plan)
            self.assertIn("git", self.quality.read_ledger(root, "Q1"))
            blocked = self.quality.quality_gate(root, "Q1")
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(blocked["next_action"], "run unit:test")

            self.quality.record_result(
                root, "Q1", "unit:test", status="passed", command="py -3 -m unittest", exit_code=0
            )
            passed = self.quality.quality_gate(root, "Q1")
            self.assertEqual(passed["status"], "passed")
            self.assertEqual(passed["coverage"], {"passed": 1, "required": 1})

    def test_failed_result_can_never_become_passed_without_new_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            plan = {"schema_version": 1, "ticket": "Q2", "checks": [{"id": "unit:test", "kind": "unit", "required": True, "status": "not-run", "command": "py -3 -m unittest"}]}
            self.quality.write_ledger(root, "Q2", plan)
            self.quality.record_result(root, "Q2", "unit:test", status="failed", command="py -3 -m unittest", exit_code=1)
            with self.assertRaises(ValueError):
                self.quality.record_result(root, "Q2", "unit:test", status="passed", command="py -3 -m unittest", exit_code=None)

    def test_artifact_cannot_escape_project_or_store_secrets(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            (root / "reports").mkdir()
            (root / "reports" / "result.html").write_text("ok", encoding="utf-8")
            plan = {"schema_version": 1, "ticket": "Q3", "checks": [{"id": "browser:e2e", "kind": "browser", "required": True, "status": "not-run", "command": "npm run test:e2e"}]}
            self.quality.write_ledger(root, "Q3", plan)
            with self.assertRaises(ValueError):
                self.quality.record_result(root, "Q3", "browser:e2e", status="passed", command="npm run test:e2e", exit_code=0, artifact="../secret.txt")
            with self.assertRaises(ValueError):
                self.quality.record_result(root, "Q3", "browser:e2e", status="passed", command="TOKEN=abc npm run test:e2e", exit_code=0)
            self.quality.record_result(root, "Q3", "browser:e2e", status="passed", command="npm run test:e2e", exit_code=0, artifact="reports/result.html")
            ledger = self.quality.read_ledger(root, "Q3")
            self.assertEqual(ledger["checks"][0]["artifact"], "reports/result.html")

    def test_reopened_ticket_retains_only_matching_gate_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            initial = {"checks": [{"id": "unit:test", "kind": "unit", "required": True, "status": "not-run", "command": "py -3 -m unittest"}]}
            self.quality.write_ledger(root, "Q4", initial)
            self.quality.record_result(root, "Q4", "unit:test", status="passed", command="py -3 -m unittest", exit_code=0)

            self.quality.write_ledger(root, "Q4", initial)
            retained = self.quality.read_ledger(root, "Q4")
            self.assertEqual(retained["checks"][0]["status"], "passed")

            changed = {"checks": [{"id": "unit:test", "kind": "unit", "required": True, "status": "not-run", "command": "pytest -q"}]}
            self.quality.write_ledger(root, "Q4", changed)
            reset = self.quality.read_ledger(root, "Q4")
            self.assertEqual(reset["checks"][0]["status"], "not-run")

            self.quality.write_ledger(root, "Q4", initial)
            self.quality.record_result(root, "Q4", "unit:test", status="passed", command="py -3 -m unittest", exit_code=0)
            changed_surface = {**initial, "changed_files": ["src/new.py"]}
            self.quality.write_ledger(root, "Q4", changed_surface)
            self.assertEqual(self.quality.read_ledger(root, "Q4")["checks"][0]["status"], "not-run")

    def test_empty_plan_never_becomes_a_vacuous_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            self.quality.write_ledger(root, "Q0", {"checks": []})
            decision = self.quality.quality_gate(root, "Q0")
            self.assertEqual(decision["status"], "blocked")
            self.assertEqual(decision["next_action"], "configure project-native quality gate")


class QualityIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.quality = load_quality()
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))

    def test_cli_initializes_then_records_a_planned_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            (root / "tests").mkdir()
            (root / "tests" / "test_sample.py").write_text("pass\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                initialized = self.quality.main(["init", "--cwd", str(root), "--ticket", "Q5"])
            self.assertEqual(initialized, 0)
            ledger = self.quality.read_ledger(root, "Q5")
            check = next(item for item in ledger["checks"] if item["kind"] == "unit")
            with contextlib.redirect_stdout(output):
                recorded = self.quality.main(
                    [
                        "record", "--cwd", str(root), "--ticket", "Q5",
                        "--check", str(check["id"]), "--status", "passed",
                        "--command", str(check["command"]), "--exit-code", "0",
                    ]
                )
            self.assertEqual(recorded, 0)
            self.assertEqual(self.quality.quality_gate(root, "Q5")["status"], "passed")

    def test_explicit_checkpoint_claim_fails_closed_until_ledger_is_green(self) -> None:
        pala_state = load_state()

        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            plan = {
                "checks": [
                    {"id": "unit:test", "kind": "unit", "required": True, "status": "not-run", "command": "py -3 -m unittest"}
                ]
            }
            self.quality.write_ledger(root, "Q7", plan)
            with self.assertRaises(ValueError):
                pala_state.require_quality_gate(root, "Q7")
            self.quality.record_result(root, "Q7", "unit:test", status="passed", command="py -3 -m unittest", exit_code=0)
            self.assertEqual(pala_state.require_quality_gate(root, "Q7")["status"], "passed")

    def test_status_html_uses_five_safe_quality_signals(self) -> None:
        import pala_report

        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            plan = {
                "tier": "ticket",
                "risk": {"level": "high", "reasons": ["authentication"]},
                "checks": [
                    {
                        "id": "unit:test", "kind": "unit", "required": True,
                        "status": "not-run", "command": "py -3 -m unittest",
                    }
                ],
            }
            self.quality.write_ledger(root, "Q6", plan)
            workflow = root / ".codex" / "pala-workflow.json"
            workflow.parent.mkdir(parents=True, exist_ok=True)
            workflow.write_text(
                json.dumps({"schema_version": 2, "active_ticket": "Q6", "updated_at": "2026-08-09T00:00:00+00:00"}),
                encoding="utf-8",
            )

            model = pala_report.build_status_model(
                root, update={"status": "current"}, catalog_root=root / "catalog"
            )
            page = pala_report.render_html(
                root, update={"status": "current"}, catalog_root=root / "catalog"
            )

            self.assertEqual(model["quality"]["status"], "blocked")
            self.assertEqual(model["next_action"], "run unit:test")
            for label in ("Aktif ticket", "Risk seviyesi", "Quality coverage", "Son eksik gate", "Tek sonraki eylem"):
                self.assertIn(label, page)
            self.assertNotIn("py -3 -m unittest", page)

    def test_green_quality_uses_the_workflow_next_action(self) -> None:
        import pala_report

        with tempfile.TemporaryDirectory(prefix="pala-quality-") as temp:
            root = Path(temp)
            plan = {"checks": [{"id": "unit:test", "kind": "unit", "required": True, "status": "not-run", "command": "py -3 -m unittest"}]}
            self.quality.write_ledger(root, "Q8", plan)
            self.quality.record_result(root, "Q8", "unit:test", status="passed", command="py -3 -m unittest", exit_code=0)
            signal = pala_report.quality_signal(root, {"active_ticket": "Q8"})

            self.assertEqual(signal["last_problem"], "yok")
            self.assertEqual(signal["next_action"], "")


if __name__ == "__main__":
    unittest.main()

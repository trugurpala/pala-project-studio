import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from build_portable import validate_internal_markdown_links
from pala_product_e2e import REQUIRED_EVIDENCE_FIELDS, write_evidence_manifest
from pala_quality import quality_ledger_path
from pala_report import write_report
from pala_store import WorkflowStore

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
FIXTURES = ROOT / "fixtures" / "product-flow"


class ProductionProductFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.project = self.base / "project"
        self.project.mkdir()
        subprocess.run(["git", "init"], cwd=self.project, check=True, capture_output=True)
        self.environment = {
            **os.environ,
            "LOCALAPPDATA": str(self.base / "local-app-data"),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        }

    def product_cli_result(
        self, *arguments: str
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "pala_product_cli.py"), *arguments],
            cwd=self.project,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
        )
        return result, json.loads(result.stdout)

    def product_cli(self, *arguments: str) -> dict[str, object]:
        result, payload = self.product_cli_result(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return payload

    def start_product(self) -> dict[str, object]:
        return self.product_cli(
            "start",
            "--cwd",
            str(self.project),
            "--intent",
            "Su içme takip sitesi istiyorum. Natro Linux cPanel hostingim var.",
            "--plan",
            str(FIXTURES / "water-tracker-plan.json"),
            "--capabilities",
            str(FIXTURES / "natro-capabilities.json"),
            "--provider-candidate",
            str(FIXTURES / "codex-candidate.json"),
            "--session-key",
            "product-e2e-session",
        )

    def initialize_quality(self, argv: list[str]) -> tuple[str, str]:
        contract_path = self.project / ".pala" / "quality.json"
        contract_path.parent.mkdir(parents=True, exist_ok=True)
        contract_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "checks": [
                        {
                            "id": "product-public-flow",
                            "kind": "integration",
                            "argv": argv,
                            "tiers": ["ticket"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        quality_ticket = "water-tracker-T-1"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "pala_quality.py"),
                "init",
                "--cwd",
                str(self.project),
                "--ticket",
                quality_ticket,
                "--tier",
                "ticket",
            ],
            cwd=self.project,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return quality_ticket, "integration:product-public-flow"

    def complete_with_approved_check(
        self,
        quality_ticket: str,
        check_id: str,
        *,
        timeout_seconds: str = "5",
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
        return self.product_cli_result(
            "complete",
            "--cwd",
            str(self.project),
            "--project-id",
            "water-tracker",
            "--session-key",
            "product-e2e-session",
            "--quality-ticket",
            quality_ticket,
            "--check-id",
            check_id,
            "--quality-timeout-seconds",
            timeout_seconds,
        )

    def assert_product_not_done(self) -> None:
        status = self.product_cli(
            "status", "--cwd", str(self.project), "--project-id", "water-tracker"
        )
        self.assertNotEqual(status["project_state"], "PACKAGE_READY")
        with patch.dict(os.environ, self.environment, clear=True):
            task = WorkflowStore(self.project)._read_ticket("water-tracker-T-1")
        self.assertIsNotNone(task)
        self.assertNotEqual(task["task_contract"]["status"], "DONE")

    def test_public_cli_persists_resumes_completes_and_wires_owner_report(self) -> None:
        started = self.start_product()

        self.assertEqual(started["status"], "awaiting_quality")
        self.assertEqual(started["provider"], "codex")
        self.assertEqual(started["task_authority"], "TaskContract")
        self.assertIn("php", started["explicit_unknowns"])

        resumed = self.product_cli(
            "status", "--cwd", str(self.project), "--project-id", "water-tracker"
        )
        self.assertEqual(
            resumed["product_spec"]["goal"], "Deliver a verified water tracking product"
        )
        self.assertEqual(resumed["project_state"], "BUILDING")
        self.assertEqual(resumed["delivery_target"], "generic-linux-cpanel")

        quality_ticket, check_id = self.initialize_quality(
            [sys.executable, "-c", "raise SystemExit(0)"]
        )
        result, completed = self.complete_with_approved_check(quality_ticket, check_id)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

        self.assertEqual(completed["status"], "package-ready")
        self.assertEqual(completed["project_state"], "PACKAGE_READY")
        self.assertEqual(completed["quality"], "passed")
        with patch.dict(os.environ, self.environment, clear=True):
            task = WorkflowStore(self.project)._read_ticket(str(completed["task_id"]))
        self.assertEqual(task["task_contract"]["status"], "DONE")

        output = self.project / "status.html"
        with patch.dict(os.environ, self.environment, clear=True):
            write_report(self.project, output)
        html = output.read_text(encoding="utf-8")
        for label in (
            "Pala 1.0 Owner Cockpit",
            "Project",
            "State",
            "Acceptance",
            "Quality",
            "Environment",
            "Delivery",
            "Live verification",
            "Blocker",
            "Next action",
            "Owner request",
            "Water Tracker",
            "PACKAGE_READY",
        ):
            self.assertIn(label, html)

    def test_caller_forged_exit_zero_cannot_complete_product(self) -> None:
        self.start_product()
        result, payload = self.product_cli_result(
            "complete",
            "--cwd",
            str(self.project),
            "--project-id",
            "water-tracker",
            "--session-key",
            "product-e2e-session",
            "--quality-command",
            json.dumps(["this-command-does-not-exist"]),
            "--quality-exit-code",
            "0",
        )
        self.assertNotEqual(result.returncode, 0, payload)
        self.assertEqual(payload["status"], "blocked")
        self.assert_product_not_done()

    def test_approved_real_zero_exit_completes_product(self) -> None:
        self.start_product()
        quality_ticket, check_id = self.initialize_quality(
            [sys.executable, "-c", "raise SystemExit(0)"]
        )
        result, payload = self.complete_with_approved_check(quality_ticket, check_id)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(payload["status"], "package-ready")
        with patch.dict(os.environ, self.environment, clear=True):
            ledger = json.loads(
                quality_ledger_path(self.project, quality_ticket).read_text(encoding="utf-8")
            )
        check = next(item for item in ledger["checks"] if item["id"] == check_id)
        self.assertEqual(check["execution_authority"], "pala-quality-runner")

    def test_approved_nonzero_exit_blocks_product(self) -> None:
        self.start_product()
        quality_ticket, check_id = self.initialize_quality(
            [sys.executable, "-c", "raise SystemExit(7)"]
        )
        result, payload = self.complete_with_approved_check(quality_ticket, check_id)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(payload["status"], "blocked")
        self.assert_product_not_done()

    def test_approved_timeout_blocks_product(self) -> None:
        self.start_product()
        quality_ticket, check_id = self.initialize_quality(
            [sys.executable, "-c", "import time; time.sleep(2)"]
        )
        result, payload = self.complete_with_approved_check(
            quality_ticket, check_id, timeout_seconds="0.05"
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(payload["status"], "blocked")
        self.assert_product_not_done()

    def test_recorded_command_drift_from_approved_argv_blocks_product(self) -> None:
        self.start_product()
        quality_ticket, check_id = self.initialize_quality(
            [sys.executable, "-c", "raise SystemExit(0)"]
        )
        with patch.dict(os.environ, self.environment, clear=True):
            ledger_path = quality_ledger_path(self.project, quality_ticket)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            check = next(item for item in ledger["checks"] if item["id"] == check_id)
            check["command"] = "this-command-does-not-exist"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
        result, payload = self.complete_with_approved_check(quality_ticket, check_id)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertEqual(payload["status"], "blocked")
        self.assert_product_not_done()


class ProductIdentityAndArtifactTests(unittest.TestCase):
    def test_current_identity_is_explicit_and_consistent(self) -> None:
        identity = json.loads((ROOT / "product-identity.json").read_text(encoding="utf-8"))
        plugin = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        project = (ROOT / "PROJECT.md").read_text(encoding="utf-8")
        goal = (ROOT / "GOAL.md").read_text(encoding="utf-8")

        self.assertEqual(identity["product_version"], "1.1.0")
        self.assertEqual(identity["plugin_version"], plugin["version"])
        self.assertEqual(identity["python_package_version"], "1.1.0")
        self.assertEqual(identity["artifact_name"], "pala-project-studio-1.1.0.zip")
        if identity["remote_publish"] == "passed":
            self.assertEqual(identity["build_release_state"], "VERIFIED")
            self.assertEqual(identity["remote_observed_state"], "PUBLIC RELEASED")
            self.assertEqual(identity["last_published_version"], "1.1.0")
        else:
            self.assertEqual(identity["build_release_state"], "LOCAL RELEASE CANDIDATE VERIFIED")
            self.assertEqual(identity["remote_observed_state"], "NOT PUBLISHED AS 1.1.0")
            self.assertEqual(identity["last_published_version"], "1.0.0")
            self.assertEqual(identity["remote_publish"], "not-run")
        for document in (readme, project, goal):
            self.assertIn(identity["product_version"], document)
        self.assertIn(identity["plugin_version"], readme)
        self.assertNotIn("docs/GOAL_0_8_1_FINISH.md", goal)
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        skill = (ROOT / "skills" / "pala-project-finisher" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("STATUS/cockpit/handoff yalnız generated read modeldir", agents)
        self.assertIn("Greenfield/new-product uses `pala_product_cli.py`", skill)
        self.assertIn("existing-project uses the canonical", " ".join(skill.split()))

    def test_every_internal_markdown_link_in_portable_surface_resolves(self) -> None:
        self.assertEqual(validate_internal_markdown_links(ROOT), [])

    def test_detailed_manifest_requires_and_emits_mechanical_evidence(self) -> None:
        expected = {
            "schema_version",
            "product",
            "product_version",
            "plugin_version",
            "source_head",
            "surface_digest",
            "changed_files",
            "tool_versions",
            "canonical_test_command",
            "canonical_test_exit_code",
            "canonical_test_count",
            "canonical_test_skip_count",
            "pytest_command",
            "pytest_exit_code",
            "pytest_count",
            "ruff_command",
            "ruff_exit_code",
            "legacy_ruff_count",
            "mypy_command",
            "mypy_exit_code",
            "mypy_scope",
            "coverage_command",
            "coverage_exit_code",
            "coverage_percent",
            "bandit_command",
            "bandit_exit_code",
            "bandit_high",
            "bandit_medium",
            "pip_audit_command",
            "pip_audit_exit_code",
            "pip_audit_known_vulnerabilities",
            "source_verify_command",
            "source_verify_exit_code",
            "portable_verify_command",
            "portable_verify_exit_code",
            "installed_verify_command",
            "installed_verify_exit_code",
            "doctor_status",
            "quality_execution_authority",
            "evidence_forgery_regression",
            "product_contract_tests",
            "production_wiring_tests",
            "planner_tests",
            "provider_tests",
            "worktree_tests",
            "credential_tests",
            "delivery_tests",
            "playwright_command",
            "playwright_exit_code",
            "playwright_report",
            "browser_tests",
            "owner_cockpit_tests",
            "golden_contract",
            "golden_real_e2e",
            "artifact_path",
            "artifact_sha256",
            "artifact_entries",
            "open_p0",
            "open_p1",
            "technical_debt",
            "needs_decision",
            "remote_publish",
            "real_remote_deploy",
            "generated_at",
        }
        self.assertEqual(REQUIRED_EVIDENCE_FIELDS, expected)

        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            artifact = root / "artifact.zip"
            with zipfile.ZipFile(artifact, "w") as archive:
                archive.writestr("pala-project-studio/README.md", "Pala")
            evidence = {name: 0 for name in expected}
            evidence.update(
                {
                    "schema_version": 2,
                    "product": "PALA Provider-Independent Local Software Delivery OS",
                    "product_version": "1.0.0-local-rc",
                    "plugin_version": "1.0.0-local-rc+codex.test",
                    "changed_files": [],
                    "tool_versions": {},
                    "mypy_scope": [],
                    "doctor_status": "passed",
                    "quality_execution_authority": "pala-quality-runner",
                    "evidence_forgery_regression": {"status": "passed", "count": 5},
                    "technical_debt": [],
                    "needs_decision": [],
                    "remote_publish": "not-run",
                    "real_remote_deploy": "not-run",
                }
            )
            path = write_evidence_manifest(root, artifact, evidence)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(set(payload), expected)
        self.assertEqual(payload["artifact_entries"], 1)
        self.assertEqual(len(payload["artifact_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()

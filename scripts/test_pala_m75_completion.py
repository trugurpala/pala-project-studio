"""M75 adversarial contracts for capability-gated canonical completion."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pala_host_capability_broker import observe_codex_host  # noqa: E402, I001
from pala_product import load_project_contract, save_project_contract  # noqa: E402
from pala_product_cli import complete_product, start_product  # noqa: E402
from pala_quality import main as quality_main  # noqa: E402
from pala_quality import quality_gate  # noqa: E402
from pala_quality_runner import EXECUTION_AUTHORITY  # noqa: E402
from pala_store import WorkflowStore  # noqa: E402


ROOT = SCRIPT_DIR.parent
FIXTURES = ROOT / "fixtures" / "product-flow"
PROJECT_ID = "water-tracker"
TASK_ID = "water-tracker-T-1"
SESSION_KEY = "m75-completion-session"
QUALITY_TICKET = "m75-completion"
CHECK_ID = "integration:m75-completion-pass"
DOCTOR_AUTHORITY = "pala-workbench-doctor"


def _fixture(name: str) -> dict[str, object]:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"fixture must be an object: {name}")
    return payload


class M75CompletionAuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="pala-m75-completion-")
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.project = base / "project"
        self.project.mkdir()
        subprocess.run(
            ["git", "init", "-q"], cwd=self.project, check=True, capture_output=True
        )
        self.environment = {
            **os.environ,
            "LOCALAPPDATA": str(base / "local-app-data"),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        }
        self.environment_patch = patch.dict(os.environ, self.environment, clear=True)
        self.environment_patch.start()
        self.addCleanup(self.environment_patch.stop)

        start_product(
            self.project,
            "Build a verified local decision log.",
            _fixture("water-tracker-plan.json"),
            _fixture("natro-capabilities.json"),
            _fixture("codex-candidate.json"),
            SESSION_KEY,
            observe_codex_host(
                available_tools=["apply_patch"],
                evidence_ref="test/observed-host-tools",
                max_concurrency=1,
            ).to_dict(),
            "a" * 64,
        )
        quality_contract = self.project / ".pala" / "quality.json"
        quality_contract.parent.mkdir(parents=True, exist_ok=True)
        quality_contract.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "checks": [
                        {
                            "id": "m75-completion-pass",
                            "kind": "integration",
                            "argv": [sys.executable, "-c", "raise SystemExit(0)"],
                            "tiers": ["ticket"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with redirect_stdout(StringIO()):
            initialized = quality_main(
                [
                    "init",
                    "--cwd",
                    str(self.project),
                    "--ticket",
                    QUALITY_TICKET,
                    "--tier",
                    "ticket",
                ]
            )
        self.assertEqual(initialized, 0)

    @staticmethod
    def requirement(
        capability: str,
        status: str,
        *,
        required: bool = True,
        authority: str = DOCTOR_AUTHORITY,
        evidence_refs: list[str] | None = None,
    ) -> dict[str, object]:
        return {
            "id": f"ENV-{capability.upper()}",
            "capability": capability,
            "status": status,
            "required": required,
            "authority": authority,
            "evidence_refs": list(evidence_refs or []),
        }

    def set_readiness(
        self,
        requirements: list[dict[str, object]],
        *,
        environment_status: str,
        authority: str = DOCTOR_AUTHORITY,
    ) -> None:
        record = load_project_contract(self.project, PROJECT_ID)
        record["environment_requirements"] = requirements
        record["environment_status"] = environment_status
        record["environment_readiness"] = {
            "status": environment_status,
            "authority": authority,
            "requirements": requirements,
        }
        save_project_contract(self.project, record)

    def complete(self) -> dict[str, object]:
        try:
            return complete_product(
                self.project,
                PROJECT_ID,
                SESSION_KEY,
                QUALITY_TICKET,
                CHECK_ID,
                5.0,
            )
        except ValueError as error:
            return {"status": "blocked", "error": str(error)}

    def assert_quality_really_passed(self) -> None:
        gate = quality_gate(self.project, QUALITY_TICKET)
        self.assertEqual(gate["status"], "passed", gate)
        check = next(item for item in gate["checks"] if item["id"] == CHECK_ID)
        self.assertEqual(check["exit_code"], 0)
        self.assertEqual(check["execution_authority"], EXECUTION_AUTHORITY)

    def assert_canonical_completion_refused(self, result: dict[str, object]) -> None:
        self.assert_quality_really_passed()
        self.assertNotEqual(result.get("status"), "package-ready", result)
        project = load_project_contract(self.project, PROJECT_ID)
        self.assertNotEqual(project["project_state"], "PACKAGE_READY", project)
        ticket = WorkflowStore(self.project)._read_ticket(TASK_ID)
        self.assertIsNotNone(ticket)
        self.assertNotEqual(ticket["task_contract"]["status"], "DONE", ticket)

    def test_a_quality_pass_with_required_semgrep_blocked_is_not_done(self) -> None:
        self.set_readiness(
            [self.requirement("security_static", "blocked")],
            environment_status="blocked",
        )

        self.assert_canonical_completion_refused(self.complete())

    def test_b_quality_pass_with_required_codegraph_absent_is_not_done(self) -> None:
        self.set_readiness(
            [self.requirement("code_intelligence", "absent")],
            environment_status="blocked",
        )

        self.assert_canonical_completion_refused(self.complete())

    def test_c_browser_acceptance_without_browser_evidence_is_not_done(self) -> None:
        record = load_project_contract(self.project, PROJECT_ID)
        record["acceptance_matrix"] = [
            {
                "id": "AC-BROWSER",
                "criterion": "browser journey is verified",
                "evidence": "browser",
                "required_capability": "browser_e2e",
            }
        ]
        record["live_verification"] = {"status": "not-run", "evidence_refs": []}
        save_project_contract(self.project, record)
        self.set_readiness(
            [self.requirement("browser_e2e", "passed", evidence_refs=[])],
            environment_status="passed",
        )

        self.assert_canonical_completion_refused(self.complete())

    def test_d_configured_not_verified_environment_cannot_be_package_ready(self) -> None:
        self.set_readiness(
            [self.requirement("web_runtime", "configured-not-verified")],
            environment_status="configured-not-verified",
        )

        self.assert_canonical_completion_refused(self.complete())

    def test_e_all_required_authoritative_capabilities_pass_allows_done(self) -> None:
        self.set_readiness(
            [
                self.requirement(
                    "code_intelligence", "passed", evidence_refs=["DOCTOR-codegraph"]
                ),
                self.requirement(
                    "security_static", "passed", evidence_refs=["DOCTOR-semgrep"]
                ),
            ],
            environment_status="passed",
        )

        result = self.complete()

        self.assert_quality_really_passed()
        self.assertEqual(result["status"], "package-ready", result)
        self.assertEqual(
            WorkflowStore(self.project)._read_ticket(TASK_ID)["task_contract"]["status"],
            "DONE",
        )

    def test_f_optional_serena_absence_does_not_block_done(self) -> None:
        self.set_readiness(
            [
                self.requirement(
                    "security_static", "passed", evidence_refs=["DOCTOR-semgrep"]
                ),
                self.requirement("symbol_precision", "absent", required=False),
            ],
            environment_status="passed",
        )

        self.assertEqual(self.complete()["status"], "package-ready")

    def test_g_optional_context7_absence_does_not_block_done(self) -> None:
        self.set_readiness(
            [
                self.requirement(
                    "code_intelligence", "passed", evidence_refs=["DOCTOR-codegraph"]
                ),
                self.requirement("current_docs", "absent", required=False),
            ],
            environment_status="passed",
        )

        self.assertEqual(self.complete()["status"], "package-ready")

    def test_h_caller_forged_capability_health_is_rejected(self) -> None:
        forged = [
            self.requirement(
                "security_static",
                "passed",
                authority="caller-supplied",
                evidence_refs=["FORGED-semgrep"],
            )
        ]
        self.set_readiness(
            forged,
            environment_status="passed",
            authority="caller-supplied",
        )

        self.assert_canonical_completion_refused(self.complete())

    def test_i_verified_task_can_complete_after_environment_repair(self) -> None:
        self.set_readiness(
            [self.requirement("code_intelligence", "absent")],
            environment_status="blocked",
        )
        first = self.complete()
        self.assert_canonical_completion_refused(first)
        self.assertEqual(
            WorkflowStore(self.project)._read_ticket(TASK_ID)["task_contract"]["status"],
            "VERIFIED",
        )

        self.set_readiness(
            [
                self.requirement(
                    "code_intelligence", "passed", evidence_refs=["DOCTOR-codegraph"]
                )
            ],
            environment_status="passed",
        )

        repaired = self.complete()

        self.assertEqual(repaired["status"], "package-ready", repaired)
        self.assertEqual(
            WorkflowStore(self.project)._read_ticket(TASK_ID)["task_contract"]["status"],
            "DONE",
        )


if __name__ == "__main__":
    unittest.main()

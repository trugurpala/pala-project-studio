from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_cold_packet import build_cold_packet
from pala_milestone_truth import canonical_milestone, current_milestones
from pala_owner_cockpit import render_control_center
from pala_release_truth import release_truth
from pala_workbench import (
    CAPABILITY_CATEGORIES,
    RUNTIME_STATES,
    CapabilityRuntimeState,
    default_registry,
)


class _CanonicalStore:
    def ticket_record(self, ticket: str) -> dict[str, object] | None:
        if ticket != "M70-T3":
            return None
        return {
            "ticket": ticket,
            "lifecycle": "completed",
            "task_contract": {
                "id": ticket,
                "status": "DONE",
                "acceptance": [{"id": "AC-01", "status": "passed"}],
            },
        }


class CapabilityRegistryTests(unittest.TestCase):
    def test_locked_registry_is_typed_advisory_and_has_no_retired_provider(self) -> None:
        registry = default_registry()
        self.assertEqual(
            set(registry.capability_ids()),
            {
                "code_intelligence",
                "security_static",
                "browser_exploration",
                "browser_e2e",
                "symbol_precision",
                "current_docs",
            },
        )
        self.assertEqual(
            set(registry.categories()),
            CAPABILITY_CATEGORIES,
        )
        for contract in registry.contracts:
            self.assertEqual(contract.authority, "advisory")
            self.assertTrue(contract.version)
            self.assertTrue(contract.official_source.startswith("https://"))
            self.assertTrue(contract.license)
            self.assertTrue(contract.integrity)
            self.assertTrue(contract.ownership)
            self.assertTrue(contract.fallback)
        self.assertTrue(registry.get("code_intelligence").required_for_core_health)
        self.assertTrue(registry.get("security_static").required_for_core_health)
        self.assertFalse(registry.get("current_docs").required_for_core_health)
        serialized = json.dumps(registry.to_dict(), sort_keys=True).casefold()
        for retired in (
            "graphify",
            "codebase-memory",
            "code-review-graph",
            "ollama",
            "qwen",
            "rtk",
            "playwright-mcp",
        ):
            self.assertNotIn(retired, serialized)

    def test_runtime_state_machine_is_truthful_and_core_health_ignores_optional(self) -> None:
        self.assertEqual(
            RUNTIME_STATES,
            {"absent", "exact", "old", "external", "foreign", "offline"},
        )
        registry = default_registry()
        runtime = {
            "code_intelligence": CapabilityRuntimeState.exact(
                "code_intelligence", "1.5.0", "official-release", "sha256:ok"
            ),
            "security_static": CapabilityRuntimeState.exact(
                "security_static", "1.172.0", "pypi", "sha256:ok"
            ),
            "current_docs": CapabilityRuntimeState(
                capability_id="current_docs",
                state="absent",
                version=None,
                provenance="not-installed",
                integrity="not-run",
                ownership="external",
                health="not-run",
                freshness="not-run",
                evidence_refs=(),
            ),
        }
        self.assertEqual(registry.core_health(runtime)["status"], "passed")
        stale = {**runtime, "code_intelligence": runtime["code_intelligence"].with_freshness("stale")}
        self.assertEqual(registry.core_health(stale)["status"], "blocked")


class HistoricalEvidenceHygieneTests(unittest.TestCase):
    def test_stale_closure_and_red_identity_cannot_override_canonical_truth(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "artifacts" / "install-field"
            evidence.mkdir(parents=True)
            (evidence / "m70-t3-closure.json").write_text(
                json.dumps({"status": "blocked", "canonical_done": False}), encoding="utf-8"
            )
            (evidence / "m70-t2-red.json").write_text(
                json.dumps({"target_version": "1.0.1", "status": "red"}), encoding="utf-8"
            )
            (root / "product-identity.json").write_text(
                json.dumps(
                    {
                        "product": "PALA",
                        "product_version": "1.0.0",
                        "plugin_version": "1.0.0",
                        "artifact_name": "pala-project-studio-1.0.0.zip",
                        "release_status": "PUBLIC RELEASED",
                        "remote_publish": "passed",
                        "last_published_version": "1.0.0",
                    }
                ),
                encoding="utf-8",
            )
            truth = canonical_milestone(root, "M70-T3", store=_CanonicalStore())
            release = release_truth(root)

        self.assertEqual(truth["status"], "passed")
        self.assertEqual(truth["task_status"], "DONE")
        self.assertEqual(truth["workflow_lifecycle"], "completed")
        self.assertEqual(truth["authority"], "WorkflowStore/TaskContract")
        self.assertEqual(release["product_version"], "1.0.0")
        self.assertNotEqual(release["product_version"], "1.0.1")

    def test_control_center_and_cold_packet_show_canonical_m70_completed(self) -> None:
        milestone = {
            "M70-T3": {
                "status": "passed",
                "task_status": "DONE",
                "workflow_lifecycle": "completed",
                "authority": "WorkflowStore/TaskContract",
            }
        }
        html = render_control_center(
            {
                "project": "PALA",
                "state": "IN_PROGRESS",
                "quality": "not-run",
                "blocker": "none",
                "next_action": "M71-T1",
                "owner_request": "Nothing",
                "milestones": milestone,
            }
        )
        self.assertIn("M70-T3", html)
        self.assertIn("DONE", html)
        with (
            patch("pala_cold_packet.current_milestones", return_value=milestone),
            tempfile.TemporaryDirectory() as temp,
        ):
            packet = build_cold_packet(Path(temp), profile="minimal", workflow={})
        self.assertEqual(packet["milestones"]["M70-T3"]["task_status"], "DONE")
        self.assertIn("M70-T3=DONE", packet["text"])
        status = (ROOT / "STATUS.md").read_text(encoding="utf-8")
        self.assertIn("canonical authority", status.casefold())
        self.assertNotIn("M70-T3", status)

    def test_current_milestones_uses_canonical_store_contract(self) -> None:
        milestones = current_milestones(Path("."), store=_CanonicalStore())
        self.assertEqual(milestones["M70-T3"]["task_status"], "DONE")


if __name__ == "__main__":
    unittest.main()

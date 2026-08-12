import json
import unittest

from pala_agent_provider import CodexProvider, ExecutionRequest, FakeProvider
from pala_capabilities import CapabilityProfile, choose_architecture
from pala_credentials import (
    CredentialRef,
    ExternalAction,
    FakeCredentialVault,
    OwnerAuthority,
    authorize_external_action,
)
from pala_delivery import FakeDeliveryAdapter, create_cpanel_plan, run_delivery
from pala_execution import ExecutionCoordinator
from pala_owner_cockpit import LiveVerification, render_owner_cockpit
from pala_product import PROJECT_STATES, ProductSpec, ProjectLifecycle
from pala_product_e2e import run_golden_scenarios
from pala_product_planner import validate_plan
from pala_task_packet import PACKET_BUDGETS, compile_task_packet


class ProductContractTests(unittest.TestCase):
    def make_spec(self) -> ProductSpec:
        return ProductSpec.from_dict(
            {
                "project_id": "water-tracker",
                "title": "Water Tracker",
                "goal": "Deliver a verified water tracking product",
                "user_outcome": "Users record and review water intake",
                "product_type": "web_application",
                "target_users": ["registered user"],
                "declared_facts": ["Natro", "cPanel", "Linux", "water tracking"],
                "unknowns": ["php", "mysql", "node", "python", "ssh", "sftp", "cron", "ssl"],
                "constraints": ["local-first delivery planning"],
                "non_goals": ["real remote deployment"],
                "environment_requirements": ["web runtime", "persistent store"],
                "architecture_decision_ref": "ADR-water-tracker",
                "acceptance": ["intake persists across login"],
                "milestones": ["plan", "build", "verify", "package"],
                "delivery_target": "generic-linux-cpanel",
                "project_status": "DISCOVERING",
            }
        )

    def test_product_spec_contains_every_locked_field(self) -> None:
        spec = self.make_spec()

        self.assertEqual(set(spec.to_dict()), ProductSpec.REQUIRED_FIELDS)
        self.assertEqual(spec.project_status, "DISCOVERING")

    def test_missing_or_blank_required_value_fails_closed(self) -> None:
        payload = self.make_spec().to_dict()
        payload["goal"] = ""

        with self.assertRaises(ValueError):
            ProductSpec.from_dict(payload)

    def test_project_lifecycle_is_explicit_and_independent_from_task_done(self) -> None:
        lifecycle = ProjectLifecycle("DISCOVERING")
        lifecycle.transition("PLANNED")
        lifecycle.observe_task_status("DONE")

        self.assertEqual(lifecycle.status, "PLANNED")
        self.assertEqual(
            PROJECT_STATES,
            {
                "DISCOVERING",
                "PLANNED",
                "BUILDING",
                "VERIFYING",
                "PACKAGE_READY",
                "AWAITING_DEPLOY_AUTH",
                "DEPLOYING",
                "LIVE_VERIFYING",
                "DELIVERED",
                "BLOCKED",
                "NEEDS_DECISION",
            },
        )

    def test_invalid_project_transition_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            ProjectLifecycle("DISCOVERING").transition("DELIVERED")


class ProductPlannerTests(ProductContractTests):
    def make_plan(self) -> dict[str, object]:
        return {
            "product_spec": self.make_spec().to_dict(),
            "acceptance_matrix": [
                {"id": "AC-01", "criterion": "intake persists", "evidence": "journey"}
            ],
            "environment_requirements": [
                {"id": "ENV-01", "capability": "web_runtime", "status": "UNKNOWN"}
            ],
            "milestone_graph": {
                "plan": {"dependencies": []},
                "build": {"dependencies": ["plan"]},
                "verify": {"dependencies": ["build"]},
            },
            "task_dag": {
                "T-1": {"goal": "plan", "status": "BACKLOG", "dependencies": []},
                "T-2": {"goal": "build", "status": "BACKLOG", "dependencies": ["T-1"]},
            },
        }

    def test_water_tracker_golden_plan_preserves_facts_and_unknowns(self) -> None:
        plan = validate_plan(self.make_plan())

        self.assertEqual(plan.status, "passed")
        self.assertEqual(
            plan.product_spec.declared_facts, ["Natro", "cPanel", "Linux", "water tracking"]
        )
        self.assertEqual(
            plan.product_spec.unknowns,
            ["php", "mysql", "node", "python", "ssh", "sftp", "cron", "ssl"],
        )
        self.assertEqual(len(plan.acceptance_matrix), 1)

    def test_missing_or_cyclic_dependencies_fail_closed(self) -> None:
        missing = self.make_plan()
        missing["task_dag"] = {"T-1": {"dependencies": ["T-X"]}}
        cyclic = self.make_plan()
        cyclic["milestone_graph"] = {
            "a": {"dependencies": ["b"]},
            "b": {"dependencies": ["a"]},
        }

        with self.assertRaises(ValueError):
            validate_plan(missing)
        with self.assertRaises(ValueError):
            validate_plan(cyclic)


class CapabilityArchitectureTests(unittest.TestCase):
    def test_profile_requires_observed_evidence_and_never_infers_from_provider(self) -> None:
        with self.assertRaises(ValueError):
            CapabilityProfile.from_dict(
                {
                    "provider": "cpanel",
                    "capabilities": {"php": {"status": "VERIFIED"}},
                }
            )

        profile = CapabilityProfile.from_dict(
            {
                "provider": "cpanel",
                "capabilities": {},
            }
        )
        self.assertEqual(profile.status_of("php"), "UNKNOWN")

    def test_unknown_requirement_requires_discovery(self) -> None:
        profile = CapabilityProfile.from_dict(
            {
                "provider": "generic",
                "capabilities": {
                    "linux": {
                        "source": "doctor",
                        "observed": "Linux",
                        "evidence": "EV-1",
                        "confidence": "observed",
                        "status": "VERIFIED",
                    },
                },
            }
        )

        decision = choose_architecture(
            {"php-sql": ["linux", "php", "mysql"]},
            ["linux", "php", "mysql"],
            profile,
        )

        self.assertEqual(decision.status, "discovery_required")
        self.assertIsNone(decision.selected)
        self.assertEqual(decision.unknown_dependencies, ["php", "mysql"])

    def test_verified_capabilities_select_and_explain_architecture(self) -> None:
        capabilities = {
            name: {
                "source": "fixture",
                "observed": name,
                "evidence": f"EV-{name}",
                "confidence": "observed",
                "status": "VERIFIED",
            }
            for name in ("linux", "php", "mysql")
        }
        decision = choose_architecture(
            {"php-sql": ["linux", "php", "mysql"], "node": ["node"]},
            ["linux", "php", "mysql"],
            CapabilityProfile.from_dict({"provider": "generic", "capabilities": capabilities}),
        )

        self.assertEqual(decision.status, "passed")
        self.assertEqual(decision.selected, "php-sql")
        self.assertIn("node", decision.rejected)
        self.assertEqual(len(decision.evidence_refs), 3)


class TaskPacketTests(unittest.TestCase):
    def task(self, status: str = "IN_PROGRESS") -> dict[str, object]:
        return {
            "id": "T-1",
            "status": status,
            "goal": "build water tracker",
            "acceptance": [{"id": "AC-1", "text": "persists", "status": "not-run"}],
            "dependencies": [],
            "architecture_refs": ["ADR-water"],
            "next_action": "implement persistence",
        }

    def test_profiles_are_bounded_and_keep_canonical_task_authority(self) -> None:
        for profile, budget in PACKET_BUDGETS.items():
            packet = compile_task_packet(
                self.task(),
                {"active_task": "T-1", "summary": "x" * 30_000},
                {"references": ["PROJECT.md", "ADR-water"]},
                {"active_task": "T-1", "next_action": "implement persistence"},
                profile,
            )
            self.assertIsNotNone(packet)
            self.assertEqual(packet.task_id, "T-1")
            self.assertLessEqual(packet.encoded_size(), budget)

    def test_done_work_is_excluded(self) -> None:
        self.assertIsNone(compile_task_packet(self.task("DONE"), {}, {}, {}, "minimal"))

    def test_conflicting_read_model_task_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            compile_task_packet(self.task(), {"active_task": "T-OTHER"}, {}, {}, "standard")


class AgentProviderTests(unittest.TestCase):
    def request(self) -> ExecutionRequest:
        return ExecutionRequest(
            request_id="REQ-1",
            task_id="T-1",
            packet={"authority": "TaskContract", "goal": "build"},
            requested_capabilities=["local_edit"],
        )

    def test_fake_provider_proves_core_is_provider_independent(self) -> None:
        provider = FakeProvider(capabilities={"local_edit"}, candidate={"files": ["app.py"]})
        result = provider.execute(self.request())

        self.assertEqual(result.status, "candidate")
        self.assertFalse(result.canonical_done)
        self.assertEqual(result.provider, "fake")

    def test_codex_provider_wraps_host_execution_as_candidate_only(self) -> None:
        provider = CodexProvider(lambda request: {"summary": request.task_id})
        result = provider.execute(self.request())

        self.assertEqual(result.candidate["summary"], "T-1")
        self.assertFalse(result.canonical_done)

    def test_missing_provider_capability_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            FakeProvider(capabilities=set(), candidate={}).execute(self.request())


class ExecutionOwnershipTests(unittest.TestCase):
    def test_duplicate_task_claim_and_overlapping_write_surface_fail_closed(self) -> None:
        coordinator = ExecutionCoordinator()
        coordinator.claim("T-1", "lease-a", ["app/model.py"], worktree="wt-a")

        with self.assertRaises(ValueError):
            coordinator.claim("T-1", "lease-b", ["app/model.py"], worktree="wt-b")
        with self.assertRaises(ValueError):
            coordinator.claim("T-2", "lease-b", ["app/model.py"], worktree="wt-b")

    def test_detached_head_is_valid_and_candidate_still_requires_quality(self) -> None:
        coordinator = ExecutionCoordinator()
        claim = coordinator.claim(
            "T-1", "lease-a", ["app/model.py"], worktree="detached-wt", detached_head=True
        )
        candidate = coordinator.submit_candidate("T-1", "lease-a", {"summary": "edited"})

        self.assertTrue(claim.detached_head)
        self.assertEqual(candidate["status"], "awaiting_quality")
        self.assertFalse(coordinator.quality_allows_completion("T-1", "blocked"))
        self.assertTrue(coordinator.quality_allows_completion("T-1", "passed"))


class CredentialAuthorityTests(unittest.TestCase):
    def test_canonical_reference_and_serialized_surfaces_never_contain_secret(self) -> None:
        secret = "top-secret-fixture"
        reference = CredentialRef("fake", "cpanel-owner", "delivery")
        vault = FakeCredentialVault({"cpanel-owner": secret})

        serialized = json.dumps(reference.to_dict())

        self.assertNotIn(secret, serialized)
        self.assertEqual(vault.resolve(reference), secret)
        self.assertNotIn(secret, json.dumps(vault.audit_events))

    def test_external_action_requires_exact_explicit_owner_authority(self) -> None:
        action = ExternalAction(
            "ACT-1", "remote_upload", CredentialRef("fake", "cpanel", "delivery")
        )

        self.assertFalse(authorize_external_action(action, None))
        self.assertFalse(authorize_external_action(action, OwnerAuthority("ACT-X", True)))
        self.assertTrue(authorize_external_action(action, OwnerAuthority("ACT-1", True)))

    def test_secret_shaped_reference_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            CredentialRef("fake", "password=secret", "delivery")


class DeliveryRuntimeTests(unittest.TestCase):
    def test_cpanel_plan_is_dry_run_with_complete_rollback_sequence(self) -> None:
        plan = create_cpanel_plan("dist/water.zip", {"linux": "VERIFIED", "cpanel": "VERIFIED"})

        self.assertTrue(plan.dry_run)
        self.assertEqual(
            plan.steps,
            ("backup", "package", "upload", "configure", "activate", "verify", "rollback"),
        )
        self.assertEqual(plan.transfer_mode, "manual")

    def test_dry_run_never_calls_adapter_and_mutation_needs_owner_authority(self) -> None:
        plan = create_cpanel_plan(
            "dist/water.zip",
            {"linux": "VERIFIED", "cpanel": "VERIFIED", "sftp": "VERIFIED"},
        )
        adapter = FakeDeliveryAdapter()

        dry = run_delivery(plan, adapter, mutate=False)
        denied = run_delivery(plan, adapter, mutate=True)

        self.assertEqual(dry["status"], "passed")
        self.assertEqual(denied["status"], "blocked")
        self.assertEqual(adapter.calls, [])

    def test_authorized_fake_delivery_runs_ordered_steps_only(self) -> None:
        plan = create_cpanel_plan(
            "dist/water.zip",
            {"linux": "VERIFIED", "cpanel": "VERIFIED", "sftp": "VERIFIED"},
        )
        adapter = FakeDeliveryAdapter()
        authority = OwnerAuthority(plan.action.action_id, True)

        result = run_delivery(plan, adapter, authority=authority, mutate=True)

        self.assertEqual(result["status"], "passed")
        self.assertEqual(adapter.calls, list(plan.steps))


class OwnerCockpitTests(unittest.TestCase):
    def test_deployed_and_live_verified_are_distinct_states(self) -> None:
        verification = LiveVerification("DEPLOYED", "not-run", [])

        self.assertFalse(verification.is_live_verified())
        self.assertTrue(verification.with_result("passed", ["EV-browser"]).is_live_verified())

    def test_owner_cockpit_has_required_plain_language_signals(self) -> None:
        html = render_owner_cockpit(
            {
                "project": "Water Tracker",
                "state": "LIVE_VERIFYING",
                "acceptance_verified": 6,
                "acceptance_total": 8,
                "quality": "passed",
                "environment": "configured-not-verified",
                "delivery": "not-run",
                "live_verification": "not-run",
                "blocker": "SSL unknown",
                "next_action": "Run local browser journey",
                "owner_request": "Confirm the cPanel PHP version.",
            }
        )

        for text in (
            "Water Tracker",
            "LIVE_VERIFYING",
            "6/8",
            "passed",
            "configured-not-verified",
            "not-run",
            "SSL unknown",
            "Run local browser journey",
            "Confirm the cPanel PHP version.",
        ):
            self.assertIn(text, html)
        self.assertNotIn("confidence", html.lower())


class GoldenProductE2ETests(unittest.TestCase):
    def test_scenarios_a_through_i_pass_without_remote_mutation(self) -> None:
        result = run_golden_scenarios()

        self.assertEqual(result["status"], "passed")
        self.assertEqual([row["id"] for row in result["rows"]], list("ABCDEFGHI"))
        self.assertTrue(all(row["status"] == "passed" for row in result["rows"]))
        self.assertEqual(result["remote_publish"], "not-run")
        self.assertEqual(result["real_remote_deploy"], "not-run")


if __name__ == "__main__":
    unittest.main()

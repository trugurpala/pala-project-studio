#!/usr/bin/env python3
"""M77 contracts for evidence-backed host routing and safe concurrency."""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_execution import ExecutionConflictError, ExecutionCoordinator  # noqa: E402
from pala_host_capability_broker import (  # noqa: E402
    HostCapabilityBroker,
    HostCapabilityError,
    HostCapabilitySnapshot,
    observe_codex_host,
)
from pala_subagent_contract import SubagentTaskContract  # noqa: E402


def contract(**changes: object) -> SubagentTaskContract:
    values: dict[str, object] = {
        "task_id": "M77-T1-child-01",
        "parent_task_id": "M77-T1",
        "task_contract_digest": "a" * 64,
        "context_receipt_id": "b" * 64,
        "repository_id": "c" * 24,
        "worktree_id": "d" * 24,
        "requested_capabilities": ["subagents"],
        "read_scope": ["AGENTS.md", "scripts"],
        "write_scope": ["scripts/pala_host_capability_broker.py"],
        "deny_scope": ["output", ".git"],
        "acceptance_ids": ["AC-01", "AC-03"],
        "verification_check_ids": ["unit:m77-host-broker"],
        "execution_mode": "writer",
        "integration_mode": "candidate-only",
    }
    values.update(changes)
    return SubagentTaskContract.create(**values)  # type: ignore[arg-type]


class HostCapabilitySnapshotTests(unittest.TestCase):

    def test_serialized_snapshot_must_revalidate_its_observed_digest(self) -> None:
        observed = observe_codex_host(
            available_tools=["apply_patch"],
            evidence_ref="host/current-tools",
            max_concurrency=2,
        )
        self.assertEqual(HostCapabilitySnapshot.from_dict(observed.to_dict()), observed)

        forged = observed.to_dict()
        forged["capabilities"][0]["status"] = "passed"  # type: ignore[index]
        with self.assertRaises(HostCapabilityError) as raised:
            HostCapabilitySnapshot.from_dict(forged)
        self.assertEqual(raised.exception.code, "SNAPSHOT_DIGEST_MISMATCH")

    def test_host_name_never_implies_subagent_capability(self) -> None:
        snapshot = observe_codex_host(
            available_tools=["spawn_agent"],
            evidence_ref="host/current-tools",
            max_concurrency=4,
        )

        self.assertEqual(snapshot.status_of("subagents"), "not-run")
        with self.assertRaises(HostCapabilityError) as raised:
            HostCapabilityBroker(snapshot).route(["subagents"])
        self.assertEqual(raised.exception.code, "CAPABILITY_UNVERIFIED")

    def test_exact_tool_inventory_produces_deterministic_immutable_snapshot(self) -> None:
        tools = ["wait_agent", "send_message", "spawn_agent", "apply_patch"]
        first = observe_codex_host(
            available_tools=tools,
            evidence_ref="host/current-tools",
            max_concurrency=4,
            git_worktree_supported=True,
        )
        second = observe_codex_host(
            available_tools=reversed(tools),
            evidence_ref="host/current-tools",
            max_concurrency=4,
            git_worktree_supported=True,
        )

        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.status_of("subagents"), "passed")
        self.assertEqual(first.status_of("isolated_worktree"), "passed")
        with self.assertRaises(FrozenInstanceError):
            first.max_concurrency = 9  # type: ignore[misc]

    def test_snapshot_rejects_private_evidence_and_invalid_concurrency(self) -> None:
        for evidence in (
            r"C:\Users\owner\tools.json",
            "Author" + "ization: " + "Bear" + "er top-secret-value",
            "user: copied transcript",
        ):
            with self.subTest(evidence=evidence):
                with self.assertRaises(HostCapabilityError) as raised:
                    observe_codex_host(
                        available_tools=[], evidence_ref=evidence, max_concurrency=2
                    )
                self.assertEqual(raised.exception.code, "PRIVATE_DATA_REJECTED")
        for value in (False, 0, 65):
            with self.subTest(value=value), self.assertRaises(HostCapabilityError):
                observe_codex_host(
                    available_tools=[],
                    evidence_ref="host/current-tools",
                    max_concurrency=value,  # type: ignore[arg-type]
                )
        with self.assertRaises(HostCapabilityError) as invalid:
            observe_codex_host(
                available_tools=["apply_patch", 3],  # type: ignore[list-item]
                evidence_ref="host/current-tools",
                max_concurrency=2,
            )
        self.assertEqual(invalid.exception.code, "PRIVATE_DATA_REJECTED")


class HostCapabilityBrokerTests(unittest.TestCase):
    def test_verified_fallback_is_explicit_and_never_completion_authority(self) -> None:
        snapshot = observe_codex_host(
            available_tools=["apply_patch"],
            evidence_ref="host/current-tools",
            max_concurrency=2,
        )

        decision = HostCapabilityBroker(snapshot).route(
            ["subagents"], fallback_capabilities=["local_edit"]
        )

        self.assertEqual(decision.status, "fallback")
        self.assertEqual(decision.selected_capability, "local_edit")
        self.assertIn("CAPABILITY_FALLBACK", decision.finding_codes)
        self.assertFalse(decision.can_complete)
        self.assertEqual(decision.authority, "HostCapabilityBroker/read-only")

    def test_unsupported_and_unverified_are_distinct_sanitized_errors(self) -> None:
        snapshot = observe_codex_host(
            available_tools=[], evidence_ref="host/current-tools", max_concurrency=1
        )
        broker = HostCapabilityBroker(snapshot)

        with self.assertRaises(HostCapabilityError) as unsupported:
            broker.route(["quantum-build"])
        self.assertEqual(unsupported.exception.code, "CAPABILITY_UNSUPPORTED")
        self.assertNotIn("quantum-build", str(unsupported.exception))

        with self.assertRaises(HostCapabilityError) as unverified:
            broker.route(["subagents"])
        self.assertEqual(unverified.exception.code, "CAPABILITY_UNVERIFIED")

    def test_contract_must_match_live_repository_and_worktree(self) -> None:
        snapshot = observe_codex_host(
            available_tools=["spawn_agent", "send_message", "wait_agent"],
            evidence_ref="host/current-tools",
            max_concurrency=4,
        )
        broker = HostCapabilityBroker(snapshot)

        with self.assertRaises(HostCapabilityError) as repository:
            broker.reserve(
                contract(),
                capability="subagents",
                live_repository_id="e" * 24,
                live_worktree_id="d" * 24,
                expected_context_receipt_id="b" * 64,
                parent_write_scope=["scripts"],
            )
        self.assertEqual(repository.exception.code, "REPOSITORY_MISMATCH")
        with self.assertRaises(HostCapabilityError) as worktree:
            broker.reserve(
                contract(),
                capability="subagents",
                live_repository_id="c" * 24,
                live_worktree_id="e" * 24,
                expected_context_receipt_id="b" * 64,
                parent_write_scope=["scripts"],
            )
        self.assertEqual(worktree.exception.code, "WORKTREE_MISMATCH")

    def test_live_receipt_parent_scope_and_release_use_one_coordinator(self) -> None:
        snapshot = observe_codex_host(
            available_tools=["spawn_agent", "send_message", "wait_agent"],
            evidence_ref="host/current-tools",
            max_concurrency=1,
        )
        broker = HostCapabilityBroker(snapshot)
        delegated = contract()
        common = {
            "capability": "subagents",
            "live_repository_id": "c" * 24,
            "live_worktree_id": "d" * 24,
            "parent_write_scope": ["scripts"],
        }
        with self.assertRaises(HostCapabilityError) as receipt:
            broker.reserve(
                delegated,
                expected_context_receipt_id="e" * 64,
                **common,  # type: ignore[arg-type]
            )
        self.assertEqual(receipt.exception.code, "CONTEXT_RECEIPT_MISMATCH")
        with self.assertRaises(HostCapabilityError) as parent:
            broker.reserve(
                delegated,
                expected_context_receipt_id="b" * 64,
                **{**common, "parent_write_scope": ["docs"]},  # type: ignore[arg-type]
            )
        self.assertEqual(parent.exception.code, "PARENT_SCOPE_ESCAPE")
        with self.assertRaises(HostCapabilityError) as broader:
            broker.reserve(
                contract(write_scope=["scripts"]),
                expected_context_receipt_id="b" * 64,
                **{**common, "parent_write_scope": ["scripts/one.py"]},  # type: ignore[arg-type]
            )
        self.assertEqual(broader.exception.code, "PARENT_SCOPE_ESCAPE")

        decision = broker.reserve(
            delegated,
            expected_context_receipt_id="b" * 64,
            **common,  # type: ignore[arg-type]
        )
        self.assertEqual(decision.status, "selected")
        broker.release(delegated)

    def test_reserved_subagent_result_is_primary_review_candidate_only(self) -> None:
        snapshot = observe_codex_host(
            available_tools=["spawn_agent", "send_message", "wait_agent"],
            evidence_ref="host/current-tools",
            max_concurrency=1,
        )
        delegated = contract()
        broker = HostCapabilityBroker(snapshot)
        broker.reserve(
            delegated,
            capability="subagents",
            live_repository_id="c" * 24,
            live_worktree_id="d" * 24,
            expected_context_receipt_id="b" * 64,
            parent_write_scope=["scripts"],
        )

        result = broker.submit_candidate(
            delegated,
            {"summary": "candidate prepared"},
            changed_paths=["scripts/pala_host_capability_broker.py"],
        )

        self.assertEqual(result["status"], "awaiting_primary_review")
        self.assertFalse(result["can_complete"])
        self.assertNotIn("candidate", result)
        with self.assertRaises(HostCapabilityError) as forged:
            broker.submit_candidate(
                delegated,
                {"canonical_done": True},
                changed_paths=["scripts/pala_host_capability_broker.py"],
            )
        self.assertEqual(forged.exception.code, "CANDIDATE_AUTHORITY_REJECTED")


class ExecutionCoordinatorContractTests(unittest.TestCase):
    def test_windows_casefold_overlap_and_capacity_fail_closed_with_codes(self) -> None:
        coordinator = ExecutionCoordinator(max_concurrency=2, case_sensitive=False)
        coordinator.claim("T-1", "lease-a", ["Scripts/Owner.py"], worktree="wt-a")

        with self.assertRaises(ExecutionConflictError) as conflict:
            coordinator.claim("T-2", "lease-b", ["scripts/owner.py"], worktree="wt-b")
        self.assertEqual(conflict.exception.code, "WRITE_SURFACE_CONFLICT")

        coordinator.claim("T-2", "lease-b", ["docs/readme.md"], worktree="wt-b")
        with self.assertRaises(ExecutionConflictError) as capacity:
            coordinator.claim("T-3", "lease-c", ["tests/test_one.py"], worktree="wt-c")
        self.assertEqual(capacity.exception.code, "CONCURRENCY_LIMIT")

    def test_release_allows_new_claim_and_candidates_never_complete_directly(self) -> None:
        coordinator = ExecutionCoordinator(max_concurrency=1)
        coordinator.claim("T-1", "lease-a", ["app/a.py"])
        candidate = coordinator.submit_candidate("T-1", "lease-a", {"digest": "f" * 64})
        self.assertFalse(candidate["can_complete"])
        coordinator.release("T-1", "lease-a")
        claim = coordinator.claim("T-2", "lease-b", ["app/b.py"])
        self.assertEqual(claim.task_id, "T-2")

    def test_same_holder_reclaim_cannot_expand_its_surface(self) -> None:
        coordinator = ExecutionCoordinator(max_concurrency=2)
        coordinator.claim("T-1", "lease-a", ["app/a.py"])
        with self.assertRaises(ExecutionConflictError) as raised:
            coordinator.claim("T-1", "lease-a", ["app"])
        self.assertEqual(raised.exception.code, "CLAIM_MUTATION_BLOCKED")


class DelegationContractTests(unittest.TestCase):
    def test_contract_is_deeply_immutable_deterministic_and_candidate_only(self) -> None:
        first = contract()
        second = contract(
            requested_capabilities=["subagents"],
            read_scope=["scripts", "AGENTS.md"],
            acceptance_ids=["AC-03", "AC-01"],
        )

        self.assertEqual(first.delegation_id, second.delegation_id)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertFalse(first.can_complete)
        with self.assertRaises(AttributeError):
            first.write_scope.append("PROJECT.md")  # type: ignore[attr-defined]
        self.assertNotIn(str(SCRIPTS.parent), json.dumps(first.to_dict()))

    def test_contract_rejects_scope_escape_private_data_and_unknown_fields(self) -> None:
        for changes in (
            {"write_scope": ["../outside.py"]},
            {"read_scope": [r"C:\Users\owner\project"]},
            {"deny_scope": ["scripts/pala_host_capability_broker.py"]},
            {"verification_check_ids": ["token=top-secret-value"]},
            {"write_scope": [".env"]},
            {"integration_mode": "merge-and-complete"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                contract(**changes)

        payload = contract().to_dict()
        payload["raw_prompt"] = "do work"
        with self.assertRaises(ValueError):
            SubagentTaskContract.from_dict(payload)

    def test_read_only_contract_and_candidate_scope_are_enforced(self) -> None:
        readonly = contract(execution_mode="read-only", write_scope=[])
        self.assertEqual(readonly.validate_candidate([])["status"], "awaiting_primary_review")
        with self.assertRaises(ValueError):
            readonly.validate_candidate(["scripts/change.py"])
        with self.assertRaises(ValueError):
            contract().validate_candidate(["PROJECT.md"])
        with self.assertRaises(ValueError):
            contract().validate_candidate(["scripts"])


if __name__ == "__main__":
    unittest.main()

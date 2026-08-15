#!/usr/bin/env python3
"""Contract tests for snapshot-bound, privacy-safe Context Receipt v1."""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pala_cold_packet  # noqa: E402
from pala_context_receipt import (  # noqa: E402
    CONTEXT_RECEIPT_SCHEMA,
    EVIDENCE_STATUSES,
    ContextExpectation,
    ContextReceipt,
    ContextReceiptError,
)
from pala_project_snapshot import ProjectSnapshot  # noqa: E402
from pala_state_core import context_receipt_read_model  # noqa: E402

ROOT = SCRIPTS.parent


def snapshot(**changes: object) -> ProjectSnapshot:
    values: dict[str, object] = {
        "repository_id": "a" * 24,
        "worktree_id": "b" * 24,
        "head": "c" * 40,
        "head_state": "attached",
        "branch": "main",
        "git_state": "dirty",
        "changed_count": 2,
        "changed_digest": "d" * 64,
        "linked_worktree_count": 1,
        "remote": "https://example.test/project.git",
    }
    values.update(changes)
    return ProjectSnapshot(**values)  # type: ignore[arg-type]


def receipt(**changes: object) -> ContextReceipt:
    values: dict[str, object] = {
        "snapshot": snapshot(),
        "active_task": {
            "ticket": "M76-T3",
            "status": "IN_PROGRESS",
            "contract_digest": "e" * 64,
        },
        "profile_digest": "f" * 64,
        "source_refs": [
            {"path": "PLAN.md", "digest": "1" * 64},
            {"path": "STATUS.md", "digest": "2" * 64},
        ],
        "capabilities": [
            {
                "name": "python",
                "status": "passed",
                "evidence_ref": "quality/python",
            },
            {
                "name": "network",
                "status": "configured-not-verified",
                "evidence_ref": "doctor/network",
            },
        ],
        "verifications": [
            {
                "check_id": "unit:m76-context-receipt",
                "status": "passed",
                "exit_code": 0,
                "evidence_ref": "quality/m76-context-receipt",
            },
            {
                "check_id": "lint:m76-context-receipt",
                "status": "not-run",
                "exit_code": None,
                "evidence_ref": None,
            },
        ],
        "risk_codes": ["history-not-run", "profile-store-not-run"],
        "next_action": "implement-context-receipt",
    }
    values.update(changes)
    return ContextReceipt.create(**values)  # type: ignore[arg-type]


def expectation(**changes: object) -> ContextExpectation:
    values: dict[str, object] = {
        "snapshot": snapshot(),
        "active_task": {
            "ticket": "M76-T3",
            "status": "IN_PROGRESS",
            "contract_digest": "e" * 64,
        },
        "profile_digest": "f" * 64,
        "source_refs": [
            {"path": "PLAN.md", "digest": "1" * 64},
            {"path": "STATUS.md", "digest": "2" * 64},
        ],
    }
    values.update(changes)
    return ContextExpectation.create(**values)  # type: ignore[arg-type]


class ContextReceiptContractTests(unittest.TestCase):
    def assert_receipt_error(
        self,
        payload: dict[str, object],
        code: str,
        field: str,
        *,
        expected_snapshot: ProjectSnapshot | None = None,
    ) -> ContextReceiptError:
        with self.assertRaises(ContextReceiptError) as caught:
            ContextReceipt.from_dict(payload, expected_snapshot=expected_snapshot)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.field, field)
        return caught.exception

    def test_round_trip_is_immutable_deterministic_and_snapshot_bound(self) -> None:
        first = receipt()
        restored = ContextReceipt.from_dict(
            first.to_dict(), expected=expectation()
        )
        reordered = ContextReceipt.create(
            snapshot=snapshot(),
            active_task={
                "status": "IN_PROGRESS",
                "contract_digest": "e" * 64,
                "ticket": "M76-T3",
            },
            profile_digest="f" * 64,
            source_refs=list(reversed(first.to_dict()["source_refs"])),
            capabilities=list(reversed(first.to_dict()["capabilities"])),
            verifications=list(reversed(first.to_dict()["verifications"])),
            risk_codes=list(reversed(first.to_dict()["risk_codes"])),
            next_action="implement-context-receipt",
        )

        self.assertEqual(restored, first)
        self.assertEqual(reordered.to_json(), first.to_json())
        self.assertEqual(reordered.receipt_id, first.receipt_id)
        self.assertEqual(first.schema_version, CONTEXT_RECEIPT_SCHEMA)
        self.assertIsInstance(first.source_refs, tuple)
        self.assertIsInstance(first.active_task.contract_digest, str)
        self.assertLessEqual(len(first.to_json().encode("utf-8")), 16_384)
        with self.assertRaises(FrozenInstanceError):
            first.next_action = "mutated"  # type: ignore[misc]
        with self.assertRaises(FrozenInstanceError):
            first.source_refs[0].path = "mutated"  # type: ignore[misc]

    def test_snapshot_head_worktree_and_changed_digest_mismatch_fail_closed(self) -> None:
        payload = receipt().to_dict()
        mismatches = (
            (replace(snapshot(), head="9" * 40), "project.head"),
            (replace(snapshot(), worktree_id="8" * 24), "project.worktree_id"),
            (
                replace(snapshot(), changed_digest="7" * 64),
                "project.changed_digest",
            ),
        )
        for expected, field in mismatches:
            with self.subTest(field=field):
                self.assert_receipt_error(
                    payload,
                    "CONTEXT_RECEIPT_SNAPSHOT_MISMATCH",
                    field,
                    expected_snapshot=expected,
                )

    def test_profile_task_and_source_expectation_mismatch_fail_closed(self) -> None:
        payload = receipt().to_dict()
        mismatches = (
            (
                expectation(profile_digest="9" * 64),
                "profile_digest",
            ),
            (
                expectation(
                    active_task={
                        "ticket": "M76-T3",
                        "status": "IN_PROGRESS",
                        "contract_digest": "8" * 64,
                    }
                ),
                "active_task.contract_digest",
            ),
            (
                expectation(
                    source_refs=[
                        {"path": "PLAN.md", "digest": "7" * 64},
                        {"path": "STATUS.md", "digest": "2" * 64},
                    ]
                ),
                "source_refs",
            ),
        )
        for expected, field in mismatches:
            with self.subTest(field=field):
                with self.assertRaises(ContextReceiptError) as caught:
                    ContextReceipt.from_dict(payload, expected=expected)
                self.assertEqual(
                    caught.exception.code, "CONTEXT_RECEIPT_CONTEXT_MISMATCH"
                )
                self.assertEqual(caught.exception.field, field)

    def test_missing_unknown_type_digest_and_completion_fields_fail_closed(self) -> None:
        missing = receipt().to_dict()
        missing.pop("active_task")
        self.assert_receipt_error(
            missing, "CONTEXT_RECEIPT_FIELD_MISSING", "active_task"
        )

        unknown = receipt().to_dict()
        unknown["chat_transcript"] = "not-authorized"
        self.assert_receipt_error(
            unknown, "CONTEXT_RECEIPT_FIELD_UNKNOWN", "chat_transcript"
        )

        malformed = receipt().to_dict()
        malformed["source_refs"] = "STATUS.md"
        self.assert_receipt_error(
            malformed, "CONTEXT_RECEIPT_TYPE_INVALID", "source_refs"
        )

        bad_digest = receipt().to_dict()
        bad_digest["receipt_id"] = "0" * 64
        self.assert_receipt_error(
            bad_digest, "CONTEXT_RECEIPT_DIGEST_MISMATCH", "receipt_id"
        )

        completion = receipt().to_dict()
        completion["complete"] = True
        self.assert_receipt_error(
            completion, "CONTEXT_RECEIPT_FIELD_UNKNOWN", "complete"
        )

    def test_private_secret_absolute_path_and_transcript_shapes_never_echo(self) -> None:
        mutations = (
            ("next_action", "token=super-private-fixture", "next_action"),
            ("next_action", "owner@example.test", "next_action"),
            ("next_action", r"C:\\Users\\Private\\project", "next_action"),
            ("next_action", "user: hello\nassistant: secret", "next_action"),
        )
        for key, value, field in mutations:
            with self.subTest(value=value):
                payload = receipt().to_dict()
                payload[key] = value
                error = self.assert_receipt_error(
                    payload, "CONTEXT_RECEIPT_PRIVATE_DATA_REJECTED", field
                )
                finding = json.dumps(error.finding(), sort_keys=True)
                self.assertNotIn(value, finding)
                self.assertNotIn("super-private-fixture", str(error))

        absolute = receipt().to_dict()
        absolute["source_refs"][0]["path"] = r"C:\\Users\\Private\\STATUS.md"
        self.assert_receipt_error(
            absolute,
            "CONTEXT_RECEIPT_SOURCE_REF_INVALID",
            "source_refs[0].path",
        )

    def test_relative_source_refs_and_collections_are_canonical_and_bounded(self) -> None:
        canonical = receipt(
            source_refs=[
                {"path": "scripts\\tool.py", "digest": "4" * 64},
                {"path": "STATUS.md", "digest": "2" * 64},
                {"path": "STATUS.md", "digest": "2" * 64},
            ]
        )
        self.assertEqual(
            tuple(item.path for item in canonical.source_refs),
            ("scripts/tool.py", "STATUS.md"),
        )

        with self.assertRaises(ContextReceiptError) as caught:
            receipt(
                source_refs=[
                    {"path": f"file-{index}.txt", "digest": "5" * 64}
                    for index in range(33)
                ]
            )
        self.assertEqual(caught.exception.code, "CONTEXT_RECEIPT_LIMIT_EXCEEDED")

        traversal = receipt().to_dict()
        traversal["source_refs"][0]["path"] = "../STATUS.md"
        self.assert_receipt_error(
            traversal,
            "CONTEXT_RECEIPT_SOURCE_REF_INVALID",
            "source_refs[0].path",
        )

        conflict = receipt().to_dict()
        conflict["source_refs"].append(
            {"path": "status.md", "digest": "9" * 64}
        )
        self.assert_receipt_error(
            conflict,
            "CONTEXT_RECEIPT_SOURCE_REF_INVALID",
            "source_refs",
        )

    def test_verification_status_and_exit_evidence_rules_are_fail_closed(self) -> None:
        self.assertEqual(
            EVIDENCE_STATUSES,
            ("blocked", "configured-not-verified", "not-run", "passed"),
        )
        invalid = (
            (
                {
                    "check_id": "unit:x",
                    "status": "passed",
                    "exit_code": 1,
                    "evidence_ref": "quality/x",
                },
                "exit_code",
            ),
            (
                {
                    "check_id": "unit:x",
                    "status": "passed",
                    "exit_code": 0,
                    "evidence_ref": None,
                },
                "evidence_ref",
            ),
            (
                {
                    "check_id": "unit:x",
                    "status": "success",
                    "exit_code": 0,
                    "evidence_ref": "quality/x",
                },
                "status",
            ),
            (
                {
                    "check_id": "unit:x",
                    "status": "not-run",
                    "exit_code": 0,
                    "evidence_ref": None,
                },
                "exit_code",
            ),
        )
        for verification, suffix in invalid:
            with self.subTest(verification=verification):
                payload = receipt().to_dict()
                payload["verifications"] = [verification]
                self.assert_receipt_error(
                    payload,
                    "CONTEXT_RECEIPT_EVIDENCE_INVALID",
                    f"verifications[0].{suffix}",
                )

    def test_state_and_cold_packet_adapters_expose_only_safe_read_model(self) -> None:
        current = receipt()
        report = context_receipt_read_model(
            current.to_dict(), expected=expectation()
        )
        git = {
            "branch": "main",
            "worktree": str(ROOT),
            "base_commit": "c" * 40,
            "changed_files": [],
            "freshness": "live",
        }
        workflow = {
            "active_ticket": "M76-T3",
            "goal": "Context Receipt",
            "next_action": "implement-context-receipt",
            "verification_tier": "not-run",
        }
        with patch.object(pala_cold_packet, "git_surface", return_value=git):
            packet = pala_cold_packet.build_cold_packet(
                ROOT,
                workflow=workflow,
                context_receipt=current.to_dict(),
                context_expectation=expectation(),
            )

        for value in (report, packet["context_receipt"]):
            serialized = json.dumps(value, sort_keys=True)
            self.assertEqual(value["receipt_id"], current.receipt_id)
            self.assertEqual(value["validation_status"], "passed")
            self.assertFalse(value["can_complete"])
            self.assertNotIn(str(ROOT), serialized)
            self.assertNotIn("source_refs", serialized)
            self.assertLessEqual(len(serialized.encode("utf-8")), 2_048)
        self.assertLessEqual(packet["bytes"], pala_cold_packet.MINIMAL_MAX_BYTES)
        receipt_records = [
            item
            for item in packet["context_records"]
            if item.get("scope") == "context_receipt"
        ]
        self.assertEqual(len(receipt_records), 1)
        self.assertTrue(receipt_records[0]["protected"])

        without_expectation = context_receipt_read_model(current.to_dict())
        self.assertEqual(without_expectation["validation_status"], "blocked")
        self.assertEqual(
            without_expectation["finding"]["code"],
            "CONTEXT_RECEIPT_EXPECTATION_REQUIRED",
        )

        unknown_snapshot = snapshot(
            git_state="unknown",
            changed_count=None,
            changed_digest=None,
        )
        unknown_receipt = receipt(snapshot=unknown_snapshot)
        unknown_report = context_receipt_read_model(
            unknown_receipt.to_dict(),
            expected=expectation(snapshot=unknown_snapshot),
        )
        self.assertEqual(unknown_report["validation_status"], "blocked")
        self.assertEqual(
            unknown_report["finding"]["code"],
            "CONTEXT_RECEIPT_SNAPSHOT_UNVERIFIABLE",
        )


if __name__ == "__main__":
    unittest.main()

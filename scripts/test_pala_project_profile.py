#!/usr/bin/env python3
"""Contract tests for the professional, secrets-free ProjectProfile v1."""

from __future__ import annotations

import json
import sys
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_project_profile import (  # noqa: E402
    PROFILE_KINDS,
    PROJECT_PROFILE_SCHEMA,
    ProjectProfile,
    ProjectProfileError,
)
from pala_state_documents import (  # noqa: E402
    discover,
    professional_project_profile_report,
)

ROOT = SCRIPTS.parent


def profile_payload(kind: str = "standard") -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": PROJECT_PROFILE_SCHEMA,
        "project_id": "pala-project-studio",
        "display_name": "Pala Project Studio",
        "profile_kind": kind,
        "data_classification": "internal",
        "scope": {
            "summary": "Local software delivery operating system",
            "in_scope": ["local-delivery", "quality-evidence"],
            "out_of_scope": ["automatic-publication"],
            "trust_boundaries": ["explicit-external-actions", "local-machine"],
        },
        "stack": {
            "languages": ["python"],
            "frameworks": [],
            "package_managers": ["uv", "npm"],
            "runtimes": ["cpython-3.13", "node-22"],
        },
        "risk": {
            "level": "medium",
            "categories": ["code-execution", "supply-chain"],
        },
        "quality": {
            "minimum_tier": "ticket",
            "required_check_ids": ["unit:m76-project-profile"],
            "completion_authority": "pala-quality-engine",
        },
        "release": {
            "target": "local-only",
            "required_gates": ["security"],
            "publication_authority": "explicit-owner-approval",
            "sbom_required": False,
            "rollback_required": True,
        },
        "ownership": {
            "product_owner_role": "product-owner",
            "engineering_owner_role": "maintainer",
            "security_owner_role": "security-reviewer",
            "data_owner_role": "product-owner",
        },
        "security": {
            "secret_handling": "external-references-only",
            "network_policy": "approved-external",
            "pii_policy": "prohibited",
            "review_required": True,
        },
    }
    if kind == "confidential":
        payload["data_classification"] = "confidential"
        payload["release"] = {
            **dict(payload["release"]),
            "target": "private-artifact",
        }
    elif kind == "regulated":
        payload["data_classification"] = "restricted"
        payload["quality"] = {
            **dict(payload["quality"]),
            "minimum_tier": "release",
        }
        payload["release"] = {
            **dict(payload["release"]),
            "target": "private-artifact",
            "required_gates": ["dependency", "package", "security"],
            "sbom_required": True,
        }
    elif kind == "public-release":
        payload["data_classification"] = "public"
        payload["quality"] = {
            **dict(payload["quality"]),
            "minimum_tier": "release",
        }
        payload["risk"] = {
            "level": "high",
            "categories": ["publication", "supply-chain"],
        }
        payload["release"] = {
            **dict(payload["release"]),
            "target": "public-artifact",
            "required_gates": ["dependency", "package", "security"],
            "sbom_required": True,
        }
    return payload


class ProjectProfileContractTests(unittest.TestCase):
    def assert_profile_error(
        self,
        payload: dict[str, object],
        code: str,
        field: str,
    ) -> ProjectProfileError:
        with self.assertRaises(ProjectProfileError) as caught:
            ProjectProfile.from_dict(payload)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.field, field)
        return caught.exception

    def test_all_profile_kinds_cover_professional_contract_and_round_trip(self) -> None:
        self.assertEqual(
            PROFILE_KINDS,
            ("confidential", "public-release", "regulated", "standard"),
        )
        for kind in PROFILE_KINDS:
            with self.subTest(kind=kind):
                profile = ProjectProfile.from_dict(profile_payload(kind))
                restored = ProjectProfile.from_dict(profile.to_dict())

                self.assertEqual(restored, profile)
                self.assertEqual(profile.profile_kind.value, kind)
                self.assertTrue(profile.scope.in_scope)
                self.assertTrue(profile.stack.languages)
                self.assertTrue(profile.risk.categories)
                self.assertTrue(profile.quality.required_check_ids)
                self.assertTrue(profile.release.required_gates)
                self.assertEqual(profile.security.secret_handling, "external-references-only")
                self.assertEqual(profile.ownership.product_owner_role, "product-owner")

    def test_semantic_input_order_has_stable_json_and_digest(self) -> None:
        first = profile_payload()
        second = dict(reversed(list(profile_payload().items())))
        second_scope = dict(second["scope"])
        second_scope["in_scope"] = list(reversed(second_scope["in_scope"]))
        second_scope["trust_boundaries"] = list(
            reversed(second_scope["trust_boundaries"])
        )
        second["scope"] = second_scope

        left = ProjectProfile.from_dict(first)
        right = ProjectProfile.from_dict(second)

        self.assertEqual(left.to_json(), right.to_json())
        self.assertEqual(left.digest(), right.digest())
        self.assertLessEqual(len(left.to_json().encode("utf-8")), 16_384)

    def test_profile_and_nested_collections_are_immutable(self) -> None:
        profile = ProjectProfile.from_dict(profile_payload())

        self.assertIsInstance(profile.scope.in_scope, tuple)
        self.assertIsInstance(profile.risk.categories, tuple)
        with self.assertRaises(FrozenInstanceError):
            profile.display_name = "mutated"  # type: ignore[misc]

    def test_missing_unknown_type_and_enum_values_fail_closed(self) -> None:
        missing = profile_payload()
        missing.pop("display_name")
        self.assert_profile_error(
            missing, "PROFILE_FIELD_MISSING", "display_name"
        )

        unknown = profile_payload()
        unknown["future_field"] = True
        self.assert_profile_error(
            unknown, "PROFILE_FIELD_UNKNOWN", "future_field"
        )

        bad_enum = profile_payload()
        bad_enum["profile_kind"] = "enterprise-plus"
        self.assert_profile_error(
            bad_enum, "PROFILE_VALUE_UNKNOWN", "profile_kind"
        )

        bad_type = profile_payload()
        bad_type["stack"] = {**dict(bad_type["stack"]), "languages": "python"}
        self.assert_profile_error(
            bad_type, "PROFILE_TYPE_INVALID", "stack.languages"
        )

    def test_secret_personal_identifier_and_private_path_never_echo(self) -> None:
        rejected = (
            ("password=super-sensitive-fixture", "PROFILE_PRIVATE_DATA_REJECTED"),
            ("owner@example.test", "PROFILE_PRIVATE_DATA_REJECTED"),
            (r"C:\Users\Private\project", "PROFILE_PRIVATE_DATA_REJECTED"),
            (r"path=C:\Users\Private\project", "PROFILE_PRIVATE_DATA_REJECTED"),
            ("https://owner:secret@example.test/repo", "PROFILE_PRIVATE_DATA_REJECTED"),
            ("user: request\nassistant: response", "PROFILE_PRIVATE_DATA_REJECTED"),
        )
        for value, code in rejected:
            with self.subTest(value=value):
                payload = profile_payload()
                payload["scope"] = {**dict(payload["scope"]), "summary": value}
                error = self.assert_profile_error(payload, code, "scope.summary")
                serialized = json.dumps(error.finding(), sort_keys=True)
                self.assertNotIn(value, serialized)
                self.assertNotIn("super-sensitive-fixture", str(error))

    def test_security_and_release_mode_policies_fail_closed(self) -> None:
        public_private_data = profile_payload("public-release")
        public_private_data["data_classification"] = "internal"
        self.assert_profile_error(
            public_private_data,
            "PROFILE_POLICY_VIOLATION",
            "data_classification",
        )

        confidential_publication = profile_payload("confidential")
        confidential_publication["release"] = {
            **dict(confidential_publication["release"]),
            "target": "public-artifact",
        }
        self.assert_profile_error(
            confidential_publication,
            "PROFILE_POLICY_VIOLATION",
            "release.target",
        )

        regulated_without_sbom = profile_payload("regulated")
        regulated_without_sbom["release"] = {
            **dict(regulated_without_sbom["release"]),
            "sbom_required": False,
        }
        self.assert_profile_error(
            regulated_without_sbom,
            "PROFILE_POLICY_VIOLATION",
            "release.sbom_required",
        )

        high_risk_without_review = profile_payload("public-release")
        high_risk_without_review["security"] = {
            **dict(high_risk_without_review["security"]),
            "review_required": False,
        }
        self.assert_profile_error(
            high_risk_without_review,
            "PROFILE_POLICY_VIOLATION",
            "security.review_required",
        )

    def test_state_document_adapter_is_bounded_and_not_profile_authority(self) -> None:
        discovery = discover(ROOT)
        report = professional_project_profile_report(profile_payload("regulated"))

        self.assertIn("profiles", discovery)
        self.assertIn("project_profile", discovery)
        self.assertEqual(discovery["project_profile"]["status"], "passed")
        self.assertFalse(discovery["project_profile"]["can_complete"])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["authority"], "ProjectProfile")
        self.assertEqual(report["persistence"], "not-run")
        self.assertNotIn("scope", report)
        self.assertLessEqual(len(json.dumps(report).encode("utf-8")), 2_048)

    def test_state_document_adapter_returns_sanitized_typed_finding(self) -> None:
        secret = "token=adapter-private-fixture"
        payload = profile_payload()
        payload["scope"] = {**dict(payload["scope"]), "summary": secret}

        report = professional_project_profile_report(payload)

        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            report["finding"]["code"], "PROFILE_PRIVATE_DATA_REJECTED"
        )
        self.assertNotIn(secret, json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    unittest.main()

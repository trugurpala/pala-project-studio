from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import build_portable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pala_release_candidate import (
    build_release_candidate,
    generate_sbom,
    isolated_install_canary,
    release_identity,
    self_verify_release_candidate,
)

ROOT = Path(__file__).resolve().parent.parent


class FinalAgencyReleaseCandidateTests(unittest.TestCase):
    def test_release_identity_is_derived_from_the_canonical_product_identity(self) -> None:
        identity = json.loads((ROOT / "product-identity.json").read_text(encoding="utf-8"))
        result = release_identity(ROOT)
        version = str(identity["product_version"])
        self.assertEqual(result["version"], version)
        self.assertEqual(result["artifact"], f"pala-project-studio-{version}.zip")
        implementation = (ROOT / "scripts" / "pala_release_candidate.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn('tool_version="1.1.2"', implementation)
        self.assertNotIn('manifest["version"] = "1.1.3-local-rollback-probe"', implementation)
        self.assertEqual(result["sbom"], f"pala-project-studio-{version}.cdx.json")
        self.assertEqual(result["inventory"], f"pala-project-studio-{version}.inventory.json")
        self.assertEqual(result["manifest"], f"pala-project-studio-{version}.manifest.json")

    def test_sbom_is_deterministic_complete_and_private_safe(self) -> None:
        first = generate_sbom(ROOT)
        second = generate_sbom(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(first["bomFormat"], "CycloneDX")
        self.assertEqual(first["specVersion"], "1.5")
        components = first["components"]
        refs = {item["bom-ref"] for item in components}
        self.assertIn("pkg:npm/%40playwright/test@1.62.1", refs)
        self.assertIn("pkg:pypi/ruff@0.16.2", refs)
        serialized = json.dumps(first, sort_keys=True)
        self.assertNotIn(str(ROOT), serialized)
        self.assertNotIn("Pala-Pc", serialized)

    def test_two_builds_are_byte_identical_and_inventory_covers_every_member(self) -> None:
        with (
            tempfile.TemporaryDirectory(prefix="pala-m79-build-a-") as a,
            tempfile.TemporaryDirectory(prefix="pala-m79-build-b-") as b,
        ):
            first = build_release_candidate(ROOT, Path(a))
            second = build_release_candidate(ROOT, Path(b))
            self.assertEqual(first["status"], "passed")
            self.assertEqual(first["artifact_sha256"], second["artifact_sha256"])
            self.assertEqual(first["sbom_sha256"], second["sbom_sha256"])
            self.assertEqual(first["inventory_sha256"], second["inventory_sha256"])
            self.assertEqual(first["artifact_entries"], first["inventory_entries"])
            self.assertTrue(all(len(item["sha256"]) == 64 for item in first["files"]))
            archive = Path(a) / str(first["artifact"])
            with zipfile.ZipFile(archive) as payload:
                self.assertEqual({item.create_system for item in payload.infolist()}, {3})
            self.assertEqual(first["remote_publish"], "not-run")
            self.assertEqual(first["real_remote_deploy"], "not-run")
            self.assertFalse(first["can_complete"])
            serialized = json.dumps(first, sort_keys=True)
            self.assertNotIn(a, serialized)
            self.assertNotIn(b, serialized)

    def test_isolated_install_noop_and_fault_rollback_preserve_sqlite(self) -> None:
        result = isolated_install_canary(ROOT)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["first_install"], "installed")
        self.assertEqual(result["second_install"], "ready")
        self.assertFalse(result["second_changed"])
        self.assertTrue(result["doctor_healthy"])
        self.assertTrue(result["rollback_restored"])
        self.assertTrue(result["sqlite_preserved"])
        self.assertTrue(result["failure_intelligence_preserved"])
        self.assertEqual(result["scope"], "isolated-temporary-profile")

    def test_sealed_manifest_contains_the_real_install_canary_without_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m79-sealed-") as temp:
            result = build_release_candidate(
                ROOT,
                Path(temp),
                include_install_canary=True,
                include_self_verification=True,
            )
            identity = release_identity(ROOT)
            manifest = json.loads(
                (Path(temp) / identity["manifest"]).read_text(
                    encoding="utf-8"
                )
            )
        self.assertEqual(result["status"], "passed")
        self.assertEqual(manifest["install_canary"]["status"], "passed")
        self.assertEqual(manifest["self_verification"]["status"], "passed")
        self.assertTrue(manifest["self_verification"]["fingerprint_drift_free"])
        self.assertNotIn(str(ROOT), json.dumps(manifest, sort_keys=True))

    def test_self_verification_has_no_fingerprint_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m80-self-verify-") as temp:
            result = self_verify_release_candidate(ROOT, Path(temp))
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["source_verified"])
        self.assertTrue(result["portable_verified"])
        self.assertTrue(result["installed_verified"])
        self.assertTrue(result["fingerprint_drift_free"])
        self.assertEqual(result["can_complete"], False)

    def test_portable_archive_rejects_a_symlink_canary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m80-symlink-") as temp:
            source = Path(temp) / "source"
            source.mkdir()
            marker = source / "linked.txt"
            target = source / "target.txt"
            target.write_text("target", encoding="utf-8")
            try:
                marker.symlink_to(target)
            except OSError as error:
                if os.environ.get("PALA_REQUIRE_SYMLINK_CANARY") == "1":
                    self.fail(f"required symlink canary unavailable: {error}")
                self.skipTest(f"symlinks unavailable in this profile: {error}")
            with (
                self.assertRaisesRegex(ValueError, "symbolic links are not portable"),
                patch.object(build_portable, "source_files", return_value=[marker]),
            ):
                build_portable.archive_entries(source)

    def test_ci_runs_browser_and_real_installer_canaries(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")
        for marker in (
            "actions/setup-node@",
            "npm ci",
            "npx playwright install --with-deps chromium",
            "npm run test:e2e",
            "scripts.test_pala_release_candidate",
            "actions/upload-artifact@",
            "actions/download-artifact@",
            "Compare Windows and Linux artifact hashes",
            'PALA_REQUIRE_SYMLINK_CANARY: "1"',
        ):
            self.assertIn(marker, workflow)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contracts for the real-release Pala upgrade matrix runner."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "pala_upgrade_matrix.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pala_upgrade_matrix", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("pala_upgrade_matrix.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UpgradeMatrixContracts(unittest.TestCase):
    def test_real_release_specs_are_sha_pinned(self) -> None:
        module = load_module()
        self.assertEqual(set(module.RELEASES), {"0.4.4", "0.8.0", "0.8.1", "1.0.0"})
        for version, item in module.RELEASES.items():
            self.assertIn(f"/v{version}/", item["url"])
            self.assertRegex(item["sha256"], r"^[0-9A-F]{64}$")

    def test_safe_extract_rejects_parent_escape(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("../outside.txt", "no")
            with self.assertRaisesRegex(ValueError, "unsafe archive path"):
                module.safe_extract(archive, Path(temp) / "out")

    def test_candidate_accepts_current_release_identity(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / ".codex-plugin" / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                '{"name":"pala-project-studio","version":"1.1.0"}',
                encoding="utf-8",
            )
            self.assertEqual(module.candidate_version(root), "1.1.0")

    def test_candidate_rejects_non_release_identity(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / ".codex-plugin" / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                '{"name":"pala-project-studio","version":"dev"}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "release version"):
                module.candidate_version(root)

    def test_upgrade_case_preserves_runtime_state_and_second_run_is_noop(self) -> None:
        module = load_module()
        from scripts.test_pala_installer import load_installer, make_bundle

        with tempfile.TemporaryDirectory(prefix="pala-upgrade-contract-") as temp:
            root = Path(temp)
            old_root = make_bundle(root / "old", "0.4.4+codex.published")
            candidate = make_bundle(root / "candidate", "1.0.0")
            result = module.run_case(
                load_installer(),
                candidate,
                old_root,
                root / "case",
                legacy=False,
                target_version="1.0.0",
            )

        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["state_preservation"], {
            "canonical_user_state": True,
            "project_catalog": True,
            "failure_intelligence": True,
        })
        self.assertEqual(result["second_ensure_current_status"], "ready")
        self.assertFalse(result["second_ensure_current_changed"])
        self.assertTrue(result["doctor_healthy"])

    def test_matrix_runs_published_044_as_managed_and_legacy(self) -> None:
        module = load_module()

        class Installer:
            @staticmethod
            def bundle_fingerprint(_candidate: Path) -> str:
                return "A" * 64

        with tempfile.TemporaryDirectory(prefix="pala-upgrade-matrix-") as temp:
            root = Path(temp)
            archive = root / "release.zip"
            archive.write_bytes(b"release")
            calls: list[tuple[str, bool]] = []

            def run_case(_installer, _candidate, _old_root, _workspace, *, legacy, target_version):
                calls.append((target_version, legacy))
                return {"status": "passed"}

            with (
                patch.object(module, "candidate_version", return_value="1.0.0"),
                patch.object(module, "load_installer", return_value=Installer()),
                patch.object(module, "download_release", return_value=archive),
                patch.object(module, "safe_extract", return_value=root / "published"),
                patch.object(module, "sha256", return_value="B" * 64),
                patch.object(module, "run_case", side_effect=run_case),
            ):
                result = module.run_matrix(root, root / "cache")

        self.assertEqual(result["status"], "passed")
        self.assertIn(("1.0.0", False), calls)
        self.assertIn(("1.0.0", True), calls)
        self.assertEqual(sum(1 for row in result["rows"] if row["source_release"] == "0.4.4"), 2)


if __name__ == "__main__":
    unittest.main()

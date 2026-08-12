#!/usr/bin/env python3
"""Contracts for the real-release Pala upgrade matrix runner."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


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
        self.assertEqual(set(module.RELEASES), {"0.8.0", "0.8.1"})
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

    def test_candidate_must_be_090(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / ".codex-plugin" / "plugin.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"name":"pala-project-studio","version":"0.8.1"}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "0.9.0"):
                module.candidate_version(root)


if __name__ == "__main__":
    unittest.main()

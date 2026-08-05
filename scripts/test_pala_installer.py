#!/usr/bin/env python3
"""Contract tests for Pala's idempotent local installer core."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
INSTALLER_PATH = ROOT / "scripts" / "pala_installer.py"


def load_installer():
    spec = importlib.util.spec_from_file_location("pala_installer", INSTALLER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pala_installer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_bundle(root: Path, version: str = "0.4.0+codex.test") -> Path:
    source = root / "source"
    (source / ".codex-plugin").mkdir(parents=True)
    (source / "scripts").mkdir()
    (source / "hooks").mkdir()
    (source / "skills" / "pala-project-finisher").mkdir(parents=True)
    (source / ".codex-plugin" / "plugin.json").write_text(
        json.dumps(
            {
                "name": "pala-project-studio",
                "version": version,
                "description": "test bundle",
            }
        ),
        encoding="utf-8",
    )
    (source / "scripts" / "pala_state.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_hook.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "hooks" / "hooks.json").write_text("{}\n", encoding="utf-8")
    (source / "skills" / "pala-project-finisher" / "SKILL.md").write_text(
        "---\nname: pala-project-finisher\ndescription: test\n---\n",
        encoding="utf-8",
    )
    (source / "README.md").write_text("source-only documentation\n", encoding="utf-8")
    return source


class InstallerCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.installer = load_installer()

    def test_install_is_idempotent_for_fifty_runs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"

            first = self.installer.install_bundle(source, install_root, state_root)
            self.assertEqual(first["status"], "installed")
            fingerprint = self.installer.tree_fingerprint(install_root)

            for _ in range(49):
                report = self.installer.install_bundle(
                    source, install_root, state_root
                )
                self.assertEqual(report["status"], "ready")
                self.assertFalse(report["changed"])
                self.assertEqual(
                    self.installer.tree_fingerprint(install_root), fingerprint
                )

    def test_existing_unowned_installation_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            install_root.mkdir(parents=True)
            marker = install_root / "owner-file.txt"
            marker.write_text("keep me", encoding="utf-8")

            report = self.installer.install_bundle(source, install_root, state_root)

            self.assertEqual(report["status"], "external_conflict")
            self.assertFalse(report["changed"])
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep me")

    def test_legacy_pala_bundle_is_migrated_into_managed_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root, "0.4.0+codex.test")
            legacy = make_bundle(root / "legacy", "0.3.3+codex.legacy")
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            install_root.parent.mkdir(parents=True)
            legacy.replace(install_root)

            report = self.installer.install_bundle(source, install_root, state_root)
            doctor = self.installer.doctor_bundle(source, install_root, state_root)

            self.assertEqual(report["status"], "migrated")
            self.assertEqual(doctor["plugin"]["status"], "ready")
            self.assertTrue((state_root / "install-state.json").is_file())

    def test_dry_run_never_writes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"

            report = self.installer.install_bundle(
                source, install_root, state_root, dry_run=True
            )

            self.assertEqual(report["status"], "would_install")
            self.assertFalse(install_root.exists())
            self.assertFalse(state_root.exists())

    def test_repair_replaces_only_owned_drifted_installation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)
            changed = install_root / "scripts" / "pala_state.py"
            changed.write_text("BROKEN = True\n", encoding="utf-8")

            before = self.installer.doctor_bundle(source, install_root, state_root)
            repaired = self.installer.install_bundle(
                source, install_root, state_root, repair=True
            )
            after = self.installer.doctor_bundle(source, install_root, state_root)

            self.assertEqual(before["plugin"]["status"], "drifted")
            self.assertEqual(repaired["status"], "repaired")
            self.assertEqual(after["plugin"]["status"], "ready")
            self.assertTrue(after["healthy"])

    def test_failed_activation_rolls_back_previous_working_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            first_source = make_bundle(root / "v1", "0.3.3+codex.test")
            second_source = make_bundle(root / "v2", "0.4.0+codex.test")
            (second_source / "scripts" / "pala_state.py").write_text(
                "VALUE = 2\n", encoding="utf-8"
            )
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(first_source, install_root, state_root)
            old_fingerprint = self.installer.tree_fingerprint(install_root)

            with patch.object(
                self.installer,
                "atomic_write_json",
                side_effect=OSError("simulated state failure"),
            ):
                with self.assertRaises(OSError):
                    self.installer.install_bundle(
                        second_source, install_root, state_root
                    )

            self.assertEqual(
                self.installer.tree_fingerprint(install_root), old_fingerprint
            )
            installed = json.loads(
                (install_root / ".codex-plugin" / "plugin.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(installed["version"], "0.3.3+codex.test")

    def test_uninstall_removes_only_owned_unchanged_installation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)

            removed = self.installer.uninstall_bundle(install_root, state_root)

            self.assertEqual(removed["status"], "uninstalled")
            self.assertFalse(install_root.exists())

    def test_uninstall_refuses_modified_managed_installation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)
            marker = install_root / "user-added.txt"
            marker.write_text("preserve", encoding="utf-8")

            report = self.installer.uninstall_bundle(install_root, state_root)

            self.assertEqual(report["status"], "modified")
            self.assertTrue(marker.is_file())


if __name__ == "__main__":
    unittest.main()

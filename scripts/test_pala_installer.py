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
    (source / ".agents" / "plugins").mkdir(parents=True)
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
    (source / ".agents" / "plugins" / "marketplace.json").write_text(
        json.dumps(
            {
                "name": "pala-project-studio",
                "interface": {"displayName": "Pala Project Studio"},
                "plugins": [
                    {
                        "name": "pala-project-studio",
                        "source": {"source": "local", "path": "./"},
                        "policy": {
                            "installation": "AVAILABLE",
                            "authentication": "ON_INSTALL",
                        },
                        "category": "Developer Tools",
                    }
                ],
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

    def test_codex_install_uses_supported_cli_and_becomes_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            install_root = root / "local" / "Pala" / "marketplace"
            version = "0.4.0+codex.test"
            marketplaces: list[dict[str, object]] = []
            installed: list[dict[str, object]] = []
            calls: list[tuple[str, ...]] = []

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                calls.append(command)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {"marketplaces": list(marketplaces)}
                if command == ("plugin", "list", "--json"):
                    return {"installed": list(installed), "available": []}
                if command[:3] == ("plugin", "marketplace", "add"):
                    marketplaces.append(
                        {"name": "pala-project-studio", "root": str(install_root)}
                    )
                    return {
                        "marketplaceName": "pala-project-studio",
                        "installedRoot": str(install_root),
                        "alreadyAdded": False,
                    }
                if command == (
                    "plugin",
                    "add",
                    "pala-project-studio@pala-project-studio",
                    "--json",
                ):
                    installed.append(
                        {
                            "pluginId": "pala-project-studio@pala-project-studio",
                            "name": "pala-project-studio",
                            "marketplaceName": "pala-project-studio",
                            "version": version,
                            "installed": True,
                            "enabled": True,
                        }
                    )
                    return {"pluginId": "pala-project-studio@pala-project-studio"}
                raise AssertionError(f"unexpected Codex command: {command}")

            first = self.installer.ensure_codex_install(
                install_root, version, invoke=invoke
            )
            calls_after_first = len(calls)
            second = self.installer.ensure_codex_install(
                install_root, version, invoke=invoke
            )

            self.assertEqual(first["status"], "installed")
            self.assertTrue(first["changed"])
            self.assertEqual(second["status"], "ready")
            self.assertFalse(second["changed"])
            self.assertEqual(len(calls) - calls_after_first, 2)
            self.assertIn(
                ("plugin", "marketplace", "add", str(install_root), "--json"),
                calls,
            )
            self.assertIn(
                (
                    "plugin",
                    "add",
                    "pala-project-studio@pala-project-studio",
                    "--json",
                ),
                calls,
            )

    def test_codex_marketplace_name_conflict_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            install_root = root / "local" / "Pala" / "marketplace"
            calls: list[tuple[str, ...]] = []

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                calls.append(command)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {
                        "marketplaces": [
                            {
                                "name": "pala-project-studio",
                                "root": str(root / "someone-elses-marketplace"),
                            }
                        ]
                    }
                if command == ("plugin", "list", "--json"):
                    return {"installed": [], "available": []}
                raise AssertionError("a conflicting marketplace must not be changed")

            report = self.installer.ensure_codex_install(
                install_root, "0.4.0+codex.test", invoke=invoke
            )

            self.assertEqual(report["status"], "external_conflict")
            self.assertFalse(report["changed"])
            self.assertEqual(len(calls), 2)

    def test_codex_dry_run_performs_only_inventory_reads(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            install_root = Path(temp) / "local" / "Pala" / "marketplace"
            calls: list[tuple[str, ...]] = []

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                calls.append(command)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {"marketplaces": []}
                if command == ("plugin", "list", "--json"):
                    return {"installed": [], "available": []}
                raise AssertionError("dry-run attempted to mutate Codex")

            report = self.installer.ensure_codex_install(
                install_root,
                "0.4.0+codex.test",
                dry_run=True,
                invoke=invoke,
            )

            self.assertEqual(report["status"], "would_install")
            self.assertFalse(report["changed"])
            self.assertEqual(len(calls), 2)

    def test_full_dry_run_reports_would_install_without_writes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "local" / "Pala" / "marketplace"
            state_root = root / "local" / "Pala"

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {"marketplaces": []}
                if command == ("plugin", "list", "--json"):
                    return {"installed": [], "available": []}
                raise AssertionError("full dry-run attempted to mutate Codex")

            report = self.installer.install_all(
                source,
                install_root,
                state_root,
                dry_run=True,
                invoke=invoke,
            )

            self.assertEqual(report["status"], "would_install")
            self.assertFalse(report["changed"])
            self.assertFalse(install_root.exists())
            self.assertFalse(state_root.exists())

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

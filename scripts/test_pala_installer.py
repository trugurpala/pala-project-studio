#!/usr/bin/env python3
"""Contract tests for Pala's idempotent local installer core."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
INSTALLER_PATH = ROOT / "scripts" / "pala_installer.py"
ADAPTERS_PATH = ROOT / "scripts" / "pala_adapters.py"


def load_installer():
    spec = importlib.util.spec_from_file_location("pala_installer", INSTALLER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pala_installer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_adapters():
    spec = importlib.util.spec_from_file_location("pala_adapters", ADAPTERS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pala_adapters.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pala_adapters"] = module
    spec.loader.exec_module(module)
    return module


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
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

    def test_managed_adapter_contracts_and_pins_are_valid(self) -> None:
        adapters = load_adapters()
        lock = adapters.load_managed_tools_lock(ROOT / "managed-tools.lock.json")

        self.assertEqual(lock["rtk"]["version"], "0.44.2")
        self.assertEqual(lock["code-review-graph"]["version"], "2.3.7")
        self.assertEqual(lock["graphify"]["version"], "0.9.33")
        self.assertEqual(lock["serena"]["version"], "1.6.1")
        self.assertEqual(lock["codebase-memory"]["version"], "0.9.0")
        self.assertEqual(lock["ollama"]["version"], "0.32.6")
        self.assertEqual(lock["qwen3-4b-instruct"]["integrity"], "ollama:0edcdef34593")
        self.assertEqual(lock["context7"]["version"], "3.2.5")
        self.assertEqual(lock["playwright-mcp"]["version"], "0.0.78")
        with self.assertRaises(ValueError):
            adapters.AdapterResult("rtk", "unknown", False, "invalid")

    def test_doctor_reports_missing_optional_adapters_without_breaking_core_health(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-adapters-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            (source / "managed-tools.lock.json").write_text(
                (ROOT / "managed-tools.lock.json").read_text(encoding="utf-8"), encoding="utf-8"
            )
            install_root = root / "installed"
            state_root = root / "state"
            self.installer.install_bundle(source, install_root, state_root)

            doctor = self.installer.doctor_bundle(source, install_root, state_root)

            self.assertTrue(doctor["healthy"])
            self.assertEqual(doctor["adapters"]["rtk"]["state"], "missing")

    def test_mcp_adapter_distinguishes_exact_missing_and_foreign_records(self) -> None:
        spec = {
            "name": "context7",
            "command": "npx",
            "args": ["-y", "@upstash/context7-mcp@3.2.5"],
        }
        mcp = load_script("pala_mcp", "pala_mcp.py").CodexMcpAdapter(
            lambda: {"mcpServers": {"context7": {"command": "npx", "args": spec["args"]}}}
        )
        self.assertEqual(mcp.inspect(spec).state, "ready")
        missing = load_script("pala_mcp_missing", "pala_mcp.py").CodexMcpAdapter(lambda: {"mcpServers": {}})
        self.assertEqual(missing.inspect(spec).state, "missing")
        foreign = load_script("pala_mcp_foreign", "pala_mcp.py").CodexMcpAdapter(
            lambda: {"mcpServers": {"context7": {"command": "node", "args": []}}}
        )
        self.assertEqual(foreign.inspect(spec).state, "external_conflict")

    def test_mcp_specs_match_managed_lock_versions(self) -> None:
        mcp = load_script("pala_mcp_specs", "pala_mcp.py")
        self.assertIn("3.2.5", " ".join(mcp.MCP_SPECS["context7"]["args"]))
        self.assertIn("0.0.78", " ".join(mcp.MCP_SPECS["playwright-mcp"]["args"]))

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
            state = json.loads(
                (state_root / "install-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["source"], self.installer.OFFICIAL_REPOSITORY)
            self.assertEqual(state["license"], "MIT")
            self.assertEqual(state["plugin_id"], self.installer.PLUGIN_ID)

    def test_atomic_event_log_is_bounded_and_drops_unapproved_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            path = Path(temp) / "logs" / "events.jsonl"
            path.parent.mkdir(parents=True)
            seed = b'{"mode":"install","status":"ready"}\n'
            path.write_bytes(
                seed * (self.installer.MAX_EVENT_LOG_BYTES // len(seed) + 100)
            )
            self.installer.atomic_append_event(
                path,
                {
                    "mode": "install",
                    "status": "ready",
                    "changed": True,
                    "version": "0.4.0+codex.test",
                    "token": "must-never-appear",
                    "password": "must-never-appear",
                },
            )

            content = path.read_text(encoding="utf-8")
            self.assertLessEqual(path.stat().st_size, self.installer.MAX_EVENT_LOG_BYTES)
            self.assertNotIn("must-never-appear", content)
            self.assertNotIn("token", content)
            self.assertNotIn("password", content)
            self.assertFalse(list(path.parent.glob("*.tmp")))

    def test_update_cache_is_atomic_and_contains_no_remote_claim(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            state_root = Path(temp) / "Pala"

            payload = self.installer.write_update_cache(
                state_root, "0.4.0+codex.test"
            )
            stored = json.loads(
                (state_root / "update-cache.json").read_text(encoding="utf-8")
            )

            self.assertEqual(stored, payload)
            self.assertFalse(stored["network_checked"])
            self.assertFalse(stored["update_available"])
            self.assertFalse(list(state_root.glob("*.tmp")))

    def test_second_full_install_produces_no_managed_file_changes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "local" / "Pala" / "marketplace"
            state_root = root / "local" / "Pala"
            marketplaces: list[dict[str, object]] = []
            installed: list[dict[str, object]] = []

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {"marketplaces": list(marketplaces)}
                if command == ("plugin", "list", "--json"):
                    return {"installed": list(installed), "available": []}
                if command[:3] == ("plugin", "marketplace", "add"):
                    marketplaces.append(
                        {"name": "pala-project-studio", "root": str(install_root)}
                    )
                    return {"marketplaceName": "pala-project-studio"}
                if command == ("plugin", "add", self.installer.PLUGIN_ID, "--json"):
                    installed.append(
                        {
                            "pluginId": self.installer.PLUGIN_ID,
                            "name": "pala-project-studio",
                            "marketplaceName": "pala-project-studio",
                            "version": "0.4.0+codex.test",
                            "installed": True,
                            "enabled": True,
                        }
                    )
                    return {"pluginId": self.installer.PLUGIN_ID}
                raise AssertionError(f"unexpected Codex command: {command}")

            first = self.installer.install_all(
                source, install_root, state_root, invoke=invoke
            )
            first_fingerprint = self.installer.tree_fingerprint(state_root)
            second = self.installer.install_all(
                source, install_root, state_root, invoke=invoke
            )

            self.assertEqual(first["status"], "installed")
            self.assertEqual(second["status"], "ready")
            self.assertFalse(second["changed"])
            self.assertEqual(
                self.installer.tree_fingerprint(state_root), first_fingerprint
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

    def test_codex_failure_rolls_back_previous_managed_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            first_source = make_bundle(root / "v1", "0.3.3+codex.test")
            second_source = make_bundle(root / "v2", "0.4.0+codex.test")
            (second_source / "scripts" / "pala_state.py").write_text(
                "VALUE = 2\n", encoding="utf-8"
            )
            install_root = root / "local" / "Pala" / "marketplace"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(first_source, install_root, state_root)
            old_fingerprint = self.installer.tree_fingerprint(install_root)

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {
                        "marketplaces": [
                            {"name": "pala-project-studio", "root": str(install_root)}
                        ]
                    }
                if command == ("plugin", "list", "--json"):
                    return {
                        "installed": [
                            {
                                "pluginId": self.installer.PLUGIN_ID,
                                "name": "pala-project-studio",
                                "marketplaceName": "pala-project-studio",
                                "version": "0.3.3+codex.test",
                                "installed": True,
                                "enabled": True,
                            }
                        ],
                        "available": [],
                    }
                if command == ("plugin", "add", self.installer.PLUGIN_ID, "--json"):
                    raise RuntimeError("simulated Codex update failure")
                raise AssertionError(f"unexpected Codex command: {command}")

            with self.assertRaisesRegex(RuntimeError, "simulated Codex"):
                self.installer.install_all(
                    second_source,
                    install_root,
                    state_root,
                    invoke=invoke,
                )

            self.assertEqual(
                self.installer.tree_fingerprint(install_root), old_fingerprint
            )
            state = json.loads(
                (state_root / "install-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["version"], "0.3.3+codex.test")

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
            marketplace_calls = [
                command
                for command in calls
                if command[:3] == ("plugin", "marketplace", "add")
            ]
            self.assertEqual(len(marketplace_calls), 1)
            self.assertEqual(
                self.installer.comparable_path(marketplace_calls[0][3]),
                self.installer.comparable_path(str(install_root)),
            )
            self.assertEqual(marketplace_calls[0][4], "--json")
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

    def test_foreign_same_named_plugin_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            install_root = root / "local" / "Pala" / "marketplace"
            calls: list[tuple[str, ...]] = []

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                calls.append(command)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {"marketplaces": []}
                if command == ("plugin", "list", "--json"):
                    return {
                        "installed": [
                            {
                                "pluginId": "pala-project-studio@foreign",
                                "name": "pala-project-studio",
                                "version": "9.9.9",
                                "installed": True,
                                "enabled": True,
                                "source": {
                                    "source": "local",
                                    "path": str(root / "foreign"),
                                },
                            }
                        ],
                        "available": [],
                    }
                raise AssertionError("foreign plugin must not be changed")

            report = self.installer.ensure_codex_install(
                install_root, "0.4.0+codex.test", invoke=invoke
            )

            self.assertEqual(report["status"], "external_conflict")
            self.assertFalse(report["changed"])
            self.assertEqual(report["conflicting_plugins"], ["pala-project-studio@foreign"])
            self.assertEqual(len(calls), 2)

    def test_verified_legacy_pala_is_migrated_without_changing_its_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            legacy_source = make_bundle(root / "legacy", "0.3.2+codex.legacy")
            legacy_manifest_path = legacy_source / ".codex-plugin" / "plugin.json"
            legacy_manifest = json.loads(legacy_manifest_path.read_text(encoding="utf-8"))
            legacy_manifest["repository"] = self.installer.OFFICIAL_REPOSITORY
            legacy_manifest["author"] = {
                "name": "Pala",
                "url": self.installer.OFFICIAL_AUTHOR,
            }
            legacy_manifest_path.write_text(
                json.dumps(legacy_manifest), encoding="utf-8"
            )
            legacy_fingerprint = self.installer.tree_fingerprint(legacy_source)
            install_root = root / "local" / "Pala" / "marketplace"
            version = "0.4.0+codex.test"
            marketplaces: list[dict[str, object]] = []
            installed: list[dict[str, object]] = [
                {
                    "pluginId": "pala-project-studio@legacy",
                    "name": "pala-project-studio",
                    "marketplaceName": "legacy",
                    "version": "0.3.2+codex.legacy",
                    "installed": True,
                    "enabled": True,
                    "source": {"source": "local", "path": str(legacy_source)},
                }
            ]
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
                    return {"marketplaceName": "pala-project-studio"}
                if command == ("plugin", "add", self.installer.PLUGIN_ID, "--json"):
                    installed.append(
                        {
                            "pluginId": self.installer.PLUGIN_ID,
                            "name": "pala-project-studio",
                            "marketplaceName": "pala-project-studio",
                            "version": version,
                            "installed": True,
                            "enabled": True,
                        }
                    )
                    return {"pluginId": self.installer.PLUGIN_ID}
                if command == (
                    "plugin",
                    "remove",
                    "pala-project-studio@legacy",
                    "--json",
                ):
                    installed[:] = [
                        entry
                        for entry in installed
                        if entry.get("pluginId") != "pala-project-studio@legacy"
                    ]
                    return {"pluginId": "pala-project-studio@legacy"}
                raise AssertionError(f"unexpected Codex command: {command}")

            report = self.installer.ensure_codex_install(
                install_root, version, invoke=invoke
            )

            self.assertEqual(report["status"], "migrated")
            self.assertTrue(report["changed"])
            self.assertEqual(
                self.installer.tree_fingerprint(legacy_source), legacy_fingerprint
            )
            self.assertIn(
                (
                    "plugin",
                    "remove",
                    "pala-project-studio@legacy",
                    "--json",
                ),
                calls,
            )

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

    def test_full_uninstall_handles_codex_removing_local_marketplace_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "local" / "Pala" / "marketplace"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)
            marketplaces: list[dict[str, object]] = [
                {"name": "pala-project-studio", "root": str(install_root)}
            ]
            installed: list[dict[str, object]] = [
                {
                    "pluginId": "pala-project-studio@pala-project-studio",
                    "name": "pala-project-studio",
                    "marketplaceName": "pala-project-studio",
                    "version": "0.4.0+codex.test",
                    "installed": True,
                    "enabled": True,
                }
            ]

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {"marketplaces": list(marketplaces)}
                if command == ("plugin", "list", "--json"):
                    return {"installed": list(installed), "available": []}
                if command == (
                    "plugin",
                    "remove",
                    "pala-project-studio@pala-project-studio",
                    "--json",
                ):
                    installed.clear()
                    return {"pluginId": "pala-project-studio@pala-project-studio"}
                if command == (
                    "plugin",
                    "marketplace",
                    "remove",
                    "pala-project-studio",
                    "--json",
                ):
                    marketplaces.clear()
                    for path in list(install_root.rglob("*")):
                        if path.is_file() and path.suffix in {".py", ".json"}:
                            path.unlink()
                    return {"marketplaceName": "pala-project-studio"}
                raise AssertionError(f"unexpected Codex command: {command}")

            report = self.installer.uninstall_all(
                source,
                install_root,
                state_root,
                invoke=invoke,
            )

            self.assertEqual(report["status"], "uninstalled")
            self.assertTrue(report["changed"])
            self.assertFalse(install_root.exists())
            self.assertFalse((state_root / "install-state.json").exists())

    def test_resilient_tree_removal_tolerates_concurrent_file_disappearance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp) / "owned-tree"
            root.mkdir()
            (root / "file.txt").write_text("owned", encoding="utf-8")
            real_rmtree = self.installer.shutil.rmtree
            attempts = 0

            def flaky_rmtree(path: Path, **kwargs: object) -> None:
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    raise FileNotFoundError("simulated concurrent cleanup")
                real_rmtree(path, **kwargs)

            with patch.object(
                self.installer.shutil, "rmtree", side_effect=flaky_rmtree
            ):
                self.installer.remove_tree_resilient(root)

            self.assertEqual(attempts, 2)
            self.assertFalse(root.exists())

    def test_verified_uninstall_can_detach_a_temporarily_locked_owned_tree(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "local" / "Pala" / "marketplace"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)

            with patch.object(
                self.installer, "remove_tree_resilient", return_value=False
            ):
                report = self.installer.finalize_verified_uninstall(
                    install_root, state_root
                )

            self.assertEqual(report["status"], "uninstalled")
            self.assertIsNotNone(report["cleanup_pending"])
            self.assertFalse(install_root.exists())
            self.assertFalse((state_root / "install-state.json").exists())

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

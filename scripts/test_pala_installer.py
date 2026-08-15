#!/usr/bin/env python3
"""Contract tests for Pala's idempotent local installer core."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import zipfile
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
INSTALLER_PATH = ROOT / "scripts" / "pala_installer.py"
PORTABLE_PACKAGER_PATH = ROOT / "scripts" / "build_portable.py"


def load_installer():
    spec = importlib.util.spec_from_file_location("pala_installer", INSTALLER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pala_installer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_packager():
    spec = importlib.util.spec_from_file_location(
        "pala_build_portable", PORTABLE_PACKAGER_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load build_portable.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pala_build_portable"] = module
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
                        "source": {"source": "local", "path": "."},
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
    (source / "scripts" / "pala_state_core.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_state_documents.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_state_cli.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_cold_packet_packet.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_state_git.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_quality.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_quality_discovery.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_quality_policy.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_quality_runner.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_installer_codex.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_installer_shared.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_installer_integrity.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_installer_core.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_installer_transaction.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_hook.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_hook_session.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_view_styles.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_view_layout.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "scripts" / "pala_self_audit.py").write_text(
        "VALUE = 1\n", encoding="utf-8"
    )
    (source / "hooks" / "hooks.json").write_text("{}\n", encoding="utf-8")
    (source / "skills" / "pala-project-finisher" / "SKILL.md").write_text(
        "---\nname: pala-project-finisher\ndescription: test\n---\n",
        encoding="utf-8",
    )
    (source / "README.md").write_text("source-only documentation\n", encoding="utf-8")
    return source


def extract_portable_source(destination: Path) -> Path:
    packager = load_packager()
    destination = Path(destination)
    zip_path = destination / "pala-project-studio.zip"
    if zip_path.is_file():
        zip_path.unlink()
    packager.build_archive(zip_path, ROOT)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(destination)
    return destination / "pala-project-studio"


class InstallerCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.installer = load_installer()

    def setUp(self) -> None:
        # Isolate Codex runtime cache checks from the developer's real ~/.codex
        # cache (same version string would otherwise look "stale").
        self._codex_home_dir = tempfile.TemporaryDirectory(prefix="pala-codex-home-")
        self._codex_home_patcher = patch.dict(
            os.environ, {"CODEX_HOME": self._codex_home_dir.name}
        )
        self._codex_home_patcher.start()
        self._workbench_patcher = patch.object(
            self.installer,
            "ensure_required_workbench",
            return_value={
                "status": "ready",
                "healthy": True,
                "changed": False,
                "state": "CURRENT",
            },
        )
        self._workbench_patcher.start()

    def tearDown(self) -> None:
        self._workbench_patcher.stop()
        self._codex_home_patcher.stop()
        self._codex_home_dir.cleanup()

    def test_cli_parser_is_available_for_windows_entrypoint(self) -> None:
        parsed = self.installer.parser().parse_args(["doctor"])
        self.assertEqual(parsed.mode, "doctor")

    def test_safe_source_file_forbids_secret_shaped_and_sqlite(self) -> None:
        for relative in (
            Path("credentials.json"),
            Path("hooks/id_rsa"),
            Path("scripts/secrets.json"),
            Path("data/pala.sqlite"),
            Path("scripts/token.key"),
        ):
            with self.subTest(relative=str(relative)):
                self.assertFalse(self.installer.safe_source_file(relative))
        self.assertTrue(self.installer.safe_source_file(Path("scripts/pala_quality.py")))
        self.assertTrue(self.installer.safe_source_file(Path("SECURITY.md")))

    def test_installed_fingerprint_stable_after_pycache(self) -> None:
        """Issue #13: runtime __pycache__ must not mark a healthy install drifted."""
        with tempfile.TemporaryDirectory(prefix="pala-fp-pycache-") as temp:
            dest = Path(temp) / "install"
            self.installer.copy_bundle(ROOT, dest)
            before = self.installer.tree_fingerprint(dest)
            pyc = dest / "scripts" / "__pycache__"
            pyc.mkdir(parents=True)
            (pyc / "x.pyc").write_bytes(b"abc")
            self.assertEqual(before, self.installer.tree_fingerprint(dest))

    def test_emit_json_survives_cp1254_stdout_with_replacement_char(self) -> None:
        """Doctor JSON print must not raise UnicodeEncodeError on Windows consoles."""
        import io

        class _Cp1254Stdout:
            encoding = "cp1254"

            def __init__(self) -> None:
                self.buffer = io.BytesIO()
                self.text = io.StringIO()

            def write(self, value: str) -> int:
                # Simulate console: refuse U+FFFD the way cp1254 does.
                value.encode(self.encoding)
                return self.text.write(value)

            def flush(self) -> None:
                return None

        fake = _Cp1254Stdout()
        payload = {
            "status": "attention_required",
            "note": "portable skill/rules only \ufffd not a Codex plugin install",
        }
        with patch.object(self.installer.sys, "stdout", fake):
            self.installer.emit_json(payload)
        written = fake.buffer.getvalue().decode("utf-8")
        self.assertIn('"status": "attention_required"', written)
        self.assertIn("\ufffd", written)

    def test_managed_capability_contracts_and_pins_are_valid(self) -> None:
        from pala_workbench import default_registry

        registry = default_registry()
        self.assertEqual(registry.get("code_intelligence").version, "1.5.0")
        self.assertEqual(registry.get("security_static").version, "1.172.0")
        self.assertEqual(registry.get("browser_e2e").version, "1.62.1")
        self.assertEqual(registry.get("symbol_precision").version, "1.7.0")
        self.assertEqual(registry.get("current_docs").version, "4.0.2")
        self.assertEqual(
            set(registry.categories()),
            {"DEFAULT", "PROJECT_PROFILE", "LAZY_FALLBACK", "OPTIONAL_EXTERNAL"},
        )

    def test_doctor_projects_current_capability_contracts_without_breaking_core_health(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-adapters-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "installed"
            state_root = root / "state"
            self.installer.install_bundle(source, install_root, state_root)

            doctor = self.installer.doctor_bundle(source, install_root, state_root)

            self.assertTrue(doctor["healthy"])
            self.assertEqual(doctor["adapters"]["code_intelligence"]["state"], "declared")
            self.assertEqual(doctor["adapters"]["code_intelligence"]["provider"], "CodeGraph")
            self.assertNotIn("rtk", doctor["adapters"])

    def test_resolve_codex_finds_openai_desktop_bin_when_not_on_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-codex-probe-") as temp:
            root = Path(temp)
            nested = root / "OpenAI" / "Codex" / "bin" / "deadbeef"
            nested.mkdir(parents=True)
            exe = nested / "codex.exe"
            exe.write_bytes(b"MZ")
            environ = {
                "LOCALAPPDATA": str(root),
                "APPDATA": str(root / "Roaming"),
                "USERPROFILE": str(root),
            }
            self.assertIn(
                str(exe),
                self.installer.resolve_windows_codex_candidates(environ=environ),
            )
            with patch.object(self.installer.shutil, "which", return_value=None), patch.dict(
                os.environ,
                environ,
                clear=False,
            ), patch.object(self.installer.os, "name", "nt"):
                resolved = self.installer.resolve_codex_executable()
            self.assertEqual(resolved, exe)

    def test_resolve_codex_skips_windowsapps_alias_for_local_desktop_binary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-codex-alias-") as temp:
            root = Path(temp)
            nested = root / "OpenAI" / "Codex" / "bin" / "deadbeef"
            nested.mkdir(parents=True)
            exe = nested / "codex.exe"
            exe.write_bytes(b"MZ")
            environ = {
                "LOCALAPPDATA": str(root),
                "APPDATA": str(root / "Roaming"),
                "USERPROFILE": str(root),
            }
            windowsapps_alias = str(root / "Microsoft" / "WindowsApps" / "codex.exe")
            with patch.object(
                self.installer.shutil,
                "which",
                return_value=windowsapps_alias,
            ), patch.dict(os.environ, environ, clear=False), patch.object(
                self.installer.os,
                "name",
                "nt",
            ):
                resolved = self.installer.resolve_codex_executable()
            self.assertEqual(resolved, exe)

    def test_codex_bridge_is_sibling_loaded_and_cli_call_is_shell_free(self) -> None:
        bridge = self.installer._codex_bridge
        self.assertEqual(
            Path(bridge.__file__).resolve(),
            (ROOT / "scripts" / "pala_installer_codex.py").resolve(),
        )
        completed = subprocess.CompletedProcess(
            args=["codex", "plugin", "list", "--json"],
            returncode=0,
            stdout="{}",
            stderr="",
        )
        with patch.object(
            self.installer,
            "resolve_codex_executable",
            return_value=Path("C:/tools/codex.exe"),
        ), patch.object(bridge.subprocess, "run", return_value=completed) as runner:
            self.assertEqual(
                self.installer.run_codex_json(["plugin", "list", "--json"]), {}
            )

        call = runner.call_args
        self.assertTrue(str(call.args[0][0]).casefold().endswith("codex.exe"))
        self.assertEqual(call.args[0][1:], ["plugin", "list", "--json"])
        self.assertFalse(call.kwargs["shell"])
        self.assertEqual(call.kwargs["timeout"], 30)

    def test_codex_capability_probe_is_non_mutating_and_detects_json_operations(self) -> None:
        bridge = self.installer._codex_bridge
        calls: list[tuple[str, ...]] = []

        def help_runner(arguments: list[str]) -> str:
            calls.append(tuple(arguments))
            return "Usage: codex ...\n--json\n"

        capabilities = bridge.probe_codex_capabilities(help_runner=help_runner)

        self.assertTrue(capabilities.marketplace_upgrade)
        self.assertTrue(capabilities.plugin_remove)
        self.assertTrue(capabilities.json_mode)
        self.assertEqual(capabilities.source, "codex-help-probe")
        self.assertEqual(len(calls), 7)
        self.assertNotIn("--json", " ".join(" ".join(call) for call in calls))

    def test_doctor_core_healthy_without_node_uv_experts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root / "source")
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)

            marketplaces = [{"name": "pala-project-studio", "root": str(install_root)}]
            installed = [
                {
                    "pluginId": self.installer.PLUGIN_ID,
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
                    return {"installed": list(installed)}
                raise AssertionError(f"unexpected Codex command: {command}")

            def tool_lookup(name: str) -> str | None:
                if name in {"git", "codex"}:
                    return f"C:\\\\tools\\\\{name}.exe"
                return None

            with patch.object(self.installer.sys, "version_info", (3, 11, 0)), patch.object(
                self.installer.shutil, "which", side_effect=tool_lookup
            ), patch.object(
                self.installer,
                "resolve_codex_executable",
                return_value=Path(r"C:\tools\codex.exe"),
            ), patch.object(
                self.installer,
                "project_doctor",
                return_value={
                    "available": True,
                    "project_root": str(root),
                    "project_registration": {"registered": True},
                    "hook_safety": {"status": "passed"},
                },
            ):
                report = self.installer.doctor_installation(
                    source,
                    install_root,
                    state_root,
                    root,
                    invoke=invoke,
                )

            self.assertTrue(report["plugin_ready"])
            self.assertTrue(report["healthy"])
            self.assertIn("code_intelligence", report["capability_contracts"])
            self.assertEqual(report["source_base_version"], "0.4.0")
            self.assertEqual(report["expected_base_version"], "0.4.0")
            self.assertEqual(report["codex_plugin_base_version"], "0.4.0")
            self.assertTrue(report["version_ready"])
            self.assertIn("capabilities", report["codex"])
            self.assertFalse(report["node"]["ready"])
            self.assertFalse(report["uv"]["ready"])
            self.assertIn("hooks_next_step", report)
            self.assertIn("/hooks", report["hooks_next_step"])
            self.assertIn("hook_safety=passed", report["hooks_next_step"])
            self.assertIn("dosya", report["hooks_next_step"].casefold())
            self.assertEqual(
                report["self_audit"]["status"], "configured-not-verified"
            )
            self.assertIn("pala_self_audit.py", report["self_audit"]["command"])
            self.assertIn(
                "hook_safety=passed",
                self.installer.hooks_next_step_message(
                    {"hook_safety": {"status": "passed"}}
                ),
            )
            blocked = self.installer.hooks_next_step_message(
                {"hook_safety": {"status": "blocked"}}
            )
            self.assertIn("hook_safety=blocked", blocked)
            self.assertIn("/hooks", blocked)
            drifted = self.installer.plugin_drift_next_step_message(
                {"status": "drifted"}
            )
            self.assertIn("plugin=drifted", drifted)
            self.assertIn("Repair", drifted)
            self.assertIn("healthy", drifted.casefold())
            modified = self.installer.plugin_drift_next_step_message(
                {"status": "modified"}
            )
            self.assertIn("plugin=modified", modified)
            self.assertIn("otomatik yazmaz", modified)
            self.assertEqual(
                self.installer.plugin_drift_next_step_message({"status": "ready"}),
                "",
            )
            self.assertIn("plugin_next_step", report)
            # Healthy fixture install is not drifted.
            self.assertEqual(report["plugin_next_step"], "")

    def test_doctor_legacy_expert_fields_are_retired(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-expert-readiness-") as temp:
            root = Path(temp)
            source = make_bundle(root / "source")
            bundle = {
                "healthy": True,
                "plugin": {"status": "ready"},
                "adapters": {
                    "code_intelligence": {"state": "declared", "provider": "CodeGraph"},
                    "security_static": {"state": "declared", "provider": "Semgrep"},
                },
                "state_file": str(root / "state" / "install-state.json"),
            }

            with patch.object(self.installer, "doctor_bundle", return_value=bundle), patch.object(
                self.installer, "codex_status", return_value={"healthy": True}
            ), patch.object(
                self.installer.shutil,
                "which",
                side_effect=lambda name: f"C:/tools/{name}.exe" if name in {"git", "node", "uv"} else None,
            ), patch.object(
                self.installer, "resolve_codex_executable", return_value=Path("C:/tools/codex.exe")
            ), patch.object(
                self.installer,
                "project_doctor",
                return_value={"available": True, "hook_safety": {"status": "passed"}},
            ):
                report = self.installer.doctor_installation(
                    source,
                    root / "installed",
                    root / "state",
                    root,
                )

            self.assertNotIn("expert_prerequisites_ready", report)
            self.assertNotIn("experts_ready", report)
            self.assertEqual(report["capability_contracts"], bundle["adapters"])
            self.assertTrue(report["healthy"])

    def test_doctor_bundle_does_not_project_retired_helper_registry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-workbench-contracts-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            state_root = root / "state"
            doctor = self.installer.doctor_bundle(source, root / "installed", state_root)

            self.assertEqual(doctor["adapters"]["security_static"]["provider"], "Semgrep")
            for retired in ("graphify", "codebase-memory", "code-review-graph", "ollama", "rtk"):
                self.assertNotIn(retired, doctor["adapters"])

    def test_portable_package_includes_current_quality_and_install_docs(self) -> None:
        packager = load_packager()
        names = {path.relative_to(ROOT).as_posix() for path in packager.source_files(ROOT)}

        self.assertTrue(
            {
                "docs/ARCHITECTURE.md",
                "docs/QUALITY_ENGINE.md",
                "docs/PALA_UPDATE_COMPATIBILITY.md",
                "docs/INSTALL_ARTIFACT_CONTRACT.md",
                "scripts/pala_state_git.py",
                "scripts/pala_installer_codex.py",
                "scripts/pala_installer_shared.py",
                "scripts/pala_installer_integrity.py",
                "scripts/pala_installer_core.py",
                "scripts/pala_installer_transaction.py",
                "scripts/pala_quality.py",
                "scripts/pala_quality_discovery.py",
                "scripts/pala_quality_policy.py",
                "scripts/pala_quality_runner.py",
                "scripts/pala_cold_packet_packet.py",
                "scripts/pala_hook_session.py",
            }.issubset(names)
        )

    def test_validate_bundle_requires_state_git_helper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            source = make_bundle(Path(temp))
            (source / "scripts" / "pala_state_git.py").unlink()

            with self.assertRaisesRegex(FileNotFoundError, r"scripts[\\/]pala_state_git\.py"):
                self.installer.validate_bundle(source)

    def test_validate_bundle_requires_state_runtime_siblings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            source = make_bundle(Path(temp))
            (source / "scripts" / "pala_state_core.py").unlink()

            with self.assertRaisesRegex(FileNotFoundError, "pala_state_core.py"):
                self.installer.validate_bundle(source)

    def test_validate_bundle_requires_installer_codex_helper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            source = make_bundle(Path(temp))
            (source / "scripts" / "pala_installer_codex.py").unlink()

            with self.assertRaisesRegex(
                FileNotFoundError, r"scripts[\\/]pala_installer_codex\.py"
            ):
                self.installer.validate_bundle(source)

    def test_validate_bundle_requires_installer_transaction_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            source = make_bundle(Path(temp))
            (source / "scripts" / "pala_installer_transaction.py").unlink()

            with self.assertRaisesRegex(
                FileNotFoundError, "pala_installer_transaction.py"
            ):
                self.installer.validate_bundle(source)

    def test_validate_bundle_requires_quality_policy_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            source = make_bundle(Path(temp))
            (source / "scripts" / "pala_quality_policy.py").unlink()

            with self.assertRaisesRegex(
                FileNotFoundError, r"scripts[\\/]pala_quality_policy\.py"
            ):
                self.installer.validate_bundle(source)

    def test_validate_bundle_requires_quality_runner_runtime(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            source = make_bundle(Path(temp))
            (source / "scripts" / "pala_quality_runner.py").unlink()

            with self.assertRaisesRegex(
                FileNotFoundError, r"scripts[\\/]pala_quality_runner\.py"
            ):
                self.installer.validate_bundle(source)

    def test_validate_bundle_requires_cold_packet_and_hook_session_helpers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            source = make_bundle(Path(temp))
            (source / "scripts" / "pala_hook_session.py").unlink()

            with self.assertRaisesRegex(FileNotFoundError, "pala_hook_session.py"):
                self.installer.validate_bundle(source)

    def test_validate_bundle_requires_view_runtime_helpers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            for helper in ("pala_view_styles.py", "pala_view_layout.py"):
                with self.subTest(helper=helper):
                    source = make_bundle(root / helper)
                    (source / "scripts" / helper).unlink()

                    with self.assertRaisesRegex(FileNotFoundError, helper):
                        self.installer.validate_bundle(source)

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

    def test_install_doctor_update_cycles_are_dry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            old_source = make_bundle(root / "old", "0.4.0+codex.old")
            source = make_bundle(root / "next", "0.4.1+codex.new")
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            marketplaces: list[dict[str, object]] = []
            installed: list[dict[str, object]] = []
            expected_version = ["0.4.0+codex.old"]

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
                    return {
                        "marketplaceName": "pala-project-studio",
                        "installedRoot": str(install_root),
                        "alreadyAdded": False,
                    }
                if command == ("plugin", "add", self.installer.PLUGIN_ID, "--json"):
                    installed[:] = [
                        entry
                        for entry in installed
                        if entry.get("pluginId") != self.installer.PLUGIN_ID
                    ]
                    installed.append(
                        {
                            "pluginId": self.installer.PLUGIN_ID,
                            "name": "pala-project-studio",
                            "marketplaceName": "pala-project-studio",
                            "version": expected_version[0],
                            "installed": True,
                            "enabled": True,
                        }
                    )
                    return {"pluginId": self.installer.PLUGIN_ID}
                if command == ("plugin", "remove", self.installer.PLUGIN_ID, "--json"):
                    installed[:] = [
                        entry
                        for entry in installed
                        if entry.get("pluginId") != self.installer.PLUGIN_ID
                    ]
                    return {"pluginId": self.installer.PLUGIN_ID}
                raise AssertionError(f"unexpected Codex command: {command}")

            first_install = self.installer.install_all(
                old_source, install_root, state_root, invoke=invoke
            )
            self.assertEqual(first_install["status"], "installed")
            self.assertTrue(first_install["changed"])
            expected_version[0] = "0.4.1+codex.new"
            update = self.installer.install_all(
                source, install_root, state_root, invoke=invoke
            )
            self.assertEqual(update["status"], "updated")
            self.assertTrue(update["changed"])
            fingerprint = self.installer.tree_fingerprint(install_root)

            with (
                patch.object(self.installer, "project_doctor", return_value={"available": True}),
                patch.object(
                    self.installer.shutil,
                    "which",
                    side_effect=lambda tool: f"/tools/{tool}",
                ),
            ):
                for _ in range(50):
                    doctor = self.installer.doctor_installation(
                        source,
                        install_root,
                        state_root,
                        root,
                        invoke=invoke,
                    )
                    self.assertTrue(doctor["healthy"])
                    cycle = self.installer.install_all(source, install_root, state_root, invoke=invoke)
                    self.assertEqual(cycle["status"], "ready")
                    self.assertFalse(cycle["changed"])
                    self.assertEqual(fingerprint, self.installer.tree_fingerprint(install_root))
                    self.assertEqual(cycle["codex"]["status"], "ready")

    def test_install_all_reports_unavailable_when_codex_is_offline(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root / "source", "0.4.0+codex.test")
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"

            def invoke(arguments: list[str]) -> dict[str, object]:
                raise RuntimeError("network is unreachable")

            # Pre-install a valid copy and state so we can assert no mutation occurs.
            self.installer.install_bundle(source, install_root, state_root)
            state_before = (state_root / "install-state.json").read_text(encoding="utf-8")
            fingerprint_before = self.installer.tree_fingerprint(install_root)

            report = self.installer.install_all(
                source,
                install_root,
                state_root,
                invoke=invoke,
            )

            self.assertEqual(report["status"], "unavailable")
            self.assertFalse(report["changed"])
            self.assertEqual(report["codex"]["status"], "unavailable")
            self.assertEqual(state_before, (state_root / "install-state.json").read_text(encoding="utf-8"))
            self.assertEqual(fingerprint_before, self.installer.tree_fingerprint(install_root))

    def test_install_all_current_version_is_noop_for_ready_codex(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root, "0.4.1+codex.current")
            install_root = root / "home" / "plugins" / "pala-project-studio"
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
                    return {
                        "marketplaceName": "pala-project-studio",
                        "installedRoot": str(install_root),
                        "alreadyAdded": False,
                    }
                if command == ("plugin", "add", self.installer.PLUGIN_ID, "--json"):
                    installed[:] = [
                        entry
                        for entry in installed
                        if entry.get("pluginId") != self.installer.PLUGIN_ID
                    ]
                    installed.append(
                        {
                            "pluginId": self.installer.PLUGIN_ID,
                            "name": "pala-project-studio",
                            "marketplaceName": "pala-project-studio",
                            "version": "0.4.1+codex.current",
                            "installed": True,
                            "enabled": True,
                        }
                    )
                    return {"pluginId": self.installer.PLUGIN_ID}
                raise AssertionError(f"unexpected Codex command: {command}")

            first = self.installer.install_all(source, install_root, state_root, invoke=invoke)
            self.assertEqual(first["status"], "installed")

            second = self.installer.install_all(source, install_root, state_root, invoke=invoke)
            self.assertEqual(second["status"], "ready")
            self.assertFalse(second["changed"])
            self.assertEqual(second["bundle"]["status"], "ready")
            self.assertEqual(first["version"], second["version"])

    def test_install_all_restores_previous_state_after_mid_install_exception(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root / "source", "0.4.1+codex.test")
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            marketplaces: list[dict[str, object]] = []
            installed: list[dict[str, object]] = []
            self.installer.install_bundle(source, install_root, state_root)

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
                    return {
                        "marketplaceName": "pala-project-studio",
                        "installedRoot": str(install_root),
                        "alreadyAdded": False,
                    }
                if command == ("plugin", "add", self.installer.PLUGIN_ID, "--json"):
                    installed[:] = [
                        entry
                        for entry in installed
                        if entry.get("pluginId") != self.installer.PLUGIN_ID
                    ]
                    installed.append(
                        {
                            "pluginId": self.installer.PLUGIN_ID,
                            "name": "pala-project-studio",
                            "marketplaceName": "pala-project-studio",
                            "version": "0.4.1+codex.test",
                            "installed": True,
                            "enabled": True,
                        }
                    )
                    return {"pluginId": self.installer.PLUGIN_ID}
                raise AssertionError(f"unexpected Codex command: {command}")

            expected_state = (state_root / "install-state.json").read_text(encoding="utf-8")
            expected_fingerprint = self.installer.tree_fingerprint(install_root)

            with patch.object(
                self.installer,
                "install_bundle",
                side_effect=RuntimeError("simulated half staging"),
            ):
                with self.assertRaises(RuntimeError):
                    self.installer.install_all(
                        source,
                        install_root,
                        state_root,
                        invoke=invoke,
                    )

            self.assertEqual(expected_state, (state_root / "install-state.json").read_text(encoding="utf-8"))
            self.assertEqual(expected_fingerprint, self.installer.tree_fingerprint(install_root))

    def test_doctor_installation_reports_missing_required_tools(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "home" / "plugins" / "pala-project-studio"
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
                    return {
                        "marketplaceName": "pala-project-studio",
                        "installedRoot": str(install_root),
                        "alreadyAdded": False,
                    }
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
                if command == ("plugin", "remove", self.installer.PLUGIN_ID, "--json"):
                    installed.clear()
                    return {"pluginId": self.installer.PLUGIN_ID}
                raise AssertionError(f"unexpected Codex command: {command}")

            install = self.installer.install_all(source, install_root, state_root, invoke=invoke)
            self.assertEqual(install["status"], "installed")

            def tool_lookup(name: str) -> str | None:
                if name == "git":
                    return None
                if name == "node":
                    return None
                if name == "uv":
                    return None
                if name == "codex":
                    return "C:\\\\Program Files\\\\codex.exe"
                return None

            with patch.object(self.installer.sys, "version_info", (3, 9, 0)), patch.object(
                self.installer.shutil, "which", side_effect=tool_lookup
            ):
                report = self.installer.doctor_installation(
                    source,
                    install_root,
                    state_root,
                    root,
                    invoke=invoke,
                )

            self.assertEqual(report["status"], "attention_required")
            self.assertFalse(report["healthy"])
            self.assertFalse(report["python"]["ready"])
            self.assertFalse(report["node"]["ready"])
            self.assertFalse(report["uv"]["ready"])
            self.assertFalse(report["git"]["ready"])

    def test_doctor_installation_blocks_if_project_hook_safety_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root / "source")
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)

            with patch.object(
                self.installer,
                "project_doctor",
                return_value={
                    "available": False,
                    "project_root": str(root),
                    "error": "hook safety failed",
                    "hook_safety": {"status": "blocked"},
                },
            ):
                report = self.installer.doctor_installation(
                    source,
                    install_root,
                    state_root,
                    root,
                    invoke=lambda arguments: {"marketplaces": [{"name": "pala-project-studio", "root": str(install_root)}], "installed": []},
                )

            self.assertEqual(report["status"], "attention_required")
            self.assertFalse(report["healthy"])
            self.assertEqual(report["project"]["available"], False)

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
            legacy_manifest_path = legacy / ".codex-plugin" / "plugin.json"
            legacy_manifest = json.loads(legacy_manifest_path.read_text(encoding="utf-8"))
            legacy_manifest["repository"] = self.installer.OFFICIAL_REPOSITORY
            legacy_manifest["author"] = {
                "name": "Pala",
                "url": self.installer.OFFICIAL_AUTHOR,
            }
            legacy_manifest_path.write_text(json.dumps(legacy_manifest), encoding="utf-8")
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            install_root.parent.mkdir(parents=True)
            self.installer.copy_bundle(legacy, install_root)

            report = self.installer.install_bundle(source, install_root, state_root)
            doctor = self.installer.doctor_bundle(source, install_root, state_root)

            self.assertEqual(report["status"], "migrated")
            self.assertEqual(doctor["plugin"]["status"], "ready")
            self.assertTrue((state_root / "install-state.json").is_file())

    def test_real_shape_legacy_does_not_need_future_runtime_siblings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root / "candidate", "0.8.2+codex.test")
            legacy = make_bundle(root / "legacy", "0.8.0+codex.legacy")
            manifest_path = legacy / ".codex-plugin" / "plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["repository"] = self.installer.OFFICIAL_REPOSITORY
            manifest["author"] = {"name": "Pala", "url": self.installer.OFFICIAL_AUTHOR}
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            for relative in (
                "scripts/pala_installer_codex.py",
                "scripts/pala_installer_shared.py",
                "scripts/pala_installer_integrity.py",
                "scripts/pala_installer_core.py",
                "scripts/pala_installer_transaction.py",
                "scripts/pala_quality_discovery.py",
                "scripts/pala_quality_policy.py",
                "scripts/pala_state_core.py",
                "scripts/pala_state_documents.py",
                "scripts/pala_state_cli.py",
                "scripts/pala_state_git.py",
                "scripts/pala_cold_packet_packet.py",
                "scripts/pala_hook_session.py",
                "scripts/pala_view_styles.py",
                "scripts/pala_view_layout.py",
            ):
                (legacy / relative).unlink(missing_ok=True)
            install_root = root / "local" / "Pala" / "marketplace"
            state_root = root / "local" / "Pala"
            self.installer.copy_bundle(legacy, install_root)

            report = self.installer.install_bundle(source, install_root, state_root)

            self.assertEqual(report["status"], "migrated")
            self.assertEqual(
                json.loads((install_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"],
                "0.8.2+codex.test",
            )

    def test_upgrade_transfers_new_runtime_skill_and_hook_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            candidate = make_bundle(root / "candidate", "0.8.2+codex.test")
            old = make_bundle(root / "old", "0.8.1+codex.old")
            expected = {
                "scripts/pala_state_documents.py": "NEW_DOCUMENT_RUNTIME = True\n",
                "scripts/pala_hook_session.py": "NEW_SESSION_RUNTIME = True\n",
                "hooks/hooks.json": '{"version":"0.8.2-hook"}\n',
                "skills/pala-project-finisher/SKILL.md": "# Pala 0.8.2 skill\n",
            }
            for relative, content in expected.items():
                (candidate / relative).write_text(content, encoding="utf-8")
            for relative in (
                "scripts/pala_state_documents.py",
                "scripts/pala_hook_session.py",
            ):
                (old / relative).unlink()
            install_root = root / "local" / "Pala" / "marketplace"
            state_root = root / "local" / "Pala"
            self.installer.copy_bundle(old, install_root)
            self.installer.atomic_write_json(
                self.installer.state_path(state_root),
                {
                    "schema_version": self.installer.SCHEMA_VERSION,
                    "owner": self.installer.OWNER,
                    "install_root": str(install_root.resolve()),
                    "version": "0.8.1+codex.old",
                    "fingerprint": self.installer.tree_fingerprint(install_root),
                    "file_hashes": self.installer.bundle_file_hashes(install_root),
                    "source": self.installer.OFFICIAL_REPOSITORY,
                },
            )

            report = self.installer.install_bundle(candidate, install_root, state_root)

            self.assertEqual(report["status"], "updated")
            for relative, content in expected.items():
                self.assertEqual(
                    (install_root / relative).read_text(encoding="utf-8"),
                    content,
                )
            self.assertEqual(
                self.installer.tree_fingerprint(install_root),
                self.installer.bundle_fingerprint(candidate),
            )

    def test_unattested_legacy_shape_remains_external_conflict(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root / "candidate", "0.8.2+codex.test")
            legacy = make_bundle(root / "foreign", "0.8.0+codex.foreign")
            (legacy / "scripts" / "pala_installer_core.py").unlink()
            install_root = root / "local" / "Pala" / "marketplace"
            state_root = root / "local" / "Pala"
            self.installer.copy_bundle(legacy, install_root)

            report = self.installer.install_bundle(source, install_root, state_root)

            self.assertEqual(report["status"], "external_conflict")
            self.assertFalse(report["changed"])

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

    def test_repair_refuses_modified_owned_installation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)
            changed = install_root / "scripts" / "pala_state.py"
            changed.write_text("BROKEN = True\n", encoding="utf-8")

            before = self.installer.doctor_bundle(source, install_root, state_root)
            repair = self.installer.install_bundle(
                source, install_root, state_root, repair=True
            )
            after = self.installer.doctor_bundle(source, install_root, state_root)

            self.assertEqual(before["plugin"]["status"], "modified")
            self.assertEqual(repair["status"], "modified")
            self.assertFalse(repair["changed"])
            self.assertEqual(changed.read_text(encoding="utf-8"), "BROKEN = True\n")
            self.assertEqual(after["plugin"]["status"], "modified")
            self.assertFalse(after["healthy"])

    def test_user_added_file_blocks_update_before_codex_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source_v1 = make_bundle(root / "source-v1", "0.4.0+codex.test")
            source_v2 = make_bundle(root / "source-v2", "0.4.1+codex.test")
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source_v1, install_root, state_root)
            marker = install_root / "preserve-me.txt"
            marker.write_text("user work", encoding="utf-8")
            state_before = (state_root / "install-state.json").read_text(encoding="utf-8")
            calls: list[tuple[str, ...]] = []

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                calls.append(command)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {"marketplaces": []}
                if command == ("plugin", "list", "--json"):
                    return {"installed": [], "available": []}
                raise AssertionError(f"modified tree attempted Codex mutation: {command}")

            doctor = self.installer.doctor_bundle(source_v2, install_root, state_root)
            direct = self.installer.install_bundle(source_v2, install_root, state_root)
            full = self.installer.install_all(
                source_v2, install_root, state_root, invoke=invoke
            )

            self.assertEqual(doctor["plugin"]["status"], "modified")
            self.assertFalse(doctor["healthy"])
            self.assertEqual(direct["status"], "modified")
            self.assertFalse(direct["changed"])
            self.assertEqual(full["status"], "modified")
            self.assertFalse(full["changed"])
            self.assertTrue(marker.is_file())
            self.assertEqual(marker.read_text(encoding="utf-8"), "user work")
            self.assertEqual(
                (state_root / "install-state.json").read_text(encoding="utf-8"),
                state_before,
            )
            self.assertEqual(
                calls,
                [
                    ("plugin", "marketplace", "list", "--json"),
                    ("plugin", "list", "--json"),
                ],
            )

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

    def test_ensure_codex_refreshes_when_cache_fingerprint_differs(self) -> None:
        """Same version must still refresh when Codex cache content drifted."""
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            codex_home = root / "codex-home"
            version = "0.4.0+codex.cache-stale"
            install_root = make_bundle(root, version)
            (install_root / "hooks" / "hooks.json").write_text(
                json.dumps(
                    {
                        "hooks": {
                            "SessionEnd": [
                                {"hooks": [{"timeout": 3}]}
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            cache_dir = (
                codex_home
                / "plugins"
                / "cache"
                / "pala-project-studio"
                / "pala-project-studio"
                / version
            )
            shutil.copytree(install_root, cache_dir)
            (cache_dir / "hooks" / "hooks.json").write_text(
                json.dumps(
                    {
                        "hooks": {
                            "SessionEnd": [
                                {"hooks": [{"timeout": 10}]}
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            self.assertNotEqual(
                self.installer.tree_fingerprint(install_root),
                self.installer.tree_fingerprint(cache_dir),
            )

            marketplaces = [
                {"name": "pala-project-studio", "root": str(install_root)}
            ]
            installed: list[dict[str, object]] = [
                {
                    "pluginId": self.installer.PLUGIN_ID,
                    "name": "pala-project-studio",
                    "marketplaceName": "pala-project-studio",
                    "version": version,
                    "installed": True,
                    "enabled": True,
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
                if command == ("plugin", "remove", self.installer.PLUGIN_ID, "--json"):
                    installed.clear()
                    if cache_dir.exists():
                        shutil.rmtree(cache_dir)
                    return {"pluginId": self.installer.PLUGIN_ID}
                if command == ("plugin", "add", self.installer.PLUGIN_ID, "--json"):
                    if cache_dir.exists():
                        shutil.rmtree(cache_dir)
                    shutil.copytree(install_root, cache_dir)
                    installed[:] = [
                        {
                            "pluginId": self.installer.PLUGIN_ID,
                            "name": "pala-project-studio",
                            "marketplaceName": "pala-project-studio",
                            "version": version,
                            "installed": True,
                            "enabled": True,
                        }
                    ]
                    return {
                        "pluginId": self.installer.PLUGIN_ID,
                        "installedPath": str(cache_dir),
                    }
                raise AssertionError(f"unexpected Codex command: {command}")

            with patch.dict(os.environ, {"CODEX_HOME": str(codex_home)}):
                before = self.installer.codex_status(
                    install_root, version, invoke=invoke
                )
                self.assertEqual(before["status"], "outdated")
                self.assertTrue(before["cache_stale"])
                self.assertFalse(before["target_ready"])

                report = self.installer.ensure_codex_install(
                    install_root, version, invoke=invoke
                )

                self.assertEqual(report["status"], "updated")
                self.assertTrue(report["changed"])
                self.assertFalse(report.get("cache_stale"))
                self.assertEqual(
                    self.installer.tree_fingerprint(install_root),
                    self.installer.tree_fingerprint(cache_dir),
                )
                self.assertEqual(
                    json.loads((cache_dir / "hooks" / "hooks.json").read_text(
                        encoding="utf-8"
                    ))["hooks"]["SessionEnd"][0]["hooks"][0]["timeout"],
                    3,
                )
                self.assertIn(
                    ("plugin", "remove", self.installer.PLUGIN_ID, "--json"),
                    calls,
                )
                self.assertIn(
                    ("plugin", "add", self.installer.PLUGIN_ID, "--json"),
                    calls,
                )
                remove_at = calls.index(
                    ("plugin", "remove", self.installer.PLUGIN_ID, "--json")
                )
                add_at = calls.index(
                    ("plugin", "add", self.installer.PLUGIN_ID, "--json")
                )
                self.assertLess(remove_at, add_at)

    def test_codex_git_stale_snapshot_requires_marketplace_upgrade_before_reinstall(
        self,
    ) -> None:
        """Model Codex's already-added Git marketplace snapshot behavior."""
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            install_root = root / "managed" / "marketplace"
            expected_version = "1.0.1"
            old_version = "0.4.4"
            calls: list[tuple[str, ...]] = []
            refreshed = {"value": False}
            installed: list[dict[str, object]] = [
                {
                    "pluginId": self.installer.PLUGIN_ID,
                    "name": "pala-project-studio",
                    "marketplaceName": "pala-project-studio",
                    "version": old_version,
                    "installed": True,
                    "enabled": True,
                }
            ]

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                calls.append(command)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {
                        "marketplaces": [
                            {
                                "name": "pala-project-studio",
                                "root": str(install_root),
                                "marketplaceSource": {
                                    "sourceType": "git",
                                    "source": "https://github.com/trugurpala/pala-project-studio.git",
                                },
                                "snapshotVersion": expected_version
                                if refreshed["value"]
                                else old_version,
                            }
                        ]
                    }
                if command == ("plugin", "list", "--json"):
                    return {"installed": list(installed), "available": []}
                if command[:3] == ("plugin", "marketplace", "add"):
                    return {
                        "marketplaceName": "pala-project-studio",
                        "alreadyAdded": True,
                    }
                if command == (
                    "plugin",
                    "marketplace",
                    "upgrade",
                    "pala-project-studio",
                    "--json",
                ):
                    refreshed["value"] = True
                    return {"marketplaceName": "pala-project-studio"}
                if command == (
                    "plugin",
                    "remove",
                    self.installer.PLUGIN_ID,
                    "--json",
                ):
                    installed.clear()
                    return {"pluginId": self.installer.PLUGIN_ID}
                if command == (
                    "plugin",
                    "add",
                    self.installer.PLUGIN_ID,
                    "--json",
                ):
                    installed[:] = [
                        {
                            "pluginId": self.installer.PLUGIN_ID,
                            "name": "pala-project-studio",
                            "marketplaceName": "pala-project-studio",
                            "version": expected_version,
                            "installed": True,
                            "enabled": True,
                        }
                    ]
                    return {"pluginId": self.installer.PLUGIN_ID}
                raise AssertionError(f"unexpected Codex command: {command}")

            with patch.object(
                self.installer, "codex_runtime_cache_matches", return_value=True
            ):
                report = self.installer.ensure_codex_install(
                    install_root, expected_version, invoke=invoke
                )

            self.assertEqual(report["status"], "updated")
            self.assertEqual(report["installed_version"], expected_version)
            upgrade = (
                "plugin",
                "marketplace",
                "upgrade",
                "pala-project-studio",
                "--json",
            )
            reinstall = (
                "plugin",
                "add",
                self.installer.PLUGIN_ID,
                "--json",
            )
            self.assertIn(upgrade, calls)
            self.assertIn(reinstall, calls)
            self.assertLess(calls.index(upgrade), calls.index(reinstall))
            self.assertNotIn(
                ("plugin", "marketplace", "add", str(install_root), "--json"),
                calls,
            )

    def test_codex_git_stale_snapshot_uses_attested_remove_readd_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            install_root = root / "managed" / "marketplace"
            expected_version = "1.0.1"
            official_source = "https://github.com/trugurpala/pala-project-studio.git"
            calls: list[tuple[str, ...]] = []
            marketplaces: list[dict[str, object]] = [
                {
                    "name": "pala-project-studio",
                    "root": str(install_root),
                    "marketplaceSource": {
                        "sourceType": "git",
                        "source": official_source,
                    },
                }
            ]
            installed: list[dict[str, object]] = [
                {
                    "pluginId": self.installer.PLUGIN_ID,
                    "name": "pala-project-studio",
                    "marketplaceName": "pala-project-studio",
                    "version": "0.4.4",
                    "installed": True,
                    "enabled": True,
                }
            ]

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                calls.append(command)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {"marketplaces": list(marketplaces)}
                if command == ("plugin", "list", "--json"):
                    return {"installed": list(installed), "available": []}
                if command == ("plugin", "remove", self.installer.PLUGIN_ID, "--json"):
                    installed.clear()
                    return {"pluginId": self.installer.PLUGIN_ID}
                if command == (
                    "plugin",
                    "marketplace",
                    "remove",
                    "pala-project-studio",
                    "--json",
                ):
                    marketplaces.clear()
                    return {"marketplaceName": "pala-project-studio"}
                if command == (
                    "plugin",
                    "marketplace",
                    "add",
                    official_source,
                    "--json",
                ):
                    marketplaces[:] = [
                        {
                            "name": "pala-project-studio",
                            "root": str(install_root),
                            "marketplaceSource": {
                                "sourceType": "git",
                                "source": official_source,
                            },
                        }
                    ]
                    return {"alreadyAdded": False}
                if command == ("plugin", "add", self.installer.PLUGIN_ID, "--json"):
                    installed[:] = [
                        {
                            "pluginId": self.installer.PLUGIN_ID,
                            "name": "pala-project-studio",
                            "marketplaceName": "pala-project-studio",
                            "version": expected_version,
                            "installed": True,
                            "enabled": True,
                        }
                    ]
                    return {"pluginId": self.installer.PLUGIN_ID}
                raise AssertionError(f"unexpected Codex command: {command}")

            capabilities = self.installer._codex_bridge.CodexCapabilities(
                marketplace_add=True,
                marketplace_list=True,
                marketplace_upgrade=False,
                marketplace_remove=True,
                plugin_add=True,
                plugin_list=True,
                plugin_remove=True,
                json_mode=True,
                source="test-no-upgrade",
            )
            with patch.object(
                self.installer, "codex_runtime_cache_matches", return_value=True
            ):
                report = self.installer.ensure_codex_install(
                    install_root,
                    expected_version,
                    invoke=invoke,
                    capabilities=capabilities,
                )

            self.assertEqual(report["status"], "updated")
            self.assertEqual(report["marketplace_refresh_path"], "verified-remove-readd")
            self.assertNotIn(
                ("plugin", "marketplace", "upgrade", "pala-project-studio", "--json"),
                calls,
            )
            self.assertIn(("plugin", "marketplace", "remove", "pala-project-studio", "--json"), calls)
            self.assertIn(("plugin", "marketplace", "add", official_source, "--json"), calls)

    def test_codex_git_fallback_failures_preserve_a_usable_old_install(self) -> None:
        bridge = self.installer._codex_bridge
        capabilities = bridge.CodexCapabilities(
            marketplace_add=True,
            marketplace_list=True,
            marketplace_upgrade=False,
            marketplace_remove=True,
            plugin_add=True,
            plugin_list=True,
            plugin_remove=True,
            json_mode=True,
            source="test-no-upgrade",
        )
        official_source = self.installer.OFFICIAL_REPOSITORY

        for failure in ("marketplace_remove", "marketplace_add", "plugin_remove", "plugin_add"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory(
                prefix="pala-installer-"
            ) as temp:
                install_root = Path(temp) / "managed" / "marketplace"
                marketplaces = [{
                    "name": "pala-project-studio",
                    "root": str(install_root),
                    "marketplaceSource": {"sourceType": "git", "source": official_source},
                }]
                installed = [{
                    "pluginId": self.installer.PLUGIN_ID,
                    "name": "pala-project-studio",
                    "marketplaceName": "pala-project-studio",
                    "version": "0.4.4",
                    "installed": True,
                    "enabled": True,
                }]
                failed_once = {"value": False}

                def invoke(arguments: list[str]) -> dict[str, object]:
                    command = tuple(arguments)
                    operation = None
                    if command == ("plugin", "marketplace", "list", "--json"):
                        return {"marketplaces": list(marketplaces)}
                    if command == ("plugin", "list", "--json"):
                        return {"installed": list(installed), "available": []}
                    if command == ("plugin", "marketplace", "remove", "pala-project-studio", "--json"):
                        operation = "marketplace_remove"
                        if failure == operation and not failed_once["value"]:
                            failed_once["value"] = True
                            raise RuntimeError(f"simulated {operation} failure")
                        marketplaces.clear()
                        return {"marketplaceName": "pala-project-studio"}
                    if command == ("plugin", "marketplace", "add", official_source, "--json"):
                        operation = "marketplace_add"
                        if failure == operation and not failed_once["value"]:
                            failed_once["value"] = True
                            raise RuntimeError(f"simulated {operation} failure")
                        marketplaces[:] = [{
                            "name": "pala-project-studio",
                            "root": str(install_root),
                            "marketplaceSource": {"sourceType": "git", "source": official_source},
                        }]
                        return {"marketplaceName": "pala-project-studio"}
                    if command == ("plugin", "remove", self.installer.PLUGIN_ID, "--json"):
                        operation = "plugin_remove"
                        if failure == operation and not failed_once["value"]:
                            failed_once["value"] = True
                            raise RuntimeError(f"simulated {operation} failure")
                        installed.clear()
                        return {"pluginId": self.installer.PLUGIN_ID}
                    if command == ("plugin", "add", self.installer.PLUGIN_ID, "--json"):
                        operation = "plugin_add"
                        if failure == operation and not failed_once["value"]:
                            failed_once["value"] = True
                            raise RuntimeError(f"simulated {operation} failure")
                        installed[:] = [{
                            "pluginId": self.installer.PLUGIN_ID,
                            "name": "pala-project-studio",
                            "marketplaceName": "pala-project-studio",
                            "version": "0.4.4",
                            "installed": True,
                            "enabled": True,
                        }]
                        return {"pluginId": self.installer.PLUGIN_ID}
                    raise AssertionError(f"unexpected Codex command: {command}")

                with (
                    patch.object(self.installer, "codex_runtime_cache_matches", return_value=False),
                    self.assertRaisesRegex(RuntimeError, f"simulated {failure} failure"),
                ):
                    self.installer.ensure_codex_install(
                        install_root,
                        "1.0.0",
                        invoke=invoke,
                        capabilities=capabilities,
                    )

                self.assertTrue(marketplaces, "owned marketplace must remain usable")
                self.assertEqual(marketplaces[0]["marketplaceSource"]["source"], official_source)
                self.assertEqual(len(installed), 1, "old plugin must remain installed")
                self.assertEqual(installed[0]["version"], "0.4.4")
                self.assertTrue(installed[0]["enabled"])

    def test_codex_build_metadata_keeps_same_base_version_ready(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            install_root = root / "managed" / "marketplace"
            expected_version = "1.0.0"

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {
                        "marketplaces": [
                            {
                                "name": "pala-project-studio",
                                "root": str(install_root),
                                "marketplaceSource": {"sourceType": "local", "source": str(install_root)},
                                "snapshotVersion": "1.0.0+codex.local",
                            }
                        ]
                    }
                if command == ("plugin", "list", "--json"):
                    return {
                        "installed": [
                            {
                                "pluginId": self.installer.PLUGIN_ID,
                                "name": "pala-project-studio",
                                "version": "1.0.0+codex.local",
                                "installed": True,
                                "enabled": True,
                            }
                        ]
                    }
                raise AssertionError(f"unexpected Codex command: {command}")

            with patch.object(self.installer, "codex_runtime_cache_matches", return_value=True):
                report = self.installer.codex_status(
                    install_root, expected_version, invoke=invoke
                )

            self.assertEqual(report["status"], "ready")
            self.assertTrue(report["healthy"])
            self.assertTrue(report["target_ready"])
            self.assertEqual(report["installed_version_base"], expected_version)
            self.assertEqual(report["expected_version_base"], expected_version)

    def test_codex_owned_git_cache_is_verified_against_snapshot_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            install_root = root / "managed" / "marketplace"
            snapshot_root = root / "codex" / "git-snapshot"
            observed_cache_basis: list[Path] = []

            def invoke(arguments: list[str]) -> dict[str, object]:
                command = tuple(arguments)
                if command == ("plugin", "marketplace", "list", "--json"):
                    return {
                        "marketplaces": [
                            {
                                "name": "pala-project-studio",
                                "root": str(snapshot_root),
                                "marketplaceSource": {
                                    "sourceType": "git",
                                    "source": self.installer.OFFICIAL_REPOSITORY,
                                },
                            }
                        ]
                    }
                if command == ("plugin", "list", "--json"):
                    return {
                        "installed": [
                            {
                                "pluginId": self.installer.PLUGIN_ID,
                                "name": "pala-project-studio",
                                "marketplaceName": "pala-project-studio",
                                "version": "1.0.0",
                                "installed": True,
                                "enabled": True,
                            }
                        ],
                        "available": [],
                    }
                raise AssertionError(f"unexpected Codex command: {command}")

            def cache_matches(path: Path, version: str) -> bool:
                observed_cache_basis.append(path)
                return path.resolve() == snapshot_root.resolve() and version == "1.0.0"

            report = self.installer._codex_bridge.codex_status(
                install_root,
                "1.0.0",
                owner=self.installer.OWNER,
                plugin_id=self.installer.PLUGIN_ID,
                official_repository=self.installer.OFFICIAL_REPOSITORY,
                trusted_legacy=self.installer.trusted_legacy_pala,
                cache_matches=cache_matches,
                invoke=invoke,
            )

            self.assertEqual(observed_cache_basis, [snapshot_root])
            self.assertEqual(report["status"], "ready")
            self.assertTrue(report["target_ready"])

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

    def test_finalize_verified_uninstall_refuses_user_added_after_dry_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "local" / "Pala" / "marketplace"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)
            preview = self.installer.uninstall_bundle(
                install_root, state_root, dry_run=True
            )
            self.assertEqual(preview["status"], "would_uninstall")
            marker = install_root / "user-added-after-preview.txt"
            marker.write_text("preserve", encoding="utf-8")

            report = self.installer.finalize_verified_uninstall(
                install_root, state_root
            )

            self.assertEqual(report["status"], "modified")
            self.assertFalse(report["changed"])
            self.assertTrue(marker.is_file())
            self.assertTrue(install_root.exists())
            self.assertTrue((state_root / "install-state.json").exists())

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

    def test_uninstall_refuses_unowned_env_file_inside_scripts(self) -> None:
        """Exact manifests protect files that the bundle allowlist ignores."""
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)
            marker = install_root / "scripts" / ".env.local"
            marker.write_text("do-not-delete", encoding="utf-8")

            report = self.installer.uninstall_bundle(install_root, state_root)

            self.assertEqual(report["status"], "modified")
            self.assertTrue(marker.is_file())

    def test_uninstall_refuses_user_added_symlink(self) -> None:
        """A link is outside Pala's owned tree even when it points at a safe file."""
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)
            target = root / "keep-me.txt"
            target.write_text("preserve", encoding="utf-8")
            link = install_root / "user-link.txt"
            try:
                link.symlink_to(target)
            except OSError as exc:
                if os.environ.get("PALA_REQUIRE_SYMLINK_CANARY") == "1":
                    self.fail(f"required symlink canary unavailable: {exc}")
                self.skipTest(f"symlinks unavailable in this profile: {exc}")

            report = self.installer.uninstall_bundle(install_root, state_root)

            self.assertEqual(report["status"], "modified")
            self.assertTrue(link.is_symlink())
            self.assertTrue(target.is_file())

    def test_uninstall_allows_runtime_pycache_junk(self) -> None:
        """Issue #13 junk must not block uninstall the way user-added files do."""
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)
            pyc = install_root / "scripts" / "__pycache__"
            pyc.mkdir(parents=True)
            (pyc / "x.pyc").write_bytes(b"abc")

            report = self.installer.uninstall_bundle(install_root, state_root)

            self.assertEqual(report["status"], "uninstalled")
            self.assertFalse(install_root.exists())

    def test_uninstall_refuses_bytecode_outside_runtime_pycache(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-") as temp:
            root = Path(temp)
            source = make_bundle(root)
            install_root = root / "home" / "plugins" / "pala-project-studio"
            state_root = root / "local" / "Pala"
            self.installer.install_bundle(source, install_root, state_root)
            marker = install_root / "preserve-me.pyc"
            marker.write_bytes(b"user bytecode")

            report = self.installer.uninstall_bundle(install_root, state_root)

            self.assertEqual(report["status"], "modified")
            self.assertTrue(marker.is_file())
            self.assertTrue(install_root.exists())

    def test_source_root_install_repair_uninstall_in_clean_profile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-clean-") as temp:
            root = Path(temp)
            source = ROOT
            manifest = self.installer.manifest(source)
            install_root = root / "clean" / "local" / "Pala" / "marketplace"
            state_root = root / "clean" / "local" / "Pala"
            marketplaces: list[dict[str, object]] = []
            installed: list[dict[str, object]] = []
            calls: list[tuple[str, ...]] = []
            target_version = str(manifest["version"])

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
                if command == ("plugin", "add", self.installer.PLUGIN_ID, "--json"):
                    installed[:] = [
                        entry
                        for entry in installed
                        if entry.get("pluginId") != self.installer.PLUGIN_ID
                    ]
                    installed.append(
                        {
                            "pluginId": self.installer.PLUGIN_ID,
                            "name": "pala-project-studio",
                            "marketplaceName": "pala-project-studio",
                            "version": target_version,
                            "installed": True,
                            "enabled": True,
                        }
                    )
                    return {"pluginId": self.installer.PLUGIN_ID}
                if command == (
                    "plugin",
                    "remove",
                    self.installer.PLUGIN_ID,
                    "--json",
                ):
                    installed[:] = [
                        entry
                        for entry in installed
                        if entry.get("pluginId") != self.installer.PLUGIN_ID
                    ]
                    return {"pluginId": self.installer.PLUGIN_ID}
                if command == (
                    "plugin",
                    "marketplace",
                    "remove",
                    "pala-project-studio",
                    "--json",
                ):
                    marketplaces[:] = [
                        entry
                        for entry in marketplaces
                        if entry.get("name") != "pala-project-studio"
                    ]
                    return {"marketplaceName": "pala-project-studio"}
                raise AssertionError(f"unexpected Codex command: {command}")

            installed_report = self.installer.install_all(
                source, install_root, state_root, invoke=invoke
            )
            self.assertEqual(installed_report["status"], "installed")
            self.assertTrue(installed_report["changed"])
            baseline_fingerprint = self.installer.tree_fingerprint(install_root)

            (install_root / "scripts" / "pala_state.py").write_text(
                "BROKEN = True\n", encoding="utf-8"
            )
            repaired = self.installer.install_all(
                source,
                install_root,
                state_root,
                repair=True,
                invoke=invoke,
            )
            self.assertEqual(repaired["status"], "modified")
            self.assertFalse(repaired["changed"])
            self.assertNotEqual(self.installer.tree_fingerprint(install_root), baseline_fingerprint)

            (install_root / "scripts" / "pala_state.py").write_bytes(
                (source / "scripts" / "pala_state.py").read_bytes()
            )
            recovered = self.installer.install_all(
                source, install_root, state_root, invoke=invoke
            )
            self.assertEqual(recovered["status"], "ready")
            self.assertEqual(self.installer.tree_fingerprint(install_root), baseline_fingerprint)

            removed = self.installer.uninstall_all(
                source,
                install_root,
                state_root,
                invoke=invoke,
            )

            self.assertEqual(removed["status"], "uninstalled")
            self.assertTrue(removed["changed"])
            self.assertFalse(install_root.exists())
            self.assertFalse((state_root / "install-state.json").exists())

    def test_portable_zip_source_install_repair_uninstall_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-installer-portable-") as temp:
            root = Path(temp)
            source = extract_portable_source(root)
            source_v1 = source
            source_v2 = root / "pala-project-studio-updated"
            shutil.copytree(source, source_v2)
            manifest_v1 = self.installer.manifest(source_v1)
            manifest_v2 = self.installer.manifest(source_v2)
            manifest_v2["version"] = "0.4.0+codex.rollback-test"
            (source_v2 / ".codex-plugin" / "plugin.json").write_text(
                json.dumps(manifest_v2), encoding="utf-8"
            )
            install_root = root / "clean" / "local" / "Pala" / "marketplace"
            state_root = root / "clean" / "local" / "Pala"
            marketplaces: list[dict[str, object]] = []
            installed: list[dict[str, object]] = []
            fail_update = {"value": False}
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
                if command == ("plugin", "add", self.installer.PLUGIN_ID, "--json"):
                    if fail_update["value"]:
                        raise RuntimeError("simulated Codex failure")
                    installed[:] = [
                        entry
                        for entry in installed
                        if entry.get("pluginId") != self.installer.PLUGIN_ID
                    ]
                    installed.append(
                        {
                            "pluginId": self.installer.PLUGIN_ID,
                            "name": "pala-project-studio",
                            "marketplaceName": "pala-project-studio",
                            "version": str(manifest_v1["version"]),
                            "installed": True,
                            "enabled": True,
                        }
                    )
                    return {"pluginId": self.installer.PLUGIN_ID}
                if command == (
                    "plugin",
                    "remove",
                    self.installer.PLUGIN_ID,
                    "--json",
                ):
                    installed[:] = [
                        entry
                        for entry in installed
                        if entry.get("pluginId") != self.installer.PLUGIN_ID
                    ]
                    return {"pluginId": self.installer.PLUGIN_ID}
                if command == (
                    "plugin",
                    "marketplace",
                    "remove",
                    "pala-project-studio",
                    "--json",
                ):
                    marketplaces[:] = [
                        entry
                        for entry in marketplaces
                        if entry.get("name") != "pala-project-studio"
                    ]
                    return {"marketplaceName": "pala-project-studio"}
                raise AssertionError(f"unexpected Codex command: {command}")

            initial_install = self.installer.install_all(
                source_v1,
                install_root,
                state_root,
                invoke=invoke,
            )
            self.assertEqual(initial_install["status"], "installed")
            self.assertTrue(initial_install["changed"])
            baseline_fingerprint = self.installer.tree_fingerprint(install_root)

            fail_update["value"] = True
            with self.assertRaises(RuntimeError):
                self.installer.install_all(
                    source_v2,
                    install_root,
                    state_root,
                    invoke=invoke,
                )

            self.assertEqual(
                self.installer.tree_fingerprint(install_root),
                baseline_fingerprint,
            )
            self.assertEqual(
                json.loads((state_root / "install-state.json").read_text(encoding="utf-8"))[
                "version"
                ],
                str(manifest_v1["version"]),
            )

            # cleanup after rollback is expected to keep the same ownership state
            calls.clear()
            uninstall = self.installer.uninstall_all(
                source_v1,
                install_root,
                state_root,
                invoke=invoke,
            )
            self.assertEqual(uninstall["status"], "uninstalled")
            self.assertFalse(install_root.exists())


if __name__ == "__main__":
    unittest.main()

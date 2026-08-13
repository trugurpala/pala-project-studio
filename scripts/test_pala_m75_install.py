#!/usr/bin/env python3
"""M75 RED contracts for complete bootstrap and ensure-current no-op."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent
INSTALLER_PATH = ROOT / "scripts" / "pala_installer.py"


def load_installer():
    spec = importlib.util.spec_from_file_location("pala_m75_installer", INSTALLER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pala_installer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest_json(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class FakeCodexPluginHost:
    """Small stateful Codex surface that exposes every mutating command."""

    def __init__(self, installer, install_root: Path, version: str) -> None:
        self.installer = installer
        self.install_root = install_root
        self.version = version
        self.marketplaces: list[dict[str, object]] = []
        self.installed: list[dict[str, object]] = []
        self.calls: list[tuple[str, ...]] = []

    def invoke(self, arguments: list[str]) -> dict[str, object]:
        command = tuple(arguments)
        self.calls.append(command)
        if command == ("plugin", "marketplace", "list", "--json"):
            return {"marketplaces": list(self.marketplaces)}
        if command == ("plugin", "list", "--json"):
            return {"installed": list(self.installed), "available": []}
        if command[:3] == ("plugin", "marketplace", "add"):
            self.marketplaces[:] = [
                {"name": "pala-project-studio", "root": str(self.install_root)}
            ]
            return {
                "marketplaceName": "pala-project-studio",
                "installedRoot": str(self.install_root),
                "alreadyAdded": False,
            }
        if command == ("plugin", "marketplace", "remove", "pala-project-studio", "--json"):
            self.marketplaces.clear()
            return {"marketplaceName": "pala-project-studio"}
        if command == ("plugin", "remove", self.installer.PLUGIN_ID, "--json"):
            self.installed.clear()
            return {"pluginId": self.installer.PLUGIN_ID}
        if command == ("plugin", "add", self.installer.PLUGIN_ID, "--json"):
            self.installed[:] = [
                {
                    "pluginId": self.installer.PLUGIN_ID,
                    "name": "pala-project-studio",
                    "marketplaceName": "pala-project-studio",
                    "version": self.version,
                    "installed": True,
                    "enabled": True,
                }
            ]
            return {"pluginId": self.installer.PLUGIN_ID}
        raise AssertionError(f"unexpected Codex command: {command}")

    @property
    def mutation_count(self) -> int:
        return sum(
            command[:3] == ("plugin", "marketplace", "add")
            or command[:2] in {("plugin", "add"), ("plugin", "remove")}
            for command in self.calls
        )


class M75InstallContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.installer = load_installer()
        cls.version = str(cls.installer.manifest(ROOT)["version"])
        cls.temporary = tempfile.TemporaryDirectory(prefix="pala-m75-bootstrap-")
        cls.codex_home = tempfile.TemporaryDirectory(prefix="pala-m75-codex-")
        cls.environment = patch.dict(os.environ, {"CODEX_HOME": cls.codex_home.name})
        cls.environment.start()
        root = Path(cls.temporary.name)
        cls.root = root
        cls.install_root = root / "Pala" / "marketplace"
        cls.state_root = root / "Pala"
        cls.host = FakeCodexPluginHost(cls.installer, cls.install_root, cls.version)
        cls.host.marketplaces[:] = [
            {"name": "pala-project-studio", "root": str(ROOT)}
        ]
        cls.host.installed[:] = [
            {
                "pluginId": cls.installer.PLUGIN_ID,
                "name": "pala-project-studio",
                "marketplaceName": "pala-project-studio",
                "version": cls.version,
                "installed": True,
                "enabled": True,
            }
        ]
        cls.first = cls.installer.install_all(
            ROOT,
            cls.install_root,
            cls.state_root,
            invoke=cls.host.invoke,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.environment.stop()
        cls.codex_home.cleanup()
        cls.temporary.cleanup()

    def _doctor(
        self,
        install_root: Path,
        state_root: Path,
        project_root: Path,
        host: FakeCodexPluginHost,
    ) -> dict[str, object]:
        with (
            patch.object(
                self.installer.shutil,
                "which",
                side_effect=lambda tool: f"C:/tools/{tool}.exe",
            ),
            patch.object(
                self.installer,
                "resolve_codex_executable",
                return_value=Path("C:/tools/codex.exe"),
            ),
            patch.object(
                self.installer,
                "project_doctor",
                return_value={"available": True},
            ),
        ):
            return self.installer.doctor_installation(
                ROOT,
                install_root,
                state_root,
                project_root,
                invoke=host.invoke,
            )

    def _fingerprints(
        self,
        install_root: Path,
        state_root: Path,
        host: FakeCodexPluginHost,
    ) -> dict[str, str | None]:
        def tree(path: Path) -> str | None:
            if not path.is_dir():
                return None
            digest = hashlib.sha256()
            for item in sorted(
                (candidate for candidate in path.rglob("*") if candidate.is_file()),
                key=lambda candidate: candidate.relative_to(path).as_posix().casefold(),
            ):
                digest.update(item.relative_to(path).as_posix().encode("utf-8"))
                digest.update(b"\0")
                digest.update(item.read_bytes())
                digest.update(b"\0")
            return digest.hexdigest()

        return {
            "plugin": digest_json(host.installed),
            "marketplace": digest_json(host.marketplaces),
            "runtime_bundle": tree(install_root),
            "codegraph": tree(state_root / "workbench" / "code_intelligence"),
            "semgrep": tree(state_root / "workbench" / "security_static"),
        }

    def test_natural_install_cannot_complete_without_required_workbench_and_healthy_doctor(
        self,
    ) -> None:
        doctor = self._doctor(
            self.install_root, self.state_root, self.root, self.host
        )

        self.assertTrue(self.first["changed"])
        self.assertTrue(self.install_root.is_dir(), "runtime bundle must be installed")
        self.assertIsNotNone(
            doctor["workbench"],
            "plugin/runtime-only installation must not be considered complete: "
            "required Workbench was not bootstrapped",
        )
        self.assertTrue(doctor["workbench"]["healthy"])
        self.assertEqual(
            doctor["workbench"]["capabilities"]["code_intelligence"]["state"],
            "exact",
        )
        self.assertEqual(
            doctor["workbench"]["capabilities"]["security_static"]["state"],
            "exact",
        )
        self.assertTrue(doctor["healthy"])
        self.assertTrue(doctor["plugin_ready"])
        self.assertTrue(doctor["version_ready"])

    def test_public_contract_forbids_plugin_only_success_in_the_first_conversation(
        self,
    ) -> None:
        surfaces = "\n".join(
            (ROOT / relative).read_text(encoding="utf-8")
            for relative in ("README.md", "README.tr.md", "docs/VIBE_INSTALL.md")
        ).casefold()
        for marker in (
            "plugin registration alone is not success",
            "yalnız eklentinin kaydedilmesi başarı değildir",
            "plugin list --json",
            "source.path",
            "install-pala.ps1",
            "codegraph exact/healthy",
            "semgrep exact/healthy",
            "aynı konuşmada seçileceğine",
        ):
            self.assertIn(marker, surfaces)

    def test_second_ensure_current_is_mutation_free_with_stable_complete_fingerprints(
        self,
    ) -> None:
        before = self._fingerprints(self.install_root, self.state_root, self.host)
        mutations_before = self.host.mutation_count

        second = self.installer.install_all(
            ROOT,
            self.install_root,
            self.state_root,
            invoke=self.host.invoke,
        )
        after = self._fingerprints(self.install_root, self.state_root, self.host)

        self.assertEqual(second["status"], "ready")
        self.assertEqual(second["installation_state"], "CURRENT")
        self.assertFalse(second["changed"])
        self.assertEqual(
            self.host.mutation_count,
            mutations_before,
            "CURRENT must short-circuit before marketplace/plugin mutation",
        )
        self.assertEqual(before, after, "CURRENT must preserve every fingerprint")
        self.assertTrue(
            all(before.values()),
            "a no-op is not proved unless plugin, marketplace, runtime, CodeGraph, "
            "and Semgrep fingerprints all exist",
        )


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contract tests for Pala-owned expert binary acquisition."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_module():
    spec = importlib.util.spec_from_file_location("pala_expert_installer", ROOT / "scripts" / "pala_expert_installer.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("pala_expert_installer.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pala_expert_installer"] = module
    spec.loader.exec_module(module)
    return module


class ExpertInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.installer = load_module()

    def test_verified_binary_is_owned_and_idempotent(self) -> None:
        payload = b"pala-owned-expert"
        spec = {"version": "1.0", "source_url": "https://example.invalid/expert", "sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            first = self.installer.install_binary("demo", spec, state, fetch=lambda _: payload)
            second = self.installer.install_binary("demo", spec, state, fetch=lambda _: (_ for _ in ()).throw(AssertionError("must not refetch")))
            self.assertEqual(first["state"], "ready")
            self.assertTrue(first["changed"])
            self.assertEqual(second["state"], "ready")
            self.assertFalse(second["changed"])
            self.assertEqual((state / "experts" / "demo" / "1.0" / "payload.bin").read_bytes(), payload)
            self.assertEqual(self.installer.inspect_binary("demo", spec, state)["state"], "ready")

    def test_hash_mismatch_never_activates_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            with self.assertRaises(ValueError):
                self.installer.install_binary("demo", {"version": "1.0", "source_url": "https://example.invalid", "sha256": "0" * 64}, state, fetch=lambda _: b"wrong")
            self.assertFalse((state / "experts" / "demo" / "1.0").exists())

    def test_inspection_reports_missing_and_modified_owned_payload(self) -> None:
        payload = b"pala-owned-expert"
        spec = {"version": "1.0", "source_url": "https://example.invalid/expert", "sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            self.assertEqual(self.installer.inspect_binary("demo", spec, state)["state"], "missing")
            self.installer.install_binary("demo", spec, state, fetch=lambda _: payload)
            (state / "experts" / "demo" / "1.0" / "payload.bin").write_bytes(b"modified")
            self.assertEqual(self.installer.inspect_binary("demo", spec, state)["state"], "external_conflict")

    def test_dry_run_does_not_create_expert_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            result = self.installer.install_binary("demo", {"version": "1.0", "source_url": "https://example.invalid", "sha256": "0" * 64}, state, dry_run=True)
            self.assertEqual(result["state"], "would_install")
            self.assertFalse(state.exists())

    def test_verified_zip_expands_atomically_and_returns_owned_executable(self) -> None:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("bin/codebase-memory-mcp.exe", b"owned executable")
        payload = buffer.getvalue()
        spec = {"version": "1.0", "source_url": "https://example.invalid/expert.zip", "sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            self.installer.install_binary("demo", spec, state, fetch=lambda _: payload)
            first = self.installer.expand_verified_zip("demo", spec, state, "bin/codebase-memory-mcp.exe")
            second = self.installer.expand_verified_zip("demo", spec, state, "bin/codebase-memory-mcp.exe")
            self.assertEqual(first["state"], "ready")
            self.assertTrue(first["changed"])
            self.assertEqual(second["state"], "ready")
            self.assertFalse(second["changed"])
            self.assertEqual(Path(str(first["executable"])).read_bytes(), b"owned executable")

    def test_zip_with_path_traversal_never_activates_expanded_files(self) -> None:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("../escape.exe", b"not allowed")
        payload = buffer.getvalue()
        spec = {"version": "1.0", "source_url": "https://example.invalid/expert.zip", "sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            self.installer.install_binary("demo", spec, state, fetch=lambda _: payload)
            with self.assertRaises(ValueError):
                self.installer.expand_verified_zip("demo", spec, state, "escape.exe")
            self.assertFalse((state / "experts" / "demo" / "1.0" / "expanded").exists())

    def test_python_tool_uses_only_pala_owned_uv_locations(self) -> None:
        payload = b"a verified wheel"
        spec = {"version": "1.0", "source_url": "https://example.invalid/expert.whl", "sha256": hashlib.sha256(payload).hexdigest()}
        calls: list[tuple[tuple[str, ...], dict[str, str]]] = []
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            self.installer.install_binary("graphify", spec, state, fetch=lambda _: payload)

            result = self.installer.install_python_tool(
                "graphify", spec, state, uv="uv.exe",
                run=lambda args, env: calls.append((args, env)) or 0,
            )

            self.assertEqual(result["state"], "ready")
            args, environment = calls[0]
            self.assertEqual(args[:3], ("uv.exe", "tool", "install"))
            self.assertIn("--no-python-downloads", args)
            self.assertIn("--no-build", args)
            self.assertEqual(environment["UV_TOOL_DIR"], str((state / "experts" / "python-tools").resolve()))
            self.assertEqual(environment["UV_TOOL_BIN_DIR"], str((state / "experts" / "python-bin").resolve()))


if __name__ == "__main__":
    unittest.main()

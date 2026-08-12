#!/usr/bin/env python3
"""Contract tests for Pala-owned expert binary acquisition."""

from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

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

    def test_fetch_rejects_non_https_before_any_network_access(self) -> None:
        for url in (
            "file:///C:/secret.txt",
            "http://example.invalid/expert",
            "data:text/plain,x",
            "https://TOKEN@example.invalid/expert",
            "https://example.invalid/expert?token=hidden",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    self.installer._fetch(url)

    def test_install_rejects_unsafe_url_even_with_an_injected_fetcher(self) -> None:
        payload = b"pala-owned-expert"
        spec = {
            "version": "1.0",
            "source_url": "file:///C:/secret.txt",
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                self.installer.install_binary(
                    "demo", spec, Path(temp) / "Pala", fetch=lambda _: payload
                )

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
        spec = {"version": "1.0", "source_url": "https://example.invalid/graphifyy-1.0-py3-none-any.whl", "sha256": hashlib.sha256(payload).hexdigest()}
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
            self.assertTrue(args[-1].endswith("graphifyy-1.0-py3-none-any.whl"))
            self.assertEqual(environment["UV_TOOL_DIR"], str((state / "experts" / "python-tools").resolve()))
            self.assertEqual(environment["UV_TOOL_BIN_DIR"], str((state / "experts" / "python-bin").resolve()))

    def test_python_tool_captures_uv_progress_outside_json_protocol(self) -> None:
        payload = b"a verified wheel"
        spec = {"version": "1.0", "source_url": "https://example.invalid/graphifyy-1.0-py3-none-any.whl", "sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            self.installer.install_binary("graphify", spec, state, fetch=lambda _: payload)

            with patch.object(self.installer.subprocess, "run") as run:
                run.return_value = subprocess.CompletedProcess(("uv.exe",), 0, stdout="", stderr="Resolved 30 packages\n")
                result = self.installer.install_python_tool("graphify", spec, state, uv="uv.exe")

            self.assertEqual(result["state"], "ready")
            self.assertTrue(run.call_args.kwargs["capture_output"])
            self.assertTrue(run.call_args.kwargs["text"])

    def test_suite_installs_only_declared_experts_in_pala_state(self) -> None:
        wheel = b"a verified wheel"
        archive = BytesIO()
        with zipfile.ZipFile(archive, "w") as zip_file:
            zip_file.writestr("codebase-memory-mcp.exe", b"exe")
            zip_file.writestr("ollama.exe", b"exe")
        zip_payload = archive.getvalue()
        lock = {
            "graphify": {"version": "1.0", "source_url": "https://example.invalid/graphify.whl", "sha256": hashlib.sha256(wheel).hexdigest()},
            "serena": {"version": "1.0", "source_url": "https://example.invalid/serena.whl", "sha256": hashlib.sha256(wheel).hexdigest()},
            "code-review-graph": {
                "version": "1.0",
                "source_url": "https://example.invalid/code_review_graph.whl",
                "sha256": hashlib.sha256(wheel).hexdigest(),
            },
            "codebase-memory": {"version": "1.0", "source_url": "https://example.invalid/cbm.zip", "sha256": hashlib.sha256(zip_payload).hexdigest()},
            "ollama": {"version": "1.0", "source_url": "https://example.invalid/ollama.zip", "sha256": hashlib.sha256(zip_payload).hexdigest()},
            "rtk": {"version": "1.0", "source_url": "https://example.invalid/rtk.exe", "sha256": hashlib.sha256(b"rtk").hexdigest()},
        }
        payloads = {entry["source_url"]: zip_payload if entry["source_url"].endswith(".zip") else wheel for entry in lock.values()}
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            report = self.installer.install_expert_suite(
                lock, state, fetch=lambda url: payloads[url], uv="uv.exe", run=lambda _args, _env: 0,
            )
            self.assertEqual(
                set(report["experts"]),
                {"graphify", "serena", "code-review-graph", "codebase-memory", "ollama"},
            )
            self.assertTrue(all(item["state"] == "ready" for item in report["experts"].values()))
            self.assertFalse((state / "experts" / "rtk").exists())

    def test_serena_build_exception_is_limited_to_its_pala_owned_tool(self) -> None:
        payload = b"a verified wheel"
        spec = {"version": "1.0", "source_url": "https://example.invalid/serena_agent-1.0-py3-none-any.whl", "sha256": hashlib.sha256(payload).hexdigest()}
        calls: list[tuple[str, ...]] = []
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            self.installer.install_binary("serena", spec, state, fetch=lambda _: payload)
            self.installer.install_python_tool("serena", spec, state, uv="uv.exe", allow_build=True, run=lambda args, _env: calls.append(args) or 0)
            self.assertNotIn("--no-build", calls[0])

    def test_model_inspection_requires_pala_host_and_pinned_identifier(self) -> None:
        spec = {"version": "qwen3:4b-instruct", "integrity": "ollama:0edcdef34593"}
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            executable = state / "experts" / "ollama" / "0.32.6" / "expanded" / "ollama.exe"
            executable.parent.mkdir(parents=True)
            executable.touch()
            result = self.installer.inspect_ollama_model(
                spec, state,
                run=lambda args, env: (args, env, 0, "qwen3:4b-instruct    0edcdef34593    2.5 GB\n"),
            )
            self.assertEqual(result["state"], "ready")
            self.assertEqual(result["environment"]["OLLAMA_HOST"], "127.0.0.1:11435")

    def test_powershell_installer_keeps_experts_explicit_and_nonfatal(self) -> None:
        """Core install stays local-first even when an optional worker is unavailable."""
        entry = (ROOT / "Install-Pala.ps1").read_text(encoding="utf-8")
        script = (ROOT / "scripts" / "Install-Pala.ps1").read_text(encoding="utf-8")

        self.assertIn("[switch]$InstallExperts", entry)
        self.assertIn('if ($InstallExperts) { $arguments["InstallExperts"] = $true }', entry)
        self.assertIn("[switch]$InstallExperts", script)
        self.assertIn("Uzman isciler varsayilan olarak kurulmaz", script)
        self.assertNotIn("if ($expertExit -ne 0) { exit $expertExit }", script)
        self.assertIn("return [pscustomobject]@{ Payload = $expertPayload; ExitCode = $expertExit }", script)

        opt_in_guard = script.index("if ($InstallExperts -and $expertInstall.ExitCode -eq 0)")
        model_call = script.index("Invoke-PalaLocalModel", opt_in_guard)
        self.assertGreater(model_call, opt_in_guard)


if __name__ == "__main__":
    unittest.main()

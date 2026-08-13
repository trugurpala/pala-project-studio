from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_artifact import IGNORED_ARTIFACT_PARTS
from pala_codegraph import (
    CODEGRAPH_SHA256,
    CODEGRAPH_VERSION,
    codegraph_environment,
    evaluate_freshness,
    lifecycle_commands,
    mcp_server_record,
)
from pala_codegraph_mcp import build_command as build_mcp_command, main as mcp_main
from pala_codegraph_runner import main as runner_main
from pala_quality_discovery import DISCOVERY_SKIP_DIRS, IGNORED_CHANGE_PREFIXES
from pala_state_core import IGNORED_DISCOVERY_DIRS
from pala_workbench_install import ArtifactSpec, install_zip_transaction, inventory


def _zip_payload() -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("bundle/node.exe", b"fake-node")
        archive.writestr("bundle/lib/dist/bin/codegraph.js", b"fake-entry")
        archive.writestr("bundle/bin/codegraph.cmd", b"@echo off\r\n")
    return stream.getvalue()


class WorkbenchTransactionTests(unittest.TestCase):
    def _spec(self, payload: bytes) -> ArtifactSpec:
        return ArtifactSpec(
            capability_id="code_intelligence",
            provider="CodeGraph",
            version="1.5.0",
            source_url="https://example.invalid/codegraph.zip",
            sha256=hashlib.sha256(payload).hexdigest(),
            owner="pala-project-studio",
        )

    def test_verified_zip_is_health_probed_then_atomically_activated(self) -> None:
        payload = _zip_payload()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            seen: list[Path] = []

            def probe(path: Path) -> dict[str, object]:
                seen.append(path)
                self.assertTrue((path / "bundle" / "node.exe").is_file())
                return {"status": "passed", "version": "1.5.0"}

            result = install_zip_transaction(
                self._spec(payload), root, executable="bundle/node.exe",
                fetch=lambda _url: payload, health_probe=probe,
            )
            state = inventory(self._spec(payload), root, executable="bundle/node.exe")

            self.assertEqual(result["state"], "exact")
            self.assertEqual(state["state"], "exact")
            self.assertEqual(state["health"], "passed")
            self.assertEqual(len(seen), 1)
            self.assertNotIn("PATH", json.dumps(result))
            self.assertEqual(
                json.loads((root / "workbench" / "code_intelligence" / "active.json").read_text(encoding="utf-8"))["version"],
                "1.5.0",
            )

    def test_hash_or_health_failure_preserves_previous_activation(self) -> None:
        payload = _zip_payload()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            active = root / "workbench" / "code_intelligence" / "active.json"
            active.parent.mkdir(parents=True)
            active.write_text(
                '{"owner":"pala-project-studio","version":"1.4.0"}\n',
                encoding="utf-8",
            )
            before = active.read_bytes()
            bad = self._spec(payload)
            bad = ArtifactSpec(**{**bad.__dict__, "sha256": "0" * 64})
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                install_zip_transaction(
                    bad, root, executable="bundle/node.exe", fetch=lambda _url: payload,
                    health_probe=lambda _path: {"status": "passed", "version": "1.5.0"},
                )
            self.assertEqual(active.read_bytes(), before)
            with self.assertRaisesRegex(RuntimeError, "health"):
                install_zip_transaction(
                    self._spec(payload), root, executable="bundle/node.exe",
                    fetch=lambda _url: payload,
                    health_probe=lambda _path: {"status": "blocked", "version": "1.5.0"},
                )
            self.assertEqual(active.read_bytes(), before)
            self.assertFalse((active.parent / "versions" / "1.5.0").exists())

    def test_foreign_version_directory_is_preserved(self) -> None:
        payload = _zip_payload()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            foreign = root / "workbench" / "code_intelligence" / "versions" / "1.5.0"
            foreign.mkdir(parents=True)
            sentinel = foreign / "user.txt"
            sentinel.write_text("keep", encoding="utf-8")
            result = install_zip_transaction(
                self._spec(payload), root, executable="bundle/node.exe",
                fetch=lambda _url: payload,
                health_probe=lambda _path: {"status": "passed", "version": "1.5.0"},
            )
            self.assertEqual(result["state"], "foreign")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_foreign_active_provider_is_preserved_without_fetch_or_takeover(self) -> None:
        payload = _zip_payload()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "workbench" / "code_intelligence"
            foreign = base / "versions" / "9.9.0"
            foreign.mkdir(parents=True)
            sentinel = foreign / "owner-data.txt"
            sentinel.write_text("keep", encoding="utf-8")
            active = base / "active.json"
            active.write_text('{"owner":"user","version":"9.9.0"}\n', encoding="utf-8")
            fetch_count = 0

            def fetch(_url: str) -> bytes:
                nonlocal fetch_count
                fetch_count += 1
                return payload

            result = install_zip_transaction(
                self._spec(payload), root, executable="bundle/node.exe",
                fetch=fetch,
                health_probe=lambda _path: {"status": "passed", "version": "1.5.0"},
            )
            self.assertEqual(result["state"], "foreign")
            self.assertFalse(result["changed"])
            self.assertEqual(fetch_count, 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            self.assertEqual(json.loads(active.read_text(encoding="utf-8"))["version"], "9.9.0")

    def test_inventory_distinguishes_absent_foreign_owner_and_old_activation(self) -> None:
        payload = _zip_payload()
        spec = self._spec(payload)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(inventory(spec, root, executable="bundle/node.exe")["state"], "absent")
            active = root / "workbench" / "code_intelligence" / "active.json"
            active.parent.mkdir(parents=True)
            active.write_text('{"owner":"user","version":"1.5.0"}\n', encoding="utf-8")
            self.assertEqual(inventory(spec, root, executable="bundle/node.exe")["state"], "foreign")
            active.write_text(
                '{"owner":"pala-project-studio","version":"1.4.0"}\n', encoding="utf-8"
            )
            old = inventory(spec, root, executable="bundle/node.exe")
            self.assertEqual((old["state"], old["version"]), ("old", "1.4.0"))
            active.write_text(
                '{"owner":"pala-project-studio","version":"1.5.0"}\n', encoding="utf-8"
            )
            exact_without_attestation = inventory(spec, root, executable="bundle/node.exe")
            self.assertEqual(exact_without_attestation["state"], "foreign")
            self.assertEqual(exact_without_attestation["health"], "blocked")

    def test_transaction_rejects_non_bytes_missing_executable_and_missing_probe(self) -> None:
        payload = _zip_payload()
        spec = self._spec(payload)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(TypeError, "return bytes"):
                install_zip_transaction(
                    spec, root, executable="bundle/node.exe", fetch=lambda _url: "not-bytes"
                )
            missing_stream = io.BytesIO()
            with zipfile.ZipFile(missing_stream, "w") as archive:
                archive.writestr("bundle/readme.txt", b"missing executable")
            missing_payload = missing_stream.getvalue()
            missing_spec = self._spec(missing_payload)
            with self.assertRaisesRegex(ValueError, "required executable"):
                install_zip_transaction(
                    missing_spec,
                    root,
                    executable="bundle/node.exe",
                    fetch=lambda _url: missing_payload,
                    health_probe=lambda _path: {"status": "passed", "version": "1.5.0"},
                )
            with self.assertRaisesRegex(ValueError, "explicit health probe"):
                install_zip_transaction(
                    spec, root, executable="bundle/node.exe", fetch=lambda _url: payload
                )

    def test_artifact_identity_and_source_fail_closed(self) -> None:
        payload = _zip_payload()
        values = self._spec(payload).__dict__
        for mutation, message in (
            ({"capability_id": "../escape"}, "unsafe"),
            ({"source_url": "http://example.invalid/tool.zip"}, "HTTPS"),
            ({"source_url": "https://user:secret@example.invalid/tool.zip"}, "credential-free"),
            ({"sha256": "bad"}, "SHA-256"),
        ):
            with self.subTest(mutation=mutation):
                with self.assertRaisesRegex(ValueError, message):
                    ArtifactSpec(**{**values, **mutation})


class CodeGraphContractTests(unittest.TestCase):
    def test_quality_runner_requires_current_graph_and_supports_explicit_state_root(self) -> None:
        with patch(
            "pala_codegraph_runner.run_lifecycle",
            return_value={"status": "passed", "freshness": "current"},
        ) as lifecycle:
            self.assertEqual(
                runner_main(["--project", ".", "--state-root", "C:/Pala"]),
                0,
            )
        self.assertEqual(lifecycle.call_args.args[1], "pre-quality")
        self.assertEqual(lifecycle.call_args.kwargs["state_root"], Path("C:/Pala").resolve())

        with patch(
            "pala_codegraph_runner.run_lifecycle",
            return_value={"status": "blocked", "freshness": "stale"},
        ):
            self.assertEqual(runner_main(["--state-root", "C:/Pala"]), 2)

    def test_mcp_launcher_uses_only_the_pala_runtime_and_propagates_exit_status(self) -> None:
        runtime = {
            "node": Path("C:/Pala/node.exe"),
            "entry": Path("C:/Pala/codegraph.js"),
        }
        with patch("pala_codegraph_mcp.runtime_paths", return_value=runtime):
            command = build_mcp_command(Path("C:/work/project"), Path("C:/Pala"))
        self.assertEqual(command[-2:], ("--mcp", "--no-watch"))
        self.assertNotIn("install", " ".join(command).casefold())

        class Result:
            returncode = 7

        with patch("pala_codegraph_mcp.runtime_paths", return_value=runtime), patch(
            "pala_codegraph_mcp.subprocess.run", return_value=Result()
        ) as run:
            self.assertEqual(
                mcp_main(["--project", "C:/work/project", "--state-root", "C:/Pala"]),
                7,
            )
        environment = run.call_args.kwargs["env"]
        self.assertEqual(environment["CODEGRAPH_NO_WATCH"], "1")

        with patch("pala_codegraph_mcp.runtime_paths", return_value=runtime), patch(
            "pala_codegraph_mcp.subprocess.run", side_effect=OSError("unavailable")
        ):
            self.assertEqual(
                mcp_main(["--project", "C:/work/project", "--state-root", "C:/Pala"]),
                1,
            )

    def test_locked_official_contract_and_bounded_environment(self) -> None:
        self.assertEqual(CODEGRAPH_VERSION, "1.5.0")
        self.assertEqual(
            CODEGRAPH_SHA256,
            "d6798622b4f44ee6757c94335f437ee27a9ff7d3537b554cb6a2b3baf11bc4a1",
        )
        env = codegraph_environment()
        self.assertEqual(env["DO_NOT_TRACK"], "1")
        self.assertEqual(env["CODEGRAPH_TELEMETRY"], "0")
        self.assertEqual(env["CODEGRAPH_NO_UPDATE_CHECK"], "1")
        self.assertEqual(env["CODEGRAPH_NO_WATCH"], "1")
        self.assertEqual(
            set(env),
            {"DO_NOT_TRACK", "CODEGRAPH_TELEMETRY", "CODEGRAPH_NO_UPDATE_CHECK", "CODEGRAPH_NO_WATCH"},
        )

    def test_lifecycle_never_invokes_third_party_installers_or_background_modes(self) -> None:
        executable = Path("C:/Pala/codegraph.cmd")
        project = Path("C:/work/project")
        expected = {
            "project-takeover": ("init", "sync", "status"),
            "pre-context": ("sync", "status", "explore"),
            "post-implementation": ("sync", "status", "impact"),
            "pre-quality": ("sync", "status"),
        }
        for stage, command_names in expected.items():
            commands = lifecycle_commands(
                executable, project, stage, query="task semantics", symbol="TargetSymbol"
            )
            self.assertEqual(tuple(command[1] for command in commands), command_names)
            flattened = " ".join(part for command in commands for part in command).casefold()
            for forbidden in (" install", " upgrade", " telemetry", " daemon", " config"):
                self.assertNotIn(forbidden, f" {flattened}")

    def test_stale_unavailable_or_failed_graph_falls_back_and_is_not_quality_evidence(self) -> None:
        healthy = {
            "initialized": True,
            "version": "1.5.0",
            "lastIndexed": "2026-08-12T12:00:00.000Z",
            "pendingChanges": {"added": 0, "modified": 0, "removed": 0},
            "worktreeMismatch": None,
            "index": {"state": "complete", "pendingRefs": 0, "reindexRecommended": False},
        }
        self.assertEqual(evaluate_freshness(healthy, sync_exit_code=0)["status"], "passed")
        for mutation in (
            {"initialized": False},
            {"pendingChanges": {"added": 0, "modified": 1, "removed": 0}},
            {"index": {"state": "partial", "pendingRefs": 0, "reindexRecommended": False}},
            {"index": {"state": "complete", "pendingRefs": 2, "reindexRecommended": False}},
            {"worktreeMismatch": {"worktreeRoot": "a", "indexRoot": "b"}},
        ):
            result = evaluate_freshness({**healthy, **mutation}, sync_exit_code=0)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["fallback"], "direct-source")
            self.assertFalse(result["quality_evidence_eligible"])
        failed = evaluate_freshness(None, sync_exit_code=1)
        self.assertEqual(failed["fallback"], "direct-source")
        self.assertFalse(failed["quality_evidence_eligible"])

    def test_plugin_scoped_mcp_exposes_only_explore_through_pala_wrapper(self) -> None:
        record = mcp_server_record(Path("C:/work/project"))
        serialized = json.dumps(record, sort_keys=True)
        self.assertIn("pala_codegraph_mcp.py", serialized)
        self.assertEqual(record["tools"], ["codegraph_explore"])
        self.assertNotIn("CODEGRAPH_MCP_TOOLS", record["env"])
        self.assertNotIn("codegraph install", serialized.casefold())
        self.assertNotIn("dashboard", serialized.casefold())

    def test_codegraph_generated_state_is_filtered_without_requiring_project_gitignore(self) -> None:
        self.assertIn(".codegraph", IGNORED_DISCOVERY_DIRS)
        self.assertIn(".codegraph", DISCOVERY_SKIP_DIRS)
        self.assertIn(".codegraph", IGNORED_ARTIFACT_PARTS)
        self.assertIn(".codegraph/", IGNORED_CHANGE_PREFIXES)


if __name__ == "__main__":
    unittest.main()

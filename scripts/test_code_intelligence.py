#!/usr/bin/env python3
"""Contract tests for Pala's optional code-intelligence integration."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


code_intel = load_module("pala_code_intel", SCRIPTS / "pala_code_intel.py")
packager = load_module("pala_build_portable", SCRIPTS / "build_portable.py")


class CodeIntelligenceTests(unittest.TestCase):
    def test_github_router_prefers_connector_then_gh_then_redacted_git(self) -> None:
        github = load_module("pala_github", SCRIPTS / "pala_github.py")
        self.assertEqual(github.GitHubRouter(connector_available=True, gh_path="gh").inspect(ROOT)["route"], "connector")
        self.assertEqual(github.GitHubRouter(gh_path="gh").inspect(ROOT)["route"], "gh")
        self.assertEqual(
            github.GitHubRouter._redact("https://token@example.com/owner/repo.git"),
            "https://example.com/owner/repo.git",
        )
    def test_graph_thresholds_only_enable_large_or_cross_module_work(self) -> None:
        self.assertFalse(code_intel.graph_eligible(999, 49, 3))
        self.assertTrue(code_intel.graph_eligible(1000, 1, 1))
        self.assertTrue(code_intel.graph_eligible(1, 50, 1))
        self.assertTrue(code_intel.graph_eligible(1, 1, 4))

    def test_graph_can_be_disabled_when_working_off_budget(self) -> None:
        self.assertFalse(code_intel.graph_eligible(2_000, 2_000, 8, use_graph=False))

    def test_missing_graph_tool_has_honest_local_fallback(self) -> None:
        with patch.object(code_intel.shutil, "which", return_value=None):
            result = code_intel.status(None)
        self.assertFalse(result["available"])
        self.assertFalse(result["graph_exists"])
        self.assertIn("git diff", result["note"])
        self.assertNotIn("installed", result["note"].casefold())

    def test_existing_graph_is_reported_without_reading_its_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".code-review-graph").mkdir()
            with patch.object(code_intel.shutil, "which", return_value="crg"):
                result = code_intel.status(root)
        self.assertTrue(result["available"])
        self.assertTrue(result["graph_exists"])

    def test_uv_tool_install_is_found_without_changing_user_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "code-review-graph.exe"
            binary.touch()
            tool_dir = Mock(returncode=0, stdout=temp)
            with (
                patch.object(
                    code_intel.shutil,
                    "which",
                    side_effect=lambda name: "uv" if name == "uv" else None,
                ),
                patch.object(code_intel.subprocess, "run", return_value=tool_dir),
            ):
                result = code_intel.status(None)
        self.assertTrue(result["available"])
        self.assertEqual(result["executable"], str(binary))

    def test_readonly_probes_timeout_to_the_existing_safe_fallback(self) -> None:
        with (
            patch.object(
                code_intel.shutil,
                "which",
                side_effect=lambda name: "uv" if name == "uv" else None,
            ),
            patch.object(
                code_intel.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(["uv"], 5),
            ) as run,
        ):
            self.assertIsNone(code_intel.find_executable())
        self.assertEqual(run.call_args.kwargs["timeout"], code_intel.READ_ONLY_TIMEOUT_SECONDS)
        self.assertFalse(run.call_args.kwargs["shell"])

        with (
            patch.object(code_intel.shutil, "which", return_value="git"),
            patch.object(
                code_intel.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(["git"], 5),
            ) as run,
        ):
            self.assertIsNone(code_intel.git_root(ROOT))
        self.assertEqual(run.call_args.kwargs["timeout"], code_intel.READ_ONLY_TIMEOUT_SECONDS)
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_github_remote_timeout_is_unknown_not_a_route_or_secret_claim(self) -> None:
        github = load_module("pala_github_timeout", SCRIPTS / "pala_github.py")
        with (
            patch.object(github.shutil, "which", return_value="git"),
            patch.object(
                github.subprocess,
                "run",
                side_effect=subprocess.TimeoutExpired(["git"], 5),
            ) as run,
        ):
            result = github.GitHubRouter(gh_path="").inspect(ROOT)
        self.assertEqual(
            result,
            {"route": "git", "write_capability": "none", "remote": None},
        )
        self.assertEqual(run.call_args.kwargs["timeout"], github.READ_ONLY_TIMEOUT_SECONDS)
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_update_uses_bounded_brief_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            completed = Mock(returncode=0)
            with (
                patch.object(code_intel.shutil, "which", return_value="crg"),
                patch.object(code_intel.subprocess, "run", return_value=completed) as run,
            ):
                self.assertEqual(code_intel.run_graph(root, "update"), 0)
        self.assertEqual(run.call_args.args[0], ["crg", "update", "--brief"])
        env = run.call_args.kwargs["env"]
        self.assertIsNot(env, os.environ)
        self.assertEqual(env.get("PYTHONUTF8"), "1")

    def test_graph_execution_timeout_is_returned_as_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with (
                patch.object(code_intel.shutil, "which", return_value="crg"),
                patch.object(
                    code_intel.subprocess,
                    "run",
                    side_effect=subprocess.TimeoutExpired(["crg"], 30),
                ) as run,
            ):
                self.assertEqual(code_intel.run_graph(root, "review"), 124)
        self.assertEqual(run.call_args.kwargs["timeout"], code_intel.EXECUTION_TIMEOUT_SECONDS)
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_installer_keeps_codex_config_and_graph_build_opt_in(self) -> None:
        installer = (SCRIPTS / "install_code_intelligence.ps1").read_text(
            encoding="utf-8"
        )
        compact = "".join(installer.split())
        self.assertIn("[switch]$ConfigureCodex", compact)
        self.assertIn("[switch]$BuildGraph", compact)
        self.assertNotIn("SkipCodexConfig", installer)
        self.assertNotIn("SkipBuild", installer)
        self.assertIn("if($ConfigureCodex)", compact)
        self.assertIn("if($BuildGraph)", compact)

    def test_portable_package_includes_adapter_installer_and_notice(self) -> None:
        names = {
            path.relative_to(ROOT).as_posix()
            for path in packager.source_files(ROOT)
        }
        self.assertIn("scripts/pala_code_intel.py", names)
        self.assertIn("scripts/install_code_intelligence.ps1", names)
        self.assertIn("THIRD_PARTY_NOTICES.md", names)

    def test_skill_routes_large_reviews_to_bounded_graph_guidance(self) -> None:
        skill = (ROOT / "skills/pala-project-finisher/SKILL.md").read_text(
            encoding="utf-8"
        )
        reference = (
            ROOT / "skills/pala-project-finisher/references/code-intelligence.md"
        ).read_text(encoding="utf-8")
        self.assertIn("(references/code-intelligence.md)", skill)
        self.assertIn("false positives", reference.casefold())
        self.assertIn("small", reference.casefold())
        self.assertIn("verify", reference.casefold())


if __name__ == "__main__":
    unittest.main()

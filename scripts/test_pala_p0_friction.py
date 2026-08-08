#!/usr/bin/env python3
"""P0 friction contracts: script paths, begin --goal DX, complete recovery."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_CATALOG_TMP: tempfile.TemporaryDirectory | None = None
_CATALOG_PREV: str | None = None
_DB_PREV: str | None = None


def setUpModule() -> None:
    global _CATALOG_TMP, _CATALOG_PREV, _DB_PREV
    _CATALOG_PREV = os.environ.get("PALA_CATALOG_ROOT")
    _DB_PREV = os.environ.get("PALA_DB_PATH")
    _CATALOG_TMP = tempfile.TemporaryDirectory()
    os.environ["PALA_CATALOG_ROOT"] = _CATALOG_TMP.name
    os.environ["PALA_DB_PATH"] = str(Path(_CATALOG_TMP.name) / "pala.sqlite")


def tearDownModule() -> None:
    global _CATALOG_TMP, _CATALOG_PREV, _DB_PREV
    if _CATALOG_PREV is None:
        os.environ.pop("PALA_CATALOG_ROOT", None)
    else:
        os.environ["PALA_CATALOG_ROOT"] = _CATALOG_PREV
    if _DB_PREV is None:
        os.environ.pop("PALA_DB_PATH", None)
    else:
        os.environ["PALA_DB_PATH"] = _DB_PREV
    if _CATALOG_TMP is not None:
        _CATALOG_TMP.cleanup()
        _CATALOG_TMP = None


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
PLUGIN_ROOT = SCRIPT_DIR.parent
SKILL = PLUGIN_ROOT / "skills" / "pala-project-finisher" / "SKILL.md"
CODE_INTEL = (
    PLUGIN_ROOT
    / "skills"
    / "pala-project-finisher"
    / "references"
    / "code-intelligence.md"
)


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pala_state = load_module("pala_state_p0", "pala_state.py")
pala_store = load_module("pala_store_p0", "pala_store.py")
pala_paths = load_module("pala_paths_p0", "pala_paths.py")


class ScriptPathFrictionTests(unittest.TestCase):
    def test_skill_does_not_instruct_relative_scripts_from_project_cwd(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        self.assertNotIn("../../scripts/", skill)
        self.assertNotIn("..\\..\\scripts\\", skill)
        lowered = skill.casefold()
        self.assertTrue(
            "localappdata" in lowered or "marketplace" in lowered or "pala_state" in lowered,
            "skill must guide marketplace/absolute or pala_state entrypoints",
        )
        self.assertIn("--goal", skill)

    def test_code_intelligence_ref_avoids_broken_relative_script_path(self) -> None:
        text = CODE_INTEL.read_text(encoding="utf-8")
        self.assertNotIn("../../scripts/", text)

    def test_resolve_pala_scripts_dir_prefers_env_then_plugin_then_marketplace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scripts = root / "scripts"
            scripts.mkdir()
            (scripts / "pala_state.py").write_text("# stub\n", encoding="utf-8")
            with patch.dict(os.environ, {"PALA_SCRIPTS_DIR": str(scripts)}, clear=False):
                self.assertEqual(pala_paths.resolve_pala_scripts_dir(), scripts.resolve())

            market = root / "market" / "scripts"
            market.mkdir(parents=True)
            (market / "pala_state.py").write_text("# stub\n", encoding="utf-8")
            env = {
                "PALA_SCRIPTS_DIR": "",
                "PALA_MARKETPLACE_ROOT": str(root / "market"),
                "LOCALAPPDATA": str(root / "local"),
            }
            with patch.dict(os.environ, env, clear=False):
                os.environ.pop("PALA_SCRIPTS_DIR", None)
                self.assertEqual(
                    pala_paths.resolve_pala_scripts_dir(), market.resolve()
                )

            # Dev checkout: module next to pala_state.py
            with patch.dict(os.environ, {"LOCALAPPDATA": str(root / "empty")}, clear=False):
                os.environ.pop("PALA_SCRIPTS_DIR", None)
                os.environ.pop("PALA_MARKETPLACE_ROOT", None)
                resolved = pala_paths.resolve_pala_scripts_dir()
                self.assertTrue((resolved / "pala_state.py").is_file())


class BeginGoalDxTests(unittest.TestCase):
    def test_begin_help_documents_required_goal(self) -> None:
        import argparse

        root = pala_state.parser()
        begin = None
        for action in root._actions:
            if isinstance(action, argparse._SubParsersAction):
                begin = action.choices.get("begin")
                break
        self.assertIsNotNone(begin)
        help_text = begin.format_help()
        self.assertIn("--goal", help_text)
        sink = io.StringIO()
        with patch.object(sys, "stderr", sink):
            with self.assertRaises(SystemExit) as ctx:
                root.parse_args(["begin", "--ticket", "T-1"])
        self.assertEqual(ctx.exception.code, 2)
        err = sink.getvalue()
        self.assertIn("--goal", err)
        self.assertRegex(err, r"(?i)zorunlu|gerekli")
        self.assertRegex(err, r"(?i)örnek|begin")

    def test_begin_parser_accepts_goal_example_shape(self) -> None:
        args = pala_state.parser().parse_args(
            ["begin", "--ticket", "M29-T1", "--goal", "tek sonraki iş"]
        )
        self.assertEqual(args.goal, "tek sonraki iş")
        self.assertEqual(args.ticket, "M29-T1")


class CompleteTicketRecoveryTests(unittest.TestCase):
    def test_begin_without_session_writes_v3_ticket_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            pala_state.begin_work(root, "P0-T1", "Friction fix")
            store = pala_store.WorkflowStore(root)
            record = store._read(store._ticket_path("P0-T1"))
            self.assertIsNotNone(record)
            self.assertEqual(record["ticket"], "P0-T1")
            self.assertEqual(record["goal"], "Friction fix")
            self.assertTrue(record["dirty"])
            self.assertTrue((root / pala_state.WORKFLOW).is_file())

    def test_complete_missing_ticket_prints_actionable_recovery_not_soft_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            stderr = io.StringIO()
            with patch.object(sys, "argv", [
                "pala_state.py",
                "complete",
                "--cwd",
                str(root),
                "--ticket",
                "MISSING-1",
                "--session-key",
                "session-alpha",
            ]):
                with patch.object(sys, "stderr", stderr):
                    code = pala_state.main()
            self.assertEqual(code, 2)
            err = stderr.getvalue()
            self.assertRegex(err, r"(?i)begin")
            self.assertRegex(err, r"(?i)session|oturum|--session-key")
            self.assertRegex(err, r"(?i)register|goal|--goal")
            self.assertNotRegex(err, r"(?i)\b(bitti|done|ok)\b")

    def test_complete_happy_path_after_begin_with_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            pala_state.begin_work(
                root, "P0-T2", "Ship recovery", session="session-alpha"
            )
            store = pala_store.WorkflowStore(root)
            store.record_verification(
                "P0-T2",
                "session-alpha",
                "passed",
                "py -3 -m unittest scripts.test_pala_p0_friction",
            )
            stderr = io.StringIO()
            stdout = io.StringIO()
            with patch.object(sys, "argv", [
                "pala_state.py",
                "complete",
                "--cwd",
                str(root),
                "--ticket",
                "P0-T2",
                "--session-key",
                "session-alpha",
            ]):
                with patch.object(sys, "stderr", stderr), patch.object(sys, "stdout", stdout):
                    # Disable fail-closed gate by ensuring no open INC / empty docs
                    with patch(
                        "pala_debug_gate.complete_fail_closed",
                        return_value={"allowed": True, "reason": ""},
                    ):
                        code = pala_state.main()
            self.assertEqual(code, 0, msg=stderr.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "completed")

    def test_lifecycle_register_begin_checkpoint_context_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            for name, body in (
                ("PROJECT.md", "# Project\n"),
                ("PLAN.md", "# Plan\n\n#### P0-LIFE — lifecycle\n"),
                ("STATUS.md", "# Status\n\n- Active: P0-LIFE\n"),
                ("AGENTS.md", "# Agents\n"),
                ("DECISIONS.md", "# Decisions\n"),
                (
                    "DEBUGGING.md",
                    "# Debugging log\n\n## Format\n\n"
                    "Symptoms, Root cause, Fix criteria, Proved by, "
                    "Related files, Date, Status.\n\n## Incidents\n\n",
                ),
            ):
                (root / name).write_text(body, encoding="utf-8", newline="\n")

            def run(argv: list[str]) -> tuple[int, str, str]:
                out, err = io.StringIO(), io.StringIO()
                with patch.object(sys, "argv", ["pala_state.py", *argv]):
                    with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                        code = pala_state.main()
                return code, out.getvalue(), err.getvalue()

            code, out, err = run(["register", "--cwd", str(root)])
            self.assertEqual(code, 0, msg=err)
            code, out, err = run(
                [
                    "begin",
                    "--cwd",
                    str(root),
                    "--ticket",
                    "P0-LIFE",
                    "--goal",
                    "lifecycle smoke",
                    "--session-key",
                    "life-session",
                ]
            )
            self.assertEqual(code, 0, msg=err)
            code, out, err = run(
                [
                    "checkpoint",
                    "--cwd",
                    str(root),
                    "--ticket",
                    "P0-LIFE",
                    "--session-key",
                    "life-session",
                    "--next-action",
                    "complete",
                ]
            )
            self.assertEqual(code, 0, msg=err)
            code, out, err = run(
                ["context", "--cwd", str(root), "--session-key", "life-session"]
            )
            self.assertEqual(code, 0, msg=err)
            ctx = json.loads(out)
            self.assertIn("cmd_memory", ctx)
            # Checkpoint clears owner; recover is the safe reconcile before complete.
            code, out, err = run(
                [
                    "recover",
                    "--cwd",
                    str(root),
                    "--ticket",
                    "P0-LIFE",
                    "--session-key",
                    "life-session",
                ]
            )
            self.assertEqual(code, 0, msg=err)
            code, out, err = run(
                [
                    "record-verification",
                    "--cwd",
                    str(root),
                    "--ticket",
                    "P0-LIFE",
                    "--session-key",
                    "life-session",
                    "--status",
                    "passed",
                    "--command",
                    "unittest",
                ]
            )
            self.assertEqual(code, 0, msg=err)
            with patch(
                "pala_debug_gate.complete_fail_closed",
                return_value={"allowed": True, "reason": ""},
            ):
                code, out, err = run(
                    [
                        "complete",
                        "--cwd",
                        str(root),
                        "--ticket",
                        "P0-LIFE",
                        "--session-key",
                        "life-session",
                    ]
                )
            self.assertEqual(code, 0, msg=err)
            self.assertEqual(json.loads(out)["status"], "completed")


class PathFailureMemoryTests(unittest.TestCase):
    def test_second_cold_session_does_not_re_suggest_same_path_failure(self) -> None:
        pala_cmd_memory = load_module("pala_cmd_memory_p0", "pala_cmd_memory.py")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "pala.sqlite"
            cmd = "py -3 ../../scripts/pala_report.py --cwd ."
            err = "No such file: ../../scripts/pala_report.py"
            first = pala_cmd_memory.remember_and_guard(
                root=root,
                command=cmd,
                exit_code=2,
                stderr=err,
                failure_class="wrong_plugin_script_path",
                path=db,
            )
            self.assertTrue(first["allowed"])
            # Second cold session shares SQLite path only.
            blocked = pala_cmd_memory.guard_retry(
                command=cmd,
                failure_class="wrong_plugin_script_path",
                stderr=err,
                path=db,
            )
            self.assertFalse(blocked["allowed"])
            self.assertTrue(blocked["do_not_retry"])
            hint = pala_cmd_memory.context_packet_hint(path=db)
            self.assertIsNotNone(hint)
            self.assertIn("do not retry", (hint or "").casefold())


class LauncherSurfaceTests(unittest.TestCase):
    def test_pala_script_helper_points_at_resolved_dir(self) -> None:
        target = pala_paths.pala_script("pala_report.py")
        self.assertEqual(target.name, "pala_report.py")
        self.assertTrue(target.parent.is_dir())
        self.assertEqual(target.parent, pala_paths.resolve_pala_scripts_dir())

    def test_all_skill_references_avoid_relative_scripts(self) -> None:
        refs = PLUGIN_ROOT / "skills" / "pala-project-finisher" / "references"
        for path in refs.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("../../scripts/", text, msg=str(path))
            self.assertNotIn("..\\..\\scripts\\", text, msg=str(path))


if __name__ == "__main__":
    unittest.main()

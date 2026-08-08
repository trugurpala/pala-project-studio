#!/usr/bin/env python3
"""Contract tests for M29-T2 failed command/path memory guard."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pala_cmd_memory
import pala_db

_ENV_TMP: tempfile.TemporaryDirectory | None = None
_ENV_PREV: dict[str, str | None] = {}


def setUpModule() -> None:
    global _ENV_TMP
    _ENV_TMP = tempfile.TemporaryDirectory()
    for name in ("PALA_CATALOG_ROOT", "PALA_DB_PATH"):
        _ENV_PREV[name] = os.environ.get(name)
    os.environ["PALA_CATALOG_ROOT"] = _ENV_TMP.name
    os.environ["PALA_DB_PATH"] = str(Path(_ENV_TMP.name) / "pala.sqlite")


def tearDownModule() -> None:
    global _ENV_TMP
    for name, value in _ENV_PREV.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
    if _ENV_TMP is not None:
        _ENV_TMP.cleanup()
        _ENV_TMP = None


class NormalizeAndClassifyTests(unittest.TestCase):
    def test_normalize_command_family_from_relative_scripts_path(self) -> None:
        family = pala_cmd_memory.normalize_command_family(
            "py -3 ../../scripts/pala_report.py --cwd ."
        )
        self.assertEqual(family, "pala_report.py")

    def test_classify_wrong_plugin_script_path(self) -> None:
        klass = pala_cmd_memory.classify_failure(
            command="py -3 ../../scripts/pala_state.py discover",
            stderr="can't open file '.../../../scripts/pala_state.py': No such file",
            exit_code=2,
        )
        self.assertEqual(klass, "wrong_plugin_script_path")

    def test_failure_classes_cover_required_set(self) -> None:
        required = {
            "wrong_plugin_script_path",
            "tool_not_found",
            "trusted_repo",
            "browser_unavailable",
            "permission_policy",
            "no_network",
            "timeout_hook",
        }
        self.assertTrue(required.issubset(set(pala_cmd_memory.FAILURE_CLASSES)))


class ToolAttemptStoreTests(unittest.TestCase):
    def test_upsert_bumps_repeat_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "t.sqlite"
            first = pala_db.upsert_tool_attempt(
                command_family="pala_report.py",
                failure_class="wrong_plugin_script_path",
                os_name="Windows",
                shell="powershell",
                profile="default",
                resolution="use pala_paths",
                path=db,
            )
            self.assertEqual(first["repeat_count"], 1)
            second = pala_db.upsert_tool_attempt(
                command_family="pala_report.py",
                failure_class="wrong_plugin_script_path",
                os_name="Windows",
                shell="powershell",
                profile="default",
                path=db,
            )
            self.assertEqual(second["repeat_count"], 2)
            self.assertIn("tool_attempt", pala_db.EVENT_KINDS)


class GuardRetryTests(unittest.TestCase):
    def test_second_same_path_failure_is_blocked(self) -> None:
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
            self.assertTrue(first["recorded"])
            self.assertTrue((root / "DEBUGGING.md").is_file())
            text = (root / "DEBUGGING.md").read_text(encoding="utf-8")
            self.assertIn("do not retry", text.casefold())
            self.assertIn("wrong_plugin_script_path", text)

            second = pala_cmd_memory.remember_and_guard(
                root=root,
                command=cmd,
                exit_code=2,
                stderr=err,
                failure_class="wrong_plugin_script_path",
                path=db,
            )
            self.assertFalse(second["allowed"])
            self.assertTrue(second["do_not_retry"])
            self.assertTrue(second["require_approval"])
            self.assertIn("prior", (second.get("message") or "").casefold())

            approved = pala_cmd_memory.guard_retry(
                command=cmd,
                failure_class="wrong_plugin_script_path",
                stderr=err,
                approve_retry=True,
                path=db,
            )
            self.assertTrue(approved["allowed"])

    def test_context_hint_emits_do_not_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            pala_cmd_memory.record_failure(
                command="py -3 ../../scripts/pala_state.py",
                exit_code=2,
                stderr="No such file",
                failure_class="wrong_plugin_script_path",
                path=db,
            )
            hint = pala_cmd_memory.context_packet_hint(path=db)
            self.assertIsNotNone(hint)
            self.assertIn("do not retry", (hint or "").casefold())


if __name__ == "__main__":
    unittest.main()

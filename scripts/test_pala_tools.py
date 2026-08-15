#!/usr/bin/env python3
"""Unit tests for the deterministic Pala project-state helpers."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

_CATALOG_TMP: tempfile.TemporaryDirectory | None = None
_CATALOG_PREV: str | None = None
_DB_PREV: str | None = None
_REG_PREV: str | None = None


def setUpModule() -> None:
    """Isolate the cross-project catalog so tests never touch the real one."""
    global _CATALOG_TMP, _CATALOG_PREV, _DB_PREV, _REG_PREV
    _CATALOG_PREV = os.environ.get("PALA_CATALOG_ROOT")
    _DB_PREV = os.environ.get("PALA_DB_PATH")
    _REG_PREV = os.environ.get("PALA_PROVISION_REGISTRY")
    _CATALOG_TMP = tempfile.TemporaryDirectory()
    os.environ["PALA_CATALOG_ROOT"] = _CATALOG_TMP.name
    os.environ["PALA_DB_PATH"] = str(Path(_CATALOG_TMP.name) / "pala.sqlite")
    os.environ["PALA_PROVISION_REGISTRY"] = str(
        Path(_CATALOG_TMP.name) / "provision-registry.json"
    )


def tearDownModule() -> None:
    global _CATALOG_TMP, _CATALOG_PREV, _DB_PREV, _REG_PREV
    if _CATALOG_PREV is None:
        os.environ.pop("PALA_CATALOG_ROOT", None)
    else:
        os.environ["PALA_CATALOG_ROOT"] = _CATALOG_PREV
    if _DB_PREV is None:
        os.environ.pop("PALA_DB_PATH", None)
    else:
        os.environ["PALA_DB_PATH"] = _DB_PREV
    if _REG_PREV is None:
        os.environ.pop("PALA_PROVISION_REGISTRY", None)
    else:
        os.environ["PALA_PROVISION_REGISTRY"] = _REG_PREV
    if _CATALOG_TMP is not None:
        _CATALOG_TMP.cleanup()
        _CATALOG_TMP = None

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
SKILL_DIR = SCRIPT_DIR.parent / "skills" / "pala-project-finisher"
REFERENCE_DIR = SKILL_DIR / "references"
REQUIRED_PROFILES = (
    "project-intake.md",
    "reuse-or-build.md",
    "architecture-selection.md",
    "greenfield-scaffolding.md",
    "frontend-engineering.md",
    "backend-engineering.md",
    "modularity-budgets.md",
    "runtime-delivery.md",
)
NEW_REQUIRED_REFERENCES = (
    "github-persistence.md",
    "owner-demo-handoff.md",
    "token-efficient-context.md",
)


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pala_state_git = load_module("pala_state_git", "pala_state_git.py")
pala_state = load_module("pala_state", "pala_state.py")
pala_state_core = sys.modules["pala_state_core"]
pala_state_documents = load_module(
    "pala_state_documents", "pala_state_documents.py"
)
pala_store = load_module("pala_store", "pala_store.py")
pala_hook = load_module("pala_hook", "pala_hook.py")
pala_memory = load_module("pala_memory", "pala_memory.py")


class PalaStateTests(unittest.TestCase):
    def test_git_runner_is_shell_free_and_time_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            completed = subprocess.CompletedProcess(
                args=["git"], returncode=0, stdout="value\n"
            )
            with (
                patch.object(pala_state_git.shutil, "which", return_value="C:/tools/git.exe"),
                patch.object(pala_state_git.subprocess, "run", return_value=completed) as runner,
            ):
                result = pala_state._run_git_process(
                    root, ("rev-parse", "HEAD"), text=True
                )

            self.assertIs(result, completed)
            self.assertEqual(runner.call_count, 1)
            call = runner.call_args
            self.assertEqual(call.args[0], ["C:/tools/git.exe", "rev-parse", "HEAD"])
            self.assertFalse(call.kwargs["shell"])
            self.assertEqual(call.kwargs["timeout"], pala_state.GIT_TIMEOUT_SECONDS)
            self.assertIs(pala_state._run_git_process, pala_state_git._run_git_process)

    def test_git_timeout_or_missing_binary_keeps_state_commands_conservative(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with (
                patch.object(pala_state_git.shutil, "which", return_value="C:/tools/git.exe"),
                patch.object(
                    pala_state_git.subprocess,
                    "run",
                    side_effect=subprocess.TimeoutExpired(["git"], 5),
                ),
            ):
                self.assertEqual(pala_state.git_root(root), root.resolve())
                self.assertIsNone(pala_state.run_git(root, "rev-parse", "HEAD"))
                self.assertIsNone(pala_state.run_git_bytes(root, "status"))
                self.assertFalse(pala_state.git_is_ancestor(root, "before", "after"))

            with patch.object(pala_state_git.shutil, "which", return_value=None), patch.object(
                pala_state_git.subprocess, "run"
            ) as runner:
                self.assertEqual(pala_state.git_root(root), root.resolve())
                self.assertIsNone(pala_state.run_git(root, "rev-parse", "HEAD"))
                self.assertIsNone(pala_state.run_git_bytes(root, "status"))
                self.assertFalse(pala_state.git_is_ancestor(root, "before", "after"))
            runner.assert_not_called()

    def test_rtk_rewrites_only_simple_read_only_commands(self) -> None:
        rtk = load_module("pala_rtk", "pala_rtk.py")
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "rtk.exe"
            binary.write_text("", encoding="utf-8")
            original = {"command": "git status", "timeout_ms": 10, "cwd": "C:/project"}
            result = rtk.rewrite("git status", original, binary)

            self.assertEqual(result["timeout_ms"], 10)
            self.assertEqual(result["cwd"], "C:/project")
            self.assertIn("RTK_TELEMETRY_DISABLED", result["env"])
            for unsafe in ("git commit -m x", "rg x | sort", "grep password .", "npm install"):
                self.assertIsNone(rtk.rewrite(unsafe, original, binary))

    def test_rtk_rejects_newline_and_line_separator_injection(self) -> None:
        rtk = load_module("pala_rtk_newline", "pala_rtk.py")
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "rtk.exe"
            binary.write_text("", encoding="utf-8")
            original = {"command": "git status", "timeout_ms": 10, "cwd": "C:/project"}
            for unsafe in (
                "git status\nrm -rf /",
                "git status\r\necho pwned",
                "rg foo\u2028echo pwned",
                "rg foo\u2029Write-Host pwned",
                "git\nstatus",
            ):
                self.assertIsNone(
                    rtk.rewrite(unsafe, original, binary),
                    msg=f"expected refuse for {unsafe!r}",
                )
            safe = rtk.rewrite("git status", original, binary)
            self.assertIsNotNone(safe)
            self.assertNotIn("\n", safe["command"])
            self.assertNotIn("\r", safe["command"])
    def test_openspec_adapter_is_read_only_for_present_and_absent_projects(self) -> None:
        adapter = load_module("pala_openspec", "pala_openspec.py").OpenSpecAdapter()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(adapter.inspect(root).state, "missing")
            (root / "openspec" / "specs").mkdir(parents=True)
            result = adapter.inspect(root)

            self.assertEqual(result.state, "ready")
            self.assertFalse(result.changed)
            self.assertFalse((root / "openspec" / "changes").exists())
    def test_ticket_record_serializes_bounded_safe_session_state(self) -> None:
        models = load_module("pala_models", "pala_models.py")
        record = models.TicketRecord.new("PALA-043", "A" * 900, "session-alpha")

        payload = record.to_dict()

        self.assertEqual(payload["schema_version"], 3)
        self.assertEqual(len(payload["goal"]), 500)
        self.assertNotIn("session-alpha", json.dumps(payload))
        self.assertEqual(payload["verification"], [])

    def test_ticket_store_records_failure_fingerprint_and_blocks_second_repeat(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = pala_store.WorkflowStore(Path(temp))
            store.claim("PALA-043", "Verify state", "session-alpha")

            first = store.record_verification(
                "PALA-043", "session-alpha", "failed", "py -3 scripts/verify.py", "ValueError: bad state"
            )
            second = store.record_verification(
                "PALA-043", "session-alpha", "failed", "py -3 scripts/verify.py", "ValueError: bad state"
            )

            self.assertEqual(first.status, "recorded")
            self.assertEqual(second.status, "blocked")
            self.assertEqual(
                second.record["blockers"], ["verification repeated twice", "verification budget exhausted"]
            )

    def test_ticket_store_records_first_causal_error_and_blocks_timeout_after_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = pala_store.WorkflowStore(Path(temp))
            store.claim("PALA-043", "Verify state", "session-alpha")

            first = store.record_verification(
                "PALA-043",
                "session-alpha",
                "timeout",
                "py -3 scripts/verify.py",
                "Timed out after 5s",
            )
            second = store.record_verification(
                "PALA-043",
                "session-alpha",
                "timeout",
                "py -3 scripts/verify.py",
                "Timed out after 5s",
            )

            self.assertEqual(first.status, "recorded")
            self.assertEqual(second.status, "blocked")
            self.assertIn("verification budget exhausted", second.record["blockers"])
            failure = second.record["first_verification_failure"]
            self.assertIsInstance(failure, dict)
            self.assertEqual(failure["status"], "timeout")
            self.assertEqual(failure["command"], "py -3 scripts/verify.py")

    def test_ticket_store_treats_not_run_as_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = pala_store.WorkflowStore(Path(temp))
            store.claim("PALA-043", "Incomplete safely", "session-alpha")
            store.record_verification(
                "PALA-043", "session-alpha", "not-run", "py -3 scripts/verify.py"
            )

            completed = store.complete("PALA-043", "session-alpha")

            self.assertEqual(completed.status, "verification_required")

    def test_ticket_store_complete_requires_passed_evidence_and_no_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = pala_store.WorkflowStore(Path(temp))
            store.claim("PALA-043", "Complete safely", "session-alpha", acceptance=["verification passes"])

            refused = store.complete("PALA-043", "session-alpha")
            store.record_verification(
                "PALA-043", "session-alpha", "passed", "py -3 scripts/verify.py"
            )
            completed = store.complete("PALA-043", "session-alpha")

            self.assertEqual(refused.status, "verification_required")
            self.assertEqual(completed.status, "verification_required")
            self.assertEqual(completed.record["lifecycle"], "active")
            self.assertTrue(completed.record["dirty"])

    def test_complete_clears_only_matching_clean_legacy_active_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy_path = root / ".codex" / "pala-workflow.json"
            legacy_path.parent.mkdir()
            legacy = {
                "schema_version": 2,
                "active_ticket": "PALA-046",
                "goal": "Finish reconciliation",
                "dirty": False,
                "next_action": "owner: commit/push/tag/release",
                "verification": ["ticket=passed"],
            }
            legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
            store = pala_store.WorkflowStore(root)
            store.claim("PALA-046", "Finish reconciliation", "session-alpha", acceptance=["verification passes"])
            store.record_verification(
                "PALA-046", "session-alpha", "passed", "py -3 scripts/verify.py"
            )

            completed = pala_state.complete_work(root, "PALA-046", "session-alpha")
            reconciled = json.loads(legacy_path.read_text(encoding="utf-8"))

            self.assertEqual(completed.status, "verification_required")
            self.assertEqual(reconciled, legacy)
            self.assertEqual(reconciled["next_action"], "owner: commit/push/tag/release")
            self.assertEqual(reconciled["verification"], ["ticket=passed"])

    def test_complete_preserves_other_or_dirty_legacy_workflow(self) -> None:
        for legacy_ticket, dirty in (("PALA-OTHER", False), ("PALA-046", True)):
            with self.subTest(legacy_ticket=legacy_ticket, dirty=dirty), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                legacy_path = root / ".codex" / "pala-workflow.json"
                legacy_path.parent.mkdir()
                legacy = {
                    "schema_version": 2,
                    "active_ticket": legacy_ticket,
                    "goal": "Leave untouched",
                    "dirty": dirty,
                    "next_action": "continue safely",
                }
                legacy_path.write_text(json.dumps(legacy), encoding="utf-8")
                store = pala_store.WorkflowStore(root)
                store.claim("PALA-046", "Finish reconciliation", "session-alpha", acceptance=["verification passes"])
                store.record_verification(
                    "PALA-046", "session-alpha", "passed", "py -3 scripts/verify.py"
                )

                completed = pala_state.complete_work(root, "PALA-046", "session-alpha")

                self.assertEqual(completed.status, "verification_required")
                self.assertEqual(json.loads(legacy_path.read_text(encoding="utf-8")), legacy)

    def test_ticket_store_recovery_does_not_take_over_dirty_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = pala_store.WorkflowStore(Path(temp))
            store.claim("PALA-043", "Recover safely", "session-alpha")

            result = store.recover("PALA-043", "session-beta")

            self.assertEqual(result.status, "dirty_takeover_refused")

    def test_v2_migration_writes_marker_without_modifying_legacy_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = root / ".codex" / "pala-workflow.json"
            legacy.parent.mkdir()
            legacy.write_text(json.dumps({"schema_version": 2, "active_ticket": "PALA-042"}), encoding="utf-8")

            result = pala_store.WorkflowStore(root).migrate_v2()

            self.assertEqual(result.status, "migrated")
            self.assertTrue((root / ".codex" / "plugin-data" / "pala" / "v3" / "migration-v2.json").is_file())
            self.assertEqual(json.loads(legacy.read_text(encoding="utf-8"))["active_ticket"], "PALA-042")
    def test_session_key_is_stable_and_does_not_expose_raw_session_id(self) -> None:
        raw_session_id = "session-alpha"

        self.assertTrue(hasattr(pala_state, "session_key"))
        key = pala_state.session_key(raw_session_id)

        self.assertEqual(key, hashlib.sha256(raw_session_id.encode()).hexdigest()[:24])
        self.assertNotIn(raw_session_id, key)

    def test_ticket_store_rejects_second_session_claim(self) -> None:
        store_path = SCRIPT_DIR / "pala_store.py"
        self.assertTrue(store_path.is_file())
        pala_store = load_module("pala_store", "pala_store.py")

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = pala_store.WorkflowStore(root).claim(
                ticket="PALA-043", goal="Session ownership", session="first-session"
            )
            second = pala_store.WorkflowStore(root).claim(
                ticket="PALA-043", goal="Session ownership", session="second-session"
            )

            self.assertEqual(first.status, "claimed")
            self.assertEqual(second.status, "owned_by_other")
            self.assertEqual(second.record["owner"], pala_state.session_key("first-session"))

    def test_ticket_store_does_not_overwrite_when_ticket_lock_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            store = load_module("pala_store_lock", "pala_store.py").WorkflowStore(root)
            ticket_path = store._ticket_path("PALA-043")
            lock_path = ticket_path.with_suffix(".lock")
            lock_path.parent.mkdir(parents=True)
            lock_path.mkdir()

            result = store.claim("PALA-043", "Concurrent claim", "session-alpha")

            self.assertEqual(result.status, "busy")
            self.assertFalse(ticket_path.exists())

    def test_ticket_checkpoint_releases_clean_ownership_for_next_session(self) -> None:
        store_path = SCRIPT_DIR / "pala_store.py"
        self.assertTrue(store_path.is_file())
        pala_store = load_module("pala_store_checkpoint", "pala_store.py")

        with tempfile.TemporaryDirectory() as temp:
            store = pala_store.WorkflowStore(Path(temp))
            store.claim("PALA-043", "Session ownership", "first-session")

            checkpoint = store.checkpoint(
                ticket="PALA-043", session="first-session", next_action="Resume safely"
            )
            resumed = store.claim(
                ticket="PALA-043", goal="Session ownership", session="second-session"
            )

            self.assertEqual(checkpoint.status, "checkpointed")
            self.assertIsNone(checkpoint.record["owner"])
            self.assertFalse(checkpoint.record["dirty"])
            self.assertEqual(resumed.status, "claimed")

    def test_begin_with_session_key_claims_v3_ticket_without_changing_v2_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()

            pala_state.begin_work(
                root,
                "PALA-043",
                "Session ownership",
                session="first-session",
            )

            store = load_module("pala_store_facade", "pala_store.py").WorkflowStore(root)
            record = store._read(store._ticket_path("PALA-043"))
            self.assertEqual(record["owner"], pala_state.session_key("first-session"))
            self.assertFalse((root / pala_state.WORKFLOW).exists())

    def test_begin_without_session_key_respects_active_parallel_v3_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            pala_state.begin_work(root, "PALA-043", "Parallel session work", session="session-alpha")
            with self.assertRaises(ValueError) as context:
                pala_state.begin_work(root, "PALA-044", "Independent ticket")
            self.assertIn("session-key", str(context.exception))

    def test_begin_parser_accepts_optional_session_key(self) -> None:
        args = pala_state.parser().parse_args(
            ["begin", "--ticket", "PALA-043", "--goal", "Session ownership", "--session-key", "abc123"]
        )

        self.assertEqual(args.session_key, "abc123")

    def test_begin_parser_accepts_repeatable_acceptance(self) -> None:
        args = pala_state.parser().parse_args(
            ["begin", "--ticket", "PALA-043", "--goal", "Session ownership", "--acceptance", "tests pass", "--acceptance", "reviewed"]
        )

        self.assertEqual(args.acceptance, ["tests pass", "reviewed"])

    def test_session_context_reads_only_its_owned_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            (root / pala_state.MANIFEST).write_text(
                json.dumps(
                    {
                        "schema_version": pala_state.SCHEMA_VERSION,
                        "managed_by": "pala-project-finisher",
                        "documents": {"status": "STATUS.md", "plan": "PLAN.md"},
                    }
                ),
                encoding="utf-8",
            )
            store = pala_store.WorkflowStore(root)
            store.claim("PALA-043", "Owned work", "session-alpha")

            report = pala_state.context_report(root, session="session-alpha")

            self.assertEqual(report["active_ticket"], "PALA-043")
            self.assertTrue(report["dirty"])
            self.assertFalse(report["reconciliation"]["needed"])

    def test_session_parser_options_are_available_without_changing_legacy_flags(self) -> None:
        args = pala_state.parser().parse_args(
            ["checkpoint", "--next-action", "Continue", "--session-key", "abc123"]
        )
        self.assertEqual(args.session_key, "abc123")
        args = pala_state.parser().parse_args(["context", "--session-key", "abc123"])
        self.assertEqual(args.session_key, "abc123")

    def test_v3_lifecycle_commands_require_explicit_session_key(self) -> None:
        parser = pala_state.parser()
        args = parser.parse_args(
            ["record-verification", "--ticket", "PALA-043", "--session-key", "abc123", "--status", "passed", "--command", "py -3 scripts/verify.py"]
        )
        self.assertEqual(args.command, "record-verification")
        self.assertEqual(
            parser.parse_args(["complete", "--ticket", "PALA-043", "--session-key", "abc123"]).command,
            "complete",
        )
        self.assertEqual(
            parser.parse_args(["recover", "--ticket", "PALA-043", "--session-key", "abc123"]).command,
            "recover",
        )

    def test_session_doctor_reports_only_owned_v3_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pala_store.WorkflowStore(root).claim("PALA-043", "Doctor session", "session-alpha")

            report = pala_state.doctor_report(root, session="session-alpha")

            self.assertEqual(report["session_ticket"]["ticket"], "PALA-043")
            self.assertNotIn("session-alpha", json.dumps(report))

    def test_discover_recognizes_alternative_documents_and_laravel_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "docs").mkdir()
            (root / "reports").mkdir()
            (root / "docs" / "SCOPE.md").write_text("# Scope\n", encoding="utf-8")
            (root / "docs" / "IMPLEMENTATION_PLAN.md").write_text(
                "# Plan\n", encoding="utf-8"
            )
            (root / "reports" / "CURRENT_STATUS.md").write_text(
                "# Status\n", encoding="utf-8"
            )
            (root / "reports" / "OWNER_DEMO.md").write_text(
                "# Owner demo\n", encoding="utf-8"
            )
            (root / "docs" / "PRODUCT_DECISIONS.md").write_text(
                "# Decisions\n", encoding="utf-8"
            )
            (root / "docs" / "OPEN_SOURCE.md").write_text(
                "# Open source\n", encoding="utf-8"
            )
            (root / "composer.json").write_text(
                json.dumps({"require": {"laravel/framework": "^13.0"}}),
                encoding="utf-8",
            )

            result = pala_state.discover(root)

            self.assertEqual(result["documents"]["project"], "docs/SCOPE.md")
            self.assertEqual(
                result["documents"]["plan"], "docs/IMPLEMENTATION_PLAN.md"
            )
            self.assertEqual(
                result["documents"]["status"], "reports/CURRENT_STATUS.md"
            )
            self.assertEqual(
                result["documents"]["decisions"], "docs/PRODUCT_DECISIONS.md"
            )
            self.assertEqual(
                result["documents"]["open_source"], "docs/OPEN_SOURCE.md"
            )
            self.assertEqual(
                result["documents"]["demo"], "reports/OWNER_DEMO.md"
            )
            self.assertIn("backend-engineering", result["profiles"])

    def test_discover_reuses_existing_project_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("README.md", "TASKS.md", "PROJECT_STATE.md"):
                (root / name).write_text("# Existing\n", encoding="utf-8")
            result = pala_state.discover(root)
            self.assertEqual(result["documents"]["project"], "README.md")
            self.assertEqual(result["documents"]["plan"], "TASKS.md")
            self.assertEqual(result["documents"]["status"], "PROJECT_STATE.md")

    def test_normalize_rejects_document_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                pala_state.normalize_document(root, str(root.parent / "outside.md"))

    def test_register_and_validate_existing_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("README.md", "TASKS.md", "PROJECT_STATE.md"):
                (root / name).write_text("# Existing\n", encoding="utf-8")
            args = Namespace(
                instructions=None,
                project=None,
                plan=None,
                status=None,
                decisions=None,
                open_source=None,
                demo=None,
            )
            self.assertEqual(pala_state.register(args, root), 0)
            self.assertEqual(pala_state.validate(root), 0)
            payload = json.loads((root / pala_state.MANIFEST).read_text("utf-8"))
            self.assertEqual(payload["documents"]["status"], "PROJECT_STATE.md")
            self.assertEqual(payload["project_kind"], "greenfield")
            self.assertIn("runtime-delivery", payload["profiles"])

    def test_instruction_chain_prefers_override_and_reports_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / "apps" / "web"
            nested.mkdir(parents=True)
            (root / "AGENTS.md").write_text("root", encoding="utf-8")
            (nested.parent / "AGENTS.md").write_text("ignored", encoding="utf-8")
            (nested.parent / "AGENTS.override.md").write_text(
                "override", encoding="utf-8"
            )
            report = pala_state.instruction_report(root, nested, 32_768, ())
            self.assertEqual(
                report["selected"],
                ["AGENTS.md", "apps/AGENTS.override.md"],
            )
            self.assertTrue(report["within_budget"])

    def test_configured_instruction_report_is_callable(self) -> None:
        report = pala_state_documents.configured_instruction_report(
            SCRIPT_DIR.parent, SCRIPT_DIR.parent
        )
        self.assertIn("config", report)

    def test_explicit_workflow_checkpoint_controls_dirty_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            pala_state.begin_work(root, "T-001", "Implement the narrow fix")
            active = pala_state.load_workflow(root)
            self.assertTrue(active["dirty"])
            self.assertEqual(active["active_ticket"], "T-001")
            pala_state.checkpoint_work(
                root,
                next_action="Run full verification",
                verification=["pytest: passed"],
                blockers=[],
                tier="ticket",
            )
            checkpoint = pala_state.load_workflow(root)
            self.assertFalse(checkpoint["dirty"])
            self.assertEqual(checkpoint["next_action"], "Run full verification")
            self.assertEqual(checkpoint["verification"], ["pytest: passed"])
            self.assertEqual(checkpoint["verification_tier"], "ticket")
            self.assertIn("checkpoint_basis", checkpoint)

    def test_checkpoint_matching_status_successor_is_not_a_memory_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            status_path = root / "STATUS.md"
            status_path.write_text("# Status\n\n- Next: M43-T3 continue\n", encoding="utf-8")
            manifest = {
                "schema_version": 1,
                "managed_by": "pala-project-finisher",
                "documents": {"status": "STATUS.md"},
            }
            (root / pala_state.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
            pala_state.begin_work(root, "M43-T2", "Verify baseline")

            pala_state.checkpoint_work(
                root,
                next_action="M43-T3 continue",
                verification=["unittest=passed"],
                blockers=[],
                tier="ticket",
            )

            checkpoint = pala_state.load_workflow(root)
            self.assertFalse(checkpoint["needs_reconcile"])
            self.assertNotIn("## Memory mismatch", status_path.read_text(encoding="utf-8"))

    def test_session_checkpoint_also_closes_matching_v2_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            pala_state.begin_work(root, "M43-T4", "Unify checkpoint state")
            with patch.object(
                sys,
                "argv",
                [
                    "pala_state.py",
                    "checkpoint",
                    "--cwd",
                    str(root),
                    "--ticket",
                    "M43-T4",
                    "--session-key",
                    "pala-local",
                    "--next-action",
                    "M43-T5 continue",
                    "--verification",
                    "unit=passed",
                ],
            ):
                self.assertEqual(pala_state.main(), 0)

            workflow = pala_state.load_workflow(root)
            self.assertFalse(workflow["dirty"])
            self.assertEqual(workflow["next_action"], "M43-T5 continue")

    def test_checkpoint_different_status_successor_remains_a_memory_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            status_path = root / "STATUS.md"
            status_path.write_text("# Status\n\n- Next: M43-T4 continue\n", encoding="utf-8")
            manifest = {
                "schema_version": 1,
                "managed_by": "pala-project-finisher",
                "documents": {"status": "STATUS.md"},
            }
            (root / pala_state.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
            pala_state.begin_work(root, "M43-T2", "Verify baseline")

            pala_state.checkpoint_work(
                root,
                next_action="M43-T3 continue",
                verification=["unittest=passed"],
                blockers=[],
                tier="ticket",
            )

            checkpoint = pala_state.load_workflow(root)
            self.assertTrue(checkpoint["needs_reconcile"])
            self.assertIn("## Memory mismatch", status_path.read_text(encoding="utf-8"))

    def test_checkpoint_detects_registered_document_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            for name in ("PROJECT.md", "PLAN.md", "STATUS.md"):
                (root / name).write_text(f"# {name}\n", encoding="utf-8")
            manifest = {
                "schema_version": 1,
                "managed_by": "pala-project-finisher",
                "documents": {
                    "project": "PROJECT.md",
                    "plan": "PLAN.md",
                    "status": "STATUS.md",
                },
            }
            (root / pala_state.MANIFEST).write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            pala_state.begin_work(root, "T-001", "Implement one outcome")
            pala_state.checkpoint_work(
                root,
                next_action="Continue with T-002",
                verification=["unit: passed"],
                blockers=[],
                tier="ticket",
            )
            workflow = pala_state.load_workflow(root)
            self.assertFalse(
                pala_state.reconciliation_report(root, manifest, workflow)["needed"]
            )

            (root / "PLAN.md").write_text("# Changed plan\n", encoding="utf-8")
            report = pala_state.reconciliation_report(root, manifest, workflow)

            self.assertTrue(report["needed"])
            self.assertIn("plan changed since checkpoint", report["reasons"])

    def test_doctor_reports_hook_safety_block_and_recommendation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = {
                "schema_version": 1,
                "managed_by": "pala-project-finisher",
                "documents": {
                    "project": "PROJECT.md",
                    "plan": "PLAN.md",
                    "status": "STATUS.md",
                },
            }
            (root / ".codex").mkdir()
            (root / "PROJECT.md").write_text("# Project\n", encoding="utf-8")
            (root / "PLAN.md").write_text("# Plan\n", encoding="utf-8")
            (root / "STATUS.md").write_text("# Status\n", encoding="utf-8")
            (root / ".codex" / "pala-project.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            (root / ".codex" / "pala-workflow.json").write_text(
                json.dumps({"schema_version": 2, "active_ticket": "T-001"}),
                encoding="utf-8",
            )
            report = pala_state.doctor_report(root)
            self.assertIn("hook_safety", report)
            self.assertIn("recommendation", report["hook_safety"])
            self.assertEqual(report["hook_safety"]["status"], "blocked")

    def test_doctor_reports_checkpoint_reconciliation_when_documents_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            for name in ("PROJECT.md", "PLAN.md", "STATUS.md"):
                (root / name).write_text(f"# {name}\n", encoding="utf-8")
            manifest = {
                "schema_version": 1,
                "managed_by": "pala-project-finisher",
                "documents": {
                    "project": "PROJECT.md",
                    "plan": "PLAN.md",
                    "status": "STATUS.md",
                },
            }
            (root / pala_state.MANIFEST).write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            pala_state.begin_work(root, "T-001", "Verify doctor reconciliation")
            pala_state.checkpoint_work(
                root,
                next_action="Continue",
                verification=["unit: passed"],
                blockers=[],
                tier="ticket",
            )
            (root / "PLAN.md").write_text("# Changed plan\n", encoding="utf-8")

            report = pala_state.doctor_report(root)

            self.assertTrue(report["hook_discovery"]["needs_reconcile"])

    def test_checkpoint_command_requires_verification_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            for name in ("PROJECT.md", "PLAN.md", "STATUS.md"):
                (root / name).write_text(f"# {name}\n", encoding="utf-8")
            (root / ".codex" / "pala-project.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "managed_by": "pala-project-finisher",
                        "documents": {
                            "project": "PROJECT.md",
                            "plan": "PLAN.md",
                            "status": "STATUS.md",
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(
                sys, "argv", ["pala_state.py", "checkpoint", "--cwd", temp, "--next-action", "re-check"]
            ):
                self.assertEqual(pala_state.main(), 2)

    def test_checkpoint_detects_content_change_while_git_status_stays_modified(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            for name in ("PROJECT.md", "PLAN.md", "STATUS.md"):
                (root / name).write_text(f"# {name}\n", encoding="utf-8")
            (root / "app.txt").write_text("version one\n", encoding="utf-8")
            manifest = {
                "schema_version": 1,
                "managed_by": "pala-project-finisher",
                "documents": {
                    "project": "PROJECT.md",
                    "plan": "PLAN.md",
                    "status": "STATUS.md",
                },
            }
            (root / pala_state.MANIFEST).write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "add", "."], cwd=root, check=True, capture_output=True
            )
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Pala Tests",
                    "-c",
                    "user.email=pala-tests@example.invalid",
                    "commit",
                    "-m",
                    "fixture",
                ],
                cwd=root,
                check=True,
                capture_output=True,
            )

            (root / "app.txt").write_text("version two\n", encoding="utf-8")
            pala_state.begin_work(root, "T-002", "Track changed content")
            pala_state.checkpoint_work(
                root,
                next_action="Continue later",
                verification=["narrow: passed"],
                blockers=[],
                tier="narrow",
            )
            workflow = pala_state.load_workflow(root)
            self.assertFalse(
                pala_state.reconciliation_report(root, manifest, workflow)["needed"]
            )

            (root / "app.txt").write_text("version three\n", encoding="utf-8")
            report = pala_state.reconciliation_report(root, manifest, workflow)
            self.assertTrue(report["needed"])
            self.assertIn("working tree changed since checkpoint", report["reasons"])

    def test_checkpoint_accepts_only_the_exact_commit_of_checkpointed_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            for name in ("PROJECT.md", "PLAN.md", "STATUS.md"):
                (root / name).write_text(f"# {name}\n", encoding="utf-8")
            (root / "app.txt").write_text("version one\n", encoding="utf-8")
            manifest = {
                "schema_version": 1,
                "managed_by": "pala-project-finisher",
                "documents": {
                    "project": "PROJECT.md",
                    "plan": "PLAN.md",
                    "status": "STATUS.md",
                },
            }
            (root / pala_state.MANIFEST).write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "add", "."], cwd=root, check=True, capture_output=True
            )
            commit = [
                "git",
                "-c",
                "user.name=Pala Tests",
                "-c",
                "user.email=pala-tests@example.invalid",
                "commit",
            ]
            subprocess.run(
                [*commit, "-m", "fixture"],
                cwd=root,
                check=True,
                capture_output=True,
            )

            (root / "app.txt").write_text("version two\n", encoding="utf-8")
            (root / "STATUS.md").write_text(
                "# STATUS.md\n\nTicket complete.\n", encoding="utf-8"
            )
            pala_state.begin_work(root, "T-003", "Commit the coherent outcome")
            pala_state.checkpoint_work(
                root,
                next_action="Continue with T-004",
                verification=["ticket: passed"],
                blockers=[],
                tier="ticket",
            )
            checkpoint = pala_state.load_workflow(root)
            git_basis = checkpoint["checkpoint_basis"]["git"]
            self.assertEqual(git_basis["changed_count"], 2)
            self.assertEqual(len(git_basis["changed_snapshot_sha256"]), 64)

            subprocess.run(
                ["git", "add", "."], cwd=root, check=True, capture_output=True
            )
            subprocess.run(
                [*commit, "-m", "complete ticket"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            committed = pala_state.load_workflow(root)
            report = pala_state.reconciliation_report(root, manifest, committed)
            self.assertFalse(report["needed"], report["reasons"])

            pala_state.checkpoint_work(
                root,
                next_action="Continue with T-005",
                verification=["checkpoint metadata: passed"],
                blockers=[],
                tier="ticket",
            )
            workflow_only = pala_state.load_workflow(root)
            self.assertEqual(
                workflow_only["checkpoint_basis"]["git"]["changed_count"], 0
            )
            metadata_report = pala_state.reconciliation_report(
                root, manifest, workflow_only
            )
            self.assertFalse(metadata_report["needed"], metadata_report["reasons"])

            (root / "app.txt").write_text("version three\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "app.txt"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [*commit, "-m", "unexpected later work"],
                cwd=root,
                check=True,
                capture_output=True,
            )
            changed = pala_state.reconciliation_report(root, manifest, workflow_only)
            self.assertTrue(changed["needed"])
            self.assertIn("Git HEAD changed since checkpoint", changed["reasons"])

    def test_legacy_workflow_requires_one_reconciliation(self) -> None:
        report = pala_state.reconciliation_report(
            Path.cwd(),
            {"documents": {}},
            {"schema_version": 1, "dirty": False},
        )
        self.assertTrue(report["needed"])
        self.assertIn("legacy workflow has no checkpoint basis", report["reasons"])

    def test_discover_routes_greenfield_to_decision_and_scaffolding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = pala_state.discover(Path(temp))
            self.assertEqual(result["project_kind"], "greenfield")
            self.assertEqual(
                result["profiles"],
                [
                    "project-intake",
                    "reuse-or-build",
                    "architecture-selection",
                    "greenfield-scaffolding",
                    "modularity-budgets",
                    "runtime-delivery",
                ],
            )

    def test_discover_routes_existing_full_stack_to_both_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "package.json").write_text(
                json.dumps({"dependencies": {"next": "16.0.0"}}),
                encoding="utf-8",
            )
            service = root / "services" / "api"
            service.mkdir(parents=True)
            (service / "pyproject.toml").write_text(
                '[project]\ndependencies = ["fastapi>=0.116"]\n',
                encoding="utf-8",
            )
            result = pala_state.discover(root)
            self.assertEqual(result["project_kind"], "existing")
            self.assertIn("frontend-engineering", result["profiles"])
            self.assertIn("backend-engineering", result["profiles"])

    def test_discover_recognizes_codex_plugin_as_existing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex-plugin").mkdir()
            (root / ".codex-plugin" / "plugin.json").write_text(
                json.dumps({"name": "fixture"}), encoding="utf-8"
            )
            result = pala_state.discover(root)
            self.assertEqual(result["project_kind"], "existing")
            self.assertNotIn("greenfield-scaffolding", result["profiles"])
            self.assertNotIn("greenfield-scaffolding", result["profiles"])

    def test_discover_routes_backend_only_without_frontend_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "pyproject.toml").write_text(
                '[project]\ndependencies = ["fastapi>=0.116"]\n',
                encoding="utf-8",
            )
            result = pala_state.discover(root)
            self.assertIn("backend-engineering", result["profiles"])
            self.assertNotIn("frontend-engineering", result["profiles"])


class MemoryEvaluationMatrixTests(unittest.TestCase):
    """Named reliability fixtures; they measure state transitions, never speed."""

    def test_broken_plan_ticket_alignment_is_detected(self) -> None:
        report = pala_memory.ticket_coherence_report(
            {"active_ticket": "M46-T1", "next_action": "start M47-T1"},
            status_text="Next: M47-T1",
            plan_text="#### M47-T1 - unrelated work",
        )

        self.assertTrue(report["mismatch"])
        self.assertFalse(report["ok"])

    def test_stale_git_snapshot_requires_reconciliation(self) -> None:
        workflow = {
            "schema_version": 2,
            "active_ticket": "M46-T1",
            "dirty": False,
            "needs_reconcile": False,
            "checkpoint_basis": {
                "documents": {},
                "git": {"head": "before", "worktree_sha256": "same"},
            },
        }
        with patch.object(
            pala_state_core,
            "git_checkpoint",
            return_value={"head": "after", "worktree_sha256": "same"},
        ), patch.object(pala_state_core, "checkpoint_commit_materialized", return_value=False):
            report = pala_state.reconciliation_report(Path("."), {"documents": {}}, workflow)

        self.assertTrue(report["needed"])
        self.assertIn("Git HEAD changed since checkpoint", report["reasons"])

    def test_completed_ticket_stays_inactive_after_resume_and_compact(self) -> None:
        workflow = {
            "active_ticket": None,
            "goal": None,
            "dirty": False,
            "next_action": "owner: commit/push/tag/release",
            "blockers": [],
        }
        for source in ("resume", "compact"):
            with self.subTest(source=source):
                message = pala_hook.session_context(
                    {"status": "STATUS.md", "plan": "PLAN.md"},
                    workflow,
                    compacted=source == "compact",
                    source=source,
                )["hookSpecificOutput"]["additionalContext"]
                self.assertIn("active=none", message)
                self.assertNotIn("active=M46-T1", message)

    def test_hook_trust_fixture_stays_human_verified(self) -> None:
        checklist = (SCRIPT_DIR.parent / "docs" / "CODEX_PLUGIN_CHECKLIST.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("/hooks", checklist)
        self.assertIn("configured-not-verified", checklist)


class PalaHookTests(unittest.TestCase):
    def test_rtk_hook_rewrites_supported_command_with_managed_binary(self) -> None:
        hook = load_module("pala_rtk_hook", "pala_rtk_hook.py")
        event = json.dumps(
            {
                "tool_name": "shell_command",
                "tool_input": {
                    "command": "git status",
                    "timeout_ms": 2500,
                    "cwd": "C:/project",
                },
            }
        )
        binary = Path(tempfile.gettempdir()) / "rtk-test.exe"
        binary.write_text("", encoding="utf-8")
        output = io.StringIO()

        with (
            patch("sys.stdin", io.StringIO(event)),
            patch("sys.stdout", output),
            patch.object(hook, "managed_rtk", return_value=binary),
        ):
            self.assertEqual(hook.main(), 0)

        payload = json.loads(output.getvalue())
        self.assertEqual(payload["permissionDecision"], "allow")
        updated = payload["updatedInput"]
        self.assertIn('rewrite -- git status', updated["command"])
        self.assertIn("RTK_TELEMETRY_DISABLED", updated["env"])
        self.assertEqual(updated["env"]["RTK_TELEMETRY_DISABLED"], "1")
        self.assertEqual(updated["cwd"], "C:/project")
        self.assertEqual(updated["timeout_ms"], 2500)

    def test_rtk_hook_falls_back_to_no_update_for_disallowed_command(self) -> None:
        hook = load_module("pala_rtk_hook", "pala_rtk_hook.py")
        event = json.dumps(
            {"tool_name": "shell_command", "tool_input": {"command": "npm install"}}
        )
        output = io.StringIO()
        with (
            patch("sys.stdin", io.StringIO(event)),
            patch("sys.stdout", output),
            patch.object(hook, "managed_rtk", return_value=Path(tempfile.gettempdir()) / "rtk-test.exe"),
        ):
            self.assertEqual(hook.main(), 0)

        self.assertEqual(json.loads(output.getvalue()), {})

    def test_rtk_hook_emits_no_rewrite_without_managed_binary(self) -> None:
        hook = load_module("pala_rtk_hook", "pala_rtk_hook.py")
        event = json.dumps({"tool_name": "shell_command", "tool_input": {"command": "git status"}})
        output = io.StringIO()
        with (
            patch("sys.stdin", io.StringIO(event)),
            patch("sys.stdout", output),
            patch.object(hook, "managed_rtk", return_value=Path("missing-rtk.exe")),
        ):
            self.assertEqual(hook.main(), 0)
        self.assertEqual(json.loads(output.getvalue()), {})

    def test_hook_manifest_registers_rtk_only_for_shell_commands(self) -> None:
        hooks = json.loads((SCRIPT_DIR.parent / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(hooks["hooks"]["PreToolUse"][0]["matcher"], "shell_command")

    def test_hook_manifest_registers_session_end(self) -> None:
        hooks = json.loads((SCRIPT_DIR.parent / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertIn("SessionEnd", hooks["hooks"])
        session_end = hooks["hooks"]["SessionEnd"][0]["hooks"][0]
        self.assertLessEqual(int(session_end["timeout"]), 3)

    def test_session_end_uses_event_session_without_emitting_its_raw_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            (root / pala_hook.MANIFEST).write_text(
                json.dumps(
                    {
                        "managed_by": "pala-project-finisher",
                        "documents": {"status": "STATUS.md"},
                    }
                ),
                encoding="utf-8",
            )
            store = pala_store.WorkflowStore(root)
            store.claim("PALA-043", "Session ownership", "session-alpha")
            event = json.dumps(
                {"cwd": temp, "hook_event_name": "SessionEnd", "session_id": "session-alpha"}
            )
            output = io.StringIO()
            with (
                patch("sys.stdin", io.StringIO(event)),
                patch("sys.stdout", output),
                patch.object(pala_hook, "git_root", return_value=root),
            ):
                self.assertEqual(pala_hook.main(), 0)
            self.assertNotIn("session-alpha", output.getvalue())
            record = store._read(store._ticket_path("PALA-043"))
            self.assertEqual(record["last_event"], "session_end")

    def test_session_start_prefers_ticket_owned_by_event_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            (root / pala_hook.MANIFEST).write_text(
                json.dumps(
                    {
                        "managed_by": "pala-project-finisher",
                        "documents": {"status": "STATUS.md", "plan": "PLAN.md"},
                    }
                ),
                encoding="utf-8",
            )
            store = pala_store.WorkflowStore(root)
            store.claim("PALA-043", "Session ownership", "session-alpha")
            event = json.dumps(
                {
                    "cwd": temp,
                    "hook_event_name": "SessionStart",
                    "session_id": "session-alpha",
                }
            )
            output = io.StringIO()
            with (
                patch("sys.stdin", io.StringIO(event)),
                patch("sys.stdout", output),
                patch.object(pala_hook, "git_root", return_value=root),
            ):
                self.assertEqual(pala_hook.main(), 0)
            message = json.loads(output.getvalue())["hookSpecificOutput"]["additionalContext"]
            self.assertIn("active=PALA-043", message)
            self.assertIn("dirty=true", message)

    def test_unregistered_project_has_no_hook_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            event = json.dumps({"cwd": temp, "hook_event_name": "SessionStart"})
            output = io.StringIO()
            with (
                patch("sys.stdin", io.StringIO(event)),
                patch("sys.stdout", output),
                patch.object(pala_hook, "git_root", return_value=Path(temp)),
            ):
                self.assertEqual(pala_hook.main(), 0)
            self.assertEqual(output.getvalue(), "")

    def test_stop_requests_reconciliation_only_for_explicit_dirty_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload = {
                "managed_by": "pala-project-finisher",
                "documents": {"status": "STATUS.md"},
            }
            (root / ".codex").mkdir()
            (root / pala_hook.MANIFEST).write_text(
                json.dumps(payload), encoding="utf-8"
            )
            (root / "STATUS.md").write_text("# Status\n", encoding="utf-8")
            (root / pala_hook.WORKFLOW).write_text(
                json.dumps({"schema_version": 1, "dirty": True}),
                encoding="utf-8",
            )
            event = json.dumps(
                {
                    "cwd": temp,
                    "hook_event_name": "Stop",
                    "stop_hook_active": False,
                }
            )
            output = io.StringIO()
            with (
                patch("sys.stdin", io.StringIO(event)),
                patch("sys.stdout", output),
                patch.object(pala_hook, "git_root", return_value=root),
            ):
                self.assertEqual(pala_hook.main(), 0)
            self.assertEqual(json.loads(output.getvalue())["decision"], "block")

    def test_stop_does_not_guess_freshness_from_file_mtimes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            (root / pala_hook.MANIFEST).write_text(
                json.dumps(
                    {
                        "managed_by": "pala-project-finisher",
                        "documents": {"status": "STATUS.md"},
                    }
                ),
                encoding="utf-8",
            )
            (root / "STATUS.md").write_text("# Status\n", encoding="utf-8")
            (root / "newer-source.py").write_text("print('x')\n", encoding="utf-8")
            event = json.dumps(
                {"cwd": temp, "hook_event_name": "Stop", "stop_hook_active": False}
            )
            output = io.StringIO()
            with (
                patch("sys.stdin", io.StringIO(event)),
                patch("sys.stdout", output),
                patch.object(pala_hook, "git_root", return_value=root),
            ):
                self.assertEqual(pala_hook.main(), 0)
            self.assertEqual(json.loads(output.getvalue()), {})

    def test_precompact_checkpoint_is_reloaded_after_compaction(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload = {
                "managed_by": "pala-project-finisher",
                "documents": {
                    "project": "README.md",
                    "plan": "PLAN.md",
                    "status": "STATUS.md",
                },
            }
            (root / ".codex").mkdir()
            (root / pala_hook.MANIFEST).write_text(
                json.dumps(payload), encoding="utf-8"
            )
            (root / pala_hook.WORKFLOW).write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "active_ticket": "T-001",
                        "dirty": False,
                        "needs_reconcile": False,
                        "next_action": "Continue",
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(pala_hook, "git_root", return_value=root):
                precompact_output = io.StringIO()
                with (
                    patch(
                        "sys.stdin",
                        io.StringIO(
                            json.dumps(
                                {"cwd": temp, "hook_event_name": "PreCompact"}
                            )
                        ),
                    ),
                    patch("sys.stdout", precompact_output),
                ):
                    self.assertEqual(pala_hook.main(), 0)
                workflow = json.loads(
                    (root / pala_hook.WORKFLOW).read_text(encoding="utf-8")
                )
                self.assertTrue(workflow["needs_reconcile"])

                session_output = io.StringIO()
                with (
                    patch(
                        "sys.stdin",
                        io.StringIO(
                            json.dumps(
                                {
                                    "cwd": temp,
                                    "hook_event_name": "SessionStart",
                                    "source": "compact",
                                }
                            )
                        ),
                    ),
                    patch("sys.stdout", session_output),
                ):
                    self.assertEqual(pala_hook.main(), 0)
                context = json.loads(session_output.getvalue())
                message = context["hookSpecificOutput"]["additionalContext"]
                self.assertIn("Context was compacted", message)
                self.assertTrue((root / pala_hook.WORKFLOW).exists())

    def test_session_context_includes_registered_profiles(self) -> None:
        result = pala_hook.session_context(
            {"project": "PROJECT.md", "status": "STATUS.md"},
            {"active_ticket": "T-002", "next_action": "Build the core flow"},
            compacted=False,
            project_kind="partial",
            profiles=["frontend-engineering", "runtime-delivery"],
        )
        message = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("project kind=partial", message)
        self.assertNotIn("profiles=frontend-engineering, runtime-delivery", message)

    def test_session_context_is_compact_and_active_ticket_first(self) -> None:
        result = pala_hook.session_context(
            {
                "project": "docs/SCOPE.md",
                "plan": "docs/IMPLEMENTATION_PLAN.md",
                "status": "reports/CURRENT_STATUS.md",
                "decisions": "docs/PRODUCT_DECISIONS.md",
                "open_source": "docs/OPEN_SOURCE.md",
            },
            {
                "schema_version": 2,
                "active_ticket": "F2-T1",
                "next_action": "Write the failing domain test",
                "dirty": False,
                "blockers": [],
            },
            compacted=False,
            project_kind="existing",
            profiles=["frontend-engineering", "backend-engineering"],
            reconciliation={"needed": False, "reasons": []},
        )
        message = result["hookSpecificOutput"]["additionalContext"]
        self.assertLessEqual(len(message), pala_hook.SESSION_CONTEXT_LIMIT)
        self.assertIn("status=reports/CURRENT_STATUS.md", message)
        self.assertIn("active=F2-T1", message)
        self.assertIn("plan=docs/IMPLEMENTATION_PLAN.md", message)
        self.assertIn("Read status first", message)
        self.assertNotIn("docs/PRODUCT_DECISIONS.md", message)
        self.assertNotIn("docs/OPEN_SOURCE.md", message)

    def test_session_context_reports_only_local_health(self) -> None:
        result = pala_hook.session_context(
            {"project": "PROJECT.md", "status": "STATUS.md"},
            {"schema_version": 2, "active_ticket": "PALA-042", "dirty": True},
            compacted=False,
            project_kind="existing",
            health={"plugin": "loaded", "python": "ready", "git": "ready", "hook": "running"},
            reconciliation={"needed": False, "reasons": []},
        )
        message = result["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(message.startswith(pala_hook.PRESENCE_LINE))
        self.assertIn("Pala local health: plugin=loaded; python=ready; git=ready; hook=running.", message)
        self.assertLessEqual(len(message), pala_hook.SESSION_CONTEXT_LIMIT)
        for banned in ("token büyüt", "kota artır", "% daha hızlı", "plus install"):
            self.assertNotIn(banned.casefold(), message.casefold())

    def test_session_context_presence_survives_long_fields(self) -> None:
        long_next = "x" * 500
        result = pala_hook.session_context(
            {"project": "PROJECT.md", "status": "STATUS.md", "plan": "PLAN.md"},
            {
                "schema_version": 2,
                "active_ticket": "PALA-M21",
                "next_action": long_next,
                "dirty": True,
                "blockers": ["a", "b", "c"],
            },
            compacted=True,
            project_kind="existing",
            health={"plugin": "loaded", "python": "ready", "git": "ready", "hook": "running"},
            reconciliation={"needed": True, "reasons": ["one", "two"]},
            tools_summary="tools=n/a",
        )
        message = result["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(message.startswith(pala_hook.PRESENCE_LINE))
        self.assertLessEqual(len(message), pala_hook.SESSION_CONTEXT_LIMIT)

    def test_new_workflow_does_not_require_reconciliation_before_first_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = pala_state.reconciliation_report(
                root,
                {"documents": {}},
                {
                    "schema_version": 2,
                    "active_ticket": "PALA-042",
                    "dirty": True,
                    "needs_reconcile": False,
                    "checkpoint_basis": None,
                },
            )
        self.assertFalse(report["needed"])
        self.assertEqual(report["reasons"], [])

    def test_begin_rejects_dirty_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            (root / ".codex" / "pala-workflow.json").write_text(
                json.dumps({"schema_version": 2, "dirty": True}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                pala_state.begin_work(root, "T-001", "repair")

    def test_hook_never_runs_quality_or_network_commands(self) -> None:
        source = (SCRIPT_DIR / "pala_hook.py").read_text(encoding="utf-8").casefold()
        for forbidden in (
            "composer verify",
            "npm test",
            "php artisan test",
            "pytest",
            "scripts/verify",
            "gh ",
            "github.com",
        ):
            self.assertNotIn(forbidden, source)


class PluginContractTests(unittest.TestCase):
    def test_skill_does_not_invent_user_preapproval(self) -> None:
        skill = (
            SCRIPT_DIR.parent / "skills" / "pala-project-finisher" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("invocation pre-approves", skill)

    def test_manifest_uses_documented_capability_labels(self) -> None:
        manifest = json.loads(
            (SCRIPT_DIR.parent / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            manifest["interface"]["capabilities"],
            ["Interactive", "Read", "Write"],
        )

    def test_orchestrator_links_every_conditional_profile(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        for profile in (*REQUIRED_PROFILES, *NEW_REQUIRED_REFERENCES):
            self.assertIn(f"(references/{profile})", skill)

    def test_profiles_are_project_independent_and_bounded(self) -> None:
        forbidden = ("pala-quant", "bist", "viop", "forinvest", "osmanlı")
        for profile in REQUIRED_PROFILES:
            text = (REFERENCE_DIR / profile).read_text(encoding="utf-8")
            self.assertLessEqual(len(text.split()), 900, profile)
            lowered = text.casefold()
            for term in forbidden:
                self.assertNotIn(term, lowered, f"{term} in {profile}")

    def test_tags_are_hints_not_stack_approval(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Technology tags are discovery hints, not stack approval.", skill)

    def test_runtime_profile_contains_vibe_coder_completion_gate(self) -> None:
        text = (REFERENCE_DIR / "runtime-delivery.md").read_text(encoding="utf-8")
        required_questions = (
            "what already existed",
            "smallest maintained reusable foundation",
            "clean and low-duplication",
            "real core workflow",
            "applicable lint, typecheck, tests, build, dependency",
            "dependency",
            "secret checks",
            "open and use it now",
        )
        lowered = text.casefold()
        for question in required_questions:
            self.assertIn(question, lowered)

    def test_quality_profile_defines_tiers_and_forbids_unmeasured_claims(self) -> None:
        text = (REFERENCE_DIR / "quality-gates.md").read_text(encoding="utf-8")
        normalized = " ".join(text.casefold().split())
        for tier in ("narrow", "ticket", "milestone", "release"):
            self.assertIn(tier, normalized)
        self.assertIn("do not report a speed or token-saving percentage", normalized)
        self.assertIn("same environment", normalized)
        self.assertIn("verification before done", normalized)
        self.assertIn("configured-not-verified", normalized)
        self.assertIn("not-run", normalized)
        self.assertIn("do not invent soft", normalized)
        self.assertRegex(
            text,
            r"Report each applicable gate as `passed`, `not-run`, `blocked`, or\s*`configured-not-verified`",
        )

    def test_orchestrator_continues_authorized_local_work(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())
        self.assertIn("Read status first", normalized)
        # M30 thin skill keeps "only the active ticket"; fuller "…section"
        # wording lives in references (token-efficient-context / memory-contract).
        self.assertIn("only the active ticket", normalized)
        contract = (REFERENCE_DIR / "project-memory-contract.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "only the active ticket section",
            " ".join(contract.split()),
        )
        self.assertIn("Do not re-plan completed scope", normalized)
        self.assertIn("Continue safe in-scope local work", normalized)


class PalaViewA11yTests(unittest.TestCase):
    """Contract checks for Status HTML landmarks / keyboard / responsive CSS."""

    def _sample_html(self, **overrides: object) -> str:
        import pala_view

        model: dict[str, object] = {
            "root_name": "demo",
            "root_path": "C:/tmp/demo",
            "stamp": "2026-08-08",
            "coherence": {
                "active": "T1",
                "inferred_next": "ship",
                "mismatch": False,
                "note": "ok",
            },
            "git": {"branch": "main", "dirty_count": 0},
            "read_order": [],
            "progress": {"ready": 7, "total": 7, "missing": []},
            "projects": [],
            "events": [
                {
                    "kind": "checkpoint",
                    "created_at": "2026-08-08T10:00:00",
                    "project_name": "demo",
                    "detail": "ok",
                },
                {
                    "kind": "debug_attempt",
                    "created_at": "2026-08-08T09:00:00",
                    "project_name": "demo",
                    "detail": "tried fix A",
                },
            ],
            "provisions": [],
            "next_action": "ship",
            "debugging_brain": {"ok": True, "open": 2, "fixed": 1, "total": 3},
            "last_gate": {"label": "unittest: passed", "status": "passed"},
            "freshness_level": "fresh",
            "quality": {
                "status": "blocked",
                "ticket": "T1",
                "risk": {"level": "high", "reasons": ["authentication"]},
                "coverage": {"passed": 0, "required": 1},
                "last_problem": "unit:test=not-run",
                "next_action": "run unit:test",
            },
        }
        model.update(overrides)
        return pala_view.render(model, freshness_fn=lambda _ts: "fresh")

    def test_status_html_has_landmarks_skip_link_and_focus_styles(self) -> None:
        html = self._sample_html()
        self.assertIn('class="skip-link"', html)
        self.assertIn('href="#pala-main"', html)
        self.assertIn("<nav ", html)
        self.assertIn('id="pala-main"', html)
        self.assertIn("<main ", html)
        self.assertIn('role="status"', html)
        self.assertIn(":focus", html)
        self.assertIn("@media (max-width: 720px)", html)
        self.assertIn("outline: 3px solid", html)
        self.assertNotIn("purple", html.casefold())

    def test_status_context_readiness_is_not_presented_as_project_completion(self) -> None:
        html = self._sample_html()

        self.assertIn("Çalışma bağlamı: 7/7 hazır", html)
        self.assertIn("Bu, proje ilerlemesi veya teslim kararı değildir.", html)
        self.assertNotIn(">7/7 hazir<", html)
        self.assertNotIn("linear-gradient", html.casefold())
        # SFNSP 2026: skip target does not need tabindex=-1
        self.assertNotIn('tabindex="-1"', html)
        self.assertNotIn("tabindex='-1'", html)

    def test_status_html_has_admin_control_landmarks(self) -> None:
        html = self._sample_html(
            store_path="C:/tmp/pala.sqlite",
            verification_tier="ticket",
        )
        self.assertIn('id="pala-admin-nav"', html)
        self.assertIn('id="pala-admin-hero"', html)
        self.assertIn('id="pala-theme-toggle"', html)
        self.assertIn('id="pala-feature-toggles"', html)
        self.assertIn('id="pala-hooks-trust"', html)
        self.assertIn('data-evidence="configured-not-verified"', html)
        self.assertIn('data-admin-section="overview"', html)
        self.assertIn('data-admin-section="install"', html)
        self.assertIn('data-admin-section="hooks"', html)
        self.assertIn('data-admin-section="quality"', html)
        self.assertIn('data-admin-section="memory"', html)
        self.assertIn('data-admin-section="tickets"', html)
        self.assertIn('data-admin-section="features"', html)
        self.assertIn("pala.ui.theme", html)
        self.assertIn("localStorage", html)
        self.assertIn('id="pref-show-experts"', html)
        self.assertIn('id="pref-soft-fail-closed"', html)
        self.assertIn('id="pref-show-quality-tier"', html)
        self.assertNotIn("src=\"http", html.casefold())
        self.assertNotIn("<link ", html.casefold())
        self.assertIn("ücretli kilit yok", html.casefold())
        self.assertNotIn("purple", html.casefold())

    def test_decision_strip_has_five_signals_no_vanity_speed(self) -> None:
        html = self._sample_html()
        self.assertIn('class="decision-strip"', html)
        self.assertIn('aria-label="Karar sinyalleri"', html)
        for key in ("Aktif ticket", "Risk seviyesi", "Quality coverage", "Son eksik gate", "Tek sonraki eylem"):
            self.assertIn(key, html)
        self.assertIn("high", html)
        self.assertIn("0/1 passed", html)
        self.assertIn("unit:test=not-run", html)
        self.assertIn("run unit:test", html)
        self.assertNotIn("speed", html.casefold())
        self.assertNotIn("%", html.split("Karar sinyalleri", 1)[-1][:800])

    def test_delivery_card_distinguishes_ticket_from_release_and_hides_paths(self) -> None:
        html = self._sample_html(
            delivery={
                "status": "passed",
                "label": "Ticket hazır",
                "tier": "ticket",
                "detail": "Zorunlu proje-yerel kapılar bu tier için kanıtlı geçti.",
            },
            quality={
                "status": "passed",
                "ticket": "T1",
                "risk": {"level": "low", "reasons": []},
                "coverage": {"passed": 1, "required": 1},
                "required_checks": [
                    {"id": "integration:source-verify", "status": "passed"}
                ],
                "last_problem": "",
                "next_action": "",
            },
        )
        self.assertIn('id="pala-delivery-decision"', html)
        self.assertEqual(html.count('id="pala-delivery-decision"'), 1)
        self.assertIn('id="pala-delivery-quality"', html)
        self.assertIn("Ticket hazır", html)
        self.assertIn("integration:source-verify", html)
        self.assertIn("Zorunlu kalite kapıları", html)
        self.assertIn("Yerel yol gizli", html)
        self.assertIn('class="private-detail"', html)
        self.assertIn('aria-controls="panel-overview"', html)
        self.assertIn(":focus-visible", html)

    def test_status_suppresses_temporary_catalog_and_timeline_noise(self) -> None:
        html = self._sample_html(
            projects=[
                {"name": "tmpab12cd", "updated_at": "2026-08-08"},
                {"name": "kalici-proje", "updated_at": "2026-08-08"},
            ],
            events=[
                {"kind": "begin", "project_name": "tmpab12cd", "detail": "test"},
                {"kind": "begin", "project_name": "kalici-proje", "detail": "real"},
            ],
        )
        self.assertNotIn("tmpab12cd", html)
        self.assertIn("kalici-proje", html)

    def test_delivery_decision_never_promotes_ticket_to_release(self) -> None:
        import pala_report

        passed = {"status": "passed", "ticket": "T1", "last_problem": ""}
        ticket = pala_report.delivery_decision(
            {"verification_tier": "ticket"},
            {"active": "T1", "mismatch": False},
            passed,
        )
        release = pala_report.delivery_decision(
            {"verification_tier": "release"},
            {"active": "T1", "mismatch": False},
            passed,
        )
        blocked = pala_report.delivery_decision(
            {"verification_tier": "release"},
            {"active": "T1", "mismatch": True},
            passed,
        )
        self.assertEqual(ticket["label"], "Ticket hazır")
        self.assertEqual(release["label"], "Sürüme hazır")
        self.assertEqual(blocked["status"], "blocked")

    def test_view_sections_are_owned_separately_and_renderer_stays_reviewable(self) -> None:
        sections = SCRIPT_DIR / "pala_view_sections.py"
        self.assertTrue(sections.is_file())
        section_source = sections.read_text(encoding="utf-8")
        self.assertIn("def delivery_card(", section_source)
        self.assertIn("def section_overview(", section_source)
        renderer_lines = (SCRIPT_DIR / "pala_view.py").read_text(
            encoding="utf-8"
        ).splitlines()
        self.assertLessEqual(len(renderer_lines), 800)

    def test_view_sections_avoid_python_312_only_f_string_expressions(self) -> None:
        section_source = (SCRIPT_DIR / "pala_view_sections.py").read_text(
            encoding="utf-8"
        )
        self.assertNotRegex(
            section_source,
            r"f[\"'][^\n]*\{[^}\n]*\\[^}\n]*\}",
            "Python 3.10 rejects backslashes inside f-string expressions",
        )

    def test_timeline_distinguishes_debug_attempt_and_checkpoint(self) -> None:
        html = self._sample_html()
        self.assertIn('data-kind="checkpoint"', html)
        self.assertIn('data-kind="debug_attempt"', html)
        self.assertIn("debug denemesi", html)
        self.assertIn("kind-checkpoint", html)
        self.assertIn("kind-debug_attempt", html)

    def test_last_gate_signal_prefers_workflow_verification(self) -> None:
        import pala_report

        gate = pala_report.last_gate_signal(
            {"verification": ["narrow: passed"], "verification_tier": "ticket"},
            events=[],
        )
        self.assertEqual(gate["status"], "passed")
        self.assertIn("passed", gate["label"])
        missing = pala_report.last_gate_signal({}, events=[])
        self.assertEqual(missing["status"], "not-run")

    def test_report_prints_status_html_path_and_open_hint(self) -> None:
        import pala_report

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
            target = root / ".codex" / "pala-status.html"
            hint = pala_report.format_open_hint(target)
            self.assertIn("açmak için:", hint)
            self.assertTrue(
                "file://" in hint.casefold() or str(target.resolve()) in hint,
                msg=f"open hint must carry file:// or absolute path: {hint!r}",
            )
            printed = pala_report.format_report_output(target)
            self.assertIn(".codex/pala-status.html", printed.replace("\\", "/"))
            self.assertIn("açmak için:", printed)
            output = io.StringIO()
            with (
                patch("sys.argv", ["pala_report.py", "--cwd", str(root)]),
                patch("sys.stdout", output),
                patch.object(pala_report, "write_report", return_value=target),
                patch.object(pala_report, "open_report"),
            ):
                code = pala_report.main()
            self.assertEqual(code, 0)
            text = output.getvalue()
            self.assertIn(".codex/pala-status.html", text.replace("\\", "/"))
            self.assertIn("açmak için:", text)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Unit tests for the deterministic Pala project-state helpers."""

from __future__ import annotations

import importlib.util
import io
import hashlib
import json
import subprocess
import tempfile
import unittest
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

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


pala_state = load_module("pala_state", "pala_state.py")
pala_store = load_module("pala_store", "pala_store.py")
pala_hook = load_module("pala_hook", "pala_hook.py")


class PalaStateTests(unittest.TestCase):
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
            self.assertEqual(second.record["blockers"], ["verification repeated twice"])

    def test_ticket_store_complete_requires_passed_evidence_and_no_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = pala_store.WorkflowStore(Path(temp))
            store.claim("PALA-043", "Complete safely", "session-alpha")

            refused = store.complete("PALA-043", "session-alpha")
            store.record_verification(
                "PALA-043", "session-alpha", "passed", "py -3 scripts/verify.py"
            )
            completed = store.complete("PALA-043", "session-alpha")

            self.assertEqual(refused.status, "verification_required")
            self.assertEqual(completed.status, "completed")
            self.assertEqual(completed.record["lifecycle"], "completed")
            self.assertFalse(completed.record["dirty"])

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

    def test_begin_parser_accepts_optional_session_key(self) -> None:
        args = pala_state.parser().parse_args(
            ["begin", "--ticket", "PALA-043", "--goal", "Session ownership", "--session-key", "abc123"]
        )

        self.assertEqual(args.session_key, "abc123")

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
            subprocess.run(
                ["git", "add", str(pala_state.WORKFLOW)],
                cwd=root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [*commit, "-m", "checkpoint metadata"],
                cwd=root,
                check=True,
                capture_output=True,
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


class PalaHookTests(unittest.TestCase):
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
        self.assertLessEqual(len(message), 800)
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
        self.assertIn("Pala local health: plugin=loaded; python=ready; git=ready; hook=running.", message)
        self.assertLessEqual(len(message), 800)

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
            "applicable lint, typecheck, tests, and build",
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

    def test_orchestrator_continues_authorized_local_work(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())
        self.assertIn("Read status first", normalized)
        self.assertIn("only the active ticket section", normalized)
        self.assertIn("Do not re-plan completed scope", normalized)
        self.assertIn("continue safe in-scope local work", normalized)


if __name__ == "__main__":
    unittest.main()

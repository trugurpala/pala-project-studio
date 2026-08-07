#!/usr/bin/env python3
"""Contract tests for Pala 0.5 Project Memory Contract."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

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

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pala_catalog
import pala_hook
import pala_memory
import pala_report
import pala_state
import pala_tool_memory


class MemoryContractTests(unittest.TestCase):
    def test_discover_splits_progress_from_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "reports").mkdir()
            (root / "PROGRESS.md").write_text("# Progress\n", encoding="utf-8")
            (root / "reports" / "CURRENT_STATUS.md").write_text(
                "# Status\n", encoding="utf-8"
            )
            (root / "README.md").write_text("# P\n", encoding="utf-8")
            (root / "TASKS.md").write_text("# Plan\n", encoding="utf-8")
            result = pala_state.discover(root)
            self.assertEqual(
                result["documents"]["status"], "reports/CURRENT_STATUS.md"
            )
            self.assertEqual(result["documents"]["progress"], "PROGRESS.md")

    def test_read_order_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docs = {
                "instructions": "AGENTS.md",
                "status": "reports/CURRENT_STATUS.md",
                "progress": "PROGRESS.md",
                "plan": "PLAN.md",
                "tooling": "TOOLING_DECISIONS.md",
                "debugging": "DEBUGGING.md",
            }
            for rel in docs.values():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# x\n", encoding="utf-8")
            ordered = pala_memory.resolve_read_order(root, docs)
            purposes = [item["purpose"] for item in ordered]
            self.assertEqual(
                purposes,
                [
                    "instructions",
                    "status",
                    "progress",
                    "plan",
                    "tooling",
                    "debugging",
                    "git",
                ],
            )

    def test_ticket_coherence_detects_mismatch(self) -> None:
        report = pala_memory.ticket_coherence_report(
            {"active_ticket": "F2-T1", "next_action": "Start F2-T2 domain tests"},
            status_text="- Next: F2-T2 write failing test\n",
        )
        self.assertTrue(report["mismatch"])
        self.assertFalse(report["ok"])

    def test_checkpoint_rejects_soft_done(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            pala_state.begin_work(root, "T-1", "Do work")
            with self.assertRaises(ValueError):
                pala_state.checkpoint_work(
                    root,
                    next_action="Next ticket",
                    verification=["done"],
                    blockers=[],
                )

    def test_checkpoint_accepts_structured_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            pala_state.begin_work(root, "T-1", "Do work")
            pala_state.checkpoint_work(
                root,
                next_action="Continue T-2",
                verification=["unittest=passed", "e2e=not-run"],
                blockers=[],
            )
            payload = pala_state.load_workflow(root)
            self.assertFalse(payload["dirty"])
            self.assertEqual(len(payload["verification_evidence"]), 2)

    def test_tool_memory_maps_adapter_states(self) -> None:
        self.assertEqual(pala_tool_memory.map_adapter_state("ready"), "installed")
        self.assertEqual(pala_tool_memory.map_adapter_state("missing"), "not_installed")
        self.assertEqual(
            pala_tool_memory.map_adapter_state("external_conflict"),
            "installed_unverified",
        )

    def test_catalog_upsert_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "README.md").write_text("# demo\n", encoding="utf-8")
            cdir = Path(temp) / "Codex"
            first = pala_catalog.upsert_project(
                root, catalog_dir=cdir, next_action="A", phase="F2-T1"
            )
            second = pala_catalog.upsert_project(
                root, catalog_dir=cdir, next_action="B", phase="F2-T2"
            )
            self.assertEqual(first["id"], second["id"])
            projects = pala_catalog.list_projects(cdir)
            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0]["next_action"], "B")

    def test_report_renders_static_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
            (root / "reports").mkdir()
            (root / "reports" / "CURRENT_STATUS.md").write_text(
                "# Status\n", encoding="utf-8"
            )
            target = pala_report.write_report(
                root,
                update={
                    "status": "current",
                    "installed_version": "0.7.0",
                    "available_version": "0.7.0",
                    "url": None,
                },
            )
            self.assertTrue(target.is_file())
            markup = target.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", markup)
            self.assertIn("Okuma sirasi", markup)
            self.assertIn("Proje katalogu", markup)
            self.assertIn("Simdi:", markup)
            self.assertIn("hazir", markup)
            self.assertIn("Son olaylar", markup)
            self.assertIn("Son URL kurulumlari", markup)
            self.assertIn('name="pala-nav"', markup)
            self.assertIn('id="nav-current"', markup)
            self.assertNotIn("<script", markup)
            self.assertNotIn("<link", markup)
            self.assertNotIn('src="http', markup)
            self.assertNotIn("src='http", markup)

    def test_report_shows_timeline_and_empty_states(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cdir = Path(temp) / "Codex"
            cdir.mkdir()
            os.environ["PALA_CATALOG_ROOT"] = str(cdir)
            os.environ["PALA_DB_PATH"] = str(cdir / "pala.sqlite")
            os.environ["PALA_PROVISION_REGISTRY"] = str(
                cdir / "provision-registry.json"
            )
            root = Path(temp) / "proj"
            root.mkdir()
            (root / "AGENTS.md").write_text("# A\n", encoding="utf-8")
            import pala_db

            pala_db.add_event(
                "checkpoint",
                project_name="proj",
                detail="Continue F2-T2",
                path=cdir / "pala.sqlite",
            )
            markup = pala_report.render_html(
                root,
                update={"status": "current", "installed_version": "0.7.0"},
            )
            self.assertIn("Continue F2-T2", markup)
            self.assertIn("checkpoint", markup)
            self.assertIn("Henuz URL kurulumu yok", markup)
            self.assertIn("Henuz kayitli proje yok", markup)

    def test_report_progress_counts_ready_slots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "AGENTS.md").write_text("# A\n", encoding="utf-8")
            (root / "reports").mkdir()
            (root / "reports" / "CURRENT_STATUS.md").write_text(
                "# Status\n- Next: F2-T2 write tests\n", encoding="utf-8"
            )
            model = pala_report.build_status_model(
                root,
                update={"status": "current", "installed_version": "0.7.0"},
            )
            progress = model["progress"]
            self.assertIsInstance(progress, dict)
            self.assertGreaterEqual(int(progress["ready"]), 2)
            self.assertEqual(int(progress["total"]), 7)
            markup = pala_report.render_html(
                root,
                update={"status": "current", "installed_version": "0.7.0"},
            )
            self.assertRegex(markup, r"\d+/7 hazir")
            self.assertIn("Simdi:", markup)
            self.assertIn("F2-T2", markup)

    def test_report_sidebar_lists_catalog_projects(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            cdir = Path(temp) / "Codex"
            os.environ["PALA_CATALOG_ROOT"] = str(cdir)
            a = Path(temp) / "alpha"
            b = Path(temp) / "beta"
            a.mkdir()
            b.mkdir()
            (a / "package.json").write_text("{}\n", encoding="utf-8")
            (b / "pyproject.toml").write_text("[project]\nname='b'\n", encoding="utf-8")
            pala_catalog.upsert_project(a, catalog_dir=cdir, phase="A", next_action="a")
            pala_catalog.upsert_project(b, catalog_dir=cdir, phase="B", next_action="b")
            markup = pala_report.render_html(
                a,
                update={"status": "current", "installed_version": "0.6.0"},
            )
            self.assertIn('id="nav-0"', markup)
            self.assertIn('id="nav-1"', markup)
            self.assertIn('id="panel-0"', markup)
            self.assertIn('id="panel-1"', markup)
            self.assertIn("alpha", markup)
            self.assertIn("beta", markup)

    def test_freshness_buckets(self) -> None:
        now = datetime(2026, 8, 7, tzinfo=timezone.utc)
        self.assertEqual(
            pala_report.freshness((now - timedelta(hours=12)).isoformat(), now),
            "fresh",
        )
        self.assertEqual(
            pala_report.freshness((now - timedelta(days=3)).isoformat(), now),
            "aging",
        )
        self.assertEqual(
            pala_report.freshness((now - timedelta(days=10)).isoformat(), now),
            "stale",
        )
        self.assertEqual(pala_report.freshness(None, now), "stale")

    def test_report_currency_banner_from_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "AGENTS.md").write_text("# A\n", encoding="utf-8")
            available = pala_report.render_html(
                root,
                update={
                    "status": "update-available",
                    "installed_version": "0.5.0",
                    "available_version": "0.6.0",
                    "url": "https://github.com/trugurpala/pala-project-studio/releases/tag/v0.6.0",
                },
                update_checked_at="2026-08-07T12:00:00+00:00",
            )
            self.assertIn("Guncelleme var", available)
            self.assertIn("0.6.0", available)
            self.assertIn("https://github.com/trugurpala/pala-project-studio/releases", available)
            current = pala_report.render_html(
                root,
                update={
                    "status": "current",
                    "installed_version": "0.6.0",
                    "available_version": "0.6.0",
                    "url": None,
                },
            )
            self.assertIn("Pala guncel", current)

    def test_report_escapes_untrusted_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "proj"
            root.mkdir()
            (root / "reports").mkdir()
            (root / "reports" / "CURRENT_STATUS.md").write_text(
                "# Status\n- Next: <img src=x onerror=alert(1)>\n", encoding="utf-8"
            )
            markup = pala_report.render_html(
                root, update={"status": "unavailable", "installed_version": "0.6.0"}
            )
            self.assertNotIn("<img src=x", markup)
            self.assertIn("&lt;img", markup)

    def test_catalog_summary_is_human_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "demo-project"
            root.mkdir()
            (root / "package.json").write_text("{}\n", encoding="utf-8")
            cdir = Path(temp) / "Codex"
            empty = pala_catalog.plain_summary(cdir)
            self.assertIn("Henüz kayıtlı proje yok", empty)
            pala_catalog.upsert_project(
                root, catalog_dir=cdir, phase="F2-T2", next_action="Write tests"
            )
            text = pala_catalog.plain_summary(cdir)
            self.assertIn("Pala proje kataloğu", text)
            self.assertIn("demo-project", text)
            self.assertIn("Write tests", text)
            self.assertIn("node", text)

    def test_session_context_includes_memory_flags_under_limit(self) -> None:
        result = pala_hook.session_context(
            {
                "project": "docs/SCOPE.md",
                "plan": "docs/IMPLEMENTATION_PLAN.md",
                "status": "reports/CURRENT_STATUS.md",
            },
            {
                "active_ticket": "F2-T1",
                "next_action": "Write failing test",
                "dirty": False,
                "blockers": [],
            },
            compacted=False,
            project_kind="existing",
            reconciliation={"needed": False, "reasons": []},
            health={
                "plugin": "loaded",
                "python": "ready",
                "git": "ready",
                "hook": "running",
            },
            memory={
                "ticket_coherence": {
                    "mismatch": True,
                    "note": "active=F2-T1 but next is F2-T2",
                }
            },
            tools_summary="tools=3ok/2gap",
        )
        message = result["hookSpecificOutput"]["additionalContext"]
        self.assertLessEqual(len(message), 800)
        self.assertIn("Read status first", message)
        self.assertIn("ticket_mismatch=true", message)
        self.assertIn("tools=3ok/2gap", message)
        self.assertIn("read_order=", message)
        self.assertIn("pala_report.py --open", message)
        self.assertIn("durum sayfasini ac", message)

    def test_register_creates_memory_stubs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("README.md", "TASKS.md", "PROJECT_STATE.md"):
                (root / name).write_text("# Existing\n", encoding="utf-8")
            args = Namespace(
                instructions=None,
                project=None,
                plan=None,
                status=None,
                progress=None,
                tooling=None,
                debugging=None,
                decisions=None,
                open_source=None,
                demo=None,
            )
            self.assertEqual(pala_state.register(args, root), 0)
            self.assertTrue((root / "PROGRESS.md").is_file())
            self.assertTrue((root / "TOOLING_DECISIONS.md").is_file())
            self.assertTrue((root / "DEBUGGING.md").is_file())

    def test_plain_memory_report_is_human_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
            (root / "reports").mkdir()
            (root / "reports" / "CURRENT_STATUS.md").write_text(
                "# Status\n- Next: F2-T2\n", encoding="utf-8"
            )
            text = pala_memory.plain_memory_report(
                root,
                documents={
                    "instructions": "AGENTS.md",
                    "status": "reports/CURRENT_STATUS.md",
                },
                workflow={"active_ticket": "F2-T1", "next_action": "F2-T2"},
                tool_counts={"installed": 1, "not_installed": 2},
            )
            self.assertIn("Pala hafıza durumu", text)
            self.assertIn("Okuma sırası", text)
            self.assertIn("SORUN", text)
            self.assertIn("Araç özeti", text)


if __name__ == "__main__":
    unittest.main()

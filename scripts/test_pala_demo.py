#!/usr/bin/env python3
"""Contract tests for Pala fork demo seed (M21)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

PLUGIN_ROOT = SCRIPTS.parent
DEMO_ROOT = PLUGIN_ROOT / "examples" / "demo-software-project"

import pala_db
import pala_demo


class DemoFixtureContractTests(unittest.TestCase):
    REQUIRED = (
        "AGENTS.md",
        "PROJECT.md",
        "PLAN.md",
        "STATUS.md",
        "PROGRESS.md",
        "DECISIONS.md",
        "TOOLING_DECISIONS.md",
        "DEBUGGING.md",
        ".codex/pala-project.json",
        ".codex/pala-workflow.json",
    )

    def test_demo_fixture_has_memory_contract_and_active_ticket(self) -> None:
        for relative in self.REQUIRED:
            path = DEMO_ROOT / relative
            self.assertTrue(path.is_file(), f"missing {relative}")
        status = (DEMO_ROOT / "STATUS.md").read_text(encoding="utf-8")
        plan = (DEMO_ROOT / "PLAN.md").read_text(encoding="utf-8")
        workflow = json.loads(
            (DEMO_ROOT / ".codex" / "pala-workflow.json").read_text(encoding="utf-8")
        )
        self.assertIn("DEMO-003", plan)
        self.assertIn("[x] DEMO-003", plan)
        self.assertIn("[x] DEMO-004", plan)
        self.assertIn("[x] DEMO-005", plan)
        self.assertEqual(str(workflow.get("active_ticket") or "").strip(), "")
        self.assertIn("passed", status)
        self.assertIn("OWNER_DEMO", status)
        self.assertIn("Status HTML", status)
        for banned in ("api_key", "sk-", "BEGIN PRIVATE"):
            tree = "\n".join(
                path.read_text(encoding="utf-8")
                for path in DEMO_ROOT.rglob("*")
                if path.is_file() and path.suffix in {".md", ".json"}
            )
            self.assertNotIn(banned, tree)


class PalaDemoSeedTests(unittest.TestCase):
    def test_seed_writes_project_three_events_and_provision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog = Path(temp) / "catalog"
            catalog.mkdir()
            result = pala_demo.seed(
                demo_root=DEMO_ROOT,
                catalog_root=catalog,
            )
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["project"]["active_ticket"], "DEMO-003")
            self.assertGreaterEqual(result["events_written"], 3)
            self.assertTrue((catalog / "pala.sqlite").is_file())

            projects = pala_db.list_projects(path=catalog / "pala.sqlite")
            self.assertEqual(len(projects), 1)
            self.assertIn("DEMO-003", projects[0]["next_action"])
            events = pala_db.recent_events(limit=10, path=catalog / "pala.sqlite")
            kinds = {event["kind"] for event in events}
            self.assertTrue({"register", "begin", "checkpoint"}.issubset(kinds))
            provisions = pala_db.recent_provisions(limit=5, path=catalog / "pala.sqlite")
            self.assertGreaterEqual(len(provisions), 1)

    def test_seed_cli_json_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            catalog = Path(temp) / "catalog"
            catalog.mkdir()
            code, payload = pala_demo.run_cli(
                [
                    "seed",
                    "--demo-root",
                    str(DEMO_ROOT),
                    "--catalog-root",
                    str(catalog),
                ]
            )
            self.assertEqual(code, 0)
            body = json.loads(payload)
            self.assertEqual(body["status"], "passed")
            self.assertEqual(body["project"]["active_ticket"], "DEMO-003")

    def test_seed_rejects_missing_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            empty = Path(temp) / "empty"
            empty.mkdir()
            catalog = Path(temp) / "catalog"
            catalog.mkdir()
            with self.assertRaises(ValueError):
                pala_demo.seed(demo_root=empty, catalog_root=catalog)

    def test_seed_status_html_shows_ticket_and_timeline(self) -> None:
        """DEMO-003/004: Şimdi + active ticket + three timeline kinds after seed."""
        with tempfile.TemporaryDirectory() as temp:
            catalog = Path(temp) / "catalog"
            catalog.mkdir()
            proof = pala_demo.prove_status_html(
                demo_root=DEMO_ROOT,
                catalog_root=catalog,
            )
            self.assertEqual(proof["status"], "passed", proof)
            markup = str(proof["html"])
            self.assertIn("Şimdi:", markup)
            self.assertIn(str(proof["active_ticket"]), markup)
            self.assertEqual(proof["active_ticket"], "DEMO-003")
            for kind_label in ("kayit", "basla", "checkpoint"):
                self.assertIn(kind_label, markup)
            self.assertIn("Hata beyni", markup)


if __name__ == "__main__":
    unittest.main()

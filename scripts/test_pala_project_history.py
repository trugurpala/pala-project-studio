#!/usr/bin/env python3
"""Contracts for durable, privacy-safe project continuity and history."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pala_db  # noqa: E402
from pala_project_history import (  # noqa: E402
    ProjectHistoryError,
    list_history,
    persist_context_summary,
    record_closure,
    record_reopen,
)
from pala_project_profile import ProjectProfile  # noqa: E402
from test_pala_context_receipt import expectation, receipt  # noqa: E402
from test_pala_project_profile import profile_payload  # noqa: E402


class StoreMigrationContractTests(unittest.TestCase):
    def test_backup_failure_leaves_v1_store_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
            conn.execute("INSERT INTO schema_version VALUES (1)")
            conn.commit()
            conn.close()
            before = db.read_bytes()
            with (
                patch.object(
                    pala_db,
                    "_backup_database",
                    side_effect=pala_db.StoreMigrationError("backup blocked"),
                ),
                self.assertRaises(pala_db.StoreMigrationError),
                pala_db.connect(db),
            ):
                pass
            self.assertEqual(db.read_bytes(), before)

    def test_interrupted_v2_migration_rolls_back_schema_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
            conn.execute("INSERT INTO schema_version VALUES (1)")
            conn.commit()
            conn.close()
            with (
                patch.object(pala_db, "_SCHEMA", (*pala_db._SCHEMA, "INVALID SQL")),
                self.assertRaises(pala_db.StoreMigrationError),
                pala_db.connect(db),
            ):
                pass
            probe = sqlite3.connect(db)
            self.assertEqual(
                probe.execute("SELECT version FROM schema_version").fetchone()[0], 1
            )
            tables = {
                row[0]
                for row in probe.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            probe.close()
            self.assertNotIn("project_history", tables)

    def test_v1_to_v2_migration_is_backed_up_atomic_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            conn = sqlite3.connect(db)
            conn.executescript(
                "CREATE TABLE schema_version (version INTEGER NOT NULL);"
                "INSERT INTO schema_version VALUES (1);"
                "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
                "CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT NOT NULL "
                "DEFAULT '', path TEXT NOT NULL DEFAULT '', github TEXT, "
                "tech_json TEXT NOT NULL DEFAULT '[]', phase TEXT NOT NULL DEFAULT '', "
                "quality_result TEXT NOT NULL DEFAULT '', tools_summary TEXT NOT NULL "
                "DEFAULT '', next_action TEXT NOT NULL DEFAULT '', blockers_json TEXT "
                "NOT NULL DEFAULT '[]', updated_at TEXT NOT NULL DEFAULT '');"
                "CREATE TABLE provisions (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "source_url TEXT NOT NULL DEFAULT '', install_path TEXT NOT NULL UNIQUE, "
                "pala_version TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT '', "
                "registered INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT '');"
                "CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id "
                "TEXT NOT NULL DEFAULT '', project_name TEXT NOT NULL DEFAULT '', kind "
                "TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '', evidence TEXT NOT NULL "
                "DEFAULT '', created_at TEXT NOT NULL DEFAULT '');"
                "CREATE TABLE tool_attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "command_family TEXT NOT NULL DEFAULT '', cwd TEXT NOT NULL DEFAULT '', "
                "os_name TEXT NOT NULL DEFAULT '', shell TEXT NOT NULL DEFAULT '', profile "
                "TEXT NOT NULL DEFAULT '', exit_code INTEGER NOT NULL DEFAULT 1, "
                "failure_class TEXT NOT NULL DEFAULT '', resolution TEXT NOT NULL DEFAULT '', "
                "fallback TEXT NOT NULL DEFAULT '', scope TEXT NOT NULL DEFAULT '', freshness "
                "TEXT NOT NULL DEFAULT '', repeat_count INTEGER NOT NULL DEFAULT 1, project_id "
                "TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT '', updated_at "
                "TEXT NOT NULL DEFAULT '');"
                "INSERT INTO projects (id,name) VALUES ('legacy','Legacy');"
            )
            conn.commit()
            conn.close()

            with pala_db.connect(db) as migrated:
                version = migrated.execute("SELECT version FROM schema_version").fetchone()[0]
                self.assertEqual(version, pala_db.SCHEMA_VERSION)
                self.assertEqual(
                    migrated.execute("SELECT name FROM projects WHERE id='legacy'").fetchone()[0],
                    "Legacy",
                )
            self.assertTrue(Path(str(db) + ".v1.bak").is_file())
            before = db.read_bytes()
            with pala_db.connect(db):
                pass
            self.assertEqual(db.read_bytes(), before)

    def test_future_schema_and_read_only_missing_store_fail_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
            conn.execute("INSERT INTO schema_version VALUES (?)", (pala_db.SCHEMA_VERSION + 1,))
            conn.commit()
            conn.close()
            before = db.read_bytes()
            with self.assertRaises(pala_db.StoreSchemaError), pala_db.connect(db):
                pass
            self.assertEqual(db.read_bytes(), before)

            missing = Path(temp) / "missing.sqlite"
            with self.assertRaises(pala_db.StoreOpenError), pala_db.connect(
                missing, read_only=True
            ):
                pass
            self.assertFalse(missing.exists())


class ProjectHistoryContractTests(unittest.TestCase):
    def _context(
        self, profile_id: str = "pala-project-studio"
    ) -> tuple[dict[str, object], object, object]:
        profile = profile_payload()
        profile["project_id"] = profile_id
        digest = ProjectProfile.from_dict(profile).digest()
        return profile, receipt(profile_digest=digest), expectation(profile_digest=digest)

    def _persist(self, db: Path, *, profile_id: str = "pala-project-studio") -> dict[str, object]:
        profile, current, expected = self._context(profile_id)
        return persist_context_summary(
            profile,
            current.to_dict(),
            expected=expected,
            path=db,
        )

    def test_context_persistence_stores_owner_summaries_not_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            summary = self._persist(db)
            self.assertEqual(summary["validation_status"], "passed")
            raw = db.read_bytes()
            self.assertNotIn(b"Local software delivery operating system", raw)
            self.assertNotIn(b"PLAN.md", raw)
            self.assertNotIn(b"quality/python", raw)
            self.assertFalse(summary["can_complete"])

    def test_close_is_idempotent_immutable_and_survives_event_pruning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            continuity = self._persist(db)
            kwargs = {
                "current_receipt_id": continuity["receipt_id"],
                "summary": "M76 delivery baseline closed",
                "final_commit": "c" * 40,
                "release_ref": "v1.2.0",
                "risk_codes": ["M77-NOT-RUN"],
                "lessons": ["keep-owner-summaries"],
                "authority_ref": "quality/m76",
                "path": db,
            }
            first = record_closure("pala-project-studio", **kwargs)
            second = record_closure("pala-project-studio", **kwargs)
            self.assertEqual(first["history_id"], second["history_id"])
            for index in range(20):
                pala_db.add_event("checkpoint", project_id="noise", detail=str(index), path=db)
            pala_db.prune_events(keep=1, path=db)
            model = list_history(project_id="pala-project-studio", path=db)
            self.assertEqual(model["validation_status"], "passed")
            self.assertEqual(len(model["items"]), 1)
            self.assertFalse(model["can_complete"])

    def test_reopen_requires_fresh_live_receipt_and_preserves_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            continuity = self._persist(db)
            closed = record_closure(
                "pala-project-studio",
                current_receipt_id=continuity["receipt_id"],
                summary="M76 closed",
                final_commit="c" * 40,
                release_ref=None,
                risk_codes=[],
                lessons=["bounded-history"],
                authority_ref="quality/m76",
                path=db,
            )
            before = json.dumps(closed, sort_keys=True)
            profile, current, expected = self._context()
            reopened = record_reopen(
                "pala-project-studio",
                closure_id=closed["history_id"],
                profile_payload=profile,
                receipt_payload=current.to_dict(),
                expected=expected,
                authority_ref="task/M77-T1",
                path=db,
            )
            self.assertEqual(reopened["lifecycle"], "project-reopened")
            items = list_history(project_id="pala-project-studio", path=db)["items"]
            self.assertEqual(len(items), 2)
            self.assertEqual(json.dumps(items[-1], sort_keys=True), before)

    def test_private_history_and_corrupt_rows_fail_closed_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            continuity = self._persist(db)
            secret = "token=do-not-echo-fixture"
            with self.assertRaises(ProjectHistoryError) as caught:
                record_closure(
                    "pala-project-studio",
                    current_receipt_id=continuity["receipt_id"],
                    summary=secret,
                    final_commit="c" * 40,
                    release_ref=None,
                    risk_codes=[],
                    lessons=[],
                    authority_ref="quality/m76",
                    path=db,
                )
            self.assertEqual(caught.exception.code, "HISTORY_PRIVATE_DATA_REJECTED")
            self.assertNotIn(secret, str(caught.exception))

            with pala_db.connect(db) as conn:
                conn.execute(
                    "INSERT INTO project_history "
                    "(history_id,project_id,repository_id,lifecycle,payload_json,created_at) "
                    "VALUES (?,?,?,?,?,?)",
                    ("f" * 64, "pala-project-studio", "a" * 24, "project-closed", "{broken", "now"),
                )
            model = list_history(project_id="pala-project-studio", path=db)
            self.assertEqual(model["validation_status"], "blocked")
            self.assertNotIn("broken", json.dumps(model))

    def test_completion_events_are_supported_and_project_filtered(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            pala_db.add_event("complete", project_id="alpha", detail="done", path=db)
            pala_db.add_event("checkpoint", project_id="beta", detail="private-beta", path=db)
            events = pala_db.recent_events(limit=10, project_id="alpha", path=db)
            self.assertEqual([item["kind"] for item in events], ["complete"])
            self.assertNotIn("private-beta", json.dumps(events))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contract tests for the local SQLite store (ADR-015)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pala_db

_ENV_TMP: tempfile.TemporaryDirectory | None = None
_ENV_PREV: dict[str, str | None] = {}


def setUpModule() -> None:
    """Never let a developer environment point tests at the real store."""
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


def project_entry(project_id: str, **overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "id": project_id,
        "name": project_id,
        "path": f"C:/tmp/{project_id}",
        "github": None,
        "tech": ["python"],
        "phase": "",
        "quality_result": "",
        "tools_summary": "",
        "next_action": "",
        "blockers": [],
        "updated_at": "2026-08-01T00:00:00+00:00",
    }
    entry.update(overrides)
    return entry


class SchemaTests(unittest.TestCase):
    def test_ensure_schema_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            with pala_db.connect(db) as first:
                pala_db.ensure_schema(first)
            with pala_db.connect(db) as second:
                pala_db.ensure_schema(second)
                version = second.execute(
                    "SELECT version FROM schema_version"
                ).fetchall()
            self.assertEqual([row["version"] for row in version], [pala_db.SCHEMA_VERSION])
            self.assertTrue(db.is_file())

    def test_default_db_path_follows_catalog_root(self) -> None:
        previous = os.environ.pop("PALA_DB_PATH", None)
        try:
            self.assertEqual(
                pala_db.default_db_path(),
                Path(os.environ["PALA_CATALOG_ROOT"]) / pala_db.DB_NAME,
            )
        finally:
            if previous is not None:
                os.environ["PALA_DB_PATH"] = previous


class ProjectTests(unittest.TestCase):
    def test_upsert_merges_without_losing_previous_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            pala_db.upsert_project(
                project_entry("alpha", phase="F2-T1", next_action="A"), path=db
            )
            pala_db.upsert_project(
                project_entry(
                    "alpha",
                    phase="",
                    next_action="B",
                    updated_at="2026-08-02T00:00:00+00:00",
                ),
                path=db,
            )
            projects = pala_db.list_projects(db)
            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0]["next_action"], "B")
            self.assertEqual(projects[0]["phase"], "F2-T1")
            self.assertEqual(projects[0]["updated_at"], "2026-08-02T00:00:00+00:00")
            self.assertEqual(projects[0]["tech"], ["python"])
            self.assertEqual(projects[0]["blockers"], [])

    def test_list_projects_orders_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            pala_db.upsert_project(
                project_entry("old", updated_at="2026-01-01T00:00:00+00:00"), path=db
            )
            pala_db.upsert_project(
                project_entry("new", updated_at="2026-08-01T00:00:00+00:00"), path=db
            )
            names = [item["name"] for item in pala_db.list_projects(db)]
            self.assertEqual(names, ["new", "old"])

    def test_concurrent_writers_keep_every_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            errors: list[BaseException] = []

            def write(prefix: str) -> None:
                try:
                    for index in range(12):
                        pala_db.upsert_project(
                            project_entry(f"{prefix}-{index}"), path=db
                        )
                except BaseException as exc:  # noqa: BLE001 - surfaced below
                    errors.append(exc)

            threads = [
                threading.Thread(target=write, args=("a",)),
                threading.Thread(target=write, args=("b",)),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            self.assertEqual(errors, [])
            self.assertEqual(len(pala_db.list_projects(db)), 24)


class EventTests(unittest.TestCase):
    def test_recent_events_are_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            for index in range(3):
                pala_db.add_event(
                    "checkpoint",
                    project_name="alpha",
                    detail=f"step {index}",
                    path=db,
                )
            events = pala_db.recent_events(limit=2, path=db)
            self.assertEqual([item["detail"] for item in events], ["step 2", "step 1"])
            self.assertEqual(events[0]["kind"], "checkpoint")
            self.assertEqual(events[0]["project_name"], "alpha")

    def test_unknown_kind_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            with self.assertRaises(ValueError):
                pala_db.add_event("deploy", path=db)

    def test_long_text_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            pala_db.add_event(
                "mismatch", detail="x" * 900, evidence="y" * 900, path=db
            )
            event = pala_db.recent_events(limit=1, path=db)[0]
            self.assertEqual(len(event["detail"]), pala_db.DETAIL_LIMIT)
            self.assertEqual(len(event["evidence"]), pala_db.EVIDENCE_LIMIT)

    def test_remote_userinfo_is_scrubbed_from_projects_provisions_and_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            secret_url = "https://token:secret@github.com/example/demo.git"
            pala_db.upsert_project(project_entry("private", github=secret_url), path=db)
            pala_db.upsert_provision(
                source_url=secret_url,
                install_path="C:/tmp/private",
                path=db,
            )
            pala_db.add_event(
                "provision",
                detail=f"clone {secret_url}",
                evidence=secret_url,
                path=db,
            )

            # Simulate a pre-0.9.1 local store written before the redaction
            # boundary existed. The next read must repair persisted rows too.
            with pala_db.connect(db) as conn:
                conn.execute("UPDATE projects SET github = ?", (secret_url,))
                conn.execute("UPDATE provisions SET source_url = ?", (secret_url,))
                conn.execute(
                    "UPDATE events SET detail = ?, evidence = ?",
                    (f"clone {secret_url}", secret_url),
                )

            project = pala_db.list_projects(db)[0]
            provision = pala_db.recent_provisions(path=db)[0]
            event = pala_db.recent_events(limit=1, path=db)[0]
            self.assertEqual(project["github"], "https://github.com/example/demo.git")
            self.assertEqual(provision["source_url"], "https://github.com/example/demo.git")
            self.assertNotIn("token", event["detail"])
            self.assertNotIn("secret", event["evidence"])
            with pala_db.connect(db) as conn:
                serialized = "\n".join(
                    str(row[0])
                    for row in conn.execute(
                        "SELECT github FROM projects UNION ALL SELECT source_url FROM provisions"
                    ).fetchall()
                )
            self.assertNotIn("token", serialized)
            self.assertNotIn("secret", serialized)

    def test_prune_keeps_newest_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            for index in range(60):
                pala_db.add_event("begin", detail=f"t{index}", path=db)
            removed = pala_db.prune_events(keep=10, path=db)
            self.assertEqual(removed, 50)
            events = pala_db.recent_events(limit=50, path=db)
            self.assertEqual(len(events), 10)
            self.assertEqual(events[0]["detail"], "t59")
            self.assertEqual(events[-1]["detail"], "t50")


class ProvisionTests(unittest.TestCase):
    def test_upsert_provision_dedupes_by_install_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "pala.sqlite"
            pala_db.upsert_provision(
                source_url="https://github.com/example/demo.git",
                install_path="C:/tmp/demo",
                status="provisioned",
                pala_version="0.7.0",
                path=db,
            )
            pala_db.upsert_provision(
                source_url="https://github.com/example/demo.git",
                install_path="C:/tmp/demo",
                status="fetched",
                pala_version="0.7.0",
                registered=True,
                path=db,
            )
            rows = pala_db.recent_provisions(path=db)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "fetched")
            self.assertTrue(rows[0]["registered"])


class MigrationTests(unittest.TestCase):
    def test_migrate_imports_json_once_and_writes_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog = root / "pala-catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "projects": [
                            project_entry("legacy", phase="F1-T9", next_action="ship")
                        ],
                    }
                ),
                encoding="utf-8",
            )
            registry = root / "provision-registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "installs": [
                            {
                                "source_url": "https://github.com/example/legacy.git",
                                "installed_path": "C:/tmp/legacy",
                                "installed_at": "2026-07-01T00:00:00+00:00",
                                "pala_version": "0.6.0",
                                "last_status": "provisioned",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            db = root / "pala.sqlite"

            first = pala_db.migrate_from_json(
                catalog_path=catalog, registry_path=registry, path=db
            )
            self.assertEqual(first["projects"], 1)
            self.assertEqual(first["provisions"], 1)
            self.assertTrue((root / "pala-catalog.json.bak").is_file())

            second = pala_db.migrate_from_json(
                catalog_path=catalog, registry_path=registry, path=db
            )
            self.assertTrue(second["skipped"])
            self.assertEqual(len(pala_db.list_projects(db)), 1)
            self.assertEqual(len(pala_db.recent_provisions(path=db)), 1)
            imported = pala_db.list_projects(db)[0]
            self.assertEqual(imported["phase"], "F1-T9")
            self.assertEqual(imported["updated_at"], "2026-08-01T00:00:00+00:00")

    def test_migrate_tolerates_missing_and_broken_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            broken = root / "pala-catalog.json"
            broken.write_text("{not json", encoding="utf-8")
            result = pala_db.migrate_from_json(
                catalog_path=broken,
                registry_path=root / "missing.json",
                path=root / "pala.sqlite",
            )
            self.assertEqual(result["projects"], 0)
            self.assertEqual(result["provisions"], 0)

    def test_registry_migrates_after_catalog_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / "pala.sqlite"
            catalog = root / "pala-catalog.json"
            catalog.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "projects": [project_entry("early")],
                    }
                ),
                encoding="utf-8",
            )
            first = pala_db.migrate_from_json(catalog_path=catalog, path=db)
            self.assertEqual(first["projects"], 1)
            self.assertEqual(first["provisions"], 0)

            registry = root / "provision-registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "installs": [
                            {
                                "source_url": "https://github.com/example/late.git",
                                "installed_path": "C:/tmp/late",
                                "last_status": "provisioned",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            second = pala_db.migrate_from_json(
                catalog_path=catalog, registry_path=registry, path=db
            )
            self.assertEqual(second["projects"], 0)
            self.assertEqual(second["provisions"], 1)
            self.assertFalse(second["skipped"])
            self.assertEqual(len(pala_db.recent_provisions(path=db)), 1)


if __name__ == "__main__":
    unittest.main()

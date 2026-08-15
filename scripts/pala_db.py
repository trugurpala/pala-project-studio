#!/usr/bin/env python3
"""Local SQLite store for Pala's cross-project memory (ADR-015).

Machine-local, secrets-free, and kept next to the human-readable catalog so the
owner can see and back it up. Concurrent Codex sessions can write safely (WAL +
busy timeout), event history answers "what happened", and the JSON/INDEX exports
remain the recovery path. Stdlib only; no server, no network, no cloud.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path

from pala_redaction import redact_remote_url, redact_text

SCHEMA_VERSION = 2
DB_NAME = "pala.sqlite"
BUSY_TIMEOUT_MS = 5000
EVENT_KINDS = (
    "register",
    "begin",
    "checkpoint",
    "provision",
    "mismatch",
    "debug_attempt",
    "tool_attempt",
    "complete",
)
DETAIL_LIMIT = 300
EVIDENCE_LIMIT = 500
EVENT_KEEP = 2000
PRUNE_EVERY = 200
CATALOG_MARKER = "catalog_migrated_at"
REGISTRY_MARKER = "registry_migrated_at"
LEGACY_REGISTRY_NAME = "provision-registry.json"

class StoreError(RuntimeError):
    """Base class for sanitized machine-local store failures."""


class StoreOpenError(StoreError):
    """The requested store cannot be opened without changing it."""


class StoreSchemaError(StoreError):
    """The store schema is corrupt, ambiguous, or from a future version."""


class StoreMigrationError(StoreError):
    """A transactional schema migration could not be completed safely."""


_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)",
    "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    """CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL DEFAULT '',
        path TEXT NOT NULL DEFAULT '',
        github TEXT,
        tech_json TEXT NOT NULL DEFAULT '[]',
        phase TEXT NOT NULL DEFAULT '',
        quality_result TEXT NOT NULL DEFAULT '',
        tools_summary TEXT NOT NULL DEFAULT '',
        next_action TEXT NOT NULL DEFAULT '',
        blockers_json TEXT NOT NULL DEFAULT '[]',
        updated_at TEXT NOT NULL DEFAULT ''
    )""",
    """CREATE TABLE IF NOT EXISTS provisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_url TEXT NOT NULL DEFAULT '',
        install_path TEXT NOT NULL UNIQUE,
        pala_version TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT '',
        registered INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT ''
    )""",
    """CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT NOT NULL DEFAULT '',
        project_name TEXT NOT NULL DEFAULT '',
        kind TEXT NOT NULL,
        detail TEXT NOT NULL DEFAULT '',
        evidence TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT ''
    )""",
    """CREATE TABLE IF NOT EXISTS tool_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        command_family TEXT NOT NULL DEFAULT '',
        cwd TEXT NOT NULL DEFAULT '',
        os_name TEXT NOT NULL DEFAULT '',
        shell TEXT NOT NULL DEFAULT '',
        profile TEXT NOT NULL DEFAULT '',
        exit_code INTEGER NOT NULL DEFAULT 1,
        failure_class TEXT NOT NULL DEFAULT '',
        resolution TEXT NOT NULL DEFAULT '',
        fallback TEXT NOT NULL DEFAULT '',
        scope TEXT NOT NULL DEFAULT '',
        freshness TEXT NOT NULL DEFAULT '',
        repeat_count INTEGER NOT NULL DEFAULT 1,
        project_id TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL DEFAULT ''
    )""",
    "CREATE INDEX IF NOT EXISTS idx_projects_updated ON projects (updated_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_events_recent ON events (id DESC)",
    "CREATE INDEX IF NOT EXISTS idx_tool_attempts_lookup ON tool_attempts "
    "(failure_class, command_family, os_name, shell, profile)",
    """CREATE TABLE IF NOT EXISTS project_continuity (
        project_id TEXT PRIMARY KEY,
        repository_id TEXT NOT NULL,
        worktree_id TEXT NOT NULL,
        profile_digest TEXT NOT NULL,
        profile_kind TEXT NOT NULL,
        data_classification TEXT NOT NULL,
        receipt_id TEXT NOT NULL,
        receipt_validation_status TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_continuity_repository_project "
    "ON project_continuity (repository_id, project_id)",
    """CREATE TABLE IF NOT EXISTS project_history (
        history_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        repository_id TEXT NOT NULL,
        lifecycle TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS idx_project_history_lookup ON project_history "
    "(project_id, created_at DESC)",
    """CREATE TRIGGER IF NOT EXISTS project_history_no_update
        BEFORE UPDATE ON project_history BEGIN
        SELECT RAISE(ABORT, 'project_history is append-only'); END""",
    """CREATE TRIGGER IF NOT EXISTS project_history_no_delete
        BEFORE DELETE ON project_history BEGIN
        SELECT RAISE(ABORT, 'project_history is append-only'); END""",
)

_PROJECT_COLUMNS = (
    "name",
    "path",
    "github",
    "tech_json",
    "phase",
    "quality_result",
    "tools_summary",
    "next_action",
    "blockers_json",
)

_REQUIRED_TABLES = {
    "schema_version",
    "meta",
    "projects",
    "provisions",
    "events",
    "tool_attempts",
    "project_continuity",
    "project_history",
}


def default_catalog_root() -> Path:
    """Desktop/Codex under the current user home; portable across machines."""
    return Path.home() / "Desktop" / "Codex"


def catalog_root() -> Path:
    override = os.environ.get("PALA_CATALOG_ROOT")
    if override:
        return Path(override)
    return default_catalog_root()


def default_db_path() -> Path:
    """PALA_DB_PATH wins, otherwise the store sits in the catalog root."""
    override = os.environ.get("PALA_DB_PATH")
    if override:
        return Path(override)
    return catalog_root() / DB_NAME


def db_path_for(root: Path | None) -> Path:
    """Explicit catalog directory wins over environment defaults."""
    if root is None:
        return default_db_path()
    return Path(root) / DB_NAME


def legacy_registry_path() -> Path:
    """Pre-0.7 machine-local provision registry; kept only as a migration source."""
    override = os.environ.get("PALA_PROVISION_REGISTRY")
    if override:
        return Path(override)
    profile = Path(os.environ.get("USERPROFILE", Path.home()))
    local = Path(os.environ.get("LOCALAPPDATA", profile / "AppData" / "Local"))
    return local / "Pala" / LEGACY_REGISTRY_NAME


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _schema_version(conn: sqlite3.Connection) -> int | None:
    tables = _user_tables(conn)
    if not tables:
        return None
    if "schema_version" not in tables:
        raise StoreSchemaError("STORE_SCHEMA_VERSION_MISSING")
    try:
        rows = conn.execute("SELECT version FROM schema_version").fetchall()
    except sqlite3.DatabaseError as exc:
        raise StoreSchemaError("STORE_SCHEMA_VERSION_INVALID") from exc
    if len(rows) != 1 or not isinstance(rows[0][0], int):
        raise StoreSchemaError("STORE_SCHEMA_VERSION_AMBIGUOUS")
    return int(rows[0][0])


def _quick_check(conn: sqlite3.Connection) -> None:
    try:
        rows = conn.execute("PRAGMA quick_check").fetchall()
    except sqlite3.DatabaseError as exc:
        raise StoreSchemaError("STORE_INTEGRITY_CHECK_FAILED") from exc
    if [str(row[0]) for row in rows] != ["ok"]:
        raise StoreSchemaError("STORE_INTEGRITY_CHECK_FAILED")


def _validate_current_schema(conn: sqlite3.Connection) -> None:
    missing = _REQUIRED_TABLES - _user_tables(conn)
    if missing:
        raise StoreSchemaError("STORE_SCHEMA_INCOMPLETE")
    _quick_check(conn)


def _backup_database(conn: sqlite3.Connection, target: Path, version: int) -> Path:
    backup = Path(str(target) + f".v{version}.bak")
    if backup.exists():
        return backup
    destination: sqlite3.Connection | None = None
    try:
        destination = sqlite3.connect(str(backup))
        conn.backup(destination)
    except (OSError, sqlite3.DatabaseError) as exc:
        with suppress(OSError):
            backup.unlink(missing_ok=True)
        raise StoreMigrationError("STORE_MIGRATION_BACKUP_FAILED") from exc
    finally:
        if destination is not None:
            destination.close()
    return backup


def _create_current_schema(conn: sqlite3.Connection) -> None:
    conn.execute("BEGIN IMMEDIATE")
    try:
        current = _schema_version(conn)
        if current is not None:
            if current != SCHEMA_VERSION:
                raise StoreSchemaError("STORE_SCHEMA_CREATION_RACE")
            conn.execute("COMMIT")
            return
        for statement in _SCHEMA:
            conn.execute(statement)
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def _migrate_v1_to_v2(conn: sqlite3.Connection, target: Path) -> None:
    _quick_check(conn)
    _backup_database(conn, target, 1)
    conn.execute("BEGIN IMMEDIATE")
    try:
        for statement in _SCHEMA:
            if statement.startswith("CREATE TABLE IF NOT EXISTS schema_version"):
                continue
            conn.execute(statement)
        conn.execute("ALTER TABLE schema_version RENAME TO schema_version_v1")
        conn.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        conn.execute("DROP TABLE schema_version_v1")
    except BaseException as exc:
        conn.execute("ROLLBACK")
        raise StoreMigrationError("STORE_MIGRATION_ROLLED_BACK") from exc
    conn.execute("COMMIT")


def ensure_schema(conn: sqlite3.Connection, *, path: Path | None = None) -> None:
    """Create or transactionally migrate the store; future versions fail closed."""
    version = _schema_version(conn)
    if version is None:
        _create_current_schema(conn)
        return
    if version == SCHEMA_VERSION:
        _validate_current_schema(conn)
        return
    if version > SCHEMA_VERSION or version < 1:
        raise StoreSchemaError("STORE_SCHEMA_VERSION_UNSUPPORTED")
    if version == 1:
        if path is None:
            raise StoreMigrationError("STORE_MIGRATION_PATH_REQUIRED")
        _migrate_v1_to_v2(conn, Path(path))
        return
    raise StoreSchemaError("STORE_SCHEMA_VERSION_UNSUPPORTED")


def _scrub_remote_values(conn: sqlite3.Connection) -> None:
    """Repair pre-redaction local rows without retaining URL credentials."""
    for table, key, columns in (
        ("projects", "id", ("github",)),
        ("provisions", "id", ("source_url",)),
        ("events", "id", ("detail", "evidence")),
    ):
        selected = ", ".join((key, *columns))
        rows = conn.execute(f"SELECT {selected} FROM {table}").fetchall()
        for row in rows:
            safe = {
                column: (
                    redact_remote_url(row[column])
                    if column in ("github", "source_url")
                    else redact_text(row[column])
                )
                for column in columns
            }
            if all(safe[column] == row[column] for column in columns):
                continue
            assignments = ", ".join(f"{column} = ?" for column in columns)
            conn.execute(
                f"UPDATE {table} SET {assignments} WHERE {key} = ?",
                (*(safe[column] for column in columns), row[key]),
            )


@contextmanager
def connect(
    path: Path | None = None,
    *,
    read_only: bool = False,
) -> Iterator[sqlite3.Connection]:
    """Open the store; read-only mode never creates, migrates, or scrubs."""
    target = Path(path) if path is not None else default_db_path()
    if read_only:
        if not target.is_file():
            raise StoreOpenError("STORE_NOT_FOUND")
        uri = target.resolve().as_uri() + "?mode=ro"
        try:
            conn = sqlite3.connect(
                uri,
                timeout=BUSY_TIMEOUT_MS / 1000,
                isolation_level=None,
                uri=True,
            )
        except sqlite3.DatabaseError as exc:
            raise StoreOpenError("STORE_OPEN_FAILED") from exc
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            str(target), timeout=BUSY_TIMEOUT_MS / 1000, isolation_level=None
        )
    try:
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        if read_only:
            conn.execute("PRAGMA query_only=ON")
            version = _schema_version(conn)
            if version != SCHEMA_VERSION:
                raise StoreSchemaError("STORE_SCHEMA_MIGRATION_REQUIRED")
            _validate_current_schema(conn)
        else:
            ensure_schema(conn, path=target)
            with suppress(sqlite3.DatabaseError):
                conn.execute("PRAGMA journal_mode=WAL")
            _scrub_remote_values(conn)
        yield conn
    finally:
        conn.close()


def _text(value: object, limit: int) -> str:
    if value is None:
        return ""
    return str(value)[:limit]


def _json_list(value: object, *, item_limit: int, count_limit: int) -> str:
    items = value if isinstance(value, list) else []
    bounded = [str(item)[:item_limit] for item in items][:count_limit]
    return json.dumps(bounded, ensure_ascii=False)


def _load_list(value: object) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise StoreSchemaError("STORE_ROW_JSON_CORRUPT") from exc
    if not isinstance(payload, list):
        raise StoreSchemaError("STORE_ROW_JSON_CORRUPT")
    return [str(item) for item in payload]


def _row_to_project(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "name": row["name"],
        "path": row["path"],
        "github": redact_remote_url(row["github"]) or None,
        "tech": _load_list(row["tech_json"]),
        "phase": row["phase"],
        "quality_result": row["quality_result"],
        "tools_summary": row["tools_summary"],
        "next_action": row["next_action"],
        "blockers": _load_list(row["blockers_json"]),
        "updated_at": row["updated_at"],
    }


def _project_values(entry: dict[str, object]) -> dict[str, object]:
    return {
        "name": _text(entry.get("name"), 160),
        "path": _text(entry.get("path"), 400),
        "github": redact_remote_url(_text(entry.get("github"), 300)) or None,
        "tech_json": _json_list(entry.get("tech"), item_limit=40, count_limit=12),
        "phase": _text(entry.get("phase"), 120),
        "quality_result": _text(entry.get("quality_result"), 120),
        "tools_summary": _text(entry.get("tools_summary"), 160),
        "next_action": _text(entry.get("next_action"), 300),
        "blockers_json": _json_list(entry.get("blockers"), item_limit=160, count_limit=8),
    }


def _is_empty(column: str, value: object) -> bool:
    if value is None or value == "":
        return True
    return column in ("tech_json", "blockers_json") and value == "[]"


def upsert_project(
    entry: dict[str, object], *, path: Path | None = None
) -> dict[str, object]:
    """Insert or merge one project; empty incoming fields never erase history."""
    project_id = _text(entry.get("id"), 160)
    if not project_id:
        raise ValueError("project id is required")
    values = _project_values(entry)
    updated_at = _text(entry.get("updated_at"), 40) or _now()
    with connect(path) as conn:
        existing = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if existing is None:
            columns = ", ".join(("id", *_PROJECT_COLUMNS, "updated_at"))
            placeholders = ", ".join("?" for _ in range(len(_PROJECT_COLUMNS) + 2))
            conn.execute(
                f"INSERT INTO projects ({columns}) VALUES ({placeholders})",
                (
                    project_id,
                    *(values[column] for column in _PROJECT_COLUMNS),
                    updated_at,
                ),
            )
        else:
            merged = {
                column: (
                    existing[column]
                    if _is_empty(column, values[column])
                    else values[column]
                )
                for column in _PROJECT_COLUMNS
            }
            assignments = ", ".join(f"{column} = ?" for column in _PROJECT_COLUMNS)
            conn.execute(
                f"UPDATE projects SET {assignments}, updated_at = ? WHERE id = ?",
                (
                    *(merged[column] for column in _PROJECT_COLUMNS),
                    updated_at,
                    project_id,
                ),
            )
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return _row_to_project(row)


def list_projects(
    path: Path | None = None, *, read_only: bool = False
) -> list[dict[str, object]]:
    target = Path(path) if path is not None else default_db_path()
    if read_only and not target.is_file():
        return []
    with connect(target, read_only=read_only) as conn:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC, name ASC"
        ).fetchall()
        return [_row_to_project(row) for row in rows]


def get_project(
    project_id: str,
    path: Path | None = None,
    *,
    read_only: bool = False,
) -> dict[str, object] | None:
    target = Path(path) if path is not None else default_db_path()
    if read_only and not target.is_file():
        return None
    with connect(target, read_only=read_only) as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return _row_to_project(row) if row is not None else None


def upsert_project_continuity(
    entry: dict[str, object], *, path: Path | None = None
) -> dict[str, object]:
    """Persist one owner-validated scalar continuity summary."""
    required = (
        "project_id",
        "repository_id",
        "worktree_id",
        "profile_digest",
        "profile_kind",
        "data_classification",
        "receipt_id",
        "receipt_validation_status",
    )
    values = {name: _text(entry.get(name), 160) for name in required}
    if any(not values[name] for name in required):
        raise ValueError("continuity summary is incomplete")
    stamp = _text(entry.get("updated_at"), 40) or _now()
    with connect(path) as conn:
        existing = conn.execute(
            "SELECT * FROM project_continuity WHERE project_id = ?",
            (values["project_id"],),
        ).fetchone()
        if existing is not None and existing["repository_id"] != values["repository_id"]:
            raise ValueError("project continuity repository identity conflict")
        columns = tuple(required)
        unchanged = existing is not None and all(
            existing[column] == values[column] for column in columns
        )
        if existing is None:
            conn.execute(
                "INSERT INTO project_continuity "
                "(project_id,repository_id,worktree_id,profile_digest,profile_kind,"
                "data_classification,receipt_id,receipt_validation_status,updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (*(values[column] for column in columns), stamp),
            )
        elif not unchanged:
            conn.execute(
                "UPDATE project_continuity SET worktree_id=?, profile_digest=?, "
                "profile_kind=?, data_classification=?, receipt_id=?, "
                "receipt_validation_status=?, updated_at=? WHERE project_id=?",
                (
                    values["worktree_id"],
                    values["profile_digest"],
                    values["profile_kind"],
                    values["data_classification"],
                    values["receipt_id"],
                    values["receipt_validation_status"],
                    stamp,
                    values["project_id"],
                ),
            )
        row = conn.execute(
            "SELECT * FROM project_continuity WHERE project_id = ?",
            (values["project_id"],),
        ).fetchone()
        return dict(row)


def get_project_continuity(
    project_id: str, *, path: Path | None = None
) -> dict[str, object] | None:
    target = Path(path) if path is not None else default_db_path()
    if not target.is_file():
        return None
    with connect(target, read_only=True) as conn:
        row = conn.execute(
            "SELECT * FROM project_continuity WHERE project_id = ?", (project_id,)
        ).fetchone()
        return dict(row) if row is not None else None


def append_project_history(
    entry: dict[str, object], *, path: Path | None = None
) -> tuple[dict[str, object], bool]:
    """Append an immutable row; identical content is an idempotent no-op."""
    fields = (
        "history_id",
        "project_id",
        "repository_id",
        "lifecycle",
        "payload_json",
        "created_at",
    )
    values = {field: _text(entry.get(field), 16_384) for field in fields}
    if any(not values[field] for field in fields):
        raise ValueError("project history row is incomplete")
    with connect(path) as conn:
        existing = conn.execute(
            "SELECT * FROM project_history WHERE history_id = ?",
            (values["history_id"],),
        ).fetchone()
        if existing is not None:
            semantic_fields = tuple(field for field in fields if field != "created_at")
            if any(existing[field] != values[field] for field in semantic_fields):
                raise ValueError("project history identity collision")
            return dict(existing), False
        conn.execute(
            "INSERT INTO project_history "
            "(history_id,project_id,repository_id,lifecycle,payload_json,created_at) "
            "VALUES (?,?,?,?,?,?)",
            tuple(values[field] for field in fields),
        )
        row = conn.execute(
            "SELECT * FROM project_history WHERE history_id = ?",
            (values["history_id"],),
        ).fetchone()
        return dict(row), True


def list_project_history_rows(
    *,
    project_id: str | None = None,
    repository_id: str | None = None,
    lifecycle: str | None = None,
    limit: int = 50,
    path: Path | None = None,
) -> list[dict[str, object]]:
    target = Path(path) if path is not None else default_db_path()
    if not target.is_file():
        return []
    clauses: list[str] = []
    params: list[object] = []
    if project_id is not None:
        clauses.append("project_id = ?")
        params.append(_text(project_id, 160))
    if repository_id is not None:
        clauses.append("repository_id = ?")
        params.append(_text(repository_id, 160))
    if lifecycle is not None:
        clauses.append("lifecycle = ?")
        params.append(_text(lifecycle, 80))
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(max(int(limit), 0))
    with connect(target, read_only=True) as conn:
        rows = conn.execute(
            "SELECT * FROM project_history" + where
            + " ORDER BY created_at DESC, rowid DESC LIMIT ?",
            tuple(params),
        ).fetchall()
        return [dict(row) for row in rows]


def _prune(conn: sqlite3.Connection, keep: int) -> int:
    cursor = conn.execute(
        "DELETE FROM events WHERE id NOT IN "
        "(SELECT id FROM events ORDER BY id DESC LIMIT ?)",
        (max(int(keep), 0),),
    )
    return cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0


def prune_events(keep: int = EVENT_KEEP, path: Path | None = None) -> int:
    """Bound history growth; newest events are always the survivors."""
    with connect(path) as conn:
        return _prune(conn, keep)


def add_event(
    kind: str,
    *,
    project_id: str = "",
    project_name: str = "",
    detail: str = "",
    evidence: str = "",
    path: Path | None = None,
) -> int:
    """Append one bounded, secrets-free history line."""
    if kind not in EVENT_KINDS:
        raise ValueError(f"unsupported event kind: {kind}")
    with connect(path) as conn:
        cursor = conn.execute(
            "INSERT INTO events "
            "(project_id, project_name, kind, detail, evidence, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                _text(project_id, 160),
                _text(project_name, 160),
                kind,
                _text(redact_text(detail), DETAIL_LIMIT),
                _text(redact_text(evidence), EVIDENCE_LIMIT),
                _now(),
            ),
        )
        event_id = int(cursor.lastrowid or 0)
        if event_id and event_id % PRUNE_EVERY == 0:
            _prune(conn, EVENT_KEEP)
        return event_id


def recent_events(
    limit: int = 15,
    path: Path | None = None,
    *,
    project_id: str | None = None,
    read_only: bool = False,
) -> list[dict[str, object]]:
    target = Path(path) if path is not None else default_db_path()
    if read_only and not target.is_file():
        return []
    with connect(target, read_only=read_only) as conn:
        if project_id is None:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (max(int(limit), 0),)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM events WHERE project_id = ? ORDER BY id DESC LIMIT ?",
                (_text(project_id, 160), max(int(limit), 0)),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "project_name": row["project_name"],
                "kind": row["kind"],
                "detail": redact_text(row["detail"]),
                "evidence": redact_text(row["evidence"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]


def upsert_provision(
    *,
    source_url: str,
    install_path: str,
    status: str = "",
    pala_version: str = "",
    registered: bool = False,
    created_at: str | None = None,
    path: Path | None = None,
) -> dict[str, object]:
    """Record one URL install; the destination folder is the identity."""
    target = _text(install_path, 400)
    if not target:
        raise ValueError("install path is required")
    safe_source_url = redact_remote_url(_text(source_url, 400))
    stamp = _text(created_at, 40) or _now()
    with connect(path) as conn:
        existing = conn.execute(
            "SELECT * FROM provisions WHERE install_path = ? OR "
            "(source_url = ? AND source_url <> '') ORDER BY id LIMIT 1",
            (target, safe_source_url),
        ).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO provisions "
                "(source_url, install_path, pala_version, status, registered, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    safe_source_url,
                    target,
                    _text(pala_version, 80),
                    _text(status, 80),
                    1 if registered else 0,
                    stamp,
                ),
            )
        else:
            conn.execute(
                "UPDATE provisions SET source_url = ?, install_path = ?, "
                "pala_version = ?, status = ?, registered = ?, created_at = ? "
                "WHERE id = ?",
                (
                    safe_source_url or existing["source_url"],
                    target,
                    _text(pala_version, 80) or existing["pala_version"],
                    _text(status, 80) or existing["status"],
                    1 if registered else int(existing["registered"]),
                    stamp,
                    existing["id"],
                ),
            )
        row = conn.execute(
            "SELECT * FROM provisions WHERE install_path = ?", (target,)
        ).fetchone()
        return _row_to_provision(row)


def _row_to_provision(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "source_url": redact_remote_url(row["source_url"]),
        "install_path": row["install_path"],
        "pala_version": row["pala_version"],
        "status": row["status"],
        "registered": bool(row["registered"]),
        "created_at": row["created_at"],
    }


def recent_provisions(
    limit: int = 10,
    path: Path | None = None,
    *,
    read_only: bool = False,
) -> list[dict[str, object]]:
    target = Path(path) if path is not None else default_db_path()
    if read_only and not target.is_file():
        return []
    with connect(target, read_only=read_only) as conn:
        rows = conn.execute(
            "SELECT * FROM provisions ORDER BY created_at DESC, id DESC LIMIT ?",
            (max(int(limit), 0),),
        ).fetchall()
        return [_row_to_provision(row) for row in rows]


def _read_json(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _backup_legacy_json(source: Path) -> None:
    backup = source.with_name(source.name + ".bak")
    if backup.exists():
        return
    try:
        backup.write_bytes(source.read_bytes())
    except OSError as exc:
        raise StoreMigrationError("STORE_LEGACY_BACKUP_FAILED") from exc


def _import_project_row(conn: sqlite3.Connection, entry: dict[str, object]) -> bool:
    project_id = _text(entry.get("id"), 160)
    if not project_id:
        return False
    values = _project_values(entry)
    stamp = _text(entry.get("updated_at"), 40) or _now()
    columns = ", ".join(("id", *_PROJECT_COLUMNS, "updated_at"))
    placeholders = ", ".join("?" for _ in range(len(_PROJECT_COLUMNS) + 2))
    assignments = ", ".join(
        f"{column}=CASE WHEN excluded.{column} IN ('', '[]') OR "
        f"excluded.{column} IS NULL THEN projects.{column} ELSE excluded.{column} END"
        for column in _PROJECT_COLUMNS
    )
    conn.execute(
        f"INSERT INTO projects ({columns}) VALUES ({placeholders}) "
        f"ON CONFLICT(id) DO UPDATE SET {assignments}, updated_at=excluded.updated_at",
        (project_id, *(values[column] for column in _PROJECT_COLUMNS), stamp),
    )
    return True


def _import_provision_row(conn: sqlite3.Connection, entry: dict[str, object]) -> bool:
    target = entry.get("installed_path") or entry.get("install_path")
    if not target:
        return False
    install_path = _text(target, 400)
    source_url = redact_remote_url(_text(entry.get("source_url"), 400))
    status = _text(entry.get("last_status") or entry.get("status"), 80)
    version = _text(entry.get("pala_version"), 80)
    stamp = _text(entry.get("installed_at") or entry.get("created_at"), 40) or _now()
    conn.execute(
        "INSERT INTO provisions "
        "(source_url,install_path,pala_version,status,registered,created_at) "
        "VALUES (?,?,?,?,0,?) ON CONFLICT(install_path) DO UPDATE SET "
        "source_url=CASE WHEN excluded.source_url='' THEN provisions.source_url "
        "ELSE excluded.source_url END, "
        "pala_version=CASE WHEN excluded.pala_version='' THEN provisions.pala_version "
        "ELSE excluded.pala_version END, "
        "status=CASE WHEN excluded.status='' THEN provisions.status ELSE excluded.status END, "
        "created_at=excluded.created_at",
        (source_url, install_path, version, status, stamp),
    )
    return True


def _meta_get(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row["value"] if row is not None else None


def _meta_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        (key, value),
    )


def migrate_from_json(
    *,
    catalog_path: Path | None = None,
    registry_path: Path | None = None,
    path: Path | None = None,
) -> dict[str, object]:
    """Import pre-0.7 JSON records; catalog and registry markers are independent."""
    db = Path(path) if path is not None else default_db_path()
    imported_projects = 0
    imported_provisions = 0

    with connect(db) as conn:
        catalog_done = bool(_meta_get(conn, CATALOG_MARKER))
        registry_done = bool(_meta_get(conn, REGISTRY_MARKER))

    catalog_file = Path(catalog_path) if catalog_path is not None else None
    registry_file = Path(registry_path) if registry_path is not None else None

    if catalog_file is not None and catalog_file.is_file() and not catalog_done:
        payload = _read_json(catalog_file)
        if payload is not None:
            _backup_legacy_json(catalog_file)
            projects = payload.get("projects")
            with connect(db) as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    for entry in projects if isinstance(projects, list) else []:
                        if isinstance(entry, dict) and _import_project_row(conn, entry):
                            imported_projects += 1
                    _meta_set(conn, CATALOG_MARKER, _now())
                except BaseException:
                    conn.execute("ROLLBACK")
                    raise
                conn.execute("COMMIT")
            catalog_done = True

    if registry_file is not None and registry_file.is_file() and not registry_done:
        payload = _read_json(registry_file)
        if payload is not None:
            _backup_legacy_json(registry_file)
            installs = payload.get("installs")
            with connect(db) as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    for entry in installs if isinstance(installs, list) else []:
                        if isinstance(entry, dict) and _import_provision_row(conn, entry):
                            imported_provisions += 1
                    _meta_set(conn, REGISTRY_MARKER, _now())
                except BaseException:
                    conn.execute("ROLLBACK")
                    raise
                conn.execute("COMMIT")
            registry_done = True

    skipped = imported_projects == 0 and imported_provisions == 0
    if catalog_file is not None and catalog_file.is_file():
        skipped = skipped and catalog_done
    if registry_file is not None and registry_file.is_file():
        skipped = skipped and registry_done

    return {
        "skipped": skipped,
        "projects": imported_projects,
        "provisions": imported_provisions,
    }


def _row_to_tool_attempt(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "command_family": row["command_family"],
        "cwd": row["cwd"],
        "os": row["os_name"],
        "shell": row["shell"],
        "profile": row["profile"],
        "exit_code": int(row["exit_code"]),
        "failure_class": row["failure_class"],
        "resolution": row["resolution"],
        "fallback": row["fallback"],
        "scope": row["scope"],
        "freshness": row["freshness"],
        "repeat_count": int(row["repeat_count"]),
        "project_id": row["project_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def find_tool_attempt(
    *,
    failure_class: str,
    command_family: str,
    os_name: str = "",
    shell: str = "",
    profile: str = "",
    path: Path | None = None,
) -> dict[str, object] | None:
    """Return the newest matching failure memory row, if any."""
    with connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM tool_attempts WHERE failure_class = ? AND "
            "command_family = ? AND os_name = ? AND shell = ? AND profile = ? "
            "ORDER BY id DESC LIMIT 1",
            (
                _text(failure_class, 80),
                _text(command_family, 160),
                _text(os_name, 40),
                _text(shell, 40),
                _text(profile, 80),
            ),
        ).fetchone()
        return _row_to_tool_attempt(row) if row is not None else None


def upsert_tool_attempt(
    *,
    command_family: str,
    failure_class: str,
    cwd: str = "",
    os_name: str = "",
    shell: str = "",
    profile: str = "",
    exit_code: int = 1,
    resolution: str = "",
    fallback: str = "",
    scope: str = "",
    freshness: str = "",
    project_id: str = "",
    path: Path | None = None,
) -> dict[str, object]:
    """Insert or bump repeat_count for the same failure signature."""
    stamp = _now()
    family = _text(command_family, 160)
    klass = _text(failure_class, 80)
    os_key = _text(os_name, 40)
    shell_key = _text(shell, 40)
    profile_key = _text(profile, 80)
    with connect(path) as conn:
        existing = conn.execute(
            "SELECT * FROM tool_attempts WHERE failure_class = ? AND "
            "command_family = ? AND os_name = ? AND shell = ? AND profile = ? "
            "ORDER BY id DESC LIMIT 1",
            (klass, family, os_key, shell_key, profile_key),
        ).fetchone()
        if existing is None:
            cursor = conn.execute(
                "INSERT INTO tool_attempts "
                "(command_family, cwd, os_name, shell, profile, exit_code, "
                "failure_class, resolution, fallback, scope, freshness, "
                "repeat_count, project_id, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)",
                (
                    family,
                    _text(cwd, 400),
                    os_key,
                    shell_key,
                    profile_key,
                    int(exit_code),
                    klass,
                    _text(resolution, DETAIL_LIMIT),
                    _text(fallback, DETAIL_LIMIT),
                    _text(scope, 80),
                    _text(freshness, 40) or "fresh",
                    _text(project_id, 160),
                    stamp,
                    stamp,
                ),
            )
            row_id = int(cursor.lastrowid or 0)
        else:
            row_id = int(existing["id"])
            conn.execute(
                "UPDATE tool_attempts SET cwd = ?, exit_code = ?, "
                "resolution = ?, fallback = ?, scope = ?, freshness = ?, "
                "repeat_count = repeat_count + 1, project_id = ?, "
                "updated_at = ? WHERE id = ?",
                (
                    _text(cwd, 400) or existing["cwd"],
                    int(exit_code),
                    _text(resolution, DETAIL_LIMIT) or existing["resolution"],
                    _text(fallback, DETAIL_LIMIT) or existing["fallback"],
                    _text(scope, 80) or existing["scope"],
                    _text(freshness, 40) or "stale",
                    _text(project_id, 160) or existing["project_id"],
                    stamp,
                    row_id,
                ),
            )
        row = conn.execute(
            "SELECT * FROM tool_attempts WHERE id = ?", (row_id,)
        ).fetchone()
        return _row_to_tool_attempt(row)


def list_tool_attempts(
    *,
    limit: int = 20,
    failure_class: str | None = None,
    path: Path | None = None,
) -> list[dict[str, object]]:
    with connect(path) as conn:
        if failure_class:
            rows = conn.execute(
                "SELECT * FROM tool_attempts WHERE failure_class = ? "
                "ORDER BY updated_at DESC, id DESC LIMIT ?",
                (_text(failure_class, 80), max(int(limit), 0)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM tool_attempts ORDER BY updated_at DESC, id DESC "
                "LIMIT ?",
                (max(int(limit), 0),),
            ).fetchall()
        return [_row_to_tool_attempt(row) for row in rows]

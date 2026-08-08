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
from contextlib import contextmanager
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
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
)
DETAIL_LIMIT = 300
EVIDENCE_LIMIT = 500
EVENT_KEEP = 2000
PRUNE_EVERY = 200
CATALOG_MARKER = "catalog_migrated_at"
REGISTRY_MARKER = "registry_migrated_at"
LEGACY_REGISTRY_NAME = "provision-registry.json"

_SCHEMA = (
    "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)",
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


def ensure_schema(conn: sqlite3.Connection) -> None:
    for statement in _SCHEMA:
        conn.execute(statement)
    row = conn.execute("SELECT COUNT(*) AS total FROM schema_version").fetchone()
    if not row or row["total"] == 0:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))


@contextmanager
def connect(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Open the store with concurrency-safe pragmas and a ready schema."""
    target = Path(path) if path is not None else default_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), timeout=BUSY_TIMEOUT_MS / 1000, isolation_level=None)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            # Network shares and some filesystems refuse WAL; rollback journal is fine.
            pass
        ensure_schema(conn)
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
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload]


def _row_to_project(row: sqlite3.Row) -> dict[str, object]:
    return {
        "id": row["id"],
        "name": row["name"],
        "path": row["path"],
        "github": row["github"],
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
        "github": _text(entry.get("github"), 300) or None,
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


def list_projects(path: Path | None = None) -> list[dict[str, object]]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY updated_at DESC, name ASC"
        ).fetchall()
        return [_row_to_project(row) for row in rows]


def get_project(project_id: str, path: Path | None = None) -> dict[str, object] | None:
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return _row_to_project(row) if row is not None else None


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
                _text(detail, DETAIL_LIMIT),
                _text(evidence, EVIDENCE_LIMIT),
                _now(),
            ),
        )
        event_id = int(cursor.lastrowid or 0)
        if event_id and event_id % PRUNE_EVERY == 0:
            _prune(conn, EVENT_KEEP)
        return event_id


def recent_events(limit: int = 15, path: Path | None = None) -> list[dict[str, object]]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (max(int(limit), 0),)
        ).fetchall()
        return [
            {
                "id": row["id"],
                "project_id": row["project_id"],
                "project_name": row["project_name"],
                "kind": row["kind"],
                "detail": row["detail"],
                "evidence": row["evidence"],
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
    stamp = _text(created_at, 40) or _now()
    with connect(path) as conn:
        existing = conn.execute(
            "SELECT * FROM provisions WHERE install_path = ? OR "
            "(source_url = ? AND source_url <> '') ORDER BY id LIMIT 1",
            (target, _text(source_url, 400)),
        ).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO provisions "
                "(source_url, install_path, pala_version, status, registered, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    _text(source_url, 400),
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
                    _text(source_url, 400) or existing["source_url"],
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
        "source_url": row["source_url"],
        "install_path": row["install_path"],
        "pala_version": row["pala_version"],
        "status": row["status"],
        "registered": bool(row["registered"]),
        "created_at": row["created_at"],
    }


def recent_provisions(limit: int = 10, path: Path | None = None) -> list[dict[str, object]]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM provisions ORDER BY created_at DESC, id DESC LIMIT ?",
            (max(int(limit), 0),),
        ).fetchall()
        return [_row_to_provision(row) for row in rows]


def _read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


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
        backup = catalog_file.with_name(catalog_file.name + ".bak")
        if not backup.exists():
            try:
                backup.write_bytes(catalog_file.read_bytes())
            except OSError:
                pass
        projects = _read_json(catalog_file).get("projects")
        for entry in projects if isinstance(projects, list) else []:
            if not isinstance(entry, dict) or not entry.get("id"):
                continue
            upsert_project(entry, path=db)
            imported_projects += 1
        with connect(db) as conn:
            _meta_set(conn, CATALOG_MARKER, _now())
        catalog_done = True

    if registry_file is not None and registry_file.is_file() and not registry_done:
        installs = _read_json(registry_file).get("installs")
        for entry in installs if isinstance(installs, list) else []:
            if not isinstance(entry, dict):
                continue
            target = entry.get("installed_path") or entry.get("install_path")
            if not target:
                continue
            upsert_provision(
                source_url=str(entry.get("source_url") or ""),
                install_path=str(target),
                status=str(entry.get("last_status") or entry.get("status") or ""),
                pala_version=str(entry.get("pala_version") or ""),
                created_at=str(
                    entry.get("installed_at") or entry.get("created_at") or ""
                ),
                path=db,
            )
            imported_provisions += 1
        with connect(db) as conn:
            _meta_set(conn, REGISTRY_MARKER, _now())
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

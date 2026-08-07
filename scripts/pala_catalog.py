#!/usr/bin/env python3
"""Secrets-free cross-project catalog backed by the local SQLite store."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pala_db

SCHEMA_VERSION = 1
CATALOG_NAME = "pala-catalog.json"
INDEX_NAME = "INDEX.md"


def default_catalog_root() -> Path:
    """Desktop/Codex under the current user home; portable across machines."""
    return pala_db.default_catalog_root()


def catalog_root() -> Path:
    return pala_db.catalog_root()


def catalog_path(root: Path | None = None) -> Path:
    return (root or catalog_root()) / CATALOG_NAME


def index_path(root: Path | None = None) -> Path:
    return (root or catalog_root()) / INDEX_NAME


def db_path(root: Path | None = None) -> Path:
    return pala_db.db_path_for(root)


def _ensure_migrated(cdir: Path) -> None:
    """Lazy one-shot import of pre-0.7 JSON into the SQLite store."""
    try:
        pala_db.migrate_from_json(
            catalog_path=catalog_path(cdir),
            registry_path=pala_db.legacy_registry_path(),
            path=db_path(cdir),
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass


def _project_id(project_path: Path) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", str(project_path.resolve())).strip("-")[:160]


def _detect_github(root: Path) -> str | None:
    git_config = root / ".git" / "config"
    if not git_config.is_file():
        return None
    try:
        text = git_config.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    match = re.search(r"url\s*=\s*(.+)", text)
    if not match:
        return None
    url = match.group(1).strip()
    if "github.com" not in url.casefold():
        return None
    return url[:300]


def _tech_tags(root: Path) -> list[str]:
    tags: list[str] = []
    markers = {
        "python": ["pyproject.toml", "requirements.txt", "setup.py"],
        "node": ["package.json"],
        "php": ["composer.json"],
        "rust": ["Cargo.toml"],
        "go": ["go.mod"],
        "codex-plugin": [".codex-plugin/plugin.json"],
    }
    for tag, files in markers.items():
        if any((root / name).exists() for name in files):
            tags.append(tag)
    return tags


def entry_from_project(
    root: Path,
    *,
    phase: str | None = None,
    quality_result: str | None = None,
    tools_summary: str | None = None,
    next_action: str | None = None,
    blockers: list[str] | None = None,
) -> dict[str, object]:
    name = root.name
    return {
        "id": _project_id(root),
        "name": name,
        "path": str(root.resolve()),
        "github": _detect_github(root),
        "tech": _tech_tags(root),
        "phase": (phase or "")[:120],
        "quality_result": (quality_result or "")[:120],
        "tools_summary": (tools_summary or "")[:160],
        "next_action": (next_action or "")[:300],
        "blockers": [str(b)[:160] for b in (blockers or [])][:8],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _write_index(cdir: Path, projects: list[object]) -> None:
    lines = [
        "# Pala project catalog",
        "",
        "| Project | Phase | Next | Quality | Path |",
        "| --- | --- | --- | --- | --- |",
    ]
    for raw in projects:
        if not isinstance(raw, dict):
            continue
        lines.append(
            "| {name} | {phase} | {next_action} | {quality_result} | `{path}` |".format(
                name=str(raw.get("name", ""))[:80],
                phase=str(raw.get("phase", ""))[:40],
                next_action=str(raw.get("next_action", ""))[:60].replace("|", "/"),
                quality_result=str(raw.get("quality_result", ""))[:40],
                path=str(raw.get("path", ""))[:120],
            )
        )
    lines.append("")
    index_path(cdir).parent.mkdir(parents=True, exist_ok=True)
    index_path(cdir).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def export_json_and_index(catalog_dir: Path | None = None) -> dict[str, object]:
    """Rebuild human-readable JSON + INDEX.md from the SQLite store."""
    cdir = catalog_dir or catalog_root()
    _ensure_migrated(cdir)
    projects = pala_db.list_projects(db_path(cdir))
    payload = {"schema_version": SCHEMA_VERSION, "projects": projects}
    target = catalog_path(cdir)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    _write_index(cdir, projects)
    return payload


def upsert_project(
    root: Path,
    *,
    catalog_dir: Path | None = None,
    phase: str | None = None,
    quality_result: str | None = None,
    tools_summary: str | None = None,
    next_action: str | None = None,
    blockers: list[str] | None = None,
) -> dict[str, object]:
    cdir = catalog_dir or catalog_root()
    _ensure_migrated(cdir)
    entry = entry_from_project(
        root,
        phase=phase,
        quality_result=quality_result,
        tools_summary=tools_summary,
        next_action=next_action,
        blockers=blockers,
    )
    stored = pala_db.upsert_project(entry, path=db_path(cdir))
    export_json_and_index(cdir)
    return stored


def list_projects(catalog_dir: Path | None = None) -> list[dict[str, object]]:
    cdir = catalog_dir or catalog_root()
    _ensure_migrated(cdir)
    return pala_db.list_projects(db_path(cdir))


def plain_summary(catalog_dir: Path | None = None) -> str:
    """Human-readable Turkish overview across all catalogued projects."""
    cdir = catalog_dir or catalog_root()
    projects = list_projects(cdir)
    lines = [
        "Pala proje kataloğu",
        "===================",
        f"Konum: {catalog_path(cdir)}",
        f"Veritabanı: {db_path(cdir)}",
        f"Proje sayısı: {len(projects)}",
        "",
    ]
    if not projects:
        lines.append("Henüz kayıtlı proje yok. Bir projede 'register' çalıştır.")
        return "\n".join(lines) + "\n"
    ordered = sorted(
        projects,
        key=lambda item: str(item.get("updated_at", "")),
        reverse=True,
    )
    for item in ordered:
        name = str(item.get("name", "?"))
        phase = str(item.get("phase", "") or "belirsiz")
        nxt = str(item.get("next_action", "") or "yok")
        quality = str(item.get("quality_result", "") or "yok")
        tech = ", ".join(item.get("tech", []) if isinstance(item.get("tech"), list) else [])
        blockers = item.get("blockers")
        blocker_count = len(blockers) if isinstance(blockers, list) else 0
        lines.append(f"- {name}")
        lines.append(f"    Faz: {phase} · Kalite: {quality} · Teknoloji: {tech or '?'}")
        lines.append(f"    Sonraki iş: {nxt}")
        if blocker_count:
            lines.append(f"    Blokaj: {blocker_count} adet")
        lines.append(f"    Yol: {item.get('path', '')}")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "sync", "show", "summary", "export"))
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--catalog-root", default="")
    args = parser.parse_args()
    cdir = Path(args.catalog_root) if args.catalog_root else catalog_root()
    root = Path(args.cwd).resolve()
    if args.command == "list":
        print(json.dumps(list_projects(cdir), ensure_ascii=False, indent=2))
        return 0
    if args.command == "summary":
        print(plain_summary(cdir), end="")
        return 0
    if args.command == "export":
        payload = export_json_and_index(cdir)
        print(json.dumps({"exported": len(payload.get("projects", [])), "path": str(catalog_path(cdir))}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "sync":
        entry = upsert_project(root, catalog_dir=cdir)
        print(json.dumps(entry, ensure_ascii=False, indent=2))
        return 0
    # show
    pid = _project_id(root)
    for item in list_projects(cdir):
        if item.get("id") == pid:
            print(json.dumps(item, ensure_ascii=False, indent=2))
            return 0
    print("{}", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

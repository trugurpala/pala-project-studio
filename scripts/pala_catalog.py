#!/usr/bin/env python3
"""Secrets-free cross-project catalog under Desktop/Codex."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
DEFAULT_CATALOG_ROOT = Path(r"C:\Users\Pala-Pc\Desktop\Codex")
CATALOG_NAME = "pala-catalog.json"
INDEX_NAME = "INDEX.md"


def catalog_root() -> Path:
    override = os.environ.get("PALA_CATALOG_ROOT")
    if override:
        return Path(override)
    return DEFAULT_CATALOG_ROOT


def catalog_path(root: Path | None = None) -> Path:
    return (root or catalog_root()) / CATALOG_NAME


def index_path(root: Path | None = None) -> Path:
    return (root or catalog_root()) / INDEX_NAME


def _load(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "projects": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": SCHEMA_VERSION, "projects": []}
    if not isinstance(payload, dict):
        return {"schema_version": SCHEMA_VERSION, "projects": []}
    projects = payload.get("projects")
    if not isinstance(projects, list):
        projects = []
    return {"schema_version": SCHEMA_VERSION, "projects": projects}


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


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
    path = catalog_path(cdir)
    payload = _load(path)
    projects = list(payload.get("projects", []))
    entry = entry_from_project(
        root,
        phase=phase,
        quality_result=quality_result,
        tools_summary=tools_summary,
        next_action=next_action,
        blockers=blockers,
    )
    replaced = False
    for idx, existing in enumerate(projects):
        if isinstance(existing, dict) and existing.get("id") == entry["id"]:
            merged = dict(existing)
            merged.update({k: v for k, v in entry.items() if v not in (None, "", [])})
            merged["updated_at"] = entry["updated_at"]
            projects[idx] = merged
            replaced = True
            break
    if not replaced:
        projects.append(entry)
    payload = {"schema_version": SCHEMA_VERSION, "projects": projects}
    _write(path, payload)
    _write_index(cdir, projects)
    return entry


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
    index_path(cdir).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def list_projects(catalog_dir: Path | None = None) -> list[dict[str, object]]:
    payload = _load(catalog_path(catalog_dir or catalog_root()))
    projects = payload.get("projects", [])
    return [p for p in projects if isinstance(p, dict)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "sync", "show"))
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--catalog-root", default="")
    args = parser.parse_args()
    cdir = Path(args.catalog_root) if args.catalog_root else catalog_root()
    root = Path(args.cwd).resolve()
    if args.command == "list":
        print(json.dumps(list_projects(cdir), ensure_ascii=False, indent=2))
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

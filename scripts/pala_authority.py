"""Repository identity and shared single-host coordination paths."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

GIT_TIMEOUT_SECONDS = 5
RUNTIME_DIRECTORIES = (
    "tasks",
    "leases",
    "quality",
    "events",
    "generated",
    "cache",
    "migration",
    "product",
)


class RuntimeMigrationConflict(RuntimeError):
    """Raised when legacy and runtime authority data disagree."""


def _git(root: Path, *args: str) -> str | None:
    executable = shutil.which("git")
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def git_common_dir(root: Path) -> Path | None:
    value = _git(root, "rev-parse", "--git-common-dir")
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = (Path(root).resolve() / path).resolve()
    return path.resolve() if path.is_dir() else None


def repository_instance(root: Path) -> str:
    common = git_common_dir(root)
    identity = str(common or Path(root).resolve()).casefold()
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def worktree_id(root: Path) -> str:
    return hashlib.sha256(str(Path(root).resolve()).casefold().encode("utf-8")).hexdigest()[:24]


def runtime_repositories_root() -> Path:
    """Return Pala's OS user-state root for repository-scoped runtime data."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Pala" / "runtime" / "repositories"
    xdg_state_home = os.environ.get("XDG_STATE_HOME")
    if xdg_state_home:
        return Path(xdg_state_home) / "pala" / "runtime" / "repositories"
    return Path.home() / ".local" / "state" / "pala" / "runtime" / "repositories"


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json_write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def atomic_json_write(path: Path, payload: object) -> None:
    """Public atomic JSON primitive for canonical records under Pala runtime."""
    _atomic_json_write(path, payload)


def _worktree_roots(root: Path) -> tuple[Path, ...]:
    output = _git(root, "worktree", "list", "--porcelain") or ""
    roots = [
        Path(line[9:]).resolve() for line in output.splitlines() if line.startswith("worktree ")
    ]
    if root.resolve() not in roots:
        roots.append(root.resolve())
    return tuple(dict.fromkeys(roots))


def _legacy_runtime_candidates(root: Path, common: Path, target: Path) -> list[tuple[Path, Path]]:
    repository_id = repository_instance(root)
    candidates: list[tuple[Path, Path]] = []
    worktrees = _worktree_roots(root)
    ticket_roots = tuple(
        worktree / ".codex" / "plugin-data" / "pala" / "v3" / "tickets" for worktree in worktrees
    ) + (common / "pala" / repository_id / "v3" / "tickets",)
    for ticket_root in ticket_roots:
        if ticket_root.is_dir():
            candidates.extend(
                (path, target / "tasks" / path.name) for path in sorted(ticket_root.glob("*.json"))
            )
    for worktree in worktrees:
        quality_root = worktree / ".codex" / "plugin-data" / "pala" / "v3" / "quality"
        if quality_root.is_dir():
            candidates.extend(
                (path, target / "quality" / path.name)
                for path in sorted(quality_root.glob("*.json"))
            )
        workflow = worktree / ".codex" / "pala-workflow.json"
        if workflow.is_file():
            candidates.append((workflow, target / "generated" / "pala-workflow.json"))
    return candidates


def _migrated_task_payload(payload: object) -> object:
    """Fail closed for legacy completion claims that predate structured acceptance."""
    if not isinstance(payload, dict):
        return payload
    lifecycle = str(payload.get("lifecycle") or payload.get("status") or "").casefold()
    acceptance = payload.get("acceptance")
    has_structured_acceptance = isinstance(acceptance, list) and any(
        isinstance(item, dict) for item in acceptance
    )
    if lifecycle not in {"completed", "done"} or has_structured_acceptance:
        return payload
    ticket = str(payload.get("ticket") or payload.get("id") or "legacy-ticket")
    goal = str(payload.get("goal") or "legacy completion requires acceptance review")
    conflict = {
        "type": "legacy-completed-without-structured-acceptance",
        "resolution": "needs_decision",
        "source_completion_preserved": True,
    }
    migrated = dict(payload)
    migrated.update(
        {
            "schema_version": 4,
            "lifecycle": "needs_decision",
            "dirty": False,
            "external_conflict": conflict,
            "task_contract": {
                "schema_version": 4,
                "id": ticket,
                "project_id": "local",
                "title": ticket,
                "goal": goal,
                "acceptance": [],
                "status": "NEEDS_DECISION",
                "external_conflict": conflict,
            },
        }
    )
    return migrated


def _migrate_legacy_runtime(root: Path, common: Path, target: Path) -> None:
    marker = target / "migration" / "runtime-v1.json"
    if marker.is_file():
        payload = _read_json(marker)
        if isinstance(payload, dict) and payload.get("status") == "migrated":
            return
        raise RuntimeMigrationConflict(f"runtime migration requires decision: {marker}")

    selected: dict[Path, tuple[Path, object]] = {}
    conflicts: list[str] = []
    for source, destination in _legacy_runtime_candidates(root, common, target):
        try:
            source_payload = _read_json(source)
        except (OSError, json.JSONDecodeError):
            conflicts.append(str(source))
            continue
        if destination.parent.name == "tasks":
            source_payload = _migrated_task_payload(source_payload)
        prior = selected.get(destination)
        if prior is not None and prior[1] != source_payload:
            conflicts.extend((str(prior[0]), str(source)))
            continue
        if destination.is_file():
            try:
                if _read_json(destination) != source_payload:
                    conflicts.extend((str(source), str(destination)))
            except (OSError, json.JSONDecodeError):
                conflicts.extend((str(source), str(destination)))
            continue
        selected[destination] = (source, source_payload)

    if conflicts:
        _atomic_json_write(
            marker,
            {
                "schema_version": 1,
                "status": "needs_decision",
                "reason": "legacy-runtime-conflict",
                "conflicts": list(dict.fromkeys(conflicts)),
                "observed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        raise RuntimeMigrationConflict(f"runtime migration requires decision: {marker}")

    for destination, (_, payload) in selected.items():
        _atomic_json_write(destination, payload)
    _atomic_json_write(
        marker,
        {
            "schema_version": 1,
            "status": "migrated",
            "copied": len(selected),
            "source_data_preserved": True,
            "migrated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def shared_state_root(root: Path) -> Path | None:
    """Return a repo-global store for real Git worktrees; None for non-Git roots."""
    common = git_common_dir(root)
    if common is None:
        return None
    path = runtime_repositories_root() / repository_instance(root)
    path.mkdir(parents=True, exist_ok=True)
    for name in RUNTIME_DIRECTORIES:
        (path / name).mkdir(exist_ok=True)
    _migrate_legacy_runtime(Path(root).resolve(), common, path)
    return path

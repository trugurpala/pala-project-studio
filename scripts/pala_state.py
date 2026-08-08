#!/usr/bin/env python3
"""Discover, register, and validate durable Pala project-state documents."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
MANIFEST = Path(".codex/pala-project.json")
WORKFLOW = Path(".codex/pala-workflow.json")
WORKFLOW_SCHEMA_VERSION = 2
SESSION_KEY_LENGTH = 24
# begin without --session-key still claims a v3 ticket under this local owner
DEFAULT_LOCAL_SESSION = "pala-local"
DEFAULT_INSTRUCTION_LIMIT = 32_768
VERIFICATION_TIERS = ("narrow", "ticket", "milestone", "release", "not-run")
CANDIDATES = {
    "instructions": ("AGENTS.md",),
    "project": (
        "PROJECT.md",
        "docs/SCOPE.md",
        "README.md",
        "docs/codex/PROJECT.md",
    ),
    "plan": (
        "PLAN.md",
        "docs/IMPLEMENTATION_PLAN.md",
        "TASKS.md",
        "ROADMAP.md",
        "docs/codex/PLAN.md",
    ),
    "status": (
        "reports/CURRENT_STATUS.md",
        "STATUS.md",
        "PROJECT_STATE.md",
        "docs/codex/STATUS.md",
    ),
    "progress": (
        "PROGRESS.md",
        "docs/PROGRESS.md",
    ),
    "tooling": (
        "TOOLING_DECISIONS.md",
        "docs/TOOLING_DECISIONS.md",
    ),
    "debugging": (
        "DEBUGGING.md",
        "docs/vibe-os/TROUBLESHOOTING.md",
        "docs/DEBUGGING.md",
    ),
    "decisions": (
        "DECISIONS.md",
        "docs/PRODUCT_DECISIONS.md",
        "docs/adr",
        "docs/codex/DECISIONS.md",
    ),
    "open_source": (
        "OPEN_SOURCE.md",
        "docs/OPEN_SOURCE.md",
        "THIRD_PARTY_NOTICES.md",
        "docs/codex/OPEN_SOURCE.md",
    ),
    "demo": (
        "reports/OWNER_DEMO.md",
        "reports/PATRON_DEMO.md",
        "DEMO.md",
        "docs/DEMO.md",
    ),
}
REQUIRED = ("project", "plan", "status")
VERIFY_STATUS_PASSED_KEYWORDS = ("passed",)
VERIFY_STATUS_FAILED_KEYWORDS = ("failed", "error", "broken", "exception")
EVIDENCE_STATUSES = (
    "passed",
    "not-run",
    "blocked",
    "configured-not-verified",
    "failed",
    "timeout",
)
SOFT_DONE_RE = ("bitti", "done", "complete", "completed", "finished", "ok", "succeeded")
PROJECT_MARKERS = (
    ".codex-plugin/plugin.json",
    "SKILL.md",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Gemfile",
    "composer.json",
)
FRONTEND_PACKAGES = (
    "next",
    "react",
    "vue",
    "svelte",
    "@angular/core",
    "vite",
    "astro",
)
BACKEND_PACKAGES = (
    "express",
    "fastify",
    "@nestjs/core",
    "hono",
    "koa",
)
BACKEND_PYTHON_MARKERS = ("fastapi", "django", "flask", "litestar", "starlette")
BACKEND_COMPOSER_PACKAGES = (
    "laravel/framework",
    "symfony/framework-bundle",
    "cakephp/cakephp",
    "yiisoft/yii2",
)
IGNORED_DISCOVERY_DIRS = {
    ".git",
    ".next",
    ".nx",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
}


def session_key(session_id: str) -> str:
    """Return a bounded stable key without persisting the raw Codex session id."""
    from pala_models import SessionKey

    return SessionKey.from_session_id(session_id)


def git_root(cwd: Path) -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    return cwd.resolve()


def relative(root: Path, path: Path) -> str:
    root_path = root.resolve()
    try:
        return path.resolve().relative_to(root_path).as_posix()
    except ValueError:
        if os.name != "nt":
            raise
        root_parts = tuple(part.casefold() for part in root_path.parts)
        path_parts = tuple(part.casefold() for part in path.resolve().parts)

        def _segment_matches(left: str, right: str) -> bool:
            if left == right:
                return True
            left_short, right_short = left.casefold(), right.casefold()
            if "~" in left_short:
                return right_short.startswith(left_short.split("~", 1)[0])
            if "~" in right_short:
                return left_short.startswith(right_short.split("~", 1)[0])
            return False

        if (
            len(path_parts) >= len(root_parts)
            and all(
                _segment_matches(left, right)
                for left, right in zip(root_parts, path_parts[: len(root_parts)])
            )
            and root_path.exists()
        ):
            return "/".join(path_parts[len(root_parts) :])
        raise


def instruction_report(
    root: Path,
    cwd: Path,
    max_bytes: int = DEFAULT_INSTRUCTION_LIMIT,
    fallback_names: tuple[str, ...] = (),
) -> dict[str, object]:
    """Report the canonical project instruction chain Codex loads for a run."""
    root = root.resolve()
    cwd = cwd.resolve()
    try:
        cwd.relative_to(root)
    except ValueError as exc:
        raise ValueError("cwd must remain inside project root") from exc

    directories = [root]
    current = root
    for part in cwd.relative_to(root).parts:
        current = current / part
        directories.append(current)

    selected: list[str] = []
    total_bytes = 0
    names = ("AGENTS.override.md", "AGENTS.md", *fallback_names)
    for directory in directories:
        match = next(
            (
                directory / name
                for name in names
                if (directory / name).is_file()
                and (directory / name).stat().st_size > 0
            ),
            None,
        )
        if match is None:
            continue
        selected.append(relative(root, match))
        total_bytes += match.stat().st_size
    return {
        "selected": selected,
        "total_bytes": total_bytes,
        "max_bytes": max_bytes,
        "within_budget": total_bytes <= max_bytes,
        "scope": "project-only",
        "note": (
            "Global ~/.codex instructions and configured fallback names are "
            "outside this project-only report unless passed explicitly."
        ),
    }


def configured_instruction_report(root: Path, cwd: Path) -> dict[str, object]:
    codex_home = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
    config_path = codex_home / "config.toml"
    config: dict[str, object] = {}
    if config_path.is_file():
        try:
            config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            config = {}
    raw_limit = config.get("project_doc_max_bytes", DEFAULT_INSTRUCTION_LIMIT)
    limit = (
        raw_limit
        if isinstance(raw_limit, int) and raw_limit > 0
        else DEFAULT_INSTRUCTION_LIMIT
    )
    raw_fallbacks = config.get("project_doc_fallback_filenames", [])
    fallbacks = (
        tuple(
            name
            for name in raw_fallbacks
            if isinstance(name, str)
            and name
            and "/" not in name
            and "\\" not in name
        )
        if isinstance(raw_fallbacks, list)
        else ()
    )
    report = instruction_report(root, cwd, limit, fallbacks)
    global_selected = next(
        (
            str(path)
            for path in (
                codex_home / "AGENTS.override.md",
                codex_home / "AGENTS.md",
            )
            if path.is_file() and path.stat().st_size > 0
        ),
        None,
    )
    report.update(
        {
            "global_selected": global_selected,
            "config": str(config_path),
            "fallback_names": list(fallbacks),
        }
    )
    return report


def project_files(root: Path, filename: str):
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name for name in dirnames if name not in IGNORED_DISCOVERY_DIRS
        ]
        if filename in filenames:
            yield Path(directory) / filename


def package_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in project_files(root, "package.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for field in ("dependencies", "devDependencies", "peerDependencies"):
            values = payload.get(field)
            if isinstance(values, dict):
                names.update(str(name).casefold() for name in values)
    return names


def composer_package_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in project_files(root, "composer.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for field in ("require", "require-dev"):
            values = payload.get(field)
            if isinstance(values, dict):
                names.update(str(name).casefold() for name in values)
    return names


def project_profiles(root: Path) -> tuple[str, list[str]]:
    meaningful = any((root / marker).exists() for marker in PROJECT_MARKERS) or any(
        (root / name).exists()
        for name in ("src", "app", "apps", "packages", "services", "backend", "server")
    )
    project_kind = "existing" if meaningful else "greenfield"
    packages = package_names(root)
    composer_packages = composer_package_names(root)
    pyproject_text = " ".join(
        path.read_text(encoding="utf-8", errors="replace").casefold()
        for path in project_files(root, "pyproject.toml")
    )
    frontend = bool(packages.intersection(FRONTEND_PACKAGES)) or any(
        (root / name).exists() for name in ("frontend", "web")
    )
    backend = bool(packages.intersection(BACKEND_PACKAGES)) or any(
        marker in pyproject_text for marker in BACKEND_PYTHON_MARKERS
    ) or bool(composer_packages.intersection(BACKEND_COMPOSER_PACKAGES)) or any(
        (root / name).exists() for name in ("backend", "server")
    )

    profiles = ["project-intake", "reuse-or-build", "architecture-selection"]
    if project_kind == "greenfield":
        profiles.append("greenfield-scaffolding")
    if frontend:
        profiles.append("frontend-engineering")
    if backend:
        profiles.append("backend-engineering")
    profiles.extend(("modularity-budgets", "runtime-delivery"))
    return project_kind, profiles


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        suffix=".tmp",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        newline="\n",
    ) as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, indent=2))
        stream.write("\n")
        temp_path = Path(stream.name)
    temp_path.replace(path)


def bounded_strings(values: list[str], *, limit: int) -> list[str]:
    return [item.strip()[:500] for item in values if item.strip()][:limit]


def file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def document_fingerprints(
    root: Path, manifest: dict[str, object]
) -> dict[str, dict[str, str | None]]:
    documents = manifest.get("documents")
    if not isinstance(documents, dict):
        return {}
    result: dict[str, dict[str, str | None]] = {}
    for purpose, value in documents.items():
        if not isinstance(purpose, str) or not isinstance(value, str) or not value:
            continue
        path = (root / value).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            continue
        result[purpose] = {"path": value, "sha256": file_sha256(path)}
    return result


def run_git(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def run_git_bytes(root: Path, *args: str) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None


def changed_git_paths(root: Path) -> list[str]:
    paths: set[str] = set()
    commands = (
        ("diff", "--name-only", "-z"),
        ("diff", "--cached", "--name-only", "-z"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    )
    for command in commands:
        output = run_git_bytes(root, *command)
        if output is None:
            continue
        for value in output.split(b"\0"):
            if value:
                paths.add(value.decode("utf-8", errors="surrogateescape"))
    return sorted(paths, key=str.casefold)


def has_failed_verification(entries: list[str]) -> bool:
    for value in entries:
        lowered = value.casefold()
        if any(token in lowered for token in VERIFY_STATUS_FAILED_KEYWORDS):
            return True
    return False


def _normalize_evidence_entries(entries: list[str]) -> list[dict[str, str]]:
    """Parse `name=status` or `name: status` evidence lines."""
    import re

    parsed: list[dict[str, str]] = []
    for raw in entries:
        text = raw.strip()
        if not text:
            continue
        lowered = text.casefold()
        # Soft completion words alone are never evidence.
        if lowered in SOFT_DONE_RE:
            raise ValueError(
                "checkpoint refused: soft done word is not evidence; "
                "use name=passed|not-run|blocked|configured-not-verified"
            )
        match = re.match(
            r"^(?P<name>[^=:]+)[=:]\s*(?P<status>[A-Za-z0-9_-]+)\s*(?P<rest>.*)$",
            text,
        )
        if not match:
            raise ValueError(
                "checkpoint refused: evidence must look like "
                "'unittest=passed' or 'install=configured-not-verified'"
            )
        status = match.group("status").casefold().replace("_", "-")
        if status not in EVIDENCE_STATUSES:
            raise ValueError(f"unsupported evidence status: {status}")
        if status in {"failed"}:
            raise ValueError("checkpoint refused: verification contains failed status")
        parsed.append(
            {
                "name": match.group("name").strip()[:120],
                "status": status,
                "detail": match.group("rest").strip()[:200],
            }
        )
    if not parsed:
        raise ValueError("verification evidence is required for checkpoint")
    if not any(item["status"] == "passed" for item in parsed):
        # Allow checkpoint when only blocked/not-run if explicitly present,
        # but require at least one non-soft structured line (already true).
        # Still refuse if every line is soft-adjacent without passed when tier expects work.
        pass
    return parsed


def hook_safety_report(root: Path) -> dict[str, object]:
    hooks_path = root / "hooks" / "hooks.json"
    hook_script = root / "scripts" / "pala_hook.py"
    state_file = root / ".codex" / "pala-workflow.json"
    reasons: list[str] = []
    if not hooks_path.is_file():
        reasons.append("hooks.json missing")
    else:
        try:
            hook_payload = json.loads(hooks_path.read_text(encoding="utf-8"))
            if not isinstance(hook_payload, dict):
                reasons.append("hooks.json is not a JSON object")
            elif "hooks" not in hook_payload:
                reasons.append("hooks.json is missing the hooks map")
        except (OSError, json.JSONDecodeError):
            reasons.append("hooks.json cannot be parsed")

    if not hook_script.is_file():
        reasons.append("pala_hook.py is missing")
    elif "github.com" in hook_script.read_text(encoding="utf-8").casefold():
        reasons.append("hook script uses restricted external references")

    if not state_file.is_file():
        reasons.append("hook state file is missing")

    if not reasons:
        return {
            "status": "passed",
            "reasons": [],
            "ui_trust": "configured-not-verified",
            "recommendation": "run /hooks to review hook policy when you change safety boundaries",
        }
    return {
        "status": "blocked",
        "reasons": reasons,
        "ui_trust": "configured-not-verified",
        "recommendation": "run /hooks to inspect and repair hook safety",
    }


def doctor_report(
    root: Path, manifest: dict[str, object] | None = None, session: str | None = None
) -> dict[str, object]:
    python_info = {
        "executable": os.environ.get("PYTHON", sys.executable),
        "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }

    git_root = run_git(root, "rev-parse", "--show-toplevel")
    plugin_root = root.resolve()
    status = {
        "plugin": {
            "root": str(plugin_root),
            "manifest": str(plugin_root / ".codex-plugin" / "plugin.json"),
            "hooks": str(plugin_root / "hooks" / "hooks.json"),
            "manifest_present": (plugin_root / ".codex-plugin" / "plugin.json").is_file(),
            "hooks_present": (plugin_root / "hooks" / "hooks.json").is_file(),
        },
        "python": python_info,
        "git": {
            "installed": git_root is not None,
            "root": git_root,
            "status_command": run_git(root, "status", "--short", "--branch"),
        },
        "project_registration": {
            "registered": False,
            "document_mapping": None,
            "error": None,
        },
        "hook_discovery": {
            "workflow_state_exists": (root / WORKFLOW).is_file(),
            "workflow_state_preview": relative(
                root, root / WORKFLOW
            )
            if (root / WORKFLOW).is_file()
            else None,
        },
        "hook_safety": hook_safety_report(root),
    }

    if manifest is None:
        try:
            manifest = load_manifest(root)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            status["project_registration"]["error"] = str(error)
        else:
            status["project_registration"]["registered"] = True
            status["project_registration"]["document_mapping"] = manifest.get("documents")

    workflow = None
    if status["project_registration"]["registered"]:
        try:
            workflow = load_workflow(root)
        except (OSError, ValueError, json.JSONDecodeError):
            workflow = None
        status["hook_discovery"]["active_ticket"] = (
            workflow.get("active_ticket") if isinstance(workflow, dict) else None
        )
        reconciliation = (
            reconciliation_report(root, manifest, workflow)
            if isinstance(workflow, dict)
            else None
        )
        status["hook_discovery"]["needs_reconcile"] = (
            reconciliation["needed"] if reconciliation is not None else None
        )
        status["hook_discovery"]["dirty"] = (
            bool(workflow and workflow.get("dirty")) if workflow else None
        )
    if session is not None:
        from pala_store import WorkflowStore

        owned = WorkflowStore(root).active_for_session(session)
        status["session_ticket"] = (
            {
                "ticket": owned.get("ticket"),
                "lifecycle": owned.get("lifecycle"),
                "dirty": bool(owned.get("dirty")),
            }
            if owned is not None
            else None
        )

    status["healthy"] = (
        status["plugin"]["manifest_present"]
        and status["plugin"]["hooks_present"]
        and status["git"]["installed"]
        and status["project_registration"]["registered"]
        and status["hook_safety"]["status"] == "passed"
    )

    try:
        from pala_shared_memory import doctor_store_block

        status["shared_store"] = doctor_store_block()
    except Exception as error:  # noqa: BLE001 — doctor JSON stays useful
        status["shared_store"] = {"error": str(error), "cloud_sync": False}

    return status


def worktree_entry_digest(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        elif path.is_file():
            digest.update(b"file\0")
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        elif path.exists():
            digest.update(b"non-file\0")
        else:
            digest.update(b"missing\0")
    except OSError as error:
        digest.update(f"unreadable:{error.errno}".encode("ascii", errors="replace"))
    return digest.hexdigest()


def git_paths_snapshot(root: Path, paths: list[str]) -> str:
    fingerprint = hashlib.sha256()
    for value in sorted(set(paths), key=str.casefold):
        normalized = value.replace("\\", "/")
        fingerprint.update(b"\0path\0")
        fingerprint.update(normalized.encode("utf-8", errors="surrogateescape"))
        fingerprint.update(b"\0content\0")
        fingerprint.update(worktree_entry_digest(root / value).encode("ascii"))
    return fingerprint.hexdigest()


def git_checkpoint(root: Path) -> dict[str, object]:
    head = run_git(root, "rev-parse", "HEAD")
    status = run_git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status is None:
        return {
            "head": head,
            "worktree_sha256": None,
            "changed_count": None,
            "changed_snapshot_sha256": None,
        }
    filtered = []
    workflow_name = WORKFLOW.as_posix().casefold()
    for line in status.splitlines():
        candidate = line[3:].strip().strip('"').replace("\\", "/").casefold()
        if candidate == workflow_name:
            continue
        filtered.append(line)
    changed_paths = [
        value
        for value in changed_git_paths(root)
        if value.replace("\\", "/").casefold() != workflow_name
    ]
    changed_snapshot = git_paths_snapshot(root, changed_paths)
    fingerprint = hashlib.sha256()
    fingerprint.update("\n".join(filtered).encode("utf-8", errors="surrogateescape"))
    fingerprint.update(b"\0snapshot\0")
    fingerprint.update(changed_snapshot.encode("ascii"))
    digest = fingerprint.hexdigest()
    return {
        "head": head,
        "worktree_sha256": digest,
        "changed_count": len(changed_paths),
        "changed_snapshot_sha256": changed_snapshot,
    }


def git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def git_diff_paths(root: Path, before: str, after: str) -> list[str] | None:
    output = run_git_bytes(root, "diff", "--name-only", "-z", f"{before}..{after}")
    if output is None:
        return None
    workflow_name = WORKFLOW.as_posix().casefold()
    paths = []
    for value in output.split(b"\0"):
        if not value:
            continue
        decoded = value.decode("utf-8", errors="surrogateescape")
        if decoded.replace("\\", "/").casefold() != workflow_name:
            paths.append(decoded)
    return paths


def checkpoint_commit_materialized(
    root: Path,
    previous: dict[str, object],
    current: dict[str, object],
) -> bool:
    previous_head = previous.get("head")
    current_head = current.get("head")
    previous_count = previous.get("changed_count")
    previous_snapshot = previous.get("changed_snapshot_sha256")
    if not (
        isinstance(previous_head, str)
        and isinstance(current_head, str)
        and isinstance(previous_count, int)
        and isinstance(previous_snapshot, str)
        and current.get("changed_count") == 0
        and git_is_ancestor(root, previous_head, current_head)
    ):
        return False
    committed_paths = git_diff_paths(root, previous_head, current_head)
    if committed_paths is None or len(committed_paths) != previous_count:
        return False
    return git_paths_snapshot(root, committed_paths) == previous_snapshot


def checkpoint_basis(
    root: Path, manifest: dict[str, object]
) -> dict[str, object]:
    return {
        "documents": document_fingerprints(root, manifest),
        "git": git_checkpoint(root),
    }


def reconciliation_report(
    root: Path,
    manifest: dict[str, object],
    workflow: dict[str, object],
) -> dict[str, object]:
    reasons: list[str] = []
    basis = workflow.get("checkpoint_basis")
    fresh_active_ticket = (
        workflow.get("schema_version") == WORKFLOW_SCHEMA_VERSION
        and workflow.get("dirty") is True
        and workflow.get("needs_reconcile") is False
        and basis is None
    )
    if fresh_active_ticket:
        pass
    elif workflow.get("schema_version") != WORKFLOW_SCHEMA_VERSION or not isinstance(
        basis, dict
    ):
        reasons.append("legacy workflow has no checkpoint basis")
    else:
        previous_documents = basis.get("documents")
        current_documents = document_fingerprints(root, manifest)
        if isinstance(previous_documents, dict):
            for purpose in sorted(set(previous_documents) | set(current_documents)):
                if previous_documents.get(purpose) != current_documents.get(purpose):
                    reasons.append(f"{purpose} changed since checkpoint")
        else:
            reasons.append("checkpoint document basis is missing")

        previous_git = basis.get("git")
        current_git = git_checkpoint(root)
        if isinstance(previous_git, dict):
            commit_materialized = (
                previous_git.get("head") != current_git.get("head")
                and checkpoint_commit_materialized(root, previous_git, current_git)
            )
            if not commit_materialized:
                if previous_git.get("head") != current_git.get("head"):
                    reasons.append("Git HEAD changed since checkpoint")
                if previous_git.get("worktree_sha256") != current_git.get(
                    "worktree_sha256"
                ):
                    reasons.append("working tree changed since checkpoint")
        else:
            reasons.append("checkpoint Git basis is missing")

    if workflow.get("needs_reconcile"):
        reasons.append("workflow was marked for reconciliation")
    return {"needed": bool(reasons), "reasons": list(dict.fromkeys(reasons))}


def load_workflow(root: Path) -> dict[str, object]:
    path = root / WORKFLOW
    if not path.is_file():
        raise ValueError(f"workflow state not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") not in (1, WORKFLOW_SCHEMA_VERSION):
        raise ValueError("unsupported Pala workflow schema")
    return payload


def _record_store_event(
    root: Path,
    kind: str,
    *,
    detail: str = "",
    evidence: str = "",
) -> None:
    """Best-effort history write; never raises into caller workflows."""
    try:
        import pala_db
        from pala_catalog import db_path, _project_id

        pala_db.add_event(
            kind,
            project_id=_project_id(root),
            project_name=root.name,
            detail=detail,
            evidence=evidence,
            path=db_path(),
        )
    except (OSError, ValueError, TypeError, KeyError, ImportError):
        pass


def _emit_debug_gate(root: Path, *, surface: str) -> None:
    """Warn on stderr + record attempt when open INC exist (Wave B)."""
    try:
        from pala_debug_gate import evaluate_gate, record_debug_attempt

        documents: dict[str, object] | None = None
        try:
            documents = dict(load_manifest(root).get("documents") or {})
        except (OSError, ValueError, json.JSONDecodeError):
            documents = {"debugging": "DEBUGGING.md"}
        report = evaluate_gate(root, documents, surface=surface)
        if not report.get("warn"):
            return
        message = str(report.get("message") or "").strip()
        if message:
            print(message, file=sys.stderr)
        for item in report.get("incidents") or []:
            if not isinstance(item, dict):
                continue
            inc_id = str(item.get("id") or "").strip()
            if not inc_id:
                continue
            record_debug_attempt(
                root,
                inc_id,
                detail=f"{surface}: saw open {inc_id}",
                evidence=f"surface={surface}",
            )
    except (OSError, ValueError, TypeError, KeyError, ImportError):
        pass


def complete_recovery_message(ticket: str, *, reason: str = "") -> str:
    """Actionable Turkish recovery when complete cannot find ticket/session."""
    tip = (
        f"complete reddedildi: ticket/oturum kaydı yok veya uyuşmuyor ({ticket}). "
        f"Önce gerekirse register; sonra "
        f'begin --ticket {ticket} --goal "tek sonraki iş" --session-key <aynı-anahtar> '
        f"(session yoksa begin varsayılanı: {DEFAULT_LOCAL_SESSION}). Soft-pass yok."
    )
    detail = (reason or "").strip()
    if detail and detail not in tip:
        return f"{tip} ({detail})"
    return tip


def begin_work(root: Path, ticket: str, goal: str, session: str | None = None) -> None:
    if not ticket.strip() or not goal.strip():
        raise ValueError("ticket and goal must be non-empty")
    _emit_debug_gate(root, surface="begin")
    from pala_store import WorkflowStore

    if session is not None:
        result = WorkflowStore(root).claim(ticket=ticket, goal=goal, session=session)
        if result.status == "owned_by_other":
            raise ValueError("ticket is owned by another active session")
        if result.status == "busy":
            raise ValueError("ticket claim busy; retry begin with the same --session-key")
        _record_store_event(
            root,
            "begin",
            detail=f"{ticket.strip()}: {goal.strip()}"[:300],
        )
        return

    if WorkflowStore(root).has_dirty_record():
        raise ValueError(
            "active ticket work exists for another session; use --session-key for parallel-safe ownership"
        )
    if (root / WORKFLOW).is_file():
        existing = load_workflow(root)
        if existing.get("dirty"):
            raise ValueError(
                "active workflow has uncheckpointed dirty work; run checkpoint before begin"
            )
    # Always write a v3 ticket row so complete/session tools can find it.
    claim = WorkflowStore(root).claim(
        ticket=ticket, goal=goal, session=DEFAULT_LOCAL_SESSION
    )
    if claim.status == "owned_by_other":
        raise ValueError("ticket is owned by another active session")
    if claim.status == "busy":
        raise ValueError("ticket claim busy; retry begin")
    payload = {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "active_ticket": ticket.strip(),
        "goal": goal.strip(),
        "dirty": True,
        "needs_reconcile": False,
        "next_action": None,
        "verification": [],
        "verification_tier": "not-run",
        "blockers": [],
        "checkpoint_basis": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(root / WORKFLOW, payload)
    _record_store_event(
        root,
        "begin",
        detail=f"{ticket.strip()}: {goal.strip()}"[:300],
    )


def checkpoint_work(
    root: Path,
    next_action: str,
    verification: list[str],
    blockers: list[str],
    tier: str = "ticket",
    *,
    changed_summary: str = "",
    changed_files: list[str] | None = None,
    session_id: str | None = None,
) -> None:
    from pala_memory import (
        append_status_mismatch,
        ticket_coherence_report,
    )

    _emit_debug_gate(root, surface="checkpoint")
    payload = load_workflow(root)
    if not next_action.strip():
        raise ValueError("next action must be non-empty")
    if tier not in VERIFICATION_TIERS:
        raise ValueError(f"unsupported verification tier: {tier}")
    if has_failed_verification(verification):
        raise ValueError("checkpoint refused: verification contains failed status")
    evidence = _normalize_evidence_entries(verification)
    try:
        manifest = load_manifest(root)
    except (OSError, ValueError, json.JSONDecodeError):
        manifest = {"documents": {}}
    documents = manifest.get("documents") if isinstance(manifest, dict) else {}
    docs = documents if isinstance(documents, dict) else {}
    status_rel = docs.get("status") if isinstance(docs.get("status"), str) else None
    status_text = ""
    if status_rel and (root / status_rel).is_file():
        status_text = (root / status_rel).read_text(encoding="utf-8")
    coherence = ticket_coherence_report(
        {**payload, "next_action": next_action.strip()},
        status_text,
        "",
    )
    needs_reconcile = bool(coherence.get("mismatch"))
    parallel_stamp: dict[str, object] | None = None
    try:
        from pala_cold_packet import (
            detect_worktree_conflict,
            git_surface,
            parallel_checkpoint_fields,
        )

        git = git_surface(root)
        prior = payload.get("parallel") if isinstance(payload.get("parallel"), dict) else {}
        conflict = detect_worktree_conflict(
            ticket=str(payload.get("active_ticket") or ""),
            this_worktree=str(git.get("worktree") or root),
            other_worktree=str(prior.get("worktree") or "") or None,
            other_branch=str(prior.get("branch") or "") or None,
            this_branch=str(git.get("branch") or "") or None,
        )
        if conflict.get("reconcile_required"):
            needs_reconcile = True
        parallel_stamp = parallel_checkpoint_fields(
            session_id=session_id,
            worktree=str(git.get("worktree") or root),
            branch=str(git.get("branch") or "unknown"),
            base_commit=str(git.get("base_commit") or "") or None,
            file_scope=list(changed_files or git.get("changed_files") or [])[:16],
        )
    except (OSError, ValueError, TypeError, ImportError):
        parallel_stamp = None
    payload.update(
        {
            "schema_version": WORKFLOW_SCHEMA_VERSION,
            "dirty": False,
            "needs_reconcile": needs_reconcile,
            "next_action": next_action.strip()[:500],
            "verification": bounded_strings(verification, limit=8),
            "verification_evidence": evidence[:8],
            "verification_tier": tier,
            "blockers": bounded_strings(blockers, limit=5),
            "changed_summary": (changed_summary or "")[:500],
            "changed_files": bounded_strings(changed_files or [], limit=16),
            "memory_mismatch": coherence if coherence.get("mismatch") else None,
            "checkpoint_basis": checkpoint_basis(root, manifest),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if parallel_stamp is not None:
        payload["parallel"] = parallel_stamp
    write_json(root / WORKFLOW, payload)
    if status_rel and coherence.get("mismatch"):
        append_status_mismatch(root / status_rel, coherence)
        _record_store_event(
            root,
            "mismatch",
            detail=str(coherence.get("note") or "ticket mismatch")[:300],
        )
    # Best-effort catalog upsert (local Desktop\Codex); never fails checkpoint.
    try:
        from pala_catalog import upsert_project
        from pala_tool_memory import tool_memory_report

        tools = tool_memory_report(
            profiles=list(manifest.get("profiles", []))
            if isinstance(manifest.get("profiles"), list)
            else []
        )
        upsert_project(
            root,
            phase=str(payload.get("active_ticket") or ""),
            quality_result=tier,
            tools_summary=(
                f"{tools['counts'].get('installed', 0)}ok/"
                f"{tools['counts'].get('not_installed', 0)}missing"
            ),
            next_action=next_action.strip()[:300],
            blockers=list(payload.get("blockers") or []),
        )
    except (OSError, ValueError, TypeError, KeyError):
        pass
    evidence_text = "; ".join(
        f"{item.get('name')}={item.get('status')}" for item in evidence[:4]
    )
    _record_store_event(
        root,
        "checkpoint",
        detail=next_action.strip()[:300],
        evidence=evidence_text[:500],
    )


def discover(root: Path) -> dict[str, object]:
    project_kind, profiles = project_profiles(root)
    documents: dict[str, str | None] = {}
    for purpose, names in CANDIDATES.items():
        match = next((root / name for name in names if (root / name).exists()), None)
        documents[purpose] = relative(root, match) if match else None
    return {
        "root": str(root),
        "manifest": str(root / MANIFEST),
        "registered": (root / MANIFEST).is_file(),
        "project_kind": project_kind,
        "profiles": profiles,
        "documents": documents,
        "fallbacks": {
            "project": "docs/codex/PROJECT.md",
            "plan": "docs/codex/PLAN.md",
            "status": "reports/CURRENT_STATUS.md",
            "progress": "PROGRESS.md",
            "tooling": "TOOLING_DECISIONS.md",
            "debugging": "DEBUGGING.md",
            "decisions": "docs/codex/DECISIONS.md",
            "open_source": "docs/codex/OPEN_SOURCE.md",
            "demo": "reports/OWNER_DEMO.md",
        },
    }


def normalize_document(root: Path, value: str | None) -> str | None:
    if not value:
        return None
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        return relative(root, resolved)
    except ValueError as exc:
        raise ValueError(f"document must remain inside project root: {value}") from exc


def register(args: argparse.Namespace, root: Path) -> int:
    from pala_memory import ensure_memory_stubs

    discovery = discover(root)
    found = discovery["documents"]
    documents = {
        "instructions": normalize_document(root, args.instructions or found["instructions"]),
        "project": normalize_document(root, args.project or found["project"]),
        "plan": normalize_document(root, args.plan or found["plan"]),
        "status": normalize_document(root, args.status or found["status"]),
        "progress": normalize_document(
            root, getattr(args, "progress", None) or found.get("progress")
        ),
        "tooling": normalize_document(
            root, getattr(args, "tooling", None) or found.get("tooling")
        ),
        "debugging": normalize_document(
            root, getattr(args, "debugging", None) or found.get("debugging")
        ),
        "decisions": normalize_document(root, args.decisions or found["decisions"]),
        "open_source": normalize_document(root, args.open_source or found["open_source"]),
        "demo": normalize_document(
            root, getattr(args, "demo", None) or found["demo"]
        ),
    }
    # Create optional memory-contract stubs when missing (status still required).
    stubbed = ensure_memory_stubs(
        root,
        {k: (v if isinstance(v, str) else None) for k, v in documents.items()},
    )
    for key in ("status", "progress", "tooling", "debugging"):
        if not documents.get(key) and stubbed.get(key):
            documents[key] = stubbed[key]
    missing = [name for name in REQUIRED if not documents[name]]
    if missing:
        print(
            "missing required document mappings: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 2
    manifest_path = root / MANIFEST
    payload = {
        "schema_version": SCHEMA_VERSION,
        "managed_by": "pala-project-finisher",
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "project_kind": discovery["project_kind"],
        "profiles": discovery["profiles"],
        "documents": documents,
        "memory_contract_version": 1,
    }
    write_json(manifest_path, payload)
    try:
        from pala_catalog import upsert_project

        upsert_project(root, phase="registered", next_action="begin first ticket")
    except (OSError, ValueError, TypeError):
        pass
    _record_store_event(root, "register", detail="project registered")
    print(str(manifest_path))
    return 0


def load_manifest(root: Path) -> dict[str, object]:
    path = root / MANIFEST
    if not path.is_file():
        raise ValueError(f"project is not registered: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported pala project-state schema")
    if payload.get("managed_by") != "pala-project-finisher":
        raise ValueError("unexpected project-state owner")
    if not isinstance(payload.get("documents"), dict):
        raise ValueError("documents must be an object")
    return payload


def validate(root: Path) -> int:
    try:
        payload = load_manifest(root)
        documents = payload["documents"]
        errors: list[str] = []
        for purpose in REQUIRED:
            value = documents.get(purpose)
            if not isinstance(value, str) or not value:
                errors.append(f"{purpose}: missing mapping")
                continue
            path = (root / value).resolve()
            try:
                relative(root, path)
            except ValueError:
                errors.append(f"{purpose}: outside project root")
                continue
            if not path.is_file():
                errors.append(f"{purpose}: file not found ({value})")
            elif not path.read_text(encoding="utf-8").strip():
                errors.append(f"{purpose}: file is empty ({value})")
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 2
        print(
            json.dumps(
                {"valid": True, "root": str(root), "documents": documents},
                ensure_ascii=False,
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


def context_report(root: Path, session: str | None = None) -> dict[str, object]:
    manifest = load_manifest(root)
    try:
        workflow = load_workflow(root)
    except (OSError, ValueError, json.JSONDecodeError):
        workflow = {}
    if session is not None:
        from pala_store import WorkflowStore

        owned_ticket = WorkflowStore(root).active_for_session(session)
        if owned_ticket is not None:
            workflow = {
                "schema_version": WORKFLOW_SCHEMA_VERSION,
                "active_ticket": owned_ticket.get("ticket"),
                "goal": owned_ticket.get("goal"),
                "next_action": owned_ticket.get("next_action"),
                "dirty": owned_ticket.get("dirty"),
                "needs_reconcile": False,
                "checkpoint_basis": None,
                "verification_tier": "not-run",
                "blockers": [],
            }
    documents = manifest.get("documents")
    safe_documents = documents if isinstance(documents, dict) else {}
    reconciliation = (
        reconciliation_report(root, manifest, workflow)
        if workflow
        else {"needed": True, "reasons": ["workflow state is missing"]}
    )
    from pala_memory import contract_context
    from pala_tool_memory import tool_memory_report

    memory = contract_context(root, safe_documents, workflow)
    tools = tool_memory_report(
        profiles=list(manifest.get("profiles", []))
        if isinstance(manifest.get("profiles"), list)
        else []
    )
    cmd_memory: dict[str, object] = {"blocks": [], "hint": None}
    try:
        from pala_cmd_memory import active_blocks, context_packet_hint

        cmd_memory = {
            "blocks": active_blocks(limit=5),
            "hint": context_packet_hint(limit=3),
        }
    except (OSError, ValueError, TypeError, ImportError):
        pass
    cold_packet: dict[str, object] | None = None
    try:
        from pala_cold_packet import build_cold_packet

        cold_packet = build_cold_packet(
            root,
            profile="minimal",
            session_id=session,
            documents=safe_documents,
            workflow=workflow if isinstance(workflow, dict) else None,
        )
    except (OSError, ValueError, TypeError, ImportError):
        cold_packet = None
    return {
        "active_ticket": workflow.get("active_ticket"),
        "goal": workflow.get("goal"),
        "next_action": workflow.get("next_action"),
        "dirty": bool(workflow.get("dirty")),
        "verification_tier": workflow.get("verification_tier", "not-run"),
        "blockers": workflow.get("blockers", []),
        "reconciliation": reconciliation,
        "read_first": safe_documents.get("status"),
        "read_order": memory.get("read_order"),
        "ticket_coherence": memory.get("ticket_coherence"),
        "tool_memory": {
            "counts": tools.get("counts"),
            "total": tools.get("total"),
        },
        "cmd_memory": cmd_memory,
        "cold_packet": cold_packet,
        "memory_contract_version": memory.get("memory_contract_version"),
        "active_plan": safe_documents.get("plan"),
        "project": safe_documents.get("project"),
    }


class _PalaArgumentParser(argparse.ArgumentParser):
    """Turkish-friendly errors for required begin --goal (and related) flags."""

    def error(self, message: str) -> None:  # type: ignore[override]
        text = str(message or "")
        lowered = text.casefold()
        if "--goal" in lowered or (
            "goal" in lowered and ("required" in lowered or "zorunlu" in lowered)
        ):
            text = (
                'begin için --goal zorunlu. '
                'Örnek: begin --ticket T1 --goal "tek sonraki iş"'
            )
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {text}\n")


def parser() -> argparse.ArgumentParser:
    result = _PalaArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(
        dest="command", required=True, parser_class=_PalaArgumentParser
    )
    for command in ("discover", "validate", "instructions", "context", "memory"):
        child = subparsers.add_parser(command)
        child.add_argument("--cwd", default=".")
        if command == "context":
            child.add_argument("--session-key")
        if command == "memory":
            child.add_argument("--session-key")
    register_parser = subparsers.add_parser("register")
    register_parser.add_argument("--cwd", default=".")
    register_parser.add_argument("--instructions")
    register_parser.add_argument("--project")
    register_parser.add_argument("--plan")
    register_parser.add_argument("--status")
    register_parser.add_argument("--decisions")
    register_parser.add_argument("--open-source", dest="open_source")
    register_parser.add_argument("--demo")
    begin_parser = subparsers.add_parser(
        "begin",
        help="Start a ticket; --goal zorunlu",
    )
    begin_parser.add_argument("--cwd", default=".")
    begin_parser.add_argument("--ticket", required=True)
    begin_parser.add_argument(
        "--goal",
        required=True,
        help='Zorunlu hedef. Örnek: begin --ticket T1 --goal "tek sonraki iş"',
    )
    begin_parser.add_argument("--session-key")
    checkpoint_parser = subparsers.add_parser("checkpoint")
    checkpoint_parser.add_argument("--cwd", default=".")
    checkpoint_parser.add_argument("--next-action", required=True)
    checkpoint_parser.add_argument("--verification", action="append", default=[])
    checkpoint_parser.add_argument("--blocker", action="append", default=[])
    checkpoint_parser.add_argument("--session-key")
    checkpoint_parser.add_argument("--ticket")
    checkpoint_parser.add_argument(
        "--tier", choices=VERIFICATION_TIERS, default="ticket"
    )
    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--cwd", default=".")
    doctor_parser.add_argument("--session-key")
    verification_parser = subparsers.add_parser("record-verification")
    verification_parser.add_argument("--cwd", default=".")
    verification_parser.add_argument("--ticket", required=True)
    verification_parser.add_argument("--session-key", required=True)
    verification_parser.add_argument("--status", required=True)
    verification_parser.add_argument("--command", dest="verification_command", required=True)
    verification_parser.add_argument("--error", default="")
    for command in ("recover", "complete"):
        child = subparsers.add_parser(command)
        child.add_argument("--cwd", default=".")
        child.add_argument("--ticket", required=True)
        child.add_argument("--session-key", required=True)
    debug_gate_parser = subparsers.add_parser("debug-gate")
    debug_gate_parser.add_argument("--cwd", default=".")
    debug_gate_parser.add_argument(
        "--surface",
        default="begin",
        choices=("session", "begin", "checkpoint", "complete"),
    )
    debug_gate_parser.add_argument("--json", action="store_true")
    debug_gate_parser.add_argument("--record-attempt", metavar="INC_ID")
    debug_gate_parser.add_argument("--attempt-detail", default="")
    return result


def main() -> int:
    args = parser().parse_args()
    root = git_root(Path(args.cwd))
    if args.command == "discover":
        print(json.dumps(discover(root), ensure_ascii=False, indent=2))
        return 0
    if args.command == "instructions":
        print(
            json.dumps(
                configured_instruction_report(root, Path(args.cwd)),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "register":
        return register(args, root)
    if args.command == "context":
        try:
            print(
                json.dumps(
                    context_report(root, args.session_key), ensure_ascii=False, indent=2
                )
            )
            return 0
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if args.command == "memory":
        try:
            from pala_memory import plain_memory_report

            try:
                report = context_report(root, getattr(args, "session_key", None))
                documents = dict(load_manifest(root).get("documents") or {})
                workflow = {
                    "active_ticket": report.get("active_ticket"),
                    "next_action": report.get("next_action"),
                }
                tool_counts = None
                tool_memory = report.get("tool_memory")
                if isinstance(tool_memory, dict) and isinstance(
                    tool_memory.get("counts"), dict
                ):
                    tool_counts = tool_memory["counts"]
                coherence = report.get("ticket_coherence")
                mismatch = (
                    isinstance(coherence, dict) and bool(coherence.get("mismatch"))
                )
            except (OSError, ValueError, json.JSONDecodeError):
                discovery = discover(root)
                documents = dict(discovery.get("documents") or {})
                workflow = {}
                tool_counts = None
                mismatch = False
            print(
                plain_memory_report(
                    root,
                    documents=documents,
                    workflow=workflow,
                    tool_counts=tool_counts,
                ),
                end="",
            )
            return 1 if mismatch else 0
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if args.command == "begin":
        try:
            begin_work(root, args.ticket, args.goal, args.session_key)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(str(root / WORKFLOW))
        return 0
    if args.command == "checkpoint":
        if args.session_key:
            if not args.ticket:
                print("ticket is required with --session-key", file=sys.stderr)
                return 2
            from pala_store import WorkflowStore

            result = WorkflowStore(root).checkpoint(
                args.ticket, args.session_key, args.next_action
            )
            print(json.dumps({"status": result.status, "record": result.record}, ensure_ascii=False))
            return 0 if result.status == "checkpointed" else 2
        try:
            manifest = load_manifest(root)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        if not args.verification:
            print("verification evidence is required for checkpoint", file=sys.stderr)
            return 2
        try:
            checkpoint_work(
                root,
                args.next_action,
                args.verification,
                args.blocker,
                args.tier,
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(str(root / WORKFLOW))
        return 0
    if args.command == "record-verification":
        from pala_store import WorkflowStore

        try:
            result = WorkflowStore(root).record_verification(
                args.ticket, args.session_key, args.status, args.verification_command, args.error
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(json.dumps({"status": result.status, "record": result.record}, ensure_ascii=False))
        return 0 if result.status in {"recorded", "blocked"} else 2
    if args.command in {"recover", "complete"}:
        from pala_store import WorkflowStore

        if args.command == "complete":
            try:
                from pala_debug_gate import complete_fail_closed

                documents: dict[str, object] | None = None
                changed: list[str] = []
                verification: list[object] = []
                try:
                    documents = dict(load_manifest(root).get("documents") or {})
                except (OSError, ValueError, json.JSONDecodeError):
                    documents = {"debugging": "DEBUGGING.md"}
                try:
                    workflow = load_workflow(root)
                    raw_changed = workflow.get("changed_files") or []
                    if isinstance(raw_changed, list):
                        changed = [str(item) for item in raw_changed]
                    raw_verify = workflow.get("verification_evidence") or workflow.get(
                        "verification"
                    ) or []
                    if isinstance(raw_verify, list):
                        verification = list(raw_verify)
                except (OSError, ValueError, json.JSONDecodeError):
                    pass
                # Session ticket store may also hold verification.
                try:
                    record = WorkflowStore(root)._read(
                        WorkflowStore(root)._ticket_path(args.ticket)
                    )
                    if isinstance(record, dict):
                        store_verify = record.get("verification") or []
                        if isinstance(store_verify, list) and store_verify:
                            verification = list(store_verify)
                        store_changed = record.get("changed_files") or []
                        if isinstance(store_changed, list) and store_changed:
                            changed = [str(item) for item in store_changed]
                except (OSError, ValueError, TypeError, AttributeError):
                    pass
                decision = complete_fail_closed(
                    root,
                    documents=documents,
                    changed_files=changed,
                    verification=verification,
                    enabled=True,
                )
                if not decision.get("allowed"):
                    print(str(decision.get("reason") or "complete refused"), file=sys.stderr)
                    return 2
            except (OSError, ValueError, TypeError, ImportError) as exc:
                print(str(exc), file=sys.stderr)
                return 2
        try:
            result = getattr(WorkflowStore(root), args.command)(args.ticket, args.session_key)
        except ValueError as exc:
            reason = str(exc)
            if args.command == "complete" and (
                "not found" in reason.casefold() or "ticket" in reason.casefold()
            ):
                print(
                    complete_recovery_message(args.ticket, reason=reason),
                    file=sys.stderr,
                )
            else:
                print(reason, file=sys.stderr)
            return 2
        if args.command == "complete" and result.status not in {"completed"}:
            if result.status in {"owned_by_other", "busy"}:
                print(
                    complete_recovery_message(
                        args.ticket,
                        reason=f"status={result.status}",
                    ),
                    file=sys.stderr,
                )
            print(
                json.dumps(
                    {"status": result.status, "record": result.record},
                    ensure_ascii=False,
                )
            )
            return 2
        print(json.dumps({"status": result.status, "record": result.record}, ensure_ascii=False))
        return 0 if result.status in {"recovered", "completed"} else 2
    if args.command == "doctor":
        payload = doctor_report(root, session=args.session_key)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["healthy"] else 2
    if args.command == "debug-gate":
        from pala_debug_gate import main as debug_gate_main

        argv = ["--cwd", str(root), "--surface", args.surface]
        if args.json:
            argv.append("--json")
        if args.record_attempt:
            argv.extend(["--record-attempt", args.record_attempt])
        if args.attempt_detail:
            argv.extend(["--attempt-detail", args.attempt_detail])
        return debug_gate_main(argv)
    return validate(root)


if __name__ == "__main__":
    raise SystemExit(main())

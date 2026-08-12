#!/usr/bin/env python3
"""Bounded, read-only discovery helpers for Pala quality planning.

This module owns project metadata, changed-surface, and repository-shape
discovery.  It never runs a project quality command and deliberately keeps Git
calls fixed-argument, shell-free, and time-bounded.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

DANGEROUS_SCRIPT = re.compile(
    r"(?i)(?:^|[;&|])\s*(?:rm\s+-[^\n]*r|del\s+/[fs]|rmdir\s+/s|format\b|diskpart\b|shutdown\b|curl\b[^\n]*\|\s*(?:sh|bash|pwsh|powershell)\b)"
)
DISCOVERY_SKIP_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".codex",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "vendor",
        "artifacts",
        "dist",
        "build",
        "coverage",
        "playwright-report",
        "test-results",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".next",
        ".nuxt",
        ".turbo",
    }
)
IGNORED_CHANGE_PREFIXES = (
    ".codex/plugin-data/",
    ".pala/runtime/",
    ".pala/tmp/",
    "artifacts/",
    "node_modules/",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".pytest_cache/",
    "playwright-report/",
    "test-results/",
    "coverage/",
)
# These documents are the local Pala memory contract, not delivery source.
# Ticket checkpoints necessarily update them after a gate; including them in
# the gate's surface would invalidate its own evidence without a code change.
MEMORY_STATE_PATHS = frozenset({"status.md", "plan.md", "progress.md", "debugging.md"})
MAX_DISCOVERY_FILES = 12_000
GIT_TIMEOUT_SECONDS = 5


def read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def project_package(root: Path) -> dict[str, object]:
    path = Path(root) / "package.json"
    return read_json(path) if path.is_file() else {}


def package_scripts(package: dict[str, object]) -> dict[str, str]:
    raw = package.get("scripts")
    if not isinstance(raw, dict):
        return {}
    return {
        str(name): str(command).strip()
        for name, command in raw.items()
        if isinstance(name, str) and isinstance(command, str) and command.strip()
    }


def workflow_text(root: Path) -> str:
    directory = Path(root) / ".github" / "workflows"
    if not directory.is_dir():
        return ""
    texts: list[str] = []
    for path in sorted(directory.glob("*.y*ml")):
        try:
            texts.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(texts).casefold()


def workflow_commands(root: Path) -> list[str]:
    """Return only simple, explicit one-line CI run commands.

    This is discovery, not a YAML interpreter. Multiline shell blocks are not
    reconstructed; a project owner can instead make those commands explicit in
    a quality contract.
    """
    directory = Path(root) / ".github" / "workflows"
    if not directory.is_dir():
        return []
    commands: list[str] = []
    pattern = re.compile(r"(?m)^\s*(?:-\s*)?run\s*:\s*([^#\r\n]+)")
    for path in sorted(directory.glob("*.y*ml")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in pattern.finditer(text):
            command = match.group(1).strip()
            if command and command not in ("|", ">", ">-", "|-"):
                commands.append(command[:500])
    return commands


def ignored_changed_path(path: str) -> bool:
    normalized = str(path).replace("\\", "/").lstrip("./").casefold()
    return normalized in MEMORY_STATE_PATHS or any(
        normalized.startswith(prefix) for prefix in IGNORED_CHANGE_PREFIXES
    )


def _run_git(
    root: Path, arguments: tuple[str, ...], *, text: bool
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str] | None:
    """Run one fixed Git read query, or return None when it is unavailable.

    The argument tuples below are owned by Pala; no project command or user
    supplied shell text reaches this function.
    """
    executable = shutil.which("git")
    if not executable:
        return None
    try:
        return subprocess.run(  # nosec B603 - fixed Git argv, shell=False
            [executable, *arguments],
            cwd=root,
            capture_output=True,
            text=text,
            check=False,
            shell=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def changed_paths(root: Path) -> tuple[list[str], list[str]]:
    """Return changed source paths and transparently ignored runtime outputs."""
    commands = (
        ("diff", "--name-only", "-z"),
        ("diff", "--cached", "--name-only", "-z"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    )
    paths: set[str] = set()
    ignored: set[str] = set()
    for command in commands:
        result = _run_git(Path(root), command, text=False)
        if result is None or result.returncode != 0:
            continue
        output = result.stdout if isinstance(result.stdout, bytes) else b""
        for part in output.split(b"\0"):
            if not part:
                continue
            value = part.decode("utf-8", errors="surrogateescape")
            if ignored_changed_path(value):
                ignored.add(value)
            else:
                paths.add(value)
    return sorted(paths, key=str.casefold), sorted(ignored, key=str.casefold)


def surface_digest(root: Path, changed_files: list[str]) -> str:
    """Hash paths plus current worktree content without persisting source text."""
    digest = hashlib.sha256(b"pala-quality-surface-v1\0")
    resolved_root = Path(root).resolve()
    for raw_path in sorted({str(item) for item in changed_files}, key=str.casefold):
        relative = raw_path.replace("\\", "/").lstrip("./")
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        candidate = resolved_root / relative
        try:
            candidate.relative_to(resolved_root)
        except ValueError:
            digest.update(b"outside-root\0")
            continue
        try:
            if candidate.is_symlink():
                digest.update(b"symlink\0")
                digest.update(
                    os.readlink(candidate).encode("utf-8", errors="surrogateescape")
                )
            elif candidate.is_file():
                digest.update(b"file\0")
                with candidate.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(64 * 1024), b""):
                        digest.update(chunk)
            elif candidate.exists():
                digest.update(b"non-file\0")
            else:
                digest.update(b"missing\0")
        except OSError:
            digest.update(b"unreadable\0")
        digest.update(b"\0")
    return digest.hexdigest()


def git_summary(root: Path, changed_files: list[str]) -> dict[str, object]:
    """Return a bounded read-only revision summary; never include diff content."""
    head = "unknown"
    diff_stat = ""
    revision = _run_git(Path(root), ("rev-parse", "HEAD"), text=True)
    if revision is not None and revision.returncode == 0:
        output = revision.stdout if isinstance(revision.stdout, str) else ""
        head = output.strip()[:80] or "unknown"
    stat = _run_git(Path(root), ("diff", "--stat", "--no-ext-diff"), text=True)
    if stat is not None and stat.returncode == 0:
        output = stat.stdout if isinstance(stat.stdout, str) else ""
        diff_stat = " ".join(output.splitlines()[-1:])[:240]
    return {
        "head": head,
        "changed_file_count": len(changed_files),
        "diff_stat": diff_stat,
    }


def iter_project_files(root: Path):
    """Bounded project walk that never lets generated/vendor trees decide gates."""
    seen = 0
    for current, directories, files in os.walk(root):
        directories[:] = sorted(
            (entry for entry in directories if entry.casefold() not in DISCOVERY_SKIP_DIRS),
            key=str.casefold,
        )
        for name in sorted(files, key=str.casefold):
            seen += 1
            if seen > MAX_DISCOVERY_FILES:
                return
            yield Path(current) / name


def python_unittest_discovery(root: Path) -> tuple[str | None, str]:
    """Return one explicit, non-vacuous unittest command when it is knowable."""
    paths = [
        path
        for path in iter_project_files(root)
        if path.name.startswith("test_") and path.suffix == ".py"
    ]
    if not paths:
        return None, ""

    supported_roots = ("tests", "test", "scripts")
    detected_roots: set[str] = set()
    for path in paths:
        try:
            relative = path.relative_to(root)
        except ValueError:
            return None, "Python test path is outside the project root"
        if len(relative.parts) == 1:
            detected_roots.add(".")
        elif relative.parts[0] in supported_roots:
            detected_roots.add(relative.parts[0])
        else:
            detected_roots.add("custom")

    if detected_roots == {"."}:
        return "py -3 -m unittest discover -p test_*.py", ""
    if len(detected_roots) == 1:
        start = next(iter(detected_roots))
        if start in supported_roots:
            return f"py -3 -m unittest discover -s {start} -p test_*.py", ""
    return (
        None,
        "Python tests use multiple or unsupported roots; add a project-owned quality contract",
    )


def has_ui(package: dict[str, object], root: Path) -> bool:
    dependencies: list[str] = []
    for key in ("dependencies", "devDependencies"):
        values = package.get(key)
        if isinstance(values, dict):
            dependencies.extend(str(name).casefold() for name in values)
    if any(
        name in {"react", "vue", "@angular/core", "svelte", "next", "nuxt"}
        for name in dependencies
    ):
        return True
    return any(
        path.suffix.casefold() in {".tsx", ".jsx", ".vue", ".svelte", ".html"}
        for path in iter_project_files(root)
    )

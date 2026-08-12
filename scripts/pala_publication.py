"""Provider-independent publication governance primitives.

The module is deliberately local and read-only.  It classifies a project before
any GitHub write so future projects can reuse the same hygiene, privacy, cost,
and version-consistency rules without creating a second release authority.
"""

from __future__ import annotations

import json
import re
import subprocess  # nosec B404 - argv is constant and shell is disabled
from pathlib import Path
from typing import Any

STATUSES = ("CURRENT", "HISTORICAL", "NOT_APPLICABLE", "DRIFTED", "UNKNOWN")
JUNK_PARTS = {
    ".git",
    ".venv",
    ".tools",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    ".codex",
    "dist",
    "node_modules",
    "playwright-report",
    "test-results",
}
JUNK_SUFFIXES = {".pyc", ".pyo", ".sqlite", ".sqlite3", ".coverage"}
HISTORICAL_PARTS = {"artifacts", "docs", "outputs", "superpowers"}
GENERATED_FILES = {"STATUS.md", "PROGRESS.md"}
HISTORICAL_MARKERS = ("historical", "superseded", "archived")
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    (
        "github-token",
        re.compile(
            rf"(?:{re.escape('gh' + 'o_')}|{re.escape('gh' + 'p_')}|{re.escape('github_' + 'pat_')})[A-Za-z0-9_]{{20,}}"
        ),
    ),
    ("authorization-header", re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._-]{16,}")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("openai-key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
)
USER_PATH = re.compile(r"(?i)(?:[A-Z]:[\\/]+Users[\\/]+|/Users/)[^\\/\s<>'\"]+")


def _iter_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part.casefold() in {item.casefold() for item in JUNK_PARTS} for part in relative.parts):
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.relative_to(root).as_posix().casefold())


def _git_inventory(root: Path) -> dict[str, list[str]]:
    """Return tracked/untracked/ignored paths without invoking a write command."""
    try:
        result = subprocess.run(  # nosec B603 - constant argv, shell disabled
            ["git", "-C", str(root), "status", "--short", "--ignored", "--untracked-files=all"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"tracked": [], "untracked": [], "ignored": [], "status": ["UNKNOWN"]}
    tracked: list[str] = []
    untracked: list[str] = []
    ignored: list[str] = []
    for line in result.stdout.splitlines():
        if line.startswith("!! "):
            ignored.append(line[3:])
        elif line.startswith("?? "):
            untracked.append(line[3:])
        elif line:
            tracked.append(line[3:] if len(line) > 3 else line)
    if result.returncode != 0:
        fallback = [path.relative_to(root).as_posix() for path in _iter_files(root)]
        return {"tracked": [], "untracked": fallback, "ignored": [], "status": ["UNKNOWN"]}
    return {"tracked": tracked, "untracked": untracked, "ignored": ignored, "status": []}


def repository_hygiene(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    inventory = _git_inventory(root)
    junk: list[str] = []
    for path in _iter_files(root):
        relative = path.relative_to(root)
        if path.suffix.casefold() in JUNK_SUFFIXES or path.name.casefold() in {".env", ".env.local"}:
            junk.append(relative.as_posix())
    tracked_junk = sorted(item for item in junk if item in inventory["tracked"])
    return {
        "status": "passed" if not tracked_junk and not inventory["status"] else "blocked" if tracked_junk else "configured-not-verified",
        "tracked_count": len(inventory["tracked"]),
        "untracked_count": len(inventory["untracked"]),
        "ignored_count": len(inventory["ignored"]),
        "tracked_junk": tracked_junk,
        "untracked_junk": sorted(item for item in junk if item in inventory["untracked"]),
        "inventory": inventory,
    }


def secret_scan(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    findings: list[dict[str, str]] = []
    historical_paths: list[str] = []
    for path in _iter_files(root):
        relative = path.relative_to(root)
        parts = {part.casefold() for part in relative.parts}
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for rule, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append({"rule": rule, "path": relative.as_posix()})
        if path.suffix.casefold() != ".py" and USER_PATH.search(text):
            if (
                parts.intersection(HISTORICAL_PARTS)
                or path.name in GENERATED_FILES
                or any(marker in text[:300].casefold() for marker in HISTORICAL_MARKERS)
            ):
                historical_paths.append(relative.as_posix())
            else:
                findings.append({"rule": "user-home-path", "path": relative.as_posix()})
    return {
        "status": "passed" if not findings else "blocked",
        "findings": sorted(findings, key=lambda item: (item["rule"], item["path"])),
        "historical_local_paths": sorted(set(historical_paths)),
        "raw_matches": "never-recorded",
    }


def load_json(root: Path, relative: str) -> dict[str, Any]:
    value = json.loads((Path(root) / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {relative}")
    return value


def generic_cost_guard(*, visibility: str | None, billing: str | None, requested_path: str) -> dict[str, str]:
    if visibility not in {"public", "private"}:
        return {"status": "blocked", "message": "Publication stopped safely. Repository visibility could not be verified."}
    if requested_path in {"billing", "larger-runner", "paid-storage", "codespaces"}:
        return {"status": "blocked", "message": "Publication stopped safely. The requested action may incur paid usage."}
    if billing not in {"known-free", "not-required"}:
        return {"status": "configured-not-verified", "message": "No paid action was requested; billing state remains unverified."}
    return {"status": "passed", "message": "No unexpected paid action detected for the approved path."}


def _base_version(value: object) -> str:
    return str(value or "").split("+", 1)[0]


def version_matrix(
    root: Path,
    expected_version: str,
    *,
    surfaces: dict[str, str | None] | None = None,
) -> dict[str, Any]:
    """Classify current publication surfaces; historical text is not drift."""
    root = Path(root).resolve()
    checked: dict[str, dict[str, str]] = {}
    drift: list[str] = []
    unknown: list[str] = []
    for name, relative in (surfaces or {}).items():
        if relative is None:
            checked[name] = {"status": "NOT_APPLICABLE", "reason": "surface not configured"}
            continue
        path = root / relative
        if not path.is_file():
            checked[name] = {"status": "UNKNOWN", "reason": "required current surface is missing"}
            unknown.append(name)
            continue
        text = path.read_text(encoding="utf-8")
        if expected_version in text:
            checked[name] = {"status": "CURRENT", "path": relative}
        elif any(marker in text[:300].casefold() for marker in HISTORICAL_MARKERS) or any(
            part.casefold() in HISTORICAL_PARTS for part in path.relative_to(root).parts
        ):
            checked[name] = {"status": "HISTORICAL", "path": relative}
        else:
            checked[name] = {"status": "DRIFTED", "path": relative}
            drift.append(name)
    return {
        "status": "passed" if not drift and not unknown else "blocked",
        "expected_version": expected_version,
        "surfaces": checked,
        "required_drift": sorted(drift),
        "unknown": sorted(unknown),
    }


def current_publication_matrix(root: Path) -> dict[str, Any]:
    """Build the Pala matrix from the canonical product identity."""
    identity = load_json(root, "product-identity.json")
    expected = str(identity.get("product_version") or "")
    plugin = load_json(root, ".codex-plugin/plugin.json")
    surfaces = {
        "product-identity": "product-identity.json",
        "plugin-identity": ".codex-plugin/plugin.json",
        "README": "README.md",
        "README.tr": "README.tr.md",
        "PROJECT": "PROJECT.md",
        "GOAL": "GOAL.md",
        "CHANGELOG": "CHANGELOG.md",
        "installer": "Install-Pala.ps1",
        "release-policy": "policies/release.json",
        "quality-policy": "policies/core-quality.json",
        "design-tokens": "design/tokens.json",
        "release-notes": "docs/RELEASE_1.0.0.md",
    }
    matrix = version_matrix(root, expected, surfaces=surfaces)
    plugin_version = _base_version(plugin.get("version"))
    if plugin_version != expected:
        matrix["surfaces"]["plugin-identity"] = {"status": "DRIFTED", "path": ".codex-plugin/plugin.json"}
        matrix["required_drift"] = sorted(set(matrix["required_drift"]) | {"plugin-identity"})
        matrix["status"] = "blocked"
    matrix["release_truth"] = {
        "product_version": expected,
        "plugin_base_version": plugin_version,
        "artifact_name": identity.get("artifact_name"),
        "authority": "product-identity.json",
    }
    return matrix


__all__ = [
    "STATUSES",
    "current_publication_matrix",
    "generic_cost_guard",
    "load_json",
    "repository_hygiene",
    "secret_scan",
    "version_matrix",
]

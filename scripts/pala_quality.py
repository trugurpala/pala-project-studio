#!/usr/bin/env python3
"""Derive and record evidence-first quality gates without running project tools.

This is Pala's Delivery Quality Engine v1. It deliberately discovers only
existing project commands and already-installed scanners. Running a command is
an explicit agent/user action; hooks never invoke this module to execute work.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


SCHEMA_VERSION = 1
QUALITY_DIR = Path(".codex/plugin-data/pala/v3/quality")
QUALITY_CONTRACT_PATH = Path(".pala/quality.json")
STATUSES = ("passed", "failed", "not-run", "blocked", "configured-not-verified")
TIERS = ("narrow", "ticket", "milestone", "release")
CHECK_KINDS = (
    "unit",
    "lint",
    "typecheck",
    "build",
    "integration",
    "browser",
    "security",
    "dependency",
    "migration",
    "runtime-smoke",
)
SENSITIVE_VALUE = re.compile(
    r"(?i)(?:\b(?:api[_-]?key|token|password|secret)\s*=|--(?:api[_-]?key|token|password|secret)=)"
)
TICKET_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
CHECK_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}\Z")
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
    "artifacts/wip/",
    "node_modules/",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".pytest_cache/",
    "playwright-report/",
    "test-results/",
    "coverage/",
)
MAX_DISCOVERY_FILES = 12_000


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_ticket(ticket: str) -> str:
    value = str(ticket or "").strip()
    if not TICKET_NAME.fullmatch(value):
        raise ValueError("ticket must be 1-80 safe characters (letters, digits, . _ -)")
    return value


def _safe_text(value: object, *, field: str, limit: int = 500) -> str:
    text = str(value or "").strip()
    if SENSITIVE_VALUE.search(text):
        raise ValueError(f"{field} may not contain a secret value")
    return text[:limit]


def _read_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _package(root: Path) -> dict[str, object]:
    path = root / "package.json"
    return _read_json(path) if path.is_file() else {}


def _scripts(package: dict[str, object]) -> dict[str, str]:
    raw = package.get("scripts")
    if not isinstance(raw, dict):
        return {}
    return {
        str(name): str(command).strip()
        for name, command in raw.items()
        if isinstance(name, str) and isinstance(command, str) and command.strip()
    }


def _workflow_text(root: Path) -> str:
    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        return ""
    texts: list[str] = []
    for path in sorted(directory.glob("*.y*ml")):
        try:
            texts.append(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    return "\n".join(texts).casefold()


def _workflow_commands(root: Path) -> list[str]:
    """Return only simple, explicit one-line CI run commands.

    This is discovery, not a YAML interpreter.  Multiline shell blocks are
    intentionally not reconstructed: a project owner can place those behind a
    quality contract instead of asking Pala to guess their execution semantics.
    """
    directory = root / ".github" / "workflows"
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


def _ignored_changed_path(path: str) -> bool:
    normalized = str(path).replace("\\", "/").lstrip("./").casefold()
    return any(normalized.startswith(prefix) for prefix in IGNORED_CHANGE_PREFIXES)


def _changed_paths(root: Path) -> tuple[list[str], list[str]]:
    """Return changed source paths and transparently ignored runtime outputs."""
    commands = (
        ("diff", "--name-only", "-z"),
        ("diff", "--cached", "--name-only", "-z"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    )
    paths: set[str] = set()
    ignored: set[str] = set()
    for command in commands:
        try:
            result = subprocess.run(
                ["git", *command], cwd=root, capture_output=True, check=False
            )
        except OSError:
            continue
        if result.returncode != 0:
            continue
        for part in result.stdout.split(b"\0"):
            if part:
                value = part.decode("utf-8", errors="surrogateescape")
                if _ignored_changed_path(value):
                    ignored.add(value)
                else:
                    paths.add(value)
    return sorted(paths, key=str.casefold), sorted(ignored, key=str.casefold)


def _changed_files(root: Path) -> list[str]:
    """Compatibility helper for callers that need only the source surface."""
    return _changed_paths(root)[0]


def _surface_digest(root: Path, changed_files: list[str]) -> str:
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
                digest.update(os.readlink(candidate).encode("utf-8", errors="surrogateescape"))
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


def _git_summary(root: Path, changed_files: list[str]) -> dict[str, object]:
    """Return a bounded read-only revision summary; never include diff content."""
    head = "unknown"
    diff_stat = ""
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if revision.returncode == 0:
            head = revision.stdout.strip()[:80] or "unknown"
        stat = subprocess.run(
            ["git", "diff", "--stat", "--no-ext-diff"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if stat.returncode == 0:
            diff_stat = " ".join(stat.stdout.splitlines()[-1:])[:240]
    except OSError:
        pass
    return {"head": head, "changed_file_count": len(changed_files), "diff_stat": diff_stat}


def risk_assessment(changed_files: list[str], *, has_project_code: bool) -> dict[str, object]:
    reasons: list[str] = []
    lowered = "\n".join(changed_files).casefold()
    if any(token in lowered for token in ("auth", "permission", "role", "session", "oauth")):
        reasons.append("authentication")
    if any(token in lowered for token in ("migration", "schema", "database", "db/")):
        reasons.append("migration")
    if any(token in lowered for token in ("payment", "billing", "checkout")):
        reasons.append("payments")
    if any(token in lowered for token in ("deploy", "infra", "terraform", "dockerfile", "workflow")):
        reasons.append("delivery")
    if reasons:
        level = "high"
    elif changed_files or has_project_code:
        level = "medium"
    else:
        level = "low"
    return {"level": level, "reasons": reasons or (["project-code"] if has_project_code else [])}


def _required_for_tier(kind: str, tier: str) -> bool:
    if tier == "narrow":
        return kind == "unit"
    return True


def _add_check(
    checks: list[dict[str, object]],
    *,
    kind: str,
    name: str,
    command: str | None,
    source: str,
    tier: str,
    status: str = "not-run",
    reason: str = "",
) -> None:
    check_id = f"{kind}:{name}"
    if any(item.get("id") == check_id for item in checks):
        return
    checks.append(
        {
            "id": check_id,
            "kind": kind,
            "required": _required_for_tier(kind, tier),
            "command": command,
            "source": source,
            "status": status,
            "reason": reason[:240],
        }
    )


def _iter_project_files(root: Path):
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


def _has_python_tests(root: Path) -> bool:
    return any(path.name.startswith("test_") and path.suffix == ".py" for path in _iter_project_files(root))


def _has_ui(package: dict[str, object], root: Path) -> bool:
    dependencies: list[str] = []
    for key in ("dependencies", "devDependencies"):
        values = package.get(key)
        if isinstance(values, dict):
            dependencies.extend(str(name).casefold() for name in values)
    if any(name in {"react", "vue", "@angular/core", "svelte", "next", "nuxt"} for name in dependencies):
        return True
    return any(
        path.suffix.casefold() in {".tsx", ".jsx", ".vue", ".svelte", ".html"}
        for path in _iter_project_files(root)
    )


def _contract_command(argv: object) -> str:
    """Validate a shell-free command contract and return its display form."""
    if not isinstance(argv, list) or not argv or len(argv) > 32:
        raise ValueError("argv must be a non-empty list with at most 32 arguments")
    values: list[str] = []
    for raw in argv:
        if not isinstance(raw, str) or not raw.strip() or len(raw) > 240:
            raise ValueError("each argv item must be a short non-empty string")
        value = raw.strip()
        if any(character in value for character in ("\n", "\r", "\0")):
            raise ValueError("argv items may not contain control characters")
        if value in {";", "|", "||", "&&", "&"}:
            raise ValueError("argv may not contain shell operators")
        values.append(value)
    command = subprocess.list2cmdline(values)
    if DANGEROUS_SCRIPT.search(command):
        raise ValueError("argv resolves to a command requiring manual safety review")
    _safe_text(command, field="contract command")
    return command


def _quality_contract_checks(root: Path, tier: str) -> tuple[list[dict[str, object]], str]:
    """Load an optional project-owned contract; invalid input fails closed."""
    path = root / QUALITY_CONTRACT_PATH
    if not path.is_file():
        return [], ""
    try:
        payload = _read_json(path)
        if payload.get("schema_version") != 1:
            raise ValueError("schema_version must be 1")
        raw_checks = payload.get("checks")
        if not isinstance(raw_checks, list) or not raw_checks:
            raise ValueError("checks must be a non-empty list")
        checks: list[dict[str, object]] = []
        seen: set[str] = set()
        for raw in raw_checks:
            if not isinstance(raw, dict):
                raise ValueError("each check must be an object")
            name = str(raw.get("id") or "").strip()
            kind = str(raw.get("kind") or "").strip()
            if not CHECK_NAME.fullmatch(name):
                raise ValueError("check id must use safe letters, digits, dots, underscores, or hyphens")
            if kind not in CHECK_KINDS:
                raise ValueError(f"unsupported contract check kind: {kind}")
            check_id = f"{kind}:{name}"
            if check_id in seen:
                raise ValueError(f"duplicate contract check: {check_id}")
            seen.add(check_id)
            tiers = raw.get("tiers", list(TIERS))
            if not isinstance(tiers, list) or not tiers or any(item not in TIERS for item in tiers):
                raise ValueError("tiers must be a non-empty list of supported tiers")
            command = _contract_command(raw.get("argv"))
            checks.append(
                {
                    "id": check_id,
                    "kind": kind,
                    "required": tier in tiers and _required_for_tier(kind, tier),
                    "command": command,
                    "source": "pala-quality-contract",
                    "status": "not-run",
                    "reason": "",
                }
            )
        return checks, ""
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [], f"invalid {QUALITY_CONTRACT_PATH.as_posix()}: {exc}"[:240]


def _add_script_check(
    checks: list[dict[str, object]],
    *,
    kind: str,
    name: str,
    scripts: dict[str, str],
    tier: str,
) -> None:
    """Add a project-native script, but never normalize a destructive command."""
    configured = scripts[name]
    if DANGEROUS_SCRIPT.search(configured):
        _add_check(
            checks,
            kind=kind,
            name=name,
            command=None,
            source="package.json",
            tier=tier,
            status="blocked",
            reason="configured script needs manual safety review",
        )
        return
    _add_check(
        checks,
        kind=kind,
        name=name,
        command=f"npm run {name}",
        source="package.json",
        tier=tier,
    )


def build_quality_plan(
    root: Path,
    *,
    tier: str = "ticket",
    changed_files: list[str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> dict[str, object]:
    """Return a deterministic plan; this function never executes project commands."""
    root = Path(root).resolve()
    if tier not in TIERS:
        raise ValueError(f"unsupported quality tier: {tier}")
    package = _package(root)
    scripts = _scripts(package)
    checks: list[dict[str, object]] = []
    contract_checks, contract_error = _quality_contract_checks(root, tier)
    checks.extend(contract_checks)
    if contract_error:
        _add_check(
            checks,
            kind="integration",
            name="quality-contract",
            command=None,
            source="pala-quality-contract",
            tier=tier,
            status="blocked",
            reason=contract_error,
        )

    for name in ("test:unit", "test"):
        if name in scripts:
            _add_script_check(checks, kind="unit", name=name, scripts=scripts, tier=tier)
            break
    if not any(item["kind"] == "unit" for item in checks) and _has_python_tests(root):
        _add_check(
            checks,
            kind="unit",
            name="unittest",
            command="py -3 -m unittest discover",
            source="python-tests",
            tier=tier,
        )
    for kind, candidates in (
        ("lint", ("lint",)),
        ("typecheck", ("typecheck", "check-types")),
        ("build", ("build",)),
        ("integration", ("test:integration", "integration")),
        ("migration", ("migrate:check", "migration:check")),
        ("runtime-smoke", ("smoke", "test:smoke")),
    ):
        for name in candidates:
            if name in scripts:
                _add_script_check(checks, kind=kind, name=name, scripts=scripts, tier=tier)
                break

    ui = _has_ui(package, root)
    playwright_config = any(
        (root / name).is_file()
        for name in ("playwright.config.ts", "playwright.config.js", "playwright.config.mjs", "playwright.config.cjs")
    )
    for name, command in scripts.items():
        has_playwright_command = "playwright" in command.casefold()
        if ui and (playwright_config or has_playwright_command) and (
            "e2e" in name.casefold() or has_playwright_command
        ):
            _add_script_check(checks, kind="browser", name=name, scripts=scripts, tier=tier)
            break
    if ui and playwright_config and not any(item["kind"] == "browser" for item in checks):
        _add_check(
            checks,
            kind="browser",
            name="playwright-config",
            command=None,
            source="playwright-config",
            tier=tier,
            status="configured-not-verified",
            reason="Playwright config exists but no explicit project-owned browser command was found",
        )

    workflow = _workflow_text(root)
    workflow_commands = _workflow_commands(root)
    scanner_specs = (
        ("gitleaks", "security"),
        ("zizmor", "security"),
        ("osv-scanner", "dependency"),
    )
    for scanner, kind in scanner_specs:
        if scanner in workflow:
            script_name = next(
                (name for name, command in scripts.items() if scanner in command.casefold()),
                None,
            )
            workflow_command = next(
                (
                    command
                    for command in workflow_commands
                    if scanner in command.casefold() and not DANGEROUS_SCRIPT.search(command)
                ),
                None,
            )
            if scanner == "osv-scanner":
                # OSV's normal scan can query remote advisory services.  A CI
                # mention is evidence of configuration, not permission for Pala
                # to repeat a potentially networked scan.
                _add_check(
                    checks,
                    kind=kind,
                    name=scanner,
                    command=None,
                    source="existing-ci",
                    tier=tier,
                    status="configured-not-verified",
                    reason="OSV scanner may use the network; use an explicit project-owned offline contract command",
                )
            elif script_name is not None:
                _add_script_check(checks, kind=kind, name=script_name, scripts=scripts, tier=tier)
            elif workflow_command and which(scanner):
                _add_check(
                    checks,
                    kind=kind,
                    name=scanner,
                    command=workflow_command,
                    source="existing-ci",
                    tier=tier,
                )
            else:
                _add_check(
                    checks,
                    kind=kind,
                    name=scanner,
                    command=None,
                    source="existing-ci",
                    tier=tier,
                    status="configured-not-verified",
                    reason="explicit installed project scanner command required",
                )
    if "audit" in scripts:
        _add_script_check(checks, kind="dependency", name="audit", scripts=scripts, tier=tier)

    ignored_files: list[str] = []
    if changed_files is None:
        files, ignored_files = _changed_paths(root)
    else:
        files = sorted({str(item) for item in changed_files}, key=str.casefold)
    risk = risk_assessment(files, has_project_code=bool(package) or _has_python_tests(root))
    reasons = set(risk.get("reasons") or [])
    if "migration" in reasons and not any(item["kind"] == "migration" for item in checks):
        _add_check(
            checks,
            kind="migration",
            name="risk-surface",
            command=None,
            source="changed-surface",
            tier=tier,
            status="blocked",
            reason="migration changed; configure a project-native migration check",
        )
    if reasons.intersection({"authentication", "payments"}) and not any(
        item["kind"] == "security" for item in checks
    ):
        _add_check(
            checks,
            kind="security",
            name="risk-surface",
            command=None,
            source="changed-surface",
            tier=tier,
            status="blocked",
            reason="high-risk surface changed; configure a project-native security check",
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "root": root.name,
        "tier": tier,
        "changed_files": [str(item)[:240] for item in files[:80]],
        "ignored_changed_paths": [str(item)[:240] for item in ignored_files[:40]],
        "surface_digest": _surface_digest(root, files),
        "risk": risk,
        "git": _git_summary(root, files),
        "checks": checks,
        "generated_at": _stamp(),
        "execution": "not-run: run only selected project-native commands; hooks never execute gates",
    }


def quality_ledger_path(root: Path, ticket: str) -> Path:
    return Path(root).resolve() / QUALITY_DIR / f"{_safe_ticket(ticket)}.json"


def _atomic_write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def write_ledger(root: Path, ticket: str, plan: dict[str, object]) -> Path:
    ticket = _safe_ticket(ticket)
    raw_checks = plan.get("checks")
    if not isinstance(raw_checks, list):
        raise ValueError("quality plan checks must be a list")
    checks: list[dict[str, object]] = []
    for item in raw_checks:
        if not isinstance(item, dict):
            raise ValueError("quality plan check must be an object")
        check_id = str(item.get("id") or "").strip()
        kind = str(item.get("kind") or "").strip()
        status = str(item.get("status") or "not-run").strip()
        if not check_id or not kind or status not in STATUSES:
            raise ValueError("quality plan contains invalid check")
        checks.append(
            {
                "id": check_id[:120],
                "kind": kind[:40],
                "required": bool(item.get("required")),
                "command": _safe_text(item.get("command"), field="command", limit=500) or None,
                "source": _safe_text(item.get("source"), field="source", limit=120),
                "status": status,
                "reason": _safe_text(item.get("reason"), field="reason", limit=240),
                "exit_code": None,
                "artifact": None,
                "updated_at": _stamp(),
            }
        )
    path = quality_ledger_path(root, ticket)
    previous: dict[str, object] = {}
    if path.is_file():
        previous = read_ledger(root, ticket)
    previous_files = [str(item) for item in list(previous.get("changed_files") or [])]
    current_files = [str(item) for item in list(plan.get("changed_files") or [])[:80]]
    previous_git = previous.get("git") if isinstance(previous.get("git"), dict) else {}
    current_git = plan.get("git") if isinstance(plan.get("git"), dict) else {}
    retain_evidence = (
        str(previous.get("tier") or "ticket") == str(plan.get("tier") or "ticket")
        and previous_files == current_files
        and str(previous.get("surface_digest") or "") == str(plan.get("surface_digest") or "")
        and str(previous_git.get("head") or "unknown") == str(current_git.get("head") or "unknown")
    )
    previous_checks = {
        str(item.get("id")): item
        for item in previous.get("checks", [])
        if isinstance(item, dict)
    }
    for check in checks:
        old = previous_checks.get(str(check["id"]))
        # A reopened ticket retains evidence only when the exact gate remains
        # executable in the same way. New or changed gates start honestly.
        if retain_evidence and isinstance(old, dict) and old.get("command") == check.get("command"):
            for key in ("status", "exit_code", "artifact", "detail", "updated_at"):
                if key in old:
                    check[key] = old[key]
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "ticket": ticket,
        "risk": copy.deepcopy(plan.get("risk") if isinstance(plan.get("risk"), dict) else {}),
        "tier": str(plan.get("tier") or "ticket"),
        "changed_files": current_files,
        "ignored_changed_paths": [
            str(item) for item in list(plan.get("ignored_changed_paths") or [])[:40]
        ],
        "surface_digest": str(plan.get("surface_digest") or ""),
        "git": copy.deepcopy(plan.get("git") if isinstance(plan.get("git"), dict) else {}),
        "checks": checks,
        "created_at": previous.get("created_at") or _stamp(),
        "updated_at": _stamp(),
    }
    _atomic_write(path, payload)
    return path


def read_ledger(root: Path, ticket: str) -> dict[str, object]:
    payload = _read_json(quality_ledger_path(root, ticket))
    if payload.get("schema_version") != SCHEMA_VERSION or payload.get("ticket") != _safe_ticket(ticket):
        raise ValueError("unsupported quality ledger")
    checks = payload.get("checks")
    if not isinstance(checks, list):
        raise ValueError("quality ledger checks are missing")
    return payload


def _artifact_path(root: Path, artifact: str | None) -> str | None:
    if not artifact:
        return None
    candidate = Path(artifact)
    if candidate.is_absolute():
        raise ValueError("artifact must be relative to the project root")
    resolved_root = Path(root).resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        relative = resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("artifact must remain inside the project root") from exc
    if not resolved.is_file():
        raise ValueError("artifact file does not exist")
    return relative.as_posix()


def record_result(
    root: Path,
    ticket: str,
    check_id: str,
    *,
    status: str,
    command: str,
    exit_code: int | None,
    artifact: str | None = None,
    detail: str = "",
) -> dict[str, object]:
    if status not in STATUSES:
        raise ValueError(f"unsupported quality status: {status}")
    safe_command = _safe_text(command, field="command")
    if not safe_command:
        raise ValueError("command is required")
    if status == "passed" and exit_code != 0:
        raise ValueError("passed quality evidence requires exit_code=0")
    if status == "failed" and (not isinstance(exit_code, int) or exit_code == 0):
        raise ValueError("failed quality evidence requires a non-zero exit code")
    if exit_code is not None and not isinstance(exit_code, int):
        raise ValueError("exit_code must be an integer or null")
    payload = read_ledger(root, ticket)
    checks = payload.get("checks")
    assert isinstance(checks, list)
    check = next((item for item in checks if isinstance(item, dict) and item.get("id") == check_id), None)
    if not isinstance(check, dict):
        raise ValueError(f"quality check not found: {check_id}")
    expected = check.get("command")
    if expected is None and status == "passed":
        raise ValueError("quality check is not executable from the approved plan")
    if isinstance(expected, str) and expected and expected != safe_command:
        raise ValueError("recorded command does not match the quality plan")
    check.update(
        {
            "status": status,
            "command": safe_command,
            "exit_code": exit_code,
            "artifact": _artifact_path(root, artifact),
            "detail": _safe_text(detail, field="detail", limit=500),
            "updated_at": _stamp(),
        }
    )
    payload["updated_at"] = _stamp()
    _atomic_write(quality_ledger_path(root, ticket), payload)
    return payload


def quality_gate(root: Path, ticket: str) -> dict[str, object]:
    payload = read_ledger(root, ticket)
    checks = [item for item in payload.get("checks", []) if isinstance(item, dict)]
    required = [item for item in checks if bool(item.get("required"))]
    passed_count = sum(1 for item in required if item.get("status") == "passed")
    recorded_files = [str(item) for item in list(payload.get("changed_files") or [])]
    recorded_digest = str(payload.get("surface_digest") or "")
    current_files, _ignored_files = _changed_paths(Path(root).resolve())
    current_digest = _surface_digest(Path(root).resolve(), current_files)
    if recorded_digest and (recorded_files != current_files or recorded_digest != current_digest):
        return {
            "status": "blocked",
            "ticket": payload.get("ticket"),
            "risk": payload.get("risk") if isinstance(payload.get("risk"), dict) else {},
            "coverage": {"passed": passed_count, "required": len(required)},
            "last_problem": "changed-surface=drifted",
            "next_action": "refresh quality plan and rerun required gates",
            "checks": checks,
        }
    if not checks:
        return {
            "status": "blocked",
            "ticket": payload.get("ticket"),
            "risk": payload.get("risk") if isinstance(payload.get("risk"), dict) else {},
            "coverage": {"passed": 0, "required": 0},
            "last_problem": "no quality gate discovered",
            "next_action": "configure project-native quality gate",
            "checks": checks,
        }
    problem = next((item for item in required if item.get("status") == "failed"), None)
    if problem is None:
        problem = next((item for item in required if item.get("status") != "passed"), None)
    if problem is None:
        status, next_action, last_problem = "passed", "", ""
    else:
        check_id = str(problem.get("id") or "quality-check")
        state = str(problem.get("status") or "not-run")
        status = "blocked"
        next_action = f"fix {check_id}" if state == "failed" else f"run {check_id}"
        if state == "configured-not-verified":
            next_action = f"configure {check_id}"
        last_problem = f"{check_id}={state}"
    risk = payload.get("risk") if isinstance(payload.get("risk"), dict) else {}
    return {
        "status": status,
        "ticket": payload.get("ticket"),
        "risk": risk,
        "coverage": {"passed": passed_count, "required": len(required)},
        "last_problem": last_problem,
        "next_action": next_action,
        "checks": checks,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan", help="Discover existing quality gates without writing or running them")
    plan.add_argument("--cwd", default=".")
    plan.add_argument("--tier", choices=TIERS, default="ticket")
    plan.add_argument("--changed", action="append", default=[])
    init = subparsers.add_parser("init", help="Create or refresh one local evidence ledger without running gates")
    init.add_argument("--cwd", default=".")
    init.add_argument("--ticket", required=True)
    init.add_argument("--tier", choices=TIERS, default="ticket")
    init.add_argument("--changed", action="append", default=[])
    record = subparsers.add_parser("record", help="Record one explicitly executed quality gate")
    record.add_argument("--cwd", default=".")
    record.add_argument("--ticket", required=True)
    record.add_argument("--check", required=True)
    record.add_argument("--status", choices=STATUSES, required=True)
    record.add_argument("--command", dest="quality_command", required=True)
    record.add_argument("--exit-code", type=int)
    record.add_argument("--artifact")
    record.add_argument("--detail", default="")
    status = subparsers.add_parser("status", help="Read the deterministic gate decision for a ticket")
    status.add_argument("--cwd", default=".")
    status.add_argument("--ticket", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.cwd).resolve()
    try:
        if args.command == "plan":
            print(json.dumps(build_quality_plan(root, tier=args.tier, changed_files=args.changed or None), ensure_ascii=False, indent=2))
            return 0
        if args.command == "init":
            plan = build_quality_plan(root, tier=args.tier, changed_files=args.changed or None)
            write_ledger(root, args.ticket, plan)
            print(json.dumps(quality_gate(root, args.ticket), ensure_ascii=False, indent=2))
            return 0
        if args.command == "record":
            record_result(root, args.ticket, args.check, status=args.status, command=args.quality_command, exit_code=args.exit_code, artifact=args.artifact, detail=args.detail)
            print(json.dumps(quality_gate(root, args.ticket), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(quality_gate(root, args.ticket), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Offline, candidate-only Semgrep capability for the Professional Workbench."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import uuid
import venv
import zipfile
from email.parser import BytesParser
from pathlib import Path

SEMGREP_VERSION = "1.172.0"
SEMGREP_SHA256 = "e32868faeb67b241bbd3fabd82a12fba4b467464dedde9da285b9bf78e808ba3"
SEMGREP_WHEEL = (
    "semgrep-1.172.0-cp310.cp311.cp312.cp313.cp314."
    "py310.py311.py312.py313.py314-none-win_amd64.whl"
)
SEMGREP_URL = (
    "https://files.pythonhosted.org/packages/8d/2b/"
    "db00aa8b50d4a3172f7d1a90005d359875004cf840b50db4b8606845453b/"
    + SEMGREP_WHEEL
)
RULE_PACK = "workbench/semgrep/rules/1.0.0"
OWNER = "pala-project-studio"
EXTENSION_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".rs": "rust",
}
SKIP_DIRS = {
    ".git", ".codegraph", ".tools", ".venv", "__pycache__", "node_modules", "dist", "build",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_object(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=True, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _canonical_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()


def _wheel_identity(path: Path) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(path) as archive:
            metadata_names = [
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_names) != 1:
                raise ValueError("wheel must contain exactly one METADATA record")
            metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
    except (OSError, zipfile.BadZipFile, KeyError) as exc:
        raise ValueError(f"invalid wheel: {path.name}") from exc
    name = str(metadata.get("Name") or "").strip()
    version = str(metadata.get("Version") or "").strip()
    if not name or not version:
        raise ValueError(f"wheel identity is missing: {path.name}")
    return _canonical_name(name), version


def build_wheelhouse_manifest(
    wheelhouse: Path, *, expected_semgrep_sha: str = SEMGREP_SHA256
) -> dict[str, object]:
    """Verify a resolved wheelhouse and return a deterministic hash inventory."""
    root = Path(wheelhouse).resolve()
    wheels: list[dict[str, str]] = []
    seen: set[str] = set()
    for wheel in sorted(root.glob("*.whl"), key=lambda item: item.name.casefold()):
        name, version = _wheel_identity(wheel)
        if name in seen:
            raise ValueError(f"duplicate wheel distribution: {name}")
        seen.add(name)
        wheels.append(
            {
                "name": name,
                "version": version,
                "filename": wheel.name,
                "sha256": _sha256(wheel),
            }
        )
    semgrep = next((item for item in wheels if item["name"] == "semgrep"), None)
    if semgrep is None or semgrep["version"] != SEMGREP_VERSION:
        raise ValueError("wheelhouse does not contain exact Semgrep 1.172.0")
    if semgrep["sha256"] != expected_semgrep_sha.casefold():
        raise ValueError("Semgrep wheel SHA-256 mismatch")
    return {
        "schema": "pala.semgrep.wheelhouse.v1",
        "provider": "semgrep",
        "version": SEMGREP_VERSION,
        "platform": "win-amd64",
        "wheels": wheels,
    }


def render_requirements_lock(manifest: dict[str, object]) -> str:
    wheels = manifest.get("wheels")
    if not isinstance(wheels, list) or not wheels:
        raise ValueError("wheelhouse manifest has no wheels")
    lines = [
        f"{item['name']}=={item['version']} --hash=sha256:{item['sha256']}"
        for item in wheels
        if isinstance(item, dict)
    ]
    if len(lines) != len(wheels):
        raise ValueError("wheelhouse manifest contains an invalid record")
    return "\n".join(sorted(lines, key=str.casefold)) + "\n"


def verify_rule_pack(rule_pack: Path) -> dict[str, object]:
    root = Path(rule_pack).resolve()
    manifest = _read_object(root / "manifest.json")
    if manifest is None or manifest.get("schema") != "pala.semgrep.rules.v1":
        return {"status": "blocked", "reason": "manifest-missing"}
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return {"status": "blocked", "reason": "rules-missing"}
    rule_ids: list[str] = []
    problems: list[str] = []
    for item in files:
        if not isinstance(item, dict):
            problems.append("invalid-file-record")
            continue
        relative = str(item.get("path") or "")
        if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
            problems.append("unsafe-rule-path")
            continue
        path = root / relative
        if not path.is_file() or _sha256(path) != item.get("sha256"):
            problems.append(f"checksum:{relative}")
        ids = item.get("rule_ids")
        if isinstance(ids, list):
            rule_ids.extend(str(value) for value in ids)
    return {
        "status": "passed" if not problems and rule_ids else "blocked",
        "version": manifest.get("version"),
        "rule_count": len(set(rule_ids)),
        "rule_ids": sorted(set(rule_ids)),
        "problems": problems,
        "license": manifest.get("license"),
    }


def semgrep_environment(state_dir: Path) -> dict[str, str]:
    return {
        "SEMGREP_SEND_METRICS": "off",
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
        "SEMGREP_SETTINGS_FILE": str(Path(state_dir).resolve() / "settings.yml"),
        "OTEL_SDK_DISABLED": "true",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_INDEX": "1",
        "PYTHONNOUSERSITE": "1",
        "NO_COLOR": "1",
    }


def bounded_environment(
    state_dir: Path, base: dict[str, str] | None = None
) -> dict[str, str]:
    environment = dict(os.environ if base is None else base)
    for name in (
        "SEMGREP_APP_TOKEN",
        "SEMGREP_REPO_NAME",
        "SEMGREP_JOB_URL",
        "SEMGREP_BRANCH",
        "SEMGREP_REPO_URL",
    ):
        environment.pop(name, None)
    environment.update(semgrep_environment(state_dir))
    return environment


def build_scan_command(
    executable: Path, project: Path, rules: Path, output: Path
) -> tuple[str, ...]:
    return (
        str(Path(executable)),
        "scan",
        "--config",
        str(Path(rules)),
        "--metrics",
        "off",
        "--disable-version-check",
        "--no-rewrite-rule-ids",
        "--exclude",
        ".codegraph",
        "--exclude",
        ".venv",
        "--exclude",
        ".tools",
        "--exclude",
        "node_modules",
        "--error",
        "--json",
        "--output",
        str(Path(output)),
        str(Path(project).resolve()),
    )


def language_coverage(project: Path, covered_languages: set[str]) -> dict[str, object]:
    root = Path(project).resolve()
    languages: set[str] = set()
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        language = EXTENSION_LANGUAGES.get(path.suffix.casefold())
        if language:
            languages.add(language)
    uncovered = sorted(languages - set(covered_languages))
    return {
        "status": "passed" if languages and not uncovered else "configured-not-verified",
        "project_languages": sorted(languages),
        "rule_languages": sorted(covered_languages),
        "covered_languages": sorted(languages & set(covered_languages)),
        "uncovered_languages": uncovered,
        "authority": "coverage-observation",
    }


def evaluate_findings(
    payload: dict[str, object] | None,
    *,
    scan_exit_code: int,
    quality_check_id: str | None = None,
    quality_runner_status: str | None = None,
) -> dict[str, object]:
    results = payload.get("results", []) if isinstance(payload, dict) else []
    errors = payload.get("errors", []) if isinstance(payload, dict) else ["result-unavailable"]
    finding_count = len(results) if isinstance(results, list) else 0
    error_count = len(errors) if isinstance(errors, list) else 1
    mapped_failure = bool(quality_check_id and quality_runner_status == "failed")
    return {
        "status": "blocked" if error_count else "passed",
        "scan_exit_code": scan_exit_code,
        "finding_count": finding_count,
        "error_count": error_count,
        "candidate_only": not mapped_failure,
        "blocks_acceptance": mapped_failure,
        "quality_check_id": quality_check_id,
        "authority": "Pala Quality Engine" if mapped_failure else "advisory-candidates",
    }


def run_local_scan(
    project: Path,
    state_root: Path,
    *,
    timeout_seconds: int = 300,
) -> dict[str, object]:
    runtime = inventory(state_root)
    if runtime.get("state") != "exact":
        return {
            "status": "blocked",
            "capability_health": runtime,
            "coverage": "not-run",
            "findings": "not-run",
        }
    target = Path(str(runtime["path"]))
    rules = target / "rules" / "pala-minimal.yml"
    rule_status = verify_rule_pack(target / "rules")
    if rule_status.get("status") != "passed":
        return {
            "status": "blocked",
            "capability_health": runtime,
            "coverage": "not-run",
            "findings": "not-run",
            "reason": "rule-pack-integrity",
        }
    manifest = _read_object(target / "rules" / "manifest.json") or {}
    languages: set[str] = set()
    for item in manifest.get("files", []):
        if isinstance(item, dict) and isinstance(item.get("languages"), list):
            languages.update(str(value) for value in item["languages"])
    coverage = language_coverage(project, languages)
    result_path = target / "results" / "latest.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    command = build_scan_command(
        Path(str(runtime["executable"])), project, rules, result_path
    )
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=bounded_environment(target / "state"),
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "status": "blocked",
            "capability_health": runtime,
            "coverage": coverage,
            "findings": "not-run",
            "reason": type(exc).__name__,
        }
    payload = _read_object(result_path)
    findings = evaluate_findings(payload, scan_exit_code=completed.returncode)
    check_ids = sorted(
        {
            str(item.get("check_id"))
            for item in (payload.get("results", []) if isinstance(payload, dict) else [])
            if isinstance(item, dict) and item.get("check_id")
        }
    )
    return {
        "status": "passed" if findings["error_count"] == 0 else "blocked",
        "capability_health": runtime,
        "coverage": coverage,
        "findings": findings,
        "candidate_check_ids": check_ids,
        "output_location": "Pala-owned-external-state",
        "network": "disabled",
        "metrics": "off",
    }


def _base_paths(state_root: Path) -> tuple[Path, Path, Path]:
    base = Path(state_root).resolve() / "workbench" / "security_static"
    return base, base / "versions" / SEMGREP_VERSION, base / "active.json"


def inventory(state_root: Path) -> dict[str, object]:
    base, target, active_path = _base_paths(state_root)
    active = _read_object(active_path)
    if active is None:
        return {"state": "foreign" if target.exists() else "absent", "health": "not-run"}
    if active.get("owner") != OWNER:
        return {"state": "foreign", "health": "blocked"}
    if active.get("version") != SEMGREP_VERSION:
        return {"state": "old", "version": active.get("version"), "health": "not-run"}
    marker = _read_object(target / "pala-install.json")
    executable = target / "venv" / "Scripts" / "semgrep.exe"
    if (
        marker is None
        or marker.get("owner") != OWNER
        or marker.get("semgrep_sha256") != SEMGREP_SHA256
        or marker.get("health") != "passed"
        or not executable.is_file()
    ):
        return {"state": "foreign", "version": SEMGREP_VERSION, "health": "blocked"}
    return {
        "state": "exact",
        "version": SEMGREP_VERSION,
        "health": "passed",
        "integrity": f"sha256:{SEMGREP_SHA256}",
        "ownership": OWNER,
        "provenance": SEMGREP_URL,
        "path": str(target),
        "executable": str(executable),
    }


def probe_health(state_root: Path) -> dict[str, object]:
    runtime = inventory(state_root)
    if runtime.get("state") != "exact":
        return {"status": "blocked", "state": runtime.get("state"), "version": "unknown"}
    target = Path(str(runtime["path"]))
    try:
        completed = subprocess.run(
            (str(runtime["executable"]), "--version"),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=bounded_environment(target / "state"),
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "blocked", "state": "exact", "version": "unknown", "reason": type(exc).__name__}
    observed = (completed.stdout or completed.stderr).strip().splitlines()
    version = observed[0].strip().lstrip("v") if observed else "unknown"
    return {
        "status": "passed" if completed.returncode == 0 and version == SEMGREP_VERSION else "blocked",
        "state": "exact",
        "version": version,
        "exit_code": completed.returncode,
        "integrity": runtime["integrity"],
        "ownership": runtime["ownership"],
        "provenance": runtime["provenance"],
    }


def install_transaction(
    wheelhouse: Path,
    state_root: Path,
    rule_pack: Path,
    requirements_lock: Path,
    *,
    run=None,
    create_venv=None,
    repair: bool = False,
) -> dict[str, object]:
    """Install only a fully resolved local wheelhouse; pip is hard-offline."""
    current = inventory(state_root)
    if current["state"] == "exact" and not repair:
        return {**current, "changed": False}
    if current["state"] == "foreign":
        return {**current, "changed": False, "reason": "foreign-active-runtime-preserved"}
    base, target, active_path = _base_paths(state_root)
    backup: Path | None = None
    if target.exists():
        if repair and current.get("state") == "exact":
            backup = target.with_name(f".{target.name}.rollback-{uuid.uuid4().hex}")
            os.replace(target, backup)
        else:
            return {"state": "foreign", "health": "blocked", "changed": False}
    manifest = build_wheelhouse_manifest(wheelhouse)
    lock = render_requirements_lock(manifest)
    expected_lock = Path(requirements_lock).read_text(encoding="utf-8")
    if lock != expected_lock:
        raise ValueError("Semgrep wheelhouse does not match the Pala hash lock")
    rules = verify_rule_pack(rule_pack)
    if rules.get("status") != "passed":
        raise ValueError("Semgrep local rule pack failed integrity verification")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{SEMGREP_VERSION}.stage-", dir=target.parent))
    previous_active = active_path.read_bytes() if active_path.is_file() else None
    version_staged = False
    try:
        staged_wheels = stage / "wheelhouse"
        shutil.copytree(Path(wheelhouse).resolve(), staged_wheels)
        (stage / "requirements.lock").write_text(lock, encoding="utf-8", newline="\n")
        _atomic_json(stage / "wheelhouse-manifest.json", manifest)
        shutil.copytree(Path(rule_pack).resolve(), stage / "rules")
        _atomic_json(
            stage / "pala-staging.json",
            {"owner": OWNER, "provider": "semgrep", "version": SEMGREP_VERSION},
        )
        os.replace(stage, target)
        version_staged = True
        venv_builder = create_venv or (lambda path: venv.EnvBuilder(with_pip=True).create(path))
        venv_builder(target / "venv")
        python = target / "venv" / "Scripts" / "python.exe"
        command = (
            str(python), "-m", "pip", "install", "--no-index", "--only-binary", ":all:",
            "--find-links", str(target / "wheelhouse"), "--require-hashes", "-r",
            str(target / "requirements.lock"),
        )
        environment = bounded_environment(target / "state")
        (target / "state").mkdir(parents=True, exist_ok=True)
        execute = run or (
            lambda argv, env, timeout: subprocess.run(
                argv, check=False, capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=env, timeout=timeout
            )
        )
        installed = execute(command, environment, 900)
        if int(installed.returncode) != 0:
            raise RuntimeError("Semgrep isolated wheelhouse installation failed")
        executable = target / "venv" / "Scripts" / "semgrep.exe"
        health = execute((str(executable), "--version"), environment, 60)
        observed = (health.stdout or health.stderr).strip().splitlines()[0].strip().lstrip("v")
        if int(health.returncode) != 0 or observed != SEMGREP_VERSION:
            raise RuntimeError("Semgrep isolated health probe failed")
        _atomic_json(
            target / "pala-install.json",
            {
                "owner": OWNER,
                "provider": "semgrep",
                "version": SEMGREP_VERSION,
                "semgrep_sha256": SEMGREP_SHA256,
                "wheel_count": len(manifest["wheels"]),
                "rule_pack_version": rules["version"],
                "rule_ids": rules["rule_ids"],
                "health": "passed",
                "network_policy": "no-index-local-wheelhouse",
                "metrics": "off",
            },
        )
        (target / "pala-staging.json").unlink(missing_ok=True)
        _atomic_json(
            active_path,
            {"owner": OWNER, "provider": "semgrep", "version": SEMGREP_VERSION, "path": str(target)},
        )
        if backup is not None and backup.exists():
            shutil.rmtree(backup)
    except Exception:
        if version_staged and target.exists():
            shutil.rmtree(target)
        if backup is not None and backup.exists():
            os.replace(backup, target)
        if previous_active is None:
            active_path.unlink(missing_ok=True)
        elif not active_path.is_file() or active_path.read_bytes() != previous_active:
            restore = active_path.with_name(f".{active_path.name}.restore")
            restore.write_bytes(previous_active)
            os.replace(restore, active_path)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {**inventory(state_root), "changed": True}

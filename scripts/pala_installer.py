#!/usr/bin/env python3
"""Idempotent, atomic installer core for Pala Project Studio."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1
OWNER = "pala-project-studio"
STATE_NAME = "install-state.json"
REQUIRED_FILES = (
    Path(".codex-plugin/plugin.json"),
    Path("scripts/pala_state.py"),
    Path("scripts/pala_hook.py"),
    Path("hooks/hooks.json"),
    Path("skills/pala-project-finisher/SKILL.md"),
)
PACKAGE_DIRECTORIES = (".codex-plugin", "hooks", "scripts", "skills")
PACKAGE_FILES = (
    "LICENSE",
    "OPEN_SOURCE.md",
    "THIRD_PARTY_NOTICES.md",
)
FORBIDDEN_PARTS = {".git", ".codex", "__pycache__", ".pytest_cache", ".ruff_cache"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".pem", ".key"}


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def read_json(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def safe_source_file(relative: Path) -> bool:
    lowered = {part.casefold() for part in relative.parts}
    if lowered.intersection(FORBIDDEN_PARTS):
        return False
    if relative.name.casefold().endswith(tuple(FORBIDDEN_SUFFIXES)):
        return False
    if any(
        part.casefold() == ".env" or part.casefold().startswith(".env.")
        for part in relative.parts
    ):
        return False
    return True


def bundle_files(source: Path) -> list[Path]:
    source = source.resolve()
    candidates: list[Path] = []
    for name in PACKAGE_FILES:
        path = source / name
        if path.is_file():
            candidates.append(path)
    for name in PACKAGE_DIRECTORIES:
        directory = source / name
        if directory.is_dir():
            candidates.extend(path for path in directory.rglob("*") if path.is_file())
    result = []
    for path in candidates:
        if path.is_symlink():
            raise ValueError(f"symbolic links are not installable: {path}")
        relative = path.relative_to(source)
        if safe_source_file(relative):
            result.append(path)
    return sorted(set(result), key=lambda item: item.relative_to(source).as_posix().casefold())


def manifest(source: Path) -> dict[str, object]:
    path = source / ".codex-plugin" / "plugin.json"
    value = read_json(path)
    if value is None:
        raise ValueError(f"invalid plugin manifest: {path}")
    if value.get("name") != OWNER:
        raise ValueError("plugin manifest name does not match Pala")
    version = value.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("plugin manifest version is missing")
    return value


def validate_bundle(source: Path) -> dict[str, object]:
    source = source.resolve()
    for relative in REQUIRED_FILES:
        if not (source / relative).is_file():
            raise FileNotFoundError(f"required plugin file is missing: {relative}")
    value = manifest(source)
    files = bundle_files(source)
    if not files:
        raise ValueError("plugin bundle is empty")
    for path in files:
        if path.suffix.casefold() == ".py":
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
    return value


def tree_fingerprint(root: Path) -> str:
    root = root.resolve()
    digest = hashlib.sha256()
    files = sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda item: item.relative_to(root).as_posix().casefold(),
    )
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest().upper()


def bundle_fingerprint(source: Path) -> str:
    source = source.resolve()
    digest = hashlib.sha256()
    for path in bundle_files(source):
        relative = path.relative_to(source).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest().upper()


def copy_bundle(source: Path, destination: Path) -> None:
    source = source.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    for path in bundle_files(source):
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def state_path(state_root: Path) -> Path:
    return state_root / STATE_NAME


def owned_state(install_root: Path, state_root: Path) -> dict[str, object] | None:
    payload = read_json(state_path(state_root))
    if payload is None or payload.get("schema_version") != SCHEMA_VERSION:
        return None
    if payload.get("owner") != OWNER:
        return None
    recorded = payload.get("install_root")
    if not isinstance(recorded, str):
        return None
    try:
        matches = Path(recorded).resolve() == install_root.resolve()
    except OSError:
        return None
    return payload if matches else None


def plugin_status(source: Path, install_root: Path, state_root: Path) -> dict[str, object]:
    source_manifest = validate_bundle(source)
    state = owned_state(install_root, state_root)
    if not install_root.exists():
        return {
            "status": "missing",
            "expected_version": source_manifest["version"],
            "installed_version": None,
        }
    if not install_root.is_dir():
        return {
            "status": "external_conflict",
            "expected_version": source_manifest["version"],
            "installed_version": None,
        }
    if state is None:
        try:
            installed_manifest = validate_bundle(install_root)
        except (OSError, ValueError):
            return {
                "status": "external_conflict",
                "expected_version": source_manifest["version"],
                "installed_version": None,
            }
        return {
            "status": "legacy_pala",
            "expected_version": source_manifest["version"],
            "installed_version": installed_manifest["version"],
        }
    installed_manifest = read_json(install_root / ".codex-plugin" / "plugin.json")
    installed_version = (
        installed_manifest.get("version") if isinstance(installed_manifest, dict) else None
    )
    actual = tree_fingerprint(install_root)
    expected = bundle_fingerprint(source)
    if actual == expected:
        status = "ready"
    elif installed_version != source_manifest["version"]:
        status = "outdated"
    else:
        status = "drifted"
    return {
        "status": status,
        "expected_version": source_manifest["version"],
        "installed_version": installed_version,
        "expected_fingerprint": expected,
        "actual_fingerprint": actual,
        "recorded_fingerprint": state.get("fingerprint"),
    }


def doctor_bundle(source: Path, install_root: Path, state_root: Path) -> dict[str, object]:
    plugin = plugin_status(source, install_root, state_root)
    return {
        "schema_version": SCHEMA_VERSION,
        "healthy": plugin["status"] == "ready",
        "plugin": plugin,
        "state_file": str(state_path(state_root).resolve()),
    }


def install_bundle(
    source: Path,
    install_root: Path,
    state_root: Path,
    *,
    dry_run: bool = False,
    repair: bool = False,
) -> dict[str, object]:
    source = source.resolve()
    install_root = install_root.resolve()
    state_root = state_root.resolve()
    source_manifest = validate_bundle(source)
    if source == install_root or source in install_root.parents:
        raise ValueError("installation target must be outside the source bundle")

    current = plugin_status(source, install_root, state_root)
    current_status = str(current["status"])
    if current_status == "ready":
        return {"status": "ready", "changed": False, "version": source_manifest["version"]}
    if current_status == "external_conflict":
        return {
            "status": "external_conflict",
            "changed": False,
            "version": source_manifest["version"],
        }
    if dry_run:
        action = "repair" if repair or current_status == "drifted" else "install"
        if current_status in {"outdated", "legacy_pala"}:
            action = "update"
        return {
            "status": f"would_{action}",
            "changed": False,
            "version": source_manifest["version"],
        }

    install_root.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(prefix=f".{OWNER}.stage-", dir=install_root.parent)
    )
    backup = install_root.parent / f".{OWNER}.rollback-{uuid.uuid4().hex}"
    moved_previous = False
    activated = False
    try:
        shutil.rmtree(stage)
        copy_bundle(source, stage)
        validate_bundle(stage)
        if tree_fingerprint(stage) != bundle_fingerprint(source):
            raise RuntimeError("staged plugin fingerprint does not match source")

        if install_root.exists():
            os.replace(install_root, backup)
            moved_previous = True
        os.replace(stage, install_root)
        activated = True
        installed_fingerprint = tree_fingerprint(install_root)
        payload: dict[str, object] = {
            "schema_version": SCHEMA_VERSION,
            "owner": OWNER,
            "install_root": str(install_root),
            "version": source_manifest["version"],
            "fingerprint": installed_fingerprint,
            "installed_at": now_utc(),
        }
        atomic_write_json(state_path(state_root), payload)
        if moved_previous and backup.exists():
            shutil.rmtree(backup)
    except Exception:
        if activated and install_root.exists():
            shutil.rmtree(install_root)
        if moved_previous and backup.exists():
            os.replace(backup, install_root)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)

    if repair or current_status == "drifted":
        result_status = "repaired"
    elif current_status == "legacy_pala":
        result_status = "migrated"
    elif current_status == "outdated":
        result_status = "updated"
    else:
        result_status = "installed"
    return {
        "status": result_status,
        "changed": True,
        "version": source_manifest["version"],
        "fingerprint": tree_fingerprint(install_root),
    }


def uninstall_bundle(
    install_root: Path, state_root: Path, *, dry_run: bool = False
) -> dict[str, object]:
    install_root = install_root.resolve()
    state_root = state_root.resolve()
    if not install_root.exists():
        return {"status": "absent", "changed": False}
    state = owned_state(install_root, state_root)
    if state is None:
        return {"status": "external_conflict", "changed": False}
    actual = tree_fingerprint(install_root)
    if state.get("fingerprint") != actual:
        return {"status": "modified", "changed": False}
    if dry_run:
        return {"status": "would_uninstall", "changed": False}

    trash = install_root.parent / f".{OWNER}.uninstall-{uuid.uuid4().hex}"
    os.replace(install_root, trash)
    try:
        shutil.rmtree(trash)
        state_path(state_root).unlink(missing_ok=True)
    except Exception:
        if trash.exists() and not install_root.exists():
            os.replace(trash, install_root)
        raise
    return {"status": "uninstalled", "changed": True}


def default_paths() -> tuple[Path, Path, Path]:
    source = Path(__file__).resolve().parent.parent
    profile = Path(os.environ.get("USERPROFILE", Path.home()))
    local_app_data = Path(os.environ.get("LOCALAPPDATA", profile / "AppData" / "Local"))
    return source, profile / "plugins" / OWNER, local_app_data / "Pala"


def parser() -> argparse.ArgumentParser:
    source, install_root, state_root = default_paths()
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("mode", choices=("install", "doctor", "repair", "update", "uninstall"))
    result.add_argument("--source", type=Path, default=source)
    result.add_argument("--install-root", type=Path, default=install_root)
    result.add_argument("--state-root", type=Path, default=state_root)
    result.add_argument("--dry-run", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.mode == "doctor":
            report = doctor_bundle(args.source, args.install_root, args.state_root)
        elif args.mode == "uninstall":
            report = uninstall_bundle(
                args.install_root, args.state_root, dry_run=args.dry_run
            )
        else:
            report = install_bundle(
                args.source,
                args.install_root,
                args.state_root,
                dry_run=args.dry_run,
                repair=args.mode == "repair",
            )
    except (OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report.get("status") in {"external_conflict", "modified"}:
        return 2
    if args.mode == "doctor" and not report.get("healthy"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

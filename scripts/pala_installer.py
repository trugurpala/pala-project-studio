#!/usr/bin/env python3
"""Idempotent, atomic installer core for Pala Project Studio."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1
OWNER = "pala-project-studio"
PLUGIN_ID = f"{OWNER}@{OWNER}"
STATE_NAME = "install-state.json"
REQUIRED_FILES = (
    Path(".agents/plugins/marketplace.json"),
    Path(".codex-plugin/plugin.json"),
    Path("scripts/pala_state.py"),
    Path("scripts/pala_hook.py"),
    Path("hooks/hooks.json"),
    Path("skills/pala-project-finisher/SKILL.md"),
)
PACKAGE_DIRECTORIES = (".agents", ".codex-plugin", "hooks", "scripts", "skills")
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


def run_codex_json(arguments: list[str]) -> dict[str, object]:
    executable = shutil.which("codex")
    if executable is None:
        raise RuntimeError("Codex CLI is not available on PATH")
    try:
        completed = subprocess.run(
            [executable, *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("Codex CLI timed out") from error
    if completed.returncode != 0:
        label = " ".join(arguments[:3])
        raise RuntimeError(
            f"Codex CLI command failed with exit {completed.returncode}: {label}"
        )
    try:
        payload = json.loads(completed.stdout)
    except ValueError as error:
        raise RuntimeError("Codex CLI returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError("Codex CLI JSON root is not an object")
    return payload


def comparable_path(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.removeprefix("\\\\?\\")
    try:
        return str(Path(normalized).resolve()).casefold()
    except OSError:
        return os.path.normcase(os.path.abspath(normalized))


def codex_status(
    install_root: Path,
    expected_version: str,
    *,
    invoke=run_codex_json,
) -> dict[str, object]:
    try:
        marketplace_payload = invoke(
            ["plugin", "marketplace", "list", "--json"]
        )
        plugin_payload = invoke(["plugin", "list", "--json"])
    except RuntimeError as error:
        return {
            "status": "unavailable",
            "healthy": False,
            "error": str(error),
        }

    marketplaces = marketplace_payload.get("marketplaces", [])
    installed = plugin_payload.get("installed", [])
    if not isinstance(marketplaces, list) or not isinstance(installed, list):
        return {
            "status": "unavailable",
            "healthy": False,
            "error": "Codex CLI inventory has an invalid shape",
        }

    expected_root = comparable_path(str(install_root))
    named_marketplaces = [
        entry
        for entry in marketplaces
        if isinstance(entry, dict) and entry.get("name") == OWNER
    ]
    marketplace = named_marketplaces[0] if named_marketplaces else None
    if marketplace is not None and comparable_path(marketplace.get("root")) != expected_root:
        return {
            "status": "external_conflict",
            "healthy": False,
            "marketplace_root": marketplace.get("root"),
        }

    target = next(
        (
            entry
            for entry in installed
            if isinstance(entry, dict) and entry.get("pluginId") == PLUGIN_ID
        ),
        None,
    )
    duplicates = [
        str(entry.get("pluginId"))
        for entry in installed
        if isinstance(entry, dict)
        and entry.get("name") == OWNER
        and entry.get("pluginId") != PLUGIN_ID
    ]
    if duplicates:
        return {
            "status": "external_conflict",
            "healthy": False,
            "conflicting_plugins": duplicates,
        }
    if marketplace is None:
        status = "missing"
    elif target is None:
        status = "missing"
    elif target.get("version") != expected_version or not target.get("enabled"):
        status = "outdated"
    else:
        status = "ready"
    return {
        "status": status,
        "healthy": status == "ready",
        "marketplace_registered": marketplace is not None,
        "marketplace_root": marketplace.get("root") if marketplace else None,
        "plugin_id": target.get("pluginId") if target else None,
        "installed_version": target.get("version") if target else None,
        "expected_version": expected_version,
        "enabled": bool(target and target.get("enabled")),
    }


def ensure_codex_install(
    install_root: Path,
    expected_version: str,
    *,
    dry_run: bool = False,
    invoke=run_codex_json,
) -> dict[str, object]:
    install_root = install_root.resolve()
    before = codex_status(install_root, expected_version, invoke=invoke)
    status = str(before["status"])
    if status == "ready":
        return {**before, "changed": False}
    if status in {"external_conflict", "unavailable"}:
        return {**before, "changed": False}
    if dry_run:
        action = "update" if status == "outdated" else "install"
        return {**before, "status": f"would_{action}", "changed": False}

    marketplace_added = False
    try:
        if not before.get("marketplace_registered"):
            invoke(
                [
                    "plugin",
                    "marketplace",
                    "add",
                    str(install_root),
                    "--json",
                ]
            )
            marketplace_added = True
        invoke(["plugin", "add", PLUGIN_ID, "--json"])
        after = codex_status(install_root, expected_version, invoke=invoke)
        if after.get("status") != "ready":
            raise RuntimeError("Codex did not report Pala as installed and enabled")
    except Exception:
        if marketplace_added:
            try:
                invoke(["plugin", "marketplace", "remove", OWNER, "--json"])
            except Exception:
                pass
        raise
    result_status = "updated" if status == "outdated" else "installed"
    return {**after, "status": result_status, "changed": True}


def remove_codex_install(
    install_root: Path,
    expected_version: str,
    *,
    dry_run: bool = False,
    invoke=run_codex_json,
) -> dict[str, object]:
    before = codex_status(install_root, expected_version, invoke=invoke)
    status = str(before["status"])
    if status in {"external_conflict", "unavailable"}:
        return {**before, "changed": False}
    present = bool(before.get("marketplace_registered") or before.get("plugin_id"))
    if not present:
        return {**before, "status": "absent", "changed": False}
    if dry_run:
        return {**before, "status": "would_uninstall", "changed": False}

    if before.get("plugin_id") == PLUGIN_ID:
        invoke(["plugin", "remove", PLUGIN_ID, "--json"])
    if before.get("marketplace_registered"):
        invoke(["plugin", "marketplace", "remove", OWNER, "--json"])
    return {**before, "status": "uninstalled", "healthy": True, "changed": True}


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


def remove_tree_resilient(path: Path, *, required: bool = True) -> bool:
    """Remove an owned tree even if another owner cleanup is racing us."""
    target = path
    if os.name == "nt":
        resolved = str(path.resolve())
        if not resolved.startswith("\\\\?\\"):
            target = Path(f"\\\\?\\{resolved}")
    for _ in range(100):
        if not target.exists():
            return True
        try:
            shutil.rmtree(target, ignore_errors=True)
        except FileNotFoundError:
            pass
        if not target.exists():
            return True
        time.sleep(0.05)
    if target.exists() and required:
        raise OSError(f"Pala-owned directory could not be removed: {path}")
    return not target.exists()


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


def project_doctor(install_root: Path, project_root: Path) -> dict[str, object]:
    script = install_root / "scripts" / "pala_state.py"
    if not script.is_file():
        return {
            "available": False,
            "project_root": str(project_root.resolve()),
            "error": "Pala project doctor is not installed",
        }
    try:
        completed = subprocess.run(
            [sys.executable, str(script), "doctor", "--cwd", str(project_root)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        return {
            "available": False,
            "project_root": str(project_root.resolve()),
            "error": "Pala project doctor timed out",
        }
    try:
        payload = json.loads(completed.stdout)
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        return {
            "available": False,
            "project_root": str(project_root.resolve()),
            "error": "Pala project doctor returned invalid JSON",
        }
    payload["available"] = completed.returncode == 0
    return payload


def doctor_installation(
    source: Path,
    install_root: Path,
    state_root: Path,
    project_root: Path,
    *,
    invoke=run_codex_json,
) -> dict[str, object]:
    bundle = doctor_bundle(source, install_root, state_root)
    expected_version = str(manifest(source)["version"])
    codex = codex_status(install_root, expected_version, invoke=invoke)
    python_ready = sys.version_info >= (3, 10)
    git_path = shutil.which("git")
    codex_path = shutil.which("codex")
    project = project_doctor(install_root, project_root)
    healthy = bool(
        bundle["healthy"]
        and codex.get("healthy")
        and python_ready
        and git_path
        and codex_path
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "healthy": healthy,
        "status": "ready" if healthy else "attention_required",
        "plugin": bundle["plugin"],
        "codex": codex,
        "python": {
            "ready": python_ready,
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "executable": sys.executable,
        },
        "git": {"ready": bool(git_path), "executable": git_path},
        "codex_cli": {"ready": bool(codex_path), "executable": codex_path},
        "project": project,
        "state_file": bundle["state_file"],
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
            remove_tree_resilient(backup)
    except Exception:
        if activated and install_root.exists():
            remove_tree_resilient(install_root)
        if moved_previous and backup.exists():
            os.replace(backup, install_root)
        raise
    finally:
        if stage.exists():
            remove_tree_resilient(stage)

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


def install_all(
    source: Path,
    install_root: Path,
    state_root: Path,
    *,
    dry_run: bool = False,
    repair: bool = False,
    invoke=run_codex_json,
) -> dict[str, object]:
    expected_version = str(manifest(source)["version"])
    codex_before = codex_status(install_root, expected_version, invoke=invoke)
    if codex_before.get("status") in {"external_conflict", "unavailable"}:
        return {
            "status": codex_before["status"],
            "changed": False,
            "codex": codex_before,
        }

    bundle = install_bundle(
        source,
        install_root,
        state_root,
        dry_run=dry_run,
        repair=repair,
    )
    if bundle.get("status") in {"external_conflict", "modified"}:
        return {**bundle, "bundle": bundle, "codex": codex_before}
    codex = ensure_codex_install(
        install_root,
        expected_version,
        dry_run=dry_run,
        invoke=invoke,
    )
    if codex.get("status") in {"external_conflict", "unavailable"}:
        return {
            "status": codex["status"],
            "changed": bool(bundle.get("changed")),
            "bundle": bundle,
            "codex": codex,
        }
    changed = bool(bundle.get("changed") or codex.get("changed"))
    if dry_run:
        statuses = {str(bundle.get("status")), str(codex.get("status"))}
        status = "would_update" if "would_update" in statuses else "would_install"
        if "would_repair" in statuses:
            status = "would_repair"
    elif not changed:
        status = "ready"
    elif repair or bundle.get("status") == "repaired":
        status = "repaired"
    elif "updated" in {bundle.get("status"), codex.get("status")}:
        status = "updated"
    elif bundle.get("status") == "migrated":
        status = "migrated"
    else:
        status = "installed"
    return {
        "status": status,
        "changed": changed,
        "version": expected_version,
        "bundle": bundle,
        "codex": codex,
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
        remove_tree_resilient(trash)
        state_path(state_root).unlink(missing_ok=True)
    except Exception:
        if trash.exists() and not install_root.exists():
            os.replace(trash, install_root)
        raise
    return {"status": "uninstalled", "changed": True}


def finalize_verified_uninstall(
    install_root: Path, state_root: Path
) -> dict[str, object]:
    """Remove a previously verified Pala-owned root after Codex cleanup."""
    install_root = install_root.resolve()
    state_root = state_root.resolve()
    state = owned_state(install_root, state_root)
    if state is None:
        return {"status": "external_conflict", "changed": False}
    if install_root.exists():
        trash = install_root.parent / f".{OWNER}.uninstall-{uuid.uuid4().hex}"
        os.replace(install_root, trash)
        cleaned = remove_tree_resilient(trash, required=False)
    else:
        trash = None
        cleaned = True
    state_path(state_root).unlink(missing_ok=True)
    return {
        "status": "uninstalled",
        "changed": True,
        "cleanup_pending": str(trash) if trash is not None and not cleaned else None,
    }


def uninstall_all(
    source: Path,
    install_root: Path,
    state_root: Path,
    *,
    dry_run: bool = False,
    invoke=run_codex_json,
) -> dict[str, object]:
    expected_version = str(manifest(source)["version"])
    bundle_preview = uninstall_bundle(install_root, state_root, dry_run=True)
    if bundle_preview.get("status") in {"external_conflict", "modified"}:
        return {**bundle_preview, "bundle": bundle_preview}
    codex = remove_codex_install(
        install_root,
        expected_version,
        dry_run=dry_run,
        invoke=invoke,
    )
    if codex.get("status") in {"external_conflict", "unavailable"}:
        return {
            "status": codex["status"],
            "changed": False,
            "bundle": bundle_preview,
            "codex": codex,
        }
    if dry_run:
        bundle = bundle_preview
    elif bundle_preview.get("status") == "would_uninstall":
        bundle = finalize_verified_uninstall(install_root, state_root)
    else:
        bundle = uninstall_bundle(install_root, state_root, dry_run=False)
    changed = bool(bundle.get("changed") or codex.get("changed"))
    if dry_run and (bundle.get("status") == "would_uninstall" or codex.get("status") == "would_uninstall"):
        status = "would_uninstall"
    elif changed:
        status = "uninstalled"
    else:
        status = "absent"
    return {"status": status, "changed": changed, "bundle": bundle, "codex": codex}


def default_paths() -> tuple[Path, Path, Path]:
    source = Path(__file__).resolve().parent.parent
    profile = Path(os.environ.get("USERPROFILE", Path.home()))
    local_app_data = Path(os.environ.get("LOCALAPPDATA", profile / "AppData" / "Local"))
    state_root = local_app_data / "Pala"
    return source, state_root / "marketplace", state_root


def parser() -> argparse.ArgumentParser:
    source, install_root, state_root = default_paths()
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("mode", choices=("install", "doctor", "repair", "update", "uninstall"))
    result.add_argument("--source", type=Path, default=source)
    result.add_argument("--install-root", type=Path, default=install_root)
    result.add_argument("--state-root", type=Path, default=state_root)
    result.add_argument("--project-root", type=Path, default=Path.cwd())
    result.add_argument("--dry-run", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.mode == "doctor":
            report = doctor_installation(
                args.source,
                args.install_root,
                args.state_root,
                args.project_root,
            )
        elif args.mode == "uninstall":
            report = uninstall_all(
                args.source,
                args.install_root,
                args.state_root,
                dry_run=args.dry_run,
            )
        else:
            report = install_all(
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
    if report.get("status") in {
        "attention_required",
        "external_conflict",
        "modified",
        "unavailable",
    }:
        return 2
    if args.mode == "doctor" and not report.get("healthy"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

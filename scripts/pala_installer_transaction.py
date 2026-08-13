#!/usr/bin/env python3
"""Atomic installation, rollback, and uninstall transaction responsibilities."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from pala_installer_integrity import bundle_files
from pala_installer_shared import *

INSTALLATION_STATES = frozenset(
    {"ABSENT", "CURRENT", "OLD", "STALE", "FOREIGN", "OFFLINE", "BROKEN"}
)


def classify_installation_state(
    bundle: dict[str, object],
    codex: dict[str, object],
    workbench: dict[str, object],
) -> str:
    """Classify all required dimensions; version equality alone is never CURRENT."""
    if codex.get("status") == "unavailable":
        return "OFFLINE"
    if codex.get("status") == "external_conflict" or bundle.get("status") in {
        "external_conflict",
        "modified",
    } or workbench.get("state") == "FOREIGN":
        return "FOREIGN"
    if bundle.get("status") == "outdated" or codex.get("status") == "outdated" or workbench.get("state") == "OLD":
        return "OLD"
    if bundle.get("status") == "drifted" or codex.get("cache_stale") or workbench.get("state") == "STALE":
        return "STALE"
    if bundle.get("status") in {"missing", "legacy_pala"} or codex.get("status") == "missing" or workbench.get("state") == "ABSENT":
        return "ABSENT"
    if (
        bundle.get("status") == "ready"
        and codex.get("status") == "ready"
        and workbench.get("status") == "ready"
        and workbench.get("healthy") is True
    ):
        return "CURRENT"
    return "BROKEN"

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

def install_bundle_transaction(
    source: Path,
    install_root: Path,
    state_root: Path,
    *,
    dry_run: bool = False,
    repair: bool = False,
    operations: dict[str, object],
) -> dict[str, object]:
    validate_bundle = operations["validate_bundle"]
    plugin_status = operations["plugin_status"]
    tree_fingerprint = operations["tree_fingerprint"]
    bundle_fingerprint = operations["bundle_fingerprint"]
    bundle_file_hashes = operations["bundle_file_hashes"]
    state_path = operations["state_path"]
    atomic_write_json = operations["atomic_write_json"]
    remove_tree_resilient = operations["remove_tree_resilient"]
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
    if current_status == "modified":
        return {
            "status": "modified",
            "changed": False,
            "version": source_manifest["version"],
        }
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
            "file_hashes": bundle_file_hashes(install_root),
            "source": OFFICIAL_REPOSITORY,
            "license": "MIT",
            "plugin_id": PLUGIN_ID,
            "installed_at": now_utc(),
            "last_verified_at": now_utc(),
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


def install_all_transaction(
    source: Path,
    install_root: Path,
    state_root: Path,
    *,
    dry_run: bool = False,
    repair: bool = False,
    invoke,
    operations: dict[str, object],
) -> dict[str, object]:
    manifest = operations["manifest"]
    codex_status = operations["codex_status"]
    plugin_status = operations["plugin_status"]
    install_bundle = operations["install_bundle"]
    ensure_codex_install = operations["ensure_codex_install"]
    ensure_workbench = operations["ensure_workbench"]
    atomic_write_json = operations["atomic_write_json"]
    install_gui_next_steps_message = operations["install_gui_next_steps_message"]
    remove_tree_resilient = operations["remove_tree_resilient"]
    state_path = operations["state_path"]
    update_cache_path = operations["update_cache_path"]
    write_update_cache = operations["write_update_cache"]
    expected_version = str(manifest(source)["version"])
    codex_before = codex_status(install_root, expected_version, invoke=invoke)
    if codex_before.get("status") in {"external_conflict", "unavailable"}:
        return {
            "status": codex_before["status"],
            "changed": False,
            "installation_state": (
                "OFFLINE" if codex_before["status"] == "unavailable" else "FOREIGN"
            ),
            "codex": codex_before,
        }

    bundle_before = plugin_status(source, install_root, state_root)
    if bundle_before.get("status") in {"external_conflict", "modified"}:
        return {
            "status": str(bundle_before["status"]),
            "changed": False,
            "installation_state": "FOREIGN",
            "bundle": bundle_before,
            "codex": codex_before,
        }

    workbench_before = ensure_workbench(
        source,
        state_root,
        dry_run=True,
        repair=False,
    )
    installation_before = classify_installation_state(
        bundle_before, codex_before, workbench_before
    )
    if workbench_before.get("state") == "FOREIGN":
        return {
            "status": "external_conflict",
            "changed": False,
            "installation_state": installation_before,
            "bundle": bundle_before,
            "codex": codex_before,
            "workbench": workbench_before,
        }
    if (
        not repair
        and not dry_run
        and bundle_before.get("status") == "ready"
        and codex_before.get("status") == "ready"
        and workbench_before.get("status") == "ready"
        and workbench_before.get("healthy") is True
    ):
        return {
            "status": "ready",
            "changed": False,
            "version": expected_version,
            "installation_state": installation_before,
            "bundle": bundle_before,
            "codex": codex_before,
            "workbench": workbench_before,
            "update_cache": read_json(update_cache_path(state_root)),
            "gui_next_steps": install_gui_next_steps_message(),
        }

    snapshot: Path | None = None
    workbench_root = state_root / "workbench"
    workbench_existed_before = workbench_root.exists()
    workbench_snapshot: Path | None = None
    previous_state = read_json(state_path(state_root))
    if not dry_run and install_root.exists():
        snapshot = install_root.parent / f".{OWNER}.snapshot-{uuid.uuid4().hex}"
        shutil.copytree(install_root, snapshot)
    if (
        not dry_run
        and workbench_existed_before
        and workbench_before.get("status") != "ready"
    ):
        workbench_snapshot = state_root / f".workbench.snapshot-{uuid.uuid4().hex}"
        shutil.copytree(workbench_root, workbench_snapshot)

    try:
        bundle = install_bundle(
            source,
            install_root,
            state_root,
            dry_run=dry_run,
            repair=repair,
        )
        if bundle.get("status") in {"external_conflict", "modified"}:
            return {**bundle, "bundle": bundle, "codex": codex_before}
        workbench = ensure_workbench(
            source,
            state_root,
            dry_run=dry_run,
            repair=repair,
        )
        if workbench.get("status") not in {"ready", "would_install"}:
            raise RuntimeError(
                f"Required Workbench did not complete: {workbench.get('status')}"
            )
        codex = ensure_codex_install(
            install_root,
            expected_version,
            dry_run=dry_run,
            invoke=invoke,
        )
        if codex.get("status") in {"external_conflict", "unavailable"}:
            raise RuntimeError(
                f"Codex installation did not complete: {codex.get('status')}"
            )
    except Exception:
        if not dry_run:
            if install_root.exists():
                remove_tree_resilient(install_root)
            if snapshot is not None and snapshot.exists():
                os.replace(snapshot, install_root)
            if previous_state is None:
                state_path(state_root).unlink(missing_ok=True)
            else:
                atomic_write_json(state_path(state_root), previous_state)
            if workbench_snapshot is not None and workbench_snapshot.exists():
                if workbench_root.exists():
                    remove_tree_resilient(workbench_root)
                os.replace(workbench_snapshot, workbench_root)
            elif not workbench_existed_before and workbench_root.exists():
                remove_tree_resilient(workbench_root)
        raise
    finally:
        if snapshot is not None and snapshot.exists():
            remove_tree_resilient(snapshot)
        if workbench_snapshot is not None and workbench_snapshot.exists():
            remove_tree_resilient(workbench_snapshot)
    changed = bool(
        bundle.get("changed") or workbench.get("changed") or codex.get("changed")
    )
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
    update_cache = None
    if not dry_run:
        existing_cache = read_json(update_cache_path(state_root))
        if changed or existing_cache is None:
            try:
                update_cache = write_update_cache(state_root, expected_version)
            except OSError:
                update_cache = {"status": "write_failed"}
        else:
            update_cache = existing_cache
    return {
        "status": status,
        "changed": changed,
        "version": expected_version,
        "installation_state": "CURRENT" if status in {"ready", "installed", "updated", "repaired", "migrated"} else "BROKEN",
        "bundle": bundle,
        "workbench": workbench,
        "codex": codex,
        "update_cache": update_cache,
        "gui_next_steps": install_gui_next_steps_message(),
    }


def uninstall_bundle_transaction(
    install_root: Path,
    state_root: Path,
    *,
    dry_run: bool = False,
    operations: dict[str, object],
) -> dict[str, object]:
    owned_state = operations["owned_state"]
    tree_fingerprint = operations["tree_fingerprint"]
    install_has_user_added_files = operations["install_has_user_added_files"]
    state_path = operations["state_path"]
    remove_tree_resilient = operations["remove_tree_resilient"]
    install_root = install_root.resolve()
    state_root = state_root.resolve()
    if not install_root.exists():
        return {"status": "absent", "changed": False}
    state = owned_state(install_root, state_root)
    if state is None:
        return {"status": "external_conflict", "changed": False}
    actual = tree_fingerprint(install_root)
    file_hashes = state.get("file_hashes") if isinstance(state.get("file_hashes"), dict) else None
    if state.get("fingerprint") != actual or install_has_user_added_files(
        install_root, file_hashes
    ):
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


def finalize_verified_uninstall_transaction(
    install_root: Path,
    state_root: Path,
    *,
    operations: dict[str, object],
) -> dict[str, object]:
    """Remove a previously verified Pala-owned root after Codex cleanup."""
    owned_state = operations["owned_state"]
    tree_fingerprint = operations["tree_fingerprint"]
    install_has_user_added_files = operations["install_has_user_added_files"]
    state_path = operations["state_path"]
    remove_tree_resilient = operations["remove_tree_resilient"]
    install_root = install_root.resolve()
    state_root = state_root.resolve()
    state = owned_state(install_root, state_root)
    if state is None:
        return {"status": "external_conflict", "changed": False}
    # Re-validate after Codex remove. Missing Pala-owned files are expected,
    # but a remaining user file, symlink, or changed owned file is never wiped.
    if install_root.exists():
        file_hashes = state.get("file_hashes") if isinstance(state.get("file_hashes"), dict) else None
        if file_hashes is None:
            # Legacy state cannot distinguish a Codex-removed file from an
            # owned-file modification, so retain its conservative behavior.
            modified = state.get("fingerprint") != tree_fingerprint(install_root)
        else:
            modified = install_has_user_added_files(install_root, file_hashes)
        if modified:
            return {"status": "modified", "changed": False}
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


def uninstall_all_transaction(
    source: Path,
    install_root: Path,
    state_root: Path,
    *,
    dry_run: bool = False,
    invoke,
    operations: dict[str, object],
) -> dict[str, object]:
    manifest = operations["manifest"]
    uninstall_bundle = operations["uninstall_bundle"]
    remove_codex_install = operations["remove_codex_install"]
    finalize_verified_uninstall = operations["finalize_verified_uninstall"]
    update_cache_path = operations["update_cache_path"]
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
    if status == "uninstalled" and not dry_run:
        update_cache_path(state_root).unlink(missing_ok=True)
    return {"status": status, "changed": changed, "bundle": bundle, "codex": codex}

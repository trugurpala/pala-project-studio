#!/usr/bin/env python3
"""Compatibility facade for Pala's idempotent, atomic installer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pala_installer_shared import *
from pala_installer_integrity import *
from pala_installer_core import *
from pala_installer_core import _codex_bridge, _host_path, _load_codex_bridge
from pala_installer_transaction import (
    copy_bundle,
    finalize_verified_uninstall_transaction,
    install_all_transaction,
    install_bundle_transaction,
    remove_tree_resilient,
    uninstall_all_transaction,
    uninstall_bundle_transaction,
)


def run_codex_json(arguments: list[str]) -> dict[str, object]:
    """Use the facade resolver so compatibility patches remain local."""
    return _codex_bridge.run_codex_json(arguments, resolver=resolve_codex_executable)


def _transaction_operations() -> dict[str, object]:
    return {
        "atomic_write_json": atomic_write_json,
        "bundle_file_hashes": bundle_file_hashes,
        "bundle_fingerprint": bundle_fingerprint,
        "codex_status": codex_status,
        "ensure_codex_install": ensure_codex_install,
        "finalize_verified_uninstall": finalize_verified_uninstall,
        "install_bundle": install_bundle,
        "install_has_user_added_files": install_has_user_added_files,
        "install_gui_next_steps_message": install_gui_next_steps_message,
        "manifest": manifest,
        "owned_state": owned_state,
        "plugin_status": plugin_status,
        "remove_codex_install": remove_codex_install,
        "remove_tree_resilient": remove_tree_resilient,
        "state_path": state_path,
        "tree_fingerprint": tree_fingerprint,
        "uninstall_bundle": uninstall_bundle,
        "update_cache_path": update_cache_path,
        "validate_bundle": validate_bundle,
        "write_update_cache": write_update_cache,
    }


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
    version_info = sys.version_info
    if hasattr(version_info, "__iter__"):
        major, minor, micro = list(version_info)[:3]
    else:
        major, minor, micro = (
            version_info.major,
            version_info.minor,
            version_info.micro,
        )
    python_ready = (major, minor) >= (3, 10)
    git_path = shutil.which("git")
    on_path = shutil.which("codex")
    resolved = resolve_codex_executable()
    codex_path = str(resolved) if resolved is not None else None
    node_path = shutil.which("node")
    uv_path = shutil.which("uv")
    project = project_doctor(install_root, project_root)
    plugin_ready = bool(
        bundle["healthy"]
        and codex.get("healthy")
        and python_ready
        and git_path
        and resolved is not None
    )
    expert_prerequisites_ready = bool(node_path and uv_path)
    adapters = bundle.get("adapters", {})
    if not isinstance(adapters, dict):
        adapters = {}
    managed_experts = (
        "code-review-graph",
        "codebase-memory",
        "graphify",
        "ollama",
        "serena",
    )
    experts_ready = bool(
        expert_prerequisites_ready
        and all(
            isinstance(adapters.get(name), dict)
            and adapters[name].get("state") == "ready"
            for name in managed_experts
        )
    )
    healthy = plugin_ready
    hooks_next = hooks_next_step_message(project)
    plugin_payload = bundle["plugin"]
    plugin_next = plugin_drift_next_step_message(
        plugin_payload if isinstance(plugin_payload, dict) else None
    )
    self_audit_script = source / "scripts" / "pala_self_audit.py"
    self_audit = {
        "status": (
            "configured-not-verified"
            if self_audit_script.is_file()
            else "not-run"
        ),
        "command": "py -3 scripts/pala_self_audit.py --profile runtime",
        "detail": (
            "Fork/presence kalite kapisi Doctor icinde otomatik kosulmaz; "
            "kurulu marketplace icin --profile runtime; kaynak agac icin "
            "verify.py veya --profile source gerekir."
        ),
    }
    try:
        from pala_shared_memory import doctor_store_block

        shared_store = doctor_store_block()
    except Exception as error:  # noqa: BLE001 â€” Doctor must stay readable
        shared_store = {
            "db_path": None,
            "error": str(error),
            "cloud_sync": False,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "healthy": healthy,
        "plugin_ready": plugin_ready,
        "experts_ready": experts_ready,
        "expert_prerequisites_ready": expert_prerequisites_ready,
        "status": "ready" if healthy else "attention_required",
        "hooks_next_step": hooks_next,
        "plugin_next_step": plugin_next,
        "gui_next_steps": install_gui_next_steps_message(),
        "self_audit": self_audit,
        "shared_store": shared_store,
        "plugin": bundle["plugin"],
        "adapters": adapters,
        "codex": codex,
        "python": {
            "ready": python_ready,
            "version": f"{major}.{minor}.{micro}",
            "executable": sys.executable,
        },
        "git": {"ready": bool(git_path), "executable": git_path},
        "codex_cli": {
            "ready": resolved is not None,
            "executable": codex_path,
            "on_path": bool(on_path),
            "resolved_via": (
                "path"
                if on_path
                else ("probe" if resolved is not None else None)
            ),
            "hint": (
                None
                if on_path or resolved is None
                else f"Codex bulundu ama PATH'te degil: {codex_path}"
            ),
        },
        "node": {"ready": bool(node_path), "executable": node_path},
        "uv": {"ready": bool(uv_path), "executable": uv_path},
        "project": project,
        "update_cache": read_json(update_cache_path(state_root)),
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
    return install_bundle_transaction(
        source,
        install_root,
        state_root,
        dry_run=dry_run,
        repair=repair,
        operations=_transaction_operations(),
    )


def install_all(
    source: Path,
    install_root: Path,
    state_root: Path,
    *,
    dry_run: bool = False,
    repair: bool = False,
    invoke=run_codex_json,
) -> dict[str, object]:
    return install_all_transaction(
        source,
        install_root,
        state_root,
        dry_run=dry_run,
        repair=repair,
        invoke=invoke,
        operations=_transaction_operations(),
    )


def uninstall_bundle(
    install_root: Path, state_root: Path, *, dry_run: bool = False
) -> dict[str, object]:
    return uninstall_bundle_transaction(
        install_root, state_root, dry_run=dry_run, operations=_transaction_operations()
    )


def finalize_verified_uninstall(
    install_root: Path, state_root: Path
) -> dict[str, object]:
    return finalize_verified_uninstall_transaction(
        install_root, state_root, operations=_transaction_operations()
    )


def uninstall_all(
    source: Path,
    install_root: Path,
    state_root: Path,
    *,
    dry_run: bool = False,
    invoke=run_codex_json,
) -> dict[str, object]:
    return uninstall_all_transaction(
        source,
        install_root,
        state_root,
        dry_run=dry_run,
        invoke=invoke,
        operations=_transaction_operations(),
    )


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
        if not args.dry_run:
            try:
                atomic_append_event(
                    event_log_path(args.state_root),
                    {"mode": args.mode, "status": "failed", "changed": False},
                )
            except OSError:
                pass
        emit_json({"status": "failed", "error": str(error)}, indent=None)
        return 1
    if not args.dry_run and report.get("changed"):
        try:
            atomic_append_event(
                event_log_path(args.state_root),
                {
                    "mode": args.mode,
                    "status": report.get("status"),
                    "changed": report.get("changed", False),
                    "version": report.get("version", ""),
                },
            )
        except OSError:
            pass
    emit_json(report)
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

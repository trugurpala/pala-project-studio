#!/usr/bin/env python3
"""Codex bridge, installer state, and non-mutating doctor responsibilities."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

from pala_installer_integrity import (
    bundle_fingerprint,
    bundle_file_hashes,
    install_has_user_added_files,
    manifest,
    tree_fingerprint,
    validate_bundle,
)
from pala_installer_shared import *

def _load_codex_bridge():
    """Load this install tree's sibling bridge without cross-tree module reuse."""
    path = Path(__file__).with_name("pala_installer_codex.py").resolve()
    module_name = "_pala_installer_codex_" + hashlib.sha256(
        str(path).encode("utf-8")
    ).hexdigest()[:16]
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load Codex bridge: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module

_codex_bridge = _load_codex_bridge()
_host_path = _codex_bridge._host_path
resolve_windows_codex_candidates = _codex_bridge.resolve_windows_codex_candidates
resolve_codex_executable = _codex_bridge.resolve_codex_executable
comparable_path = _codex_bridge.comparable_path
base_version = _codex_bridge.base_version
resolve_codex_home = _codex_bridge.resolve_codex_home


def run_codex_json(arguments: list[str]) -> dict[str, object]:
    return _codex_bridge.run_codex_json(arguments, resolver=resolve_codex_executable)


def codex_capabilities(*, invoke=run_codex_json):
    if invoke is run_codex_json or getattr(invoke, "_pala_real_codex_runner", False):
        return _codex_bridge.probe_codex_capabilities()
    return _codex_bridge.CodexCapabilities.all_supported()


def trusted_legacy_pala(entry: dict[str, object]) -> bool:
    return _codex_bridge.trusted_legacy_pala(
        entry, owner=OWNER,
        official_repository=OFFICIAL_REPOSITORY,
        official_author=OFFICIAL_AUTHOR,
        read_json_file=read_json,
    )


def codex_runtime_cache_dir(
    version: str, *, codex_home: Path | None = None
) -> Path:
    return _codex_bridge.codex_runtime_cache_dir(OWNER, version, codex_home=codex_home)


def codex_runtime_cache_matches(
    install_root: Path, version: str, *, codex_home: Path | None = None
) -> bool:
    return _codex_bridge.codex_runtime_cache_matches(
        install_root, version, owner=OWNER,
        fingerprint=tree_fingerprint,
        codex_home=codex_home,
    )


def codex_status(
    install_root: Path, expected_version: str, *, invoke=run_codex_json
) -> dict[str, object]:
    return _codex_bridge.codex_status(
        install_root, expected_version, owner=OWNER,
        plugin_id=PLUGIN_ID, official_repository=OFFICIAL_REPOSITORY,
        trusted_legacy=trusted_legacy_pala,
        cache_matches=codex_runtime_cache_matches,
        invoke=invoke,
    )


def ensure_codex_install(
    install_root: Path,
    expected_version: str,
    *,
    dry_run: bool = False,
    invoke=run_codex_json,
    capabilities=None,
) -> dict[str, object]:
    if capabilities is None:
        capabilities = codex_capabilities(invoke=invoke)
    return _codex_bridge.ensure_codex_install(
        install_root, expected_version, owner=OWNER,
        plugin_id=PLUGIN_ID, official_repository=OFFICIAL_REPOSITORY,
        status_check=codex_status,
        capabilities=capabilities,
        dry_run=dry_run,
        invoke=invoke,
    )


def remove_codex_install(
    install_root: Path,
    expected_version: str,
    *,
    dry_run: bool = False,
    invoke=run_codex_json,
) -> dict[str, object]:
    return _codex_bridge.remove_codex_install(
        install_root, expected_version, owner=OWNER,
        plugin_id=PLUGIN_ID,
        status_check=codex_status,
        dry_run=dry_run,
        invoke=invoke,
    )

def state_path(state_root: Path) -> Path:
    return state_root / STATE_NAME


def update_cache_path(state_root: Path) -> Path:
    return state_root / UPDATE_CACHE_NAME


def event_log_path(state_root: Path) -> Path:
    return state_root / "logs" / EVENT_LOG_NAME


def write_update_cache(state_root: Path, version: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "owner": OWNER,
        "source": OFFICIAL_REPOSITORY,
        "checked_at": now_utc(),
        "installed_version": version,
        "latest_known_version": version,
        "update_available": False,
        "network_checked": False,
    }
    atomic_write_json(update_cache_path(state_root), payload)
    return payload


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


def trusted_legacy_install(install_root: Path) -> dict[str, object] | None:
    """Attest a historical official Pala tree without future-file requirements."""
    value = read_json(install_root / ".codex-plugin" / "plugin.json")
    if value is None:
        return None
    author = value.get("author")
    version = value.get("version")
    historical_surface = (
        Path(".agents/plugins/marketplace.json"),
        Path("hooks/hooks.json"),
        Path("scripts/pala_state.py"),
        Path("skills/pala-project-finisher/SKILL.md"),
    )
    if not all(
        (install_root / relative).is_file()
        and not (install_root / relative).is_symlink()
        for relative in historical_surface
    ):
        return None
    if install_has_user_added_files(install_root):
        return None
    return value if bool(
        value.get("name") == OWNER
        and value.get("repository") == OFFICIAL_REPOSITORY
        and isinstance(author, dict)
        and author.get("url") == OFFICIAL_AUTHOR
        and isinstance(version, str)
        and version.strip()
    ) else None


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
        installed_manifest = trusted_legacy_install(install_root)
        if installed_manifest is None:
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
    file_hashes = state.get("file_hashes")
    exact_hashes = file_hashes if isinstance(file_hashes, dict) else None
    actual = tree_fingerprint(install_root)
    expected = bundle_fingerprint(source)
    if install_has_user_added_files(install_root, exact_hashes):
        # A changed owned file and a user-added file are intentionally treated
        # alike: neither Repair nor Update can safely infer that replacement is
        # desired. Preserve the tree and require an explicit human recovery.
        status = "modified"
    elif actual == expected:
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
        "adapters": adapter_inventory(source, state_root),
        "state_file": str(state_path(state_root).resolve()),
    }


def adapter_inventory(source: Path, state_root: Path | None = None) -> dict[str, dict[str, object]]:
    """Project the current capability contracts without mutating runtime state."""
    try:
        workbench_path = Path(__file__).with_name("pala_workbench.py")
        spec = importlib.util.spec_from_file_location("pala_installer_workbench", workbench_path)
        if spec is None or spec.loader is None:
            raise ValueError("workbench capability registry unavailable")
        module = importlib.util.module_from_spec(spec)
        sys.modules["pala_installer_workbench"] = module
        spec.loader.exec_module(module)
        contracts = module.default_registry().contracts
    except (OSError, ValueError, ImportError):
        return {
            "registry": {
                "state": "failed",
                "changed": False,
                "detail": "workbench capability registry unavailable",
            }
        }
    return {
        contract.capability_id: {
            "state": "declared",
            "changed": False,
            "detail": contract.category,
            "provider": contract.provider,
            "version": contract.version,
            "required_for_core_health": contract.required_for_core_health,
        }
        for contract in contracts
    }


def hooks_next_step_message(project: dict[str, object] | None) -> str:
    """Remind Codex Work UI trust; do not confuse with local hook_safety.

    Doctor ``hook=passed`` means hooks.json + pala_hook.py + workflow exist.
    Codex ``/hooks`` user trust is a separate interactive step and cannot be
    completed from ``codex exec``.
    """
    safety = ""
    if isinstance(project, dict):
        hook_safety = project.get("hook_safety")
        if isinstance(hook_safety, dict):
            safety = str(hook_safety.get("status") or "").strip().casefold()
    if safety == "passed":
        return (
            "hook_safety=passed (dosya kontrolu). Codex Work'te /hooks ile "
            "kullanici trust verin; terminal/codex exec yetmez. Sonra yeni sohbet."
        )
    if safety == "blocked":
        return (
            "hook_safety=blocked (dosya). Once hooks.json/pala_hook/workflow "
            "duzeltin; sonra Codex Work'te /hooks trust. Otomatik bypass yok."
        )
    return (
        "Codex Work'te yeni sohbet acin ve /hooks ile Pala hook guvenini verin; "
        "otomatik bypass yok. (Doctor hook= alani dosya guvenligidir, UI trust degil.)"
    )


def plugin_drift_next_step_message(plugin: dict[str, object] | None) -> str:
    """Tell vibe users how to clear sourceâ‰ install fingerprint drift.

    ``plugin=drifted`` after local edits is expected honesty, not soft-healthy.
    Runtime junk must not cause drift (Issue #13); real drift needs Repair/sync.
    """
    status = ""
    if isinstance(plugin, dict):
        status = str(plugin.get("status") or "").strip().casefold()
    if status == "modified":
        return (
            "plugin=modified (kurulu agacta degisen veya eklenen dosya var). "
            "Repair/Update otomatik yazmaz; dosyayi inceleyip koruyun veya "
            "bilincli olarak geri yukleyin. Sonra Doctor tekrar."
        )
    if status != "drifted":
        return ""
    return (
        "plugin=drifted (source!=install fingerprint). "
        "Install-Pala -Mode Repair veya Update / marketplace sync; "
        "healthy sayma. Sonra Doctor tekrar."
    )


def install_gui_next_steps_lines() -> list[str]:
    """Turkish Codex Work follow-ups after a successful Install (no network)."""
    return [
        "Sonraki 3 adim (Codex Work):",
        "1) Plugins'te Pala gorunuyor mu kontrol edin.",
        "2) /hooks ile Pala hook guvenini (trust) verin.",
        "3) Yeni bir sohbet acin.",
    ]


def install_gui_next_steps_message() -> str:
    """Single printable block for Install / Kur.cmd success paths."""
    return "\n".join(install_gui_next_steps_lines())


def project_doctor(install_root: Path, project_root: Path) -> dict[str, object]:
    script = install_root / "scripts" / "pala_state.py"
    if not script.is_file():
        return {
            "available": False,
            "project_root": str(project_root.resolve()),
            "error": "Pala project doctor is not installed",
        }
    try:
        env = dict(os.environ)
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.setdefault("PYTHONUTF8", "1")
        completed = subprocess.run(
            [sys.executable, str(script), "doctor", "--cwd", str(project_root)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            env=env,
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

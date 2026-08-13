#!/usr/bin/env python3
"""Bounded bridge for the external Codex CLI and marketplace state.

This module deliberately owns only Codex discovery, inventory, cache, and
marketplace operations. Bundle integrity, filesystem transactions, state, and
user-file protection remain in ``pala_installer.py``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CodexCapabilities:
    """Supported Codex plugin operations discovered from the installed CLI."""

    marketplace_add: bool = False
    marketplace_list: bool = False
    marketplace_upgrade: bool = False
    marketplace_remove: bool = False
    plugin_add: bool = False
    plugin_list: bool = False
    plugin_remove: bool = False
    json_mode: bool = False
    source: str = "not-probed"

    @classmethod
    def all_supported(cls, *, source: str = "injected-adapter") -> "CodexCapabilities":
        return cls(
            marketplace_add=True,
            marketplace_list=True,
            marketplace_upgrade=True,
            marketplace_remove=True,
            plugin_add=True,
            plugin_list=True,
            plugin_remove=True,
            json_mode=True,
            source=source,
        )


def _host_path(value: str | os.PathLike[str]) -> Path:
    """Build a Path with the host OS concrete class.

    Tests may mock ``os.name`` to exercise Windows discovery on non-Windows
    hosts. Prefer the class matching the imported ``os.path`` implementation.
    """
    text = os.fspath(value)
    if os.sep == "\\":
        from pathlib import WindowsPath

        return WindowsPath(text)
    from pathlib import PosixPath

    return PosixPath(text)


def resolve_windows_codex_candidates(
    *, environ: dict[str, str] | None = None
) -> list[str]:
    """Return off-PATH Windows Codex candidate paths as plain strings."""
    env = environ if environ is not None else os.environ
    home = env.get("USERPROFILE") or os.path.expanduser("~")
    local = env.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
    appdata = env.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
    candidates = [
        os.path.join(local, "Programs", "codex", "codex.exe"),
        os.path.join(local, "Programs", "Codex", "codex.exe"),
        os.path.join(appdata, "npm", "codex.cmd"),
        os.path.join(home, ".codex", "bin", "codex.exe"),
        os.path.join(home, ".local", "bin", "codex.exe"),
    ]
    openai_bin = os.path.join(local, "OpenAI", "Codex", "bin")
    if os.path.isdir(openai_bin):
        try:
            for name in sorted(os.listdir(openai_bin)):
                executable = os.path.join(openai_bin, name, "codex.exe")
                if os.path.isfile(executable):
                    candidates.append(executable)
        except OSError:
            pass
    return candidates


def resolve_codex_executable() -> Path | None:
    """Locate Codex CLI even when Windows desktop install is off PATH."""
    found = shutil.which("codex")
    if found:
        return _host_path(found)
    if os.name != "nt":
        return None
    for candidate in resolve_windows_codex_candidates():
        try:
            if os.path.isfile(candidate):
                return _host_path(candidate)
        except OSError:
            continue
    return None


def run_codex_json(
    arguments: list[str], *, resolver: Callable[[], Path | None] = resolve_codex_executable
) -> dict[str, object]:
    """Run a fixed Codex CLI argv and accept only a JSON object result."""
    executable = resolver()
    if executable is None:
        raise RuntimeError(
            "Codex CLI is not available on PATH or known Windows install locations "
            "(%%LOCALAPPDATA%%\\OpenAI\\Codex\\bin, %%APPDATA%%\\npm\\codex.cmd)"
        )
    try:
        completed = subprocess.run(
            [str(executable), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
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


def run_codex_help(
    arguments: list[str], *, resolver: Callable[[], Path | None] = resolve_codex_executable
) -> str:
    """Run a non-mutating Codex capability/help probe with fixed argv."""
    executable = resolver()
    if executable is None:
        return ""
    try:
        completed = subprocess.run(
            [str(executable), *arguments, "--help"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if completed.returncode != 0:
        return ""
    return f"{completed.stdout}\n{completed.stderr}"


def probe_codex_capabilities(
    *,
    help_runner: Callable[[list[str]], str] = run_codex_help,
) -> CodexCapabilities:
    """Discover command support without executing a mutating operation."""
    checks = {
        "marketplace_add": ["plugin", "marketplace", "add"],
        "marketplace_list": ["plugin", "marketplace", "list"],
        "marketplace_upgrade": ["plugin", "marketplace", "upgrade"],
        "marketplace_remove": ["plugin", "marketplace", "remove"],
        "plugin_add": ["plugin", "add"],
        "plugin_list": ["plugin", "list"],
        "plugin_remove": ["plugin", "remove"],
    }
    outputs = {name: help_runner(argv) for name, argv in checks.items()}
    json_mode = all("--json" in output for output in outputs.values())
    return CodexCapabilities(
        **{name: bool(output) for name, output in outputs.items()},
        json_mode=json_mode,
        source="codex-help-probe",
    )


def comparable_path(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.removeprefix("\\\\?\\")
    try:
        return str(Path(normalized).resolve()).casefold()
    except OSError:
        return os.path.normcase(os.path.abspath(normalized))


def trusted_legacy_pala(
    entry: dict[str, object],
    *,
    owner: str,
    official_repository: str,
    official_author: str,
    read_json_file: Callable[[Path], dict[str, object] | None],
) -> bool:
    """Recognize only an attested old Pala plugin before migration."""
    source = entry.get("source")
    if not isinstance(source, dict) or source.get("source") != "local":
        return False
    path_value = source.get("path")
    if not isinstance(path_value, str):
        return False
    value = read_json_file(Path(path_value) / ".codex-plugin" / "plugin.json")
    if value is None:
        return False
    author = value.get("author")
    return bool(
        value.get("name") == owner
        and value.get("repository") == official_repository
        and isinstance(author, dict)
        and author.get("url") == official_author
    )


def _normalized_marketplace_source(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    source = value.strip().rstrip("/").casefold()
    if source.endswith(".git"):
        source = source[:-4]
    return source


def _official_marketplace_source(value: object, official_repository: str) -> bool:
    return _normalized_marketplace_source(value) == _normalized_marketplace_source(
        official_repository
    )


def base_version(value: object) -> str | None:
    """Return the release identity without local build metadata."""
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().split("+", 1)[0]


def resolve_codex_home() -> Path:
    configured = os.environ.get("CODEX_HOME", "").strip()
    if configured:
        return Path(configured)
    return Path.home() / ".codex"


def codex_runtime_cache_dir(
    owner: str, version: str, *, codex_home: Path | None = None
) -> Path:
    """Return the versioned cache path owned by a Codex marketplace plugin."""
    home = codex_home if codex_home is not None else resolve_codex_home()
    return home / "plugins" / "cache" / owner / owner / version


def codex_runtime_cache_matches(
    install_root: Path,
    version: str,
    *,
    owner: str,
    fingerprint: Callable[[Path], str],
    codex_home: Path | None = None,
) -> bool:
    """True when cache is absent or fingerprints the marketplace tree."""
    cache_dir = codex_runtime_cache_dir(owner, version, codex_home=codex_home)
    if not cache_dir.is_dir():
        return True
    return fingerprint(cache_dir) == fingerprint(install_root.resolve())


def codex_status(
    install_root: Path,
    expected_version: str,
    *,
    owner: str,
    plugin_id: str,
    official_repository: str,
    trusted_legacy: Callable[[dict[str, object]], bool],
    cache_matches: Callable[[Path, str], bool],
    trusted_bootstrap_root: Callable[[object, str], bool] | None = None,
    invoke: Callable[[list[str]], dict[str, object]] = run_codex_json,
) -> dict[str, object]:
    """Read Codex marketplace/plugin inventory without modifying it."""
    try:
        marketplace_payload = invoke(["plugin", "marketplace", "list", "--json"])
        plugin_payload = invoke(["plugin", "list", "--json"])
    except RuntimeError as error:
        return {"status": "unavailable", "healthy": False, "error": str(error)}

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
        if isinstance(entry, dict) and entry.get("name") == owner
    ]
    marketplace = named_marketplaces[0] if named_marketplaces else None
    marketplace_source_info = (
        marketplace.get("marketplaceSource") if marketplace else None
    )
    marketplace_source_type = (
        marketplace_source_info.get("sourceType")
        if isinstance(marketplace_source_info, dict)
        else None
    )
    marketplace_source = (
        marketplace_source_info.get("source")
        if isinstance(marketplace_source_info, dict)
        else None
    )
    marketplace_owned = bool(
        marketplace_source_type == "git"
        and _official_marketplace_source(marketplace_source, official_repository)
    )
    bootstrap_target = next(
        (
            entry
            for entry in installed
            if isinstance(entry, dict) and entry.get("pluginId") == plugin_id
        ),
        None,
    )
    bootstrap_adoptable = bool(
        marketplace is not None
        and comparable_path(marketplace.get("root")) != expected_root
        and not marketplace_owned
        and trusted_bootstrap_root is not None
        and trusted_bootstrap_root(marketplace.get("root"), expected_version)
        and bootstrap_target
        and base_version(bootstrap_target.get("version"))
        == base_version(expected_version)
        and bootstrap_target.get("enabled")
    )
    if (
        marketplace is not None
        and comparable_path(marketplace.get("root")) != expected_root
        and not marketplace_owned
        and not bootstrap_adoptable
    ):
        return {
            "status": "external_conflict",
            "healthy": False,
            "marketplace_root": marketplace.get("root"),
            "marketplace_source_type": marketplace_source_type,
            "marketplace_source": marketplace_source,
        }

    target = next(
        (
            entry
            for entry in installed
            if isinstance(entry, dict) and entry.get("pluginId") == plugin_id
        ),
        None,
    )
    duplicate_entries = [
        entry
        for entry in installed
        if isinstance(entry, dict)
        and entry.get("name") == owner
        and entry.get("pluginId") != plugin_id
    ]
    untrusted_duplicates = [
        str(entry.get("pluginId"))
        for entry in duplicate_entries
        if not trusted_legacy(entry)
    ]
    if untrusted_duplicates:
        return {
            "status": "external_conflict",
            "healthy": False,
            "conflicting_plugins": untrusted_duplicates,
        }
    legacy_plugins = [str(entry.get("pluginId")) for entry in duplicate_entries]
    version_ready = bool(
        target
        and base_version(target.get("version")) == base_version(expected_version)
        and target.get("enabled")
    )
    cache_basis = install_root
    cache_basis_kind = "managed-install"
    marketplace_root = marketplace.get("root") if marketplace else None
    if marketplace_owned and isinstance(marketplace_root, str) and marketplace_root.strip():
        # A Git marketplace has its own checked-out snapshot.  Codex copies the
        # plugin from that snapshot, not from Pala's separately managed bundle,
        # so cache integrity must compare like with like.
        cache_basis = _host_path(marketplace_root)
        cache_basis_kind = "owned-git-snapshot"
    elif bootstrap_adoptable and isinstance(marketplace_root, str):
        cache_basis = _host_path(marketplace_root)
        cache_basis_kind = "verified-bootstrap-source"
    cache_stale = bool(
        version_ready and not cache_matches(cache_basis, expected_version)
    )
    target_ready = bool(version_ready and not cache_stale)
    if bootstrap_adoptable:
        status = "bootstrap_source"
    elif legacy_plugins:
        status = "legacy_pala"
    elif marketplace is None or target is None:
        status = "missing"
    elif not version_ready or cache_stale:
        status = "outdated"
    else:
        status = "ready"
    return {
        "status": status,
        "healthy": status == "ready",
        "marketplace_registered": marketplace is not None,
        "marketplace_root": marketplace.get("root") if marketplace else None,
        "cache_basis_kind": cache_basis_kind,
        "marketplace_source_type": marketplace_source_type,
        "marketplace_source": marketplace_source,
        "marketplace_owned": marketplace_owned,
        "marketplace_bootstrap_adoptable": bootstrap_adoptable,
        "marketplace_snapshot_version": (
            marketplace.get("snapshotVersion") if marketplace else None
        ),
        "plugin_id": target.get("pluginId") if target else None,
        "installed_version": target.get("version") if target else None,
        "installed_version_base": (
            base_version(target.get("version")) if target else None
        ),
        "expected_version": expected_version,
        "expected_version_base": base_version(expected_version),
        "enabled": bool(target and target.get("enabled")),
        "target_ready": target_ready,
        "cache_stale": cache_stale,
        "legacy_plugins": legacy_plugins,
    }


def ensure_codex_install(
    install_root: Path,
    expected_version: str,
    *,
    owner: str,
    plugin_id: str,
    official_repository: str,
    status_check: Callable[..., dict[str, object]],
    capabilities: CodexCapabilities | None = None,
    dry_run: bool = False,
    invoke: Callable[[list[str]], dict[str, object]] = run_codex_json,
) -> dict[str, object]:
    """Install or refresh just Pala's Codex marketplace registration."""
    install_root = install_root.resolve()
    before = status_check(install_root, expected_version, invoke=invoke)
    status = str(before["status"])
    if status == "ready":
        return {**before, "changed": False}
    if status in {"external_conflict", "unavailable"}:
        return {**before, "changed": False}
    if dry_run:
        action = "update" if status in {"outdated", "legacy_pala"} else "install"
        return {**before, "status": f"would_{action}", "changed": False}

    if capabilities is None:
        capabilities = CodexCapabilities.all_supported()

    git_marketplace = bool(
        before.get("marketplace_registered")
        and before.get("marketplace_owned")
        and before.get("marketplace_source_type") == "git"
    )
    refreshed_marketplace = False
    marketplace_refresh_path = "none"
    if status == "outdated" and git_marketplace:
        if capabilities.marketplace_upgrade and capabilities.json_mode:
            invoke(["plugin", "marketplace", "upgrade", owner, "--json"])
            refreshed_marketplace = True
            marketplace_refresh_path = "marketplace-upgrade"
            refreshed = status_check(install_root, expected_version, invoke=invoke)
            if refreshed.get("status") == "external_conflict":
                raise RuntimeError("Codex marketplace ownership changed during refresh")
            snapshot_version = refreshed.get("marketplace_snapshot_version")
            if snapshot_version is not None and base_version(snapshot_version) != base_version(expected_version):
                raise RuntimeError("Codex marketplace snapshot did not reach target version")
            before = refreshed
        else:
            # Legacy fallback is allowed only after exact Pala ownership was
            # proven from the inventory source and plugin identity.
            if not capabilities.marketplace_remove or not capabilities.marketplace_add:
                raise RuntimeError("Codex cannot refresh the owned Git marketplace")
            source = before.get("marketplace_source")
            if not isinstance(source, str) or not _official_marketplace_source(
                source, official_repository
            ):
                raise RuntimeError("Codex marketplace ownership is ambiguous")
            marketplace_removed = False
            try:
                # Keep the old enabled plugin in place while its owned Git
                # marketplace is refreshed.  This preserves a usable install
                # if either marketplace operation fails.
                invoke(["plugin", "marketplace", "remove", owner, "--json"])
                marketplace_removed = True
                invoke(["plugin", "marketplace", "add", source, "--json"])
                marketplace_removed = False
            except Exception:
                if marketplace_removed:
                    try:
                        invoke(["plugin", "marketplace", "add", source, "--json"])
                    except Exception:
                        pass
                raise
            refreshed_marketplace = True
            marketplace_refresh_path = "verified-remove-readd"
            before = status_check(install_root, expected_version, invoke=invoke)

    marketplace_added = False
    bootstrap_source = (
        str(before.get("marketplace_root"))
        if before.get("marketplace_bootstrap_adoptable")
        else None
    )
    bootstrap_removed = False
    target_was_present = bool(before.get("plugin_id") == plugin_id)
    removed_for_cache_refresh = False
    removed_legacy: list[str] = []
    try:
        if bootstrap_source is not None:
            if not capabilities.marketplace_remove or not capabilities.marketplace_add:
                raise RuntimeError("Codex cannot adopt the verified bootstrap marketplace")
            if target_was_present:
                invoke(["plugin", "remove", plugin_id, "--json"])
                removed_for_cache_refresh = True
            invoke(["plugin", "marketplace", "remove", owner, "--json"])
            bootstrap_removed = True
            before = {**before, "marketplace_registered": False}
        if not before.get("marketplace_registered"):
            invoke(["plugin", "marketplace", "add", str(install_root), "--json"])
            marketplace_added = True
        if target_was_present and (before.get("cache_stale") or refreshed_marketplace):
            invoke(["plugin", "remove", plugin_id, "--json"])
            removed_for_cache_refresh = True
        invoke(["plugin", "add", plugin_id, "--json"])
        after_add = status_check(install_root, expected_version, invoke=invoke)
        if not after_add.get("target_ready"):
            raise RuntimeError("Codex did not install the target Pala plugin")
        for legacy_plugin in before.get("legacy_plugins", []):
            if not isinstance(legacy_plugin, str):
                continue
            invoke(["plugin", "remove", legacy_plugin, "--json"])
            removed_legacy.append(legacy_plugin)
        after = status_check(install_root, expected_version, invoke=invoke)
        if after.get("status") != "ready":
            raise RuntimeError("Codex did not report Pala as installed and enabled")
    except Exception:
        for legacy_plugin in removed_legacy:
            try:
                invoke(["plugin", "add", legacy_plugin, "--json"])
            except Exception:
                pass
        if removed_for_cache_refresh:
            try:
                invoke(["plugin", "add", plugin_id, "--json"])
            except Exception:
                pass
        elif not target_was_present:
            try:
                invoke(["plugin", "remove", plugin_id, "--json"])
            except Exception:
                pass
        if marketplace_added:
            try:
                invoke(["plugin", "marketplace", "remove", owner, "--json"])
            except Exception:
                pass
        if bootstrap_removed and bootstrap_source is not None:
            try:
                invoke(["plugin", "marketplace", "add", bootstrap_source, "--json"])
                invoke(["plugin", "add", plugin_id, "--json"])
            except Exception:
                pass
        raise
    result_status = "migrated" if status == "legacy_pala" else (
        "updated" if status == "outdated" else "installed"
    )
    return {
        **after,
        "status": result_status,
        "changed": True,
        "marketplace_refresh_path": marketplace_refresh_path,
    }


def remove_codex_install(
    install_root: Path,
    expected_version: str,
    *,
    owner: str,
    plugin_id: str,
    status_check: Callable[..., dict[str, object]],
    dry_run: bool = False,
    invoke: Callable[[list[str]], dict[str, object]] = run_codex_json,
) -> dict[str, object]:
    """Remove only Pala's known Codex plugin and marketplace record."""
    before = status_check(install_root, expected_version, invoke=invoke)
    status = str(before["status"])
    if status in {"external_conflict", "unavailable"}:
        return {**before, "changed": False}
    present = bool(before.get("marketplace_registered") or before.get("plugin_id"))
    if not present:
        return {**before, "status": "absent", "changed": False}
    if dry_run:
        return {**before, "status": "would_uninstall", "changed": False}

    if before.get("plugin_id") == plugin_id:
        invoke(["plugin", "remove", plugin_id, "--json"])
    if before.get("marketplace_registered"):
        invoke(["plugin", "marketplace", "remove", owner, "--json"])
    return {**before, "status": "uninstalled", "healthy": True, "changed": True}

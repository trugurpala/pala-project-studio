#!/usr/bin/env python3
"""Idempotent, atomic installer core for Pala Project Studio."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
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
OFFICIAL_REPOSITORY = "https://github.com/trugurpala/pala-project-studio"
OFFICIAL_AUTHOR = "https://github.com/trugurpala"
STATE_NAME = "install-state.json"
UPDATE_CACHE_NAME = "update-cache.json"
EVENT_LOG_NAME = "installer-events.jsonl"
MAX_EVENT_LOG_BYTES = 256 * 1024
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
    "managed-tools.lock.json",
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


def atomic_append_event(path: Path, event: dict[str, object]) -> None:
    allowed = {
        "timestamp": now_utc(),
        "mode": str(event.get("mode", "unknown"))[:32],
        "status": str(event.get("status", "unknown"))[:64],
        "changed": bool(event.get("changed", False)),
        "version": str(event.get("version", ""))[:128],
    }
    line = (
        json.dumps(allowed, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_bytes() if path.is_file() else b""
    budget = max(0, MAX_EVENT_LOG_BYTES - len(line))
    if len(existing) > budget:
        existing = existing[-budget:]
        newline = existing.find(b"\n")
        existing = existing[newline + 1 :] if newline >= 0 else b""
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(existing)
            handle.write(line)
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


def _host_path(value: str | os.PathLike[str]) -> Path:
    """Build a Path with the host OS concrete class.

    Unit tests may mock ``os.name`` to exercise Windows discovery on Linux CI.
    ``pathlib.Path`` follows the mocked name and raises ``NotImplementedError``
    for ``WindowsPath`` on non-Windows hosts, so prefer the class that matches
    the imported ``os.path`` implementation.
    """
    text = os.fspath(value)
    if os.sep == "\\":
        from pathlib import WindowsPath

        return WindowsPath(text)
    from pathlib import PosixPath

    return PosixPath(text)


def resolve_windows_codex_candidates(
    *,
    environ: dict[str, str] | None = None,
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
                exe = os.path.join(openai_bin, name, "codex.exe")
                if os.path.isfile(exe):
                    candidates.append(exe)
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


def run_codex_json(arguments: list[str]) -> dict[str, object]:
    executable = resolve_codex_executable()
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


def trusted_legacy_pala(entry: dict[str, object]) -> bool:
    source = entry.get("source")
    if not isinstance(source, dict) or source.get("source") != "local":
        return False
    path_value = source.get("path")
    if not isinstance(path_value, str):
        return False
    value = read_json(Path(path_value) / ".codex-plugin" / "plugin.json")
    if value is None:
        return False
    author = value.get("author")
    return bool(
        value.get("name") == OWNER
        and value.get("repository") == OFFICIAL_REPOSITORY
        and isinstance(author, dict)
        and author.get("url") == OFFICIAL_AUTHOR
    )


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
    duplicate_entries = [
        entry
        for entry in installed
        if isinstance(entry, dict)
        and entry.get("name") == OWNER
        and entry.get("pluginId") != PLUGIN_ID
    ]
    untrusted_duplicates = [
        str(entry.get("pluginId"))
        for entry in duplicate_entries
        if not trusted_legacy_pala(entry)
    ]
    if untrusted_duplicates:
        return {
            "status": "external_conflict",
            "healthy": False,
            "conflicting_plugins": untrusted_duplicates,
        }
    legacy_plugins = [str(entry.get("pluginId")) for entry in duplicate_entries]
    target_ready = bool(
        target
        and target.get("version") == expected_version
        and target.get("enabled")
    )
    if legacy_plugins:
        status = "legacy_pala"
    elif marketplace is None:
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
        "target_ready": target_ready,
        "legacy_plugins": legacy_plugins,
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
        action = "update" if status in {"outdated", "legacy_pala"} else "install"
        return {**before, "status": f"would_{action}", "changed": False}

    marketplace_added = False
    target_was_present = bool(before.get("plugin_id") == PLUGIN_ID)
    removed_legacy: list[str] = []
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
        after_add = codex_status(install_root, expected_version, invoke=invoke)
        if not after_add.get("target_ready"):
            raise RuntimeError("Codex did not install the target Pala plugin")
        for legacy_plugin in before.get("legacy_plugins", []):
            if not isinstance(legacy_plugin, str):
                continue
            invoke(["plugin", "remove", legacy_plugin, "--json"])
            removed_legacy.append(legacy_plugin)
        after = codex_status(install_root, expected_version, invoke=invoke)
        if after.get("status") != "ready":
            raise RuntimeError("Codex did not report Pala as installed and enabled")
    except Exception:
        for legacy_plugin in removed_legacy:
            try:
                invoke(["plugin", "add", legacy_plugin, "--json"])
            except Exception:
                pass
        if not target_was_present:
            try:
                invoke(["plugin", "remove", PLUGIN_ID, "--json"])
            except Exception:
                pass
        if marketplace_added:
            try:
                invoke(["plugin", "marketplace", "remove", OWNER, "--json"])
            except Exception:
                pass
        raise
    if status == "legacy_pala":
        result_status = "migrated"
    else:
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
        "adapters": adapter_inventory(source, state_root),
        "state_file": str(state_path(state_root).resolve()),
    }


def adapter_inventory(source: Path, state_root: Path | None = None) -> dict[str, dict[str, object]]:
    """Report optional tools without probing, installing, or changing user configuration."""
    try:
        adapter_path = Path(__file__).with_name("pala_adapters.py")
        spec = importlib.util.spec_from_file_location("pala_installer_adapters", adapter_path)
        if spec is None or spec.loader is None:
            raise ValueError("adapter module unavailable")
        module = importlib.util.module_from_spec(spec)
        sys.modules["pala_installer_adapters"] = module
        spec.loader.exec_module(module)
        lock = module.load_managed_tools_lock(source / "managed-tools.lock.json")
    except (OSError, ValueError, ImportError):
        return {"lock": {"state": "failed", "detail": "managed tools lock unavailable"}}
    inventory: dict[str, dict[str, object]] = {}
    expert_module = None
    if state_root is not None:
        try:
            expert_path = Path(__file__).with_name("pala_expert_installer.py")
            expert_spec = importlib.util.spec_from_file_location("pala_installer_experts", expert_path)
            if expert_spec is not None and expert_spec.loader is not None:
                expert_module = importlib.util.module_from_spec(expert_spec)
                sys.modules["pala_installer_experts"] = expert_module
                expert_spec.loader.exec_module(expert_module)
        except (OSError, ImportError):
            expert_module = None
    for name, entry in lock.items():
        state = "missing"
        detail = "optional adapter is not installed"
        if expert_module is not None and "sha256" in entry:
            inspected = expert_module.inspect_binary(name, entry, state_root)
            state = str(inspected["state"])
            detail = "Pala-owned artifact integrity verified" if state == "ready" else "Pala-owned artifact is missing or conflicted"
        inventory[name] = {"state": state, "changed": False, "detail": detail, "version": entry["version"]}
    return inventory


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
    experts_ready = bool(node_path and uv_path)
    healthy = plugin_ready
    hooks_next = hooks_next_step_message(project)
    return {
        "schema_version": SCHEMA_VERSION,
        "healthy": healthy,
        "plugin_ready": plugin_ready,
        "experts_ready": experts_ready,
        "status": "ready" if healthy else "attention_required",
        "hooks_next_step": hooks_next,
        "plugin": bundle["plugin"],
        "adapters": bundle.get("adapters", {}),
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

    bundle_before = plugin_status(source, install_root, state_root)
    if bundle_before.get("status") == "external_conflict":
        return {
            "status": "external_conflict",
            "changed": False,
            "bundle": bundle_before,
            "codex": codex_before,
        }

    snapshot: Path | None = None
    previous_state = read_json(state_path(state_root))
    if not dry_run and install_root.exists():
        snapshot = install_root.parent / f".{OWNER}.snapshot-{uuid.uuid4().hex}"
        shutil.copytree(install_root, snapshot)

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
        raise
    finally:
        if snapshot is not None and snapshot.exists():
            remove_tree_resilient(snapshot)
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
        "bundle": bundle,
        "codex": codex,
        "update_cache": update_cache,
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
    if status == "uninstalled" and not dry_run:
        update_cache_path(state_root).unlink(missing_ok=True)
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
        if not args.dry_run:
            try:
                atomic_append_event(
                    event_log_path(args.state_root),
                    {"mode": args.mode, "status": "failed", "changed": False},
                )
            except OSError:
                pass
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False))
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

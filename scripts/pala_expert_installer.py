#!/usr/bin/env python3
"""Atomic acquisition of Pala-owned expert artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import uuid
from pathlib import Path
from pathlib import PurePosixPath
import stat
import zipfile


PYTHON_EXPERTS = frozenset({"graphify", "serena"})
ZIP_EXPERTS = {
    "codebase-memory": "codebase-memory-mcp.exe",
    "ollama": "ollama.exe",
}


def _safe_part(value: str) -> str:
    if not value or any(part in {"", ".", ".."} for part in Path(value).parts) or Path(value).is_absolute():
        raise ValueError("unsafe expert name or version")
    return value


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def _read_json(path: Path) -> dict[str, object] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _archive_path(name: str) -> PurePosixPath:
    candidate = PurePosixPath(name.replace("\\", "/"))
    if not name or candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise ValueError("unsafe ZIP member path")
    return candidate


def _expanded_zip_status(target: Path, executable: PurePosixPath) -> dict[str, object] | None:
    expanded = target / "expanded"
    marker = _read_json(expanded / "install.json")
    if marker is None or not expanded.is_dir():
        return None
    files = marker.get("files")
    if not isinstance(files, dict):
        return None
    for relative, expected in files.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            return None
        path = expanded.joinpath(*_archive_path(relative).parts)
        if not path.is_file() or _file_hash(path) != expected:
            return None
    executable_path = expanded.joinpath(*executable.parts)
    if not executable_path.is_file():
        return None
    return {"state": "ready", "changed": False, "path": str(expanded), "executable": str(executable_path)}


def inspect_binary(name: str, spec: dict[str, str], state_root: Path) -> dict[str, object]:
    """Report ownership and integrity without writing or using the network."""
    name = _safe_part(name)
    version = _safe_part(spec.get("version", ""))
    target = state_root.resolve() / "experts" / name / version
    marker = _read_json(target / "install.json")
    payload = target / "payload.bin"
    expected_hash = spec.get("sha256", "").casefold()
    if not target.exists():
        return {"state": "missing", "changed": False, "path": str(target)}
    if marker is None or not payload.is_file():
        return {"state": "external_conflict", "changed": False, "path": str(target)}
    if marker.get("sha256") != expected_hash or marker.get("source_url") != spec.get("source_url"):
        return {"state": "external_conflict", "changed": False, "path": str(target)}
    actual = hashlib.sha256(payload.read_bytes()).hexdigest()
    state = "ready" if actual == expected_hash else "external_conflict"
    return {"state": state, "changed": False, "path": str(target)}


def install_binary(
    name: str,
    spec: dict[str, str],
    state_root: Path,
    *,
    dry_run: bool = False,
    fetch=_fetch,
) -> dict[str, object]:
    """Fetch one immutable binary into Pala's own state root, or report its state."""
    name = _safe_part(name)
    version = _safe_part(spec.get("version", ""))
    source_url = spec.get("source_url", "")
    expected_hash = spec.get("sha256", "").casefold()
    if not source_url or len(expected_hash) != 64 or any(char not in "0123456789abcdef" for char in expected_hash):
        raise ValueError("expert spec requires a SHA-256 source artifact")
    target = state_root.resolve() / "experts" / name / version
    marker = target / "install.json"
    payload_path = target / "payload.bin"
    inspection = inspect_binary(name, spec, state_root)
    if inspection["state"] == "ready":
        return inspection
    if target.exists():
        return {"state": "external_conflict", "changed": False, "path": str(target)}
    if dry_run:
        return {"state": "would_install", "changed": False, "path": str(target)}

    payload = fetch(source_url)
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected_hash:
        raise ValueError("expert artifact SHA-256 mismatch")
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{name}.", dir=parent))
    try:
        (staging / "payload.bin").write_bytes(payload)
        (staging / "install.json").write_text(
            json.dumps({"name": name, "version": version, "source_url": source_url, "sha256": actual}, ensure_ascii=True, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {"state": "ready", "changed": True, "path": str(target)}


def expand_verified_zip(
    name: str, spec: dict[str, str], state_root: Path, executable: str
) -> dict[str, object]:
    """Expand a verified Pala-owned ZIP without trusting archive paths or links."""
    name = _safe_part(name)
    version = _safe_part(spec.get("version", ""))
    executable_path = _archive_path(executable)
    inspected = inspect_binary(name, spec, state_root)
    if inspected["state"] != "ready":
        raise ValueError("verified ZIP artifact is required before expansion")
    target = state_root.resolve() / "experts" / name / version
    expanded = target / "expanded"
    if expanded.exists():
        existing = _expanded_zip_status(target, executable_path)
        if existing is not None:
            return existing
        return {"state": "external_conflict", "changed": False, "path": str(expanded)}
    staging = Path(tempfile.mkdtemp(prefix=".expanded-", dir=target))
    try:
        files: dict[str, str] = {}
        with zipfile.ZipFile(target / "payload.bin") as archive:
            for member in archive.infolist():
                relative = _archive_path(member.filename)
                if stat.S_ISLNK(member.external_attr >> 16):
                    raise ValueError("ZIP symbolic links are not allowed")
                destination = staging.joinpath(*relative.parts)
                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, "r") as source, destination.open("xb") as output:
                    shutil.copyfileobj(source, output)
                files[relative.as_posix()] = _file_hash(destination)
        target_executable = staging.joinpath(*executable_path.parts)
        if not target_executable.is_file():
            raise ValueError("verified ZIP does not contain the required executable")
        (staging / "install.json").write_text(
            json.dumps({"files": files}, ensure_ascii=True, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, expanded)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {"state": "ready", "changed": True, "path": str(expanded), "executable": str(expanded.joinpath(*executable_path.parts))}


def install_python_tool(
    name: str,
    spec: dict[str, str],
    state_root: Path,
    *,
    uv: str = "uv",
    run=None,
) -> dict[str, object]:
    """Install a verified wheel in Pala's uv tool and binary roots only."""
    inspected = inspect_binary(name, spec, state_root)
    if inspected["state"] != "ready":
        raise ValueError("verified Python wheel is required before installation")
    root = state_root.resolve() / "experts"
    tool_dir = root / "python-tools"
    bin_dir = root / "python-bin"
    cache_dir = root / "python-cache"
    environment = os.environ.copy()
    environment.update(
        {
            "UV_TOOL_DIR": str(tool_dir),
            "UV_TOOL_BIN_DIR": str(bin_dir),
            "UV_CACHE_DIR": str(cache_dir),
            "UV_PYTHON_DOWNLOADS": "never",
        }
    )
    version = _safe_part(spec.get("version", ""))
    expected_hash = spec.get("sha256", "").casefold()
    source_payload = root / name / version / "payload.bin"
    wheel = root / "python-wheels" / f"{name}-{version}.whl"
    if wheel.exists() and _file_hash(wheel) != expected_hash:
        return {"state": "external_conflict", "changed": False, "path": str(wheel)}
    if not wheel.exists():
        wheel.parent.mkdir(parents=True, exist_ok=True)
        staging = wheel.with_name(f".{wheel.name}.{uuid.uuid4().hex}")
        try:
            shutil.copyfile(source_payload, staging)
            if _file_hash(staging) != expected_hash:
                raise ValueError("verified wheel copy hash mismatch")
            os.replace(staging, wheel)
        except Exception:
            staging.unlink(missing_ok=True)
            raise
    command = (
        uv,
        "tool",
        "install",
        "--force",
        "--python",
        sys.executable,
        "--no-python-downloads",
        "--no-build",
        "--link-mode",
        "copy",
        str(wheel),
    )
    if run is None:
        completed = subprocess.run(command, check=False, env=environment, timeout=600)
        code = completed.returncode
    else:
        result = run(command, environment)
        code = result.returncode if hasattr(result, "returncode") else int(result)
    if code != 0:
        raise RuntimeError(f"Pala-owned Python tool installation failed: {name}")
    return {
        "state": "ready",
        "changed": True,
        "path": str(tool_dir),
        "bin_dir": str(bin_dir),
    }


def install_expert_suite(
    lock: dict[str, dict[str, str]],
    state_root: Path,
    *,
    dry_run: bool = False,
    fetch=_fetch,
    uv: str = "uv",
    run=None,
) -> dict[str, object]:
    """Install Pala's explicitly allowlisted expert workers, never arbitrary lock entries."""
    experts: dict[str, dict[str, object]] = {}
    names = tuple(sorted(PYTHON_EXPERTS | set(ZIP_EXPERTS)))
    for name in names:
        spec = lock.get(name)
        if not isinstance(spec, dict):
            raise ValueError(f"managed expert is missing from the lock: {name}")
        experts[name] = install_binary(name, spec, state_root, dry_run=dry_run, fetch=fetch)
    if dry_run:
        return {"state": "would_install", "changed": False, "experts": experts}
    for name in sorted(PYTHON_EXPERTS):
        experts[name] = install_python_tool(name, lock[name], state_root, uv=uv, run=run)
    for name, executable in ZIP_EXPERTS.items():
        experts[name] = expand_verified_zip(name, lock[name], state_root, executable)
    return {"state": "ready", "changed": any(bool(item.get("changed")) for item in experts.values()), "experts": experts}


def _load_lock(path: Path) -> dict[str, dict[str, str]]:
    raw = _read_json(path)
    tools = raw.get("tools") if raw else None
    if not isinstance(tools, dict):
        raise ValueError("managed tools lock is invalid")
    result: dict[str, dict[str, str]] = {}
    for name, item in tools.items():
        if not isinstance(name, str) or not isinstance(item, dict):
            raise ValueError("managed tools lock contains an invalid entry")
        result[name] = {str(key): str(value) for key, value in item.items()}
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("action", choices=("install", "doctor"))
    result.add_argument("--lock", type=Path, required=True)
    result.add_argument("--state-root", type=Path, required=True)
    result.add_argument("--uv", default="uv")
    result.add_argument("--dry-run", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        lock = _load_lock(args.lock)
        if args.action == "doctor":
            payload = {name: inspect_binary(name, lock[name], args.state_root) for name in sorted(PYTHON_EXPERTS | set(ZIP_EXPERTS))}
            report: dict[str, object] = {"state": "ready" if all(item["state"] == "ready" for item in payload.values()) else "attention_required", "experts": payload}
        else:
            report = install_expert_suite(lock, args.state_root, dry_run=args.dry_run, uv=args.uv)
    except (OSError, RuntimeError, ValueError) as error:
        print(json.dumps({"state": "failed", "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["state"] in {"ready", "would_install"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

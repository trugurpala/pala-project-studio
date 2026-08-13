#!/usr/bin/env python3
"""Verified, versioned Workbench artifact transactions with truthful inventory."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


@dataclass(frozen=True)
class ArtifactSpec:
    capability_id: str
    provider: str
    version: str
    source_url: str
    sha256: str
    owner: str

    def __post_init__(self) -> None:
        for value in (self.capability_id, self.provider, self.version, self.owner):
            if not value or Path(value).is_absolute() or any(
                part in {"", ".", ".."} for part in Path(value).parts
            ):
                raise ValueError("unsafe Workbench artifact identity")
        parsed = urlparse(self.source_url)
        if (
            parsed.scheme.casefold() != "https"
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Workbench artifact source must be credential-free HTTPS")
        digest = self.sha256.casefold()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("Workbench artifact requires a SHA-256 digest")


def _safe_relative(value: str) -> PurePosixPath:
    candidate = PurePosixPath(value.replace("\\", "/"))
    if (
        not value
        or candidate.is_absolute()
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise ValueError("unsafe Workbench archive path")
    return candidate


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_object(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
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


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=90) as response:
        return response.read()


def _paths(spec: ArtifactSpec, state_root: Path) -> tuple[Path, Path, Path]:
    base = state_root.resolve() / "workbench" / spec.capability_id
    target = base / "versions" / spec.version
    return base, target, base / "active.json"


def _owned_version(spec: ArtifactSpec, target: Path, executable: str) -> dict[str, object] | None:
    marker = _read_object(target / "pala-install.json")
    if marker is None:
        return None
    if any(
        marker.get(key) != expected
        for key, expected in (
            ("capability_id", spec.capability_id),
            ("provider", spec.provider),
            ("version", spec.version),
            ("source_url", spec.source_url),
            ("sha256", spec.sha256.casefold()),
            ("owner", spec.owner),
        )
    ):
        return None
    files = marker.get("files")
    if not isinstance(files, dict):
        return None
    for relative, expected_hash in files.items():
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            return None
        candidate = target.joinpath(*_safe_relative(relative).parts)
        if not candidate.is_file() or _sha256_file(candidate) != expected_hash:
            return None
    executable_path = target.joinpath(*_safe_relative(executable).parts)
    if not executable_path.is_file():
        return None
    health = marker.get("health")
    if not isinstance(health, dict) or health.get("status") != "passed":
        return None
    return marker


def inventory(
    spec: ArtifactSpec, state_root: Path, *, executable: str
) -> dict[str, object]:
    """Inspect only Pala-owned state; foreign or modified material is never adopted."""
    base, target, active_path = _paths(spec, state_root)
    active = _read_object(active_path)
    if active is None:
        if target.exists():
            return {"state": "foreign", "health": "not-run", "path": str(target)}
        return {"state": "absent", "health": "not-run", "path": str(target)}
    active_version = active.get("version")
    if active.get("owner") != spec.owner:
        return {"state": "foreign", "health": "blocked", "path": str(base)}
    if active_version != spec.version:
        return {
            "state": "old",
            "version": active_version,
            "health": "not-run",
            "path": str(base / "versions" / str(active_version)),
        }
    marker = _owned_version(spec, target, executable)
    if marker is None:
        return {
            "state": "foreign",
            "version": spec.version,
            "health": "blocked",
            "path": str(target),
        }
    return {
        "state": "exact",
        "version": spec.version,
        "health": "passed",
        "integrity": f"sha256:{spec.sha256.casefold()}",
        "ownership": spec.owner,
        "provenance": spec.source_url,
        "path": str(target),
        "evidence": marker.get("health"),
    }


def install_zip_transaction(
    spec: ArtifactSpec,
    state_root: Path,
    *,
    executable: str,
    fetch=_fetch,
    health_probe=None,
) -> dict[str, object]:
    """Inventory, stage, verify, probe, and atomically activate one immutable ZIP."""
    existing = inventory(spec, state_root, executable=executable)
    if existing["state"] == "exact":
        return {**existing, "changed": False}
    if existing["state"] == "foreign":
        return {**existing, "changed": False, "reason": "foreign-active-provider-preserved"}
    base, target, active_path = _paths(spec, state_root)
    if target.exists():
        return {
            "state": "foreign",
            "health": "blocked",
            "changed": False,
            "path": str(target),
        }

    payload = fetch(spec.source_url)
    if not isinstance(payload, bytes):
        raise TypeError("Workbench artifact fetch must return bytes")
    actual = _sha256_bytes(payload)
    if actual != spec.sha256.casefold():
        raise ValueError("Workbench artifact SHA-256 mismatch")

    versions = target.parent
    versions.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{spec.version}.stage-", dir=versions))
    activated = False
    previous_active = active_path.read_bytes() if active_path.is_file() else None
    try:
        files: dict[str, str] = {}
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for member in archive.infolist():
                relative = _safe_relative(member.filename)
                if stat.S_ISLNK(member.external_attr >> 16):
                    raise ValueError("Workbench ZIP symbolic links are not allowed")
                destination = staging.joinpath(*relative.parts)
                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member, "r") as source, destination.open("xb") as output:
                    shutil.copyfileobj(source, output)
                files[relative.as_posix()] = _sha256_file(destination)
        required = staging.joinpath(*_safe_relative(executable).parts)
        if not required.is_file():
            raise ValueError("Workbench ZIP does not contain its required executable")
        if health_probe is None:
            raise ValueError("Workbench activation requires an explicit health probe")
        health = health_probe(staging)
        if (
            not isinstance(health, dict)
            or health.get("status") != "passed"
            or str(health.get("version")) != spec.version
        ):
            raise RuntimeError("Workbench artifact health probe failed")
        marker: dict[str, object] = {
            **asdict(spec),
            "sha256": actual,
            "files": files,
            "health": health,
            "activation_policy": "pala-versioned-atomic-no-global-path",
        }
        _atomic_json(staging / "pala-install.json", marker)
        os.replace(staging, target)
        activated = True
        _atomic_json(
            active_path,
            {
                "capability_id": spec.capability_id,
                "owner": spec.owner,
                "version": spec.version,
                "path": str(target),
                "integrity": f"sha256:{actual}",
            },
        )
    except Exception:
        if activated and target.exists():
            shutil.rmtree(target)
        if previous_active is None:
            active_path.unlink(missing_ok=True)
        elif not active_path.is_file() or active_path.read_bytes() != previous_active:
            restore = active_path.with_name(f".{active_path.name}.restore")
            restore.write_bytes(previous_active)
            os.replace(restore, active_path)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {**inventory(spec, state_root, executable=executable), "changed": True}

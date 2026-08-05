#!/usr/bin/env python3
"""Atomic acquisition of Pala-owned expert artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import uuid
from pathlib import Path


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

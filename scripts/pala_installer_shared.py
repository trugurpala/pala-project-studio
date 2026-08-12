#!/usr/bin/env python3
"""Shared constants and durable local-state primitives for the Pala installer."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1
OWNER = "pala-project-studio"
PLUGIN_ID = f"{OWNER}@{OWNER}"
OFFICIAL_REPOSITORY = "https://github.com/trugurpala/pala-project-studio"
OFFICIAL_AUTHOR = "https://github.com/trugurpala"
STATE_NAME, UPDATE_CACHE_NAME = "install-state.json", "update-cache.json"
EVENT_LOG_NAME = "installer-events.jsonl"
MAX_EVENT_LOG_BYTES = 256 * 1024
REQUIRED_FILES = (
    Path(".agents/plugins/marketplace.json"),
    Path(".codex-plugin/plugin.json"),
    Path("scripts/pala_installer_codex.py"),
    *map(
        Path,
        (
            "scripts/pala_installer_shared.py",
            "scripts/pala_installer_integrity.py",
            "scripts/pala_installer_core.py",
            "scripts/pala_installer_transaction.py",
        ),
    ),
    *map(
        Path,
        (
            "scripts/pala_quality.py",
            "scripts/pala_quality_discovery.py",
            "scripts/pala_quality_policy.py",
            "scripts/pala_quality_runner.py",
        ),
    ),
    Path("scripts/pala_state.py"),
    *map(
        Path,
        (
            "scripts/pala_state_core.py",
            "scripts/pala_state_documents.py",
            "scripts/pala_state_cli.py",
        ),
    ),
    Path("scripts/pala_state_git.py"),
    Path("scripts/pala_cold_packet_packet.py"),
    Path("scripts/pala_hook.py"),
    Path("scripts/pala_hook_session.py"),
    Path("scripts/pala_view_styles.py"),
    Path("scripts/pala_view_layout.py"),
    Path("hooks/hooks.json"),
    Path("skills/pala-project-finisher/SKILL.md"),
)
PACKAGE_DIRECTORIES = (".agents", ".codex-plugin", "hooks", "scripts", "skills")
PACKAGE_FILES = (
    "LICENSE",
    "OPEN_SOURCE.md",
    "THIRD_PARTY_NOTICES.md",
    "managed-tools.lock.json",
    "product-identity.json",
)
FORBIDDEN_PARTS = {".git", ".codex", "__pycache__", ".pytest_cache", ".ruff_cache"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".pem", ".key", ".sqlite"}
FORBIDDEN_BASENAMES = {"credentials.json", "id_rsa"}
SECRET_SHAPED_BASENAME = re.compile(
    r"(?i)^(?:id_rsa(?:\.[^.]+)?|credentials(?:\.[^.]+)?|secrets?(?:\.[^.]+)?)$"
)

def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def emit_json(payload: object, *, indent: int | None = 2) -> None:
    """Write JSON to stdout without crashing on Windows cp1254 consoles.

    Doctor payloads may include U+FFFD after UTF-8/cp1254 pipe mojibake.
    Prefer UTF-8 bytes via ``stdout.buffer``; fall back to text with replace.
    """
    text = json.dumps(payload, ensure_ascii=False, indent=indent, sort_keys=True)
    data = (text + "\n").encode("utf-8", errors="replace")
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is not None:
        buffer.write(data)
        buffer.flush()
        return
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    sys.stdout.write(data.decode(encoding, errors="replace"))
    sys.stdout.flush()


def emit_text(text: str, *, stream: object = sys.stdout) -> None:
    """Write plain text to ``stream`` using UTF-8 bytes when possible."""
    data = str(text).encode("utf-8", errors="replace")
    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        buffer.write(data)
        buffer.flush()
        return
    encoding = getattr(stream, "encoding", None) or "utf-8"
    stream.write(data.decode(encoding, errors="replace"))  # type: ignore[arg-type]
    stream.flush()


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

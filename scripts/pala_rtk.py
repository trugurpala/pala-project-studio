"""Conservative RTK command rewrite helper; no installation or PATH mutation."""

from __future__ import annotations

import os
import re
from pathlib import Path

READ_ONLY = {"rg", "grep"}
GIT_READ_ONLY = {"status", "diff", "log"}
FORBIDDEN = re.compile(r"[;&|`$()<>]|\b(push|commit|checkout|reset|clean|merge|rebase|deploy|publish|install|token|password|secret)\b", re.IGNORECASE)
# Newlines / line separators split PowerShell statements when embedded in rewrite text.
LINE_BREAKS = frozenset("\n\r\u2028\u2029")


def rewrite(command: str, tool_input: dict[str, object], executable: Path | None) -> dict[str, object] | None:
    """Return a copied tool input with only safe command text changed, else None."""
    if executable is None or not executable.is_file() or not isinstance(command, str):
        return None
    if any(ch in LINE_BREAKS for ch in command):
        return None
    trimmed = command.strip()
    if not trimmed or FORBIDDEN.search(trimmed):
        return None
    parts = trimmed.split()
    if not parts or any(any(ch in LINE_BREAKS for ch in part) for part in parts):
        return None
    allowed = parts[0] in READ_ONLY or (parts[0] == "git" and len(parts) > 1 and parts[1] in GIT_READ_ONLY)
    if not allowed:
        return None
    # Rebuild from argv tokens only so whitespace tricks cannot inject a second statement.
    safe_command = " ".join(parts)
    rewritten = dict(tool_input)
    quoted = str(executable).replace('"', '""')
    rewritten["command"] = f'& "{quoted}" rewrite -- {safe_command}'
    rewritten["env"] = {**(tool_input.get("env") if isinstance(tool_input.get("env"), dict) else {}), "RTK_TELEMETRY_DISABLED": "1"}
    return rewritten

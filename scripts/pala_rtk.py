"""Conservative RTK command rewrite helper; no installation or PATH mutation."""

from __future__ import annotations

import os
import re
from pathlib import Path

READ_ONLY = {"rg", "grep"}
GIT_READ_ONLY = {"status", "diff", "log"}
FORBIDDEN = re.compile(r"[;&|`$()<>]|\b(push|commit|checkout|reset|clean|merge|rebase|deploy|publish|install|token|password|secret)\b", re.IGNORECASE)


def rewrite(command: str, tool_input: dict[str, object], executable: Path | None) -> dict[str, object] | None:
    """Return a copied tool input with only safe command text changed, else None."""
    if executable is None or not executable.is_file() or not isinstance(command, str):
        return None
    trimmed = command.strip()
    if not trimmed or FORBIDDEN.search(trimmed):
        return None
    parts = trimmed.split()
    allowed = parts[0] in READ_ONLY or (parts[0] == "git" and len(parts) > 1 and parts[1] in GIT_READ_ONLY)
    if not allowed:
        return None
    rewritten = dict(tool_input)
    quoted = str(executable).replace('"', '""')
    rewritten["command"] = f'& "{quoted}" rewrite -- {trimmed}'
    rewritten["env"] = {**(tool_input.get("env") if isinstance(tool_input.get("env"), dict) else {}), "RTK_TELEMETRY_DISABLED": "1"}
    return rewritten

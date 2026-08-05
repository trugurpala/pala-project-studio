#!/usr/bin/env python3
"""PreToolUse hook that applies only safe, managed RTK rewrites."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from pala_rtk import rewrite


def managed_rtk() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", "")) / "Pala" / "tools" / "rtk" / "0.44.2"
    return root / "rtk.exe"


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    tool_input = event.get("tool_input")
    if event.get("tool_name") != "shell_command" or not isinstance(tool_input, dict):
        print("{}")
        return 0
    command = tool_input.get("command")
    result = rewrite(command, tool_input, managed_rtk()) if isinstance(command, str) else None
    if result is None:
        print("{}")
        return 0
    print(json.dumps({"permissionDecision": "allow", "updatedInput": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

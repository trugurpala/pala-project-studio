"""Safe Codex MCP inspection and opt-in registration."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable

from pala_adapters import AdapterResult

MCP_SPECS = {
    "context7": {
        "name": "context7",
        "command": "npx",
        "args": ["-y", "@upstash/context7-mcp@3.2.5"],
    },
    "playwright-mcp": {
        "name": "playwright-mcp",
        "command": "npx",
        "args": ["-y", "@playwright/mcp@0.0.78"],
    },
}


class CodexMcpAdapter:
    def __init__(self, inspect_config: Callable[[], dict[str, object]] | None = None) -> None:
        self._inspect_config = inspect_config or self._read_config

    @staticmethod
    def _read_config() -> dict[str, object]:
        executable = shutil.which("codex")
        if executable is None:
            raise RuntimeError("Codex CLI is unavailable")
        completed = subprocess.run(
            [executable, "mcp", "list", "--json"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
        if completed.returncode != 0:
            raise RuntimeError("Codex MCP inspection failed")
        import json

        payload = json.loads(completed.stdout)
        return payload if isinstance(payload, dict) else {}

    def inspect(self, spec: dict[str, object]) -> AdapterResult:
        name = spec.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("MCP spec needs a name")
        try:
            payload = self._inspect_config()
        except (OSError, RuntimeError, ValueError):
            return AdapterResult(name, "failed", False, "Codex MCP state cannot be inspected")
        records = payload.get("mcpServers", payload.get("servers", {}))
        if not isinstance(records, dict) or name not in records:
            return AdapterResult(name, "missing", False, "MCP record is absent")
        record = records[name]
        expected = {key: spec[key] for key in ("command", "args") if key in spec}
        actual = {key: record.get(key) for key in expected} if isinstance(record, dict) else {}
        if actual == expected:
            return AdapterResult(name, "ready", False, "exact pinned MCP record exists")
        return AdapterResult(name, "external_conflict", False, "same MCP name has a different user-owned configuration")

    def ensure(self, spec: dict[str, object], dry_run: bool = False) -> AdapterResult:
        current = self.inspect(spec)
        if current.state != "missing" or dry_run:
            return current
        executable = shutil.which("codex")
        if executable is None:
            return AdapterResult(str(spec["name"]), "unsupported", False, "Codex CLI is unavailable")
        args = spec.get("args")
        if not isinstance(args, list) or not all(isinstance(value, str) for value in args):
            raise ValueError("MCP args must be strings")
        completed = subprocess.run(
            [executable, "mcp", "add", str(spec["name"]), "--", str(spec["command"]), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if completed.returncode != 0:
            return AdapterResult(str(spec["name"]), "failed", False, "Codex MCP add failed")
        return AdapterResult(str(spec["name"]), "ready", True, "pinned MCP record added")

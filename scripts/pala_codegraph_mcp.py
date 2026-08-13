#!/usr/bin/env python3
"""Pala-owned, one-tool CodeGraph MCP launcher with no background side effects."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from pala_codegraph import codegraph_environment, runtime_paths


def build_command(project: Path, state_root: Path | None = None) -> tuple[str, ...]:
    runtime = runtime_paths(state_root)
    return (
        str(runtime["node"]),
        str(runtime["entry"]),
        "serve",
        "--path",
        str(project.resolve()),
        "--mcp",
        "--no-watch",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded Pala CodeGraph MCP")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--state-root", type=Path)
    args = parser.parse_args(argv)
    environment = os.environ.copy()
    environment.update(codegraph_environment())
    try:
        completed = subprocess.run(
            build_command(args.project, args.state_root),
            check=False,
            env=environment,
            stdin=None,
            stdout=None,
            stderr=None,
        )
    except OSError:
        return 1
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

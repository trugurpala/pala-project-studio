#!/usr/bin/env python3
"""Quality-runner face for Pala-owned CodeGraph freshness."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pala_codegraph import run_lifecycle


def default_state_root() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise RuntimeError("LOCALAPPDATA is required for Pala-owned Workbench state")
    return Path(local) / "Pala"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", type=Path)
    parser.add_argument("--state-root", type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_lifecycle(
            args.project.resolve(),
            "pre-quality",
            state_root=(args.state_root or default_state_root()).resolve(),
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"status": "blocked", "reason": type(exc).__name__, "sanitized": True}))
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result.get("status") == "passed" and result.get("freshness") == "current" else 2


if __name__ == "__main__":
    raise SystemExit(main())

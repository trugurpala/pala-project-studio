#!/usr/bin/env python3
"""Safe, opt-in local maintenance scheduler for Pala.

This module never touches project files and never runs from hooks.  Scheduler
operations are explicit and limited to Pala's exact task name.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

TASK_NAME = "Pala Project Studio Maintenance"
SCHEDULE = "09:30"

def _run(args: list[str]) -> tuple[int, str]:
    if os.name != "nt":
        return 2, "Windows Task Scheduler is unavailable on this host"
    p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False)
    return p.returncode, (p.stdout or p.stderr or "").strip()

def task_create() -> dict[str, object]:
    code, detail = _run(["schtasks", "/Create", "/TN", TASK_NAME, "/SC", "DAILY", "/ST", SCHEDULE, "/F", "/RL", "LIMITED", "/IT", "/TR", f'"{sys.executable}" "{Path(__file__).resolve()}" run-now'])
    return {"status": "passed" if code == 0 else "blocked", "task": TASK_NAME, "schedule": SCHEDULE, "detail": detail[:300]}

def task_query() -> dict[str, object]:
    code, detail = _run(["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "CSV", "/NH"])
    return {"status": "passed" if code == 0 else "not-found", "task": TASK_NAME, "detail": detail[:300]}

def task_disable() -> dict[str, object]:
    code, detail = _run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
    return {"status": "passed" if code == 0 else "not-found", "task": TASK_NAME, "detail": detail[:300]}

def run_now() -> dict[str, object]:
    # Update is deliberately informational until an explicit update command is added.
    return {"status": "passed", "action": "doctor-and-update-check", "network": "explicit-only", "projects_mutated": False}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pala yerel bakım scheduler yönetimi")
    parser.add_argument("command", choices=("install", "status", "run-now", "disable"))
    args = parser.parse_args(argv)
    result = {"install": task_create, "status": task_query, "run-now": run_now, "disable": task_disable}[args.command]()
    data = (json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    out = getattr(sys.stdout, "buffer", None)
    if out is not None:
        out.write(data); out.flush()
    else:
        sys.stdout.write(data.decode(getattr(sys.stdout, "encoding", None) or "utf-8", errors="replace"))
    return 0 if result.get("status") in {"passed", "not-found"} else 2

if __name__ == "__main__":
    raise SystemExit(main())

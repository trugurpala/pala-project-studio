#!/usr/bin/env python3
"""Cold-start timing for local Pala Doctor / memory / report (milliseconds only).

Optional memory_hit_rate proxy is a ratio 0..1 (no percent claims).
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PLUGIN_ROOT / "scripts"
COMMAND_TIMEOUT_SECONDS = 60
TIMEOUT_EXIT_CODE = 124


def _time_command(command: list[str], *, cwd: Path) -> dict[str, int | str]:
    started = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            shell=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        result = None
    elapsed_ms = int(round((time.perf_counter() - started) * 1000))
    if result is None:
        return {
            "elapsed_ms": max(elapsed_ms, 0),
            "returncode": TIMEOUT_EXIT_CODE,
            "status": "blocked",
        }
    return {
        "elapsed_ms": max(elapsed_ms, 0),
        "returncode": int(result.returncode),
        "status": "passed" if result.returncode == 0 else "failed",
    }


def command_specs(root: Path) -> list[dict[str, object]]:
    py = sys.executable
    scripts = root / "scripts"
    return [
        {
            "name": "doctor",
            "argv": [
                py,
                str(scripts / "pala_installer.py"),
                "doctor",
                "--source",
                str(root),
                "--project-root",
                str(root),
            ],
        },
        {
            "name": "memory",
            "argv": [py, str(scripts / "pala_state.py"), "memory", "--cwd", str(root)],
        },
        {
            "name": "report",
            "argv": [py, str(scripts / "pala_report.py"), "--cwd", str(root)],
        },
    ]


def memory_hit_canary(root: Path) -> dict[str, object]:
    """Session2-style proxy: open INC present and DEBUGGING path exists/readable."""
    from pala_debug_gate import memory_hit_rate, session_memory_hit
    from pala_memory import debugging_brain_summary

    docs = {"debugging": "DEBUGGING.md"}
    summary = debugging_brain_summary(root, docs)
    debug_open = int(summary.get("open") or 0)
    debugging_path = root / "DEBUGGING.md"
    debugging_read = debugging_path.is_file()
    sample = session_memory_hit(debug_open=debug_open, debugging_read=debugging_read)
    opportunities = 1 if sample["opportunity"] else 0
    hits = 1 if sample["hit"] else 0
    aggregate = memory_hit_rate(opportunities=opportunities, hits=hits)
    return {
        "debug_open": debug_open,
        "debugging_read": debugging_read,
        **sample,
        **aggregate,
    }


def run_benchmark(n: int = 3, root: Path | None = None) -> dict[str, object]:
    if n < 1:
        raise ValueError("n must be >= 1")
    root = (root or PLUGIN_ROOT).resolve()
    specs = command_specs(root)
    samples_ms: list[int] = []
    per_command: list[dict[str, object]] = []
    for spec in specs:
        name = str(spec["name"])
        argv = list(spec["argv"])  # type: ignore[arg-type]
        samples: list[dict[str, int | str]] = []
        for _ in range(n):
            samples.append(_time_command(argv, cwd=root))
        times = [int(sample["elapsed_ms"]) for sample in samples]
        statuses = {str(sample["status"]) for sample in samples}
        status = "blocked" if "blocked" in statuses else "failed" if "failed" in statuses else "passed"
        samples_ms.extend(times)
        per_command.append(
            {
                "name": name,
                "samples_ms": times,
                "median_ms": int(statistics.median(times)),
                "status": status,
                "returncodes": [int(sample["returncode"]) for sample in samples],
            }
        )
    hit = memory_hit_canary(root)
    command_statuses = {str(item["status"]) for item in per_command}
    report_status = "blocked" if "blocked" in command_statuses else "failed" if "failed" in command_statuses else "passed"
    report = {
        "n": n,
        "root": str(root),
        "status": report_status,
        "samples_ms": samples_ms,
        "median_ms": int(statistics.median(samples_ms)),
        "commands": per_command,
        "memory_hit_rate": hit.get("memory_hit_rate"),
        "memory_hit": hit,
    }
    # Soft speed percentages are forbidden in this report shape.
    blob = json.dumps(report, ensure_ascii=False)
    if "%" in blob:
        raise RuntimeError("cold-start report must not contain percent claims")
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--n", type=int, default=3, help="Samples per command")
    result.add_argument("--root", type=Path, default=PLUGIN_ROOT)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    report = run_benchmark(n=args.n, root=args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())

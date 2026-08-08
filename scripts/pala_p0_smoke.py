#!/usr/bin/env python3
"""Gate 0 P0 smoke: Windows-friendly E2E → artifacts/codex-compat/p0-smoke.json."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
PLUGIN_ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

ARTIFACT_REL = Path("artifacts") / "codex-compat" / "p0-smoke.json"
EVIDENCE_STATUSES = (
    "passed",
    "failed",
    "blocked",
    "configured-not-verified",
    "not-run",
)


def _plugin_version() -> str:
    try:
        payload = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        return str(payload.get("version") or "unknown")
    except (OSError, json.JSONDecodeError):
        return "unknown"


def _shell_name() -> str:
    return Path(os.environ.get("COMSPEC") or os.environ.get("SHELL") or "unknown").name


def _row(
    *,
    command: str,
    exit_code: int,
    status: str,
    evidence_path: str = "",
    fallback_used: bool = False,
    failure_class: str = "",
    worktree: str = "",
    profile: str = "default",
) -> dict[str, object]:
    if status not in EVIDENCE_STATUSES:
        status = "failed"
    return {
        "plugin_version": _plugin_version(),
        "os": platform.system(),
        "shell": _shell_name(),
        "profile": profile,
        "worktree": worktree,
        "command": command,
        "exit_code": exit_code,
        "status": status,
        "evidence_path": evidence_path,
        "fallback_used": bool(fallback_used),
        "failure_class": failure_class,
    }


def _run_py(script: Path, args: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _seed_project(root: Path) -> None:
    (root / ".codex").mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("# Agents\n\nGate0 smoke.\n", encoding="utf-8", newline="\n")
    (root / "PROJECT.md").write_text("# Project\n\nGate0.\n", encoding="utf-8", newline="\n")
    (root / "PLAN.md").write_text(
        "# Plan\n\n#### GATE0-T1 — smoke lifecycle\n", encoding="utf-8", newline="\n"
    )
    (root / "STATUS.md").write_text(
        "# Status\n\n- Active ticket: GATE0-T1\n- Next: smoke\n",
        encoding="utf-8",
        newline="\n",
    )
    (root / "DECISIONS.md").write_text("# Decisions\n\nNone.\n", encoding="utf-8", newline="\n")
    (root / "DEBUGGING.md").write_text(
        "# Debugging log\n\n## Format\n\n"
        "Symptoms, Root cause, Fix criteria, Proved by, Related files, Date, Status.\n\n"
        "## Incidents\n\n",
        encoding="utf-8",
        newline="\n",
    )
    subprocess.run(
        ["git", "init"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _scan_no_relative_scripts() -> tuple[int, str]:
    skill = PLUGIN_ROOT / "skills" / "pala-project-finisher" / "SKILL.md"
    refs = PLUGIN_ROOT / "skills" / "pala-project-finisher" / "references"
    bad: list[str] = []
    for path in [skill, *sorted(refs.glob("*.md"))]:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "../../scripts/" in text or "..\\..\\scripts\\" in text:
            bad.append(path.as_posix())
    if bad:
        return 1, "relative scripts in: " + ", ".join(bad)
    return 0, "no ../../scripts in skill/refs"


def run_smoke(*, out_path: Path | None = None) -> dict[str, object]:
    import pala_cmd_memory
    import pala_paths

    rows: list[dict[str, object]] = []
    overall_status = "passed"
    overall_failure = ""

    with tempfile.TemporaryDirectory(prefix="pala-p0-smoke-") as temp:
        work = Path(temp) / "project"
        work.mkdir()
        catalog = Path(temp) / "catalog"
        catalog.mkdir()
        db_path = catalog / "pala.sqlite"
        _seed_project(work)

        env = os.environ.copy()
        env["PALA_CATALOG_ROOT"] = str(catalog)
        env["PALA_DB_PATH"] = str(db_path)
        env["PALA_SCRIPTS_DIR"] = str(SCRIPTS)
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        # 1) Launcher resolution
        try:
            resolved = pala_paths.resolve_pala_scripts_dir()
            launcher_ok = (resolved / "pala_state.py").is_file() and resolved == SCRIPTS.resolve()
            rows.append(
                _row(
                    command="pala_paths.resolve_pala_scripts_dir",
                    exit_code=0 if launcher_ok else 1,
                    status="passed" if launcher_ok else "failed",
                    evidence_path=str(resolved),
                    worktree=str(work),
                    failure_class="" if launcher_ok else "wrong_plugin_script_path",
                )
            )
            if not launcher_ok:
                overall_status = "failed"
                overall_failure = "wrong_plugin_script_path"
        except FileNotFoundError as exc:
            rows.append(
                _row(
                    command="pala_paths.resolve_pala_scripts_dir",
                    exit_code=1,
                    status="failed",
                    evidence_path="",
                    worktree=str(work),
                    failure_class="wrong_plugin_script_path",
                )
            )
            overall_status = "failed"
            overall_failure = "wrong_plugin_script_path"
            _ = exc

        # 2) No ../../scripts contract
        code, detail = _scan_no_relative_scripts()
        rows.append(
            _row(
                command="scan skill/refs for ../../scripts",
                exit_code=code,
                status="passed" if code == 0 else "failed",
                evidence_path=detail,
                worktree=str(PLUGIN_ROOT),
                failure_class="" if code == 0 else "wrong_plugin_script_path",
            )
        )
        if code != 0:
            overall_status = "failed"
            overall_failure = "wrong_plugin_script_path"

        state = SCRIPTS / "pala_state.py"
        report = SCRIPTS / "pala_report.py"

        # 3) Lifecycle register → begin → checkpoint → context → complete
        lifecycle_ok = True
        lifecycle_detail = []
        steps = [
            ("register", ["register", "--cwd", str(work)]),
            (
                "begin",
                [
                    "begin",
                    "--cwd",
                    str(work),
                    "--ticket",
                    "GATE0-T1",
                    "--goal",
                    "Gate0 smoke lifecycle",
                    "--session-key",
                    "gate0-session-a",
                ],
            ),
            (
                "checkpoint",
                [
                    "checkpoint",
                    "--cwd",
                    str(work),
                    "--ticket",
                    "GATE0-T1",
                    "--session-key",
                    "gate0-session-a",
                    "--next-action",
                    "complete smoke",
                ],
            ),
            ("context", ["context", "--cwd", str(work), "--session-key", "gate0-session-a"]),
            (
                "recover",
                [
                    "recover",
                    "--cwd",
                    str(work),
                    "--ticket",
                    "GATE0-T1",
                    "--session-key",
                    "gate0-session-a",
                ],
            ),
            (
                "record-verification",
                [
                    "record-verification",
                    "--cwd",
                    str(work),
                    "--ticket",
                    "GATE0-T1",
                    "--session-key",
                    "gate0-session-a",
                    "--status",
                    "passed",
                    "--command",
                    "py -3 scripts/pala_p0_smoke.py",
                ],
            ),
            (
                "complete",
                [
                    "complete",
                    "--cwd",
                    str(work),
                    "--ticket",
                    "GATE0-T1",
                    "--session-key",
                    "gate0-session-a",
                ],
            ),
        ]
        for name, argv in steps:
            result = _run_py(state, argv, cwd=work, env=env)
            lifecycle_detail.append(f"{name}={result.returncode}")
            if result.returncode != 0:
                lifecycle_ok = False
                lifecycle_detail.append((result.stderr or result.stdout or "")[:200])
                break
        rows.append(
            _row(
                command="lifecycle register→begin→checkpoint→context→recover→complete",
                exit_code=0 if lifecycle_ok else 1,
                status="passed" if lifecycle_ok else "failed",
                evidence_path="; ".join(lifecycle_detail),
                worktree=str(work),
            )
        )
        if not lifecycle_ok:
            overall_status = "failed"

        # 4) Fail-closed complete (missing ticket)
        miss = _run_py(
            state,
            [
                "complete",
                "--cwd",
                str(work),
                "--ticket",
                "MISSING-GATE0",
                "--session-key",
                "gate0-session-a",
            ],
            cwd=work,
            env=env,
        )
        err = (miss.stderr or "") + (miss.stdout or "")
        fail_closed_ok = miss.returncode != 0 and (
            "begin" in err.casefold() or "session" in err.casefold() or "goal" in err.casefold()
        ) and not any(token in err.casefold().split() for token in ("bitti", "done", "ok"))
        rows.append(
            _row(
                command="complete missing ticket fail-closed",
                exit_code=miss.returncode,
                status="passed" if fail_closed_ok else "failed",
                evidence_path=err[:300],
                worktree=str(work),
            )
        )
        if not fail_closed_ok:
            overall_status = "failed"

        # 5) Path failure memory blocks second cold session
        cmd = "py -3 ../../scripts/pala_report.py --cwd ."
        err_text = "can't open file '../../scripts/pala_report.py': [Errno 2] No such file"
        first = pala_cmd_memory.remember_and_guard(
            root=work,
            command=cmd,
            exit_code=2,
            stderr=err_text,
            failure_class="wrong_plugin_script_path",
            path=db_path,
        )
        # Cold session 2: new guard call, same DB
        second = pala_cmd_memory.guard_retry(
            command=cmd,
            failure_class="wrong_plugin_script_path",
            stderr=err_text,
            approve_retry=False,
            path=db_path,
        )
        memory_ok = bool(first.get("recorded")) and (not second.get("allowed")) and bool(
            second.get("do_not_retry")
        )
        rows.append(
            _row(
                command="path failure memory blocks second attempt",
                exit_code=0 if memory_ok else 1,
                status="passed" if memory_ok else "failed",
                evidence_path=str(second.get("message") or first.get("hint") or ""),
                worktree=str(work),
                failure_class="wrong_plugin_script_path",
            )
        )
        if not memory_ok:
            overall_status = "failed"
            overall_failure = "wrong_plugin_script_path"

        # 6) pala kontrol et read-only structured statuses
        presence = "passed"  # contract: skill checklist exists; smoke marks presence line intent
        skill = (PLUGIN_ROOT / "skills" / "pala-project-finisher" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        if "Pala burada" not in skill or "kontrol et" not in skill.casefold():
            presence = "failed"
        disc = _run_py(state, ["discover", "--cwd", str(work)], cwd=work, env=env)
        discover_status = "passed" if disc.returncode == 0 else "failed"
        rep = _run_py(report, ["--cwd", str(work)], cwd=work, env=env)
        html_path = work / ".codex" / "pala-status.html"
        if rep.returncode == 0 and html_path.is_file():
            report_status = "passed"
            html_status = "passed"
        elif rep.returncode == 0:
            report_status = "passed"
            html_status = "configured-not-verified"
        else:
            report_status = "failed"
            html_status = "failed"
        for name, status, code in (
            ("kontrol-et presence", presence, 0 if presence == "passed" else 1),
            ("kontrol-et report", report_status, rep.returncode),
            ("kontrol-et discover", discover_status, disc.returncode),
            ("kontrol-et Status HTML path", html_status, 0 if html_path.is_file() else 1),
        ):
            rows.append(
                _row(
                    command=name,
                    exit_code=code,
                    status=status,
                    evidence_path=str(html_path) if "HTML" in name else "",
                    worktree=str(work),
                )
            )
            if status == "failed":
                overall_status = "failed"

    artifact = {
        "plugin_version": _plugin_version(),
        "os": platform.system(),
        "shell": _shell_name(),
        "profile": "default",
        "worktree": "temp",
        "command": "pala_p0_smoke",
        "exit_code": 0 if overall_status == "passed" else 1,
        "status": overall_status,
        "evidence_path": str(out_path or (PLUGIN_ROOT / ARTIFACT_REL)),
        "fallback_used": False,
        "failure_class": overall_failure,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rows": rows,
    }
    target = out_path or (PLUGIN_ROOT / ARTIFACT_REL)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(PLUGIN_ROOT / ARTIFACT_REL),
        help="Output JSON path",
    )
    args = parser.parse_args(argv)
    payload = run_smoke(out_path=Path(args.out))
    print(json.dumps({"status": payload.get("status"), "rows": len(payload.get("rows") or [])}, ensure_ascii=False))
    return 0 if payload.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

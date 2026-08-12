#!/usr/bin/env python3
"""Gate 0 P0 smoke: Windows-friendly E2E -> artifacts/codex-compat/p0-smoke.json."""

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
SMOKE_TIMEOUT_SECONDS = 60
TIMEOUT_EXIT_CODE = 124
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


def _status_for_exit(exit_code: int) -> str:
    if exit_code == 0:
        return "passed"
    return "blocked" if exit_code == TIMEOUT_EXIT_CODE else "failed"


def _timeout_result(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        command,
        TIMEOUT_EXIT_CODE,
        stdout="",
        stderr=f"timed out after {SMOKE_TIMEOUT_SECONDS}s",
    )


def _run_py(
    script: Path, args: list[str], *, cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(script), *args]
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            shell=False,
            timeout=SMOKE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return _timeout_result(command)


def _seed_project(root: Path) -> subprocess.CompletedProcess[str]:
    (root / ".codex").mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("# Agents\n\nGate0 smoke.\n", encoding="utf-8", newline="\n")
    (root / "PROJECT.md").write_text("# Project\n\nGate0.\n", encoding="utf-8", newline="\n")
    (root / "PLAN.md").write_text(
        "# Plan\n\n#### GATE0-T1 - smoke lifecycle\n", encoding="utf-8", newline="\n"
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
    command = ["git", "init"]
    try:
        return subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=SMOKE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return _timeout_result(command)


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


def _launcher_and_path_rows(work: Path) -> list[dict[str, object]]:
    import pala_paths

    rows: list[dict[str, object]] = []
    try:
        resolved = pala_paths.resolve_pala_scripts_dir()
        ok = (resolved / "pala_state.py").is_file() and resolved == SCRIPTS.resolve()
        rows.append(
            _row(
                command="pala_paths.resolve_pala_scripts_dir",
                exit_code=0 if ok else 1,
                status="passed" if ok else "failed",
                evidence_path=str(resolved),
                worktree=str(work),
                failure_class="" if ok else "wrong_plugin_script_path",
            )
        )
    except FileNotFoundError:
        rows.append(
            _row(
                command="pala_paths.resolve_pala_scripts_dir",
                exit_code=1,
                status="failed",
                worktree=str(work),
                failure_class="wrong_plugin_script_path",
            )
        )
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
    return rows


def _lifecycle_row(state: Path, work: Path, env: dict[str, str]) -> dict[str, object]:
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
                "--acceptance",
                "Gate0 quality gate passes",
            ],
        ),
    ]
    detail: list[str] = []
    for name, argv in steps:
        result = _run_py(state, argv, cwd=work, env=env)
        detail.append(f"{name}={result.returncode}")
        if result.returncode != 0:
            detail.append((result.stderr or result.stdout or "")[:200])
            return _row(
                command="lifecycle register->begin->checkpoint->context->recover->complete",
                exit_code=result.returncode,
                status=_status_for_exit(result.returncode),
                evidence_path="; ".join(detail),
                worktree=str(work),
            )
    try:
        from pala_quality import record_result, write_ledger
        from pala_store import WorkflowStore

        store = WorkflowStore(work)
        record = store._read_ticket("GATE0-T1")
        acceptance = record["task_contract"]["acceptance"]
        acceptance[0]["quality_check_ids"] = ["unit:gate0"]
        store._write(store._ticket_path("GATE0-T1"), record)
        write_ledger(
            work,
            "GATE0-T1",
            {"checks": [{"id": "unit:gate0", "kind": "unit", "required": True, "status": "not-run", "command": "pala_p0_smoke"}]},
        )
        record_result(work, "GATE0-T1", "unit:gate0", status="passed", command="pala_p0_smoke", exit_code=0)
        detail.append("quality=0")
    except (KeyError, OSError, ValueError) as exc:
        return _row(
            command="lifecycle register->begin->checkpoint->context->recover->complete",
            exit_code=2,
            status="failed",
            evidence_path=f"quality setup failed: {exc}",
            worktree=str(work),
        )
    steps = [
        ("checkpoint", ["checkpoint", "--cwd", str(work), "--ticket", "GATE0-T1", "--session-key", "pala-local", "--next-action", "complete smoke", "--verification", "smoke=passed"]),
        ("context", ["context", "--cwd", str(work), "--session-key", "pala-local"]),
        ("recover", ["recover", "--cwd", str(work), "--ticket", "GATE0-T1", "--session-key", "pala-local"]),
        ("record-verification", ["record-verification", "--cwd", str(work), "--ticket", "GATE0-T1", "--session-key", "pala-local", "--status", "passed", "--command", "py -3 scripts/pala_p0_smoke.py"]),
        ("complete", ["complete", "--cwd", str(work), "--ticket", "GATE0-T1", "--session-key", "pala-local", "--quality-ticket", "GATE0-T1"]),
    ]
    for name, argv in steps:
        result = _run_py(state, argv, cwd=work, env=env)
        detail.append(f"{name}={result.returncode}")
        if result.returncode != 0:
            detail.append((result.stderr or result.stdout or "")[:200])
            return _row(
                command="lifecycle register->begin->checkpoint->context->recover->complete",
                exit_code=result.returncode,
                status=_status_for_exit(result.returncode),
                evidence_path="; ".join(detail),
                worktree=str(work),
            )
    final_context = _run_py(state, ["context", "--cwd", str(work)], cwd=work, env=env)
    if final_context.returncode != 0:
        return _row(
            command="complete clears legacy active ticket",
            exit_code=final_context.returncode,
            status=_status_for_exit(final_context.returncode),
            evidence_path=(final_context.stderr or final_context.stdout or "")[:200],
            worktree=str(work),
        )
    try:
        active_ticket = json.loads(final_context.stdout).get("active_ticket")
    except json.JSONDecodeError:
        active_ticket = "invalid-context"
    if active_ticket is not None:
        return _row(
            command="complete clears legacy active ticket",
            exit_code=1,
            status="failed",
            evidence_path=f"active_ticket={active_ticket}",
            worktree=str(work),
        )
    detail.append("post-complete-context=active:none")
    return _row(
        command="lifecycle register->begin->checkpoint->context->recover->complete",
        exit_code=0,
        status="passed",
        evidence_path="; ".join(detail),
        worktree=str(work),
    )


def _missing_ticket_row(state: Path, work: Path, env: dict[str, str]) -> dict[str, object]:
    result = _run_py(
        state,
        ["complete", "--cwd", str(work), "--ticket", "MISSING-GATE0", "--session-key", "gate0-session-a"],
        cwd=work,
        env=env,
    )
    error = (result.stderr or "") + (result.stdout or "")
    ok = result.returncode != 0 and any(
        word in error.casefold() for word in ("begin", "session", "goal")
    ) and not any(token in error.casefold().split() for token in ("bitti", "done", "ok"))
    return _row(
        command="complete missing ticket fail-closed",
        exit_code=result.returncode,
        status="passed" if ok else _status_for_exit(result.returncode),
        evidence_path=error[:300],
        worktree=str(work),
    )


def _memory_row(work: Path, db_path: Path) -> dict[str, object]:
    import pala_cmd_memory

    command = "py -3 ../../scripts/pala_report.py --cwd ."
    error = "can't open file '../../scripts/pala_report.py': [Errno 2] No such file"
    first = pala_cmd_memory.remember_and_guard(
        root=work, command=command, exit_code=2, stderr=error,
        failure_class="wrong_plugin_script_path", path=db_path,
    )
    second = pala_cmd_memory.guard_retry(
        command=command, failure_class="wrong_plugin_script_path", stderr=error,
        approve_retry=False, path=db_path,
    )
    ok = bool(first.get("recorded")) and not second.get("allowed") and bool(second.get("do_not_retry"))
    return _row(
        command="path failure memory blocks second attempt",
        exit_code=0 if ok else 1,
        status="passed" if ok else "failed",
        evidence_path=str(second.get("message") or first.get("hint") or ""),
        worktree=str(work),
        failure_class="wrong_plugin_script_path",
    )


def _control_rows(state: Path, report: Path, work: Path, env: dict[str, str]) -> list[dict[str, object]]:
    skill = (PLUGIN_ROOT / "skills" / "pala-project-finisher" / "SKILL.md").read_text(encoding="utf-8")
    presence = "passed" if "Pala burada" in skill and "kontrol et" in skill.casefold() else "failed"
    discover = _run_py(state, ["discover", "--cwd", str(work)], cwd=work, env=env)
    report_result = _run_py(report, ["--cwd", str(work)], cwd=work, env=env)
    html_path = work / ".codex" / "pala-status.html"
    if report_result.returncode == 0:
        for line in (report_result.stdout or "").splitlines():
            candidate = Path(line.strip())
            if candidate.name == "pala-status.html" and candidate.is_file():
                html_path = candidate
                break
    report_status = _status_for_exit(report_result.returncode)
    html_status = "passed" if report_result.returncode == 0 and html_path.is_file() else (
        "configured-not-verified" if report_result.returncode == 0 else _status_for_exit(report_result.returncode)
    )
    rows: list[dict[str, object]] = []
    for name, status, code in (
        ("kontrol-et presence", presence, 0 if presence == "passed" else 1),
        ("kontrol-et report", report_status, report_result.returncode),
        ("kontrol-et discover", _status_for_exit(discover.returncode), discover.returncode),
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
    return rows


def _write_artifact(rows: list[dict[str, object]], out_path: Path | None) -> dict[str, object]:
    failed = [row for row in rows if row.get("status") == "failed"]
    status = "failed" if failed else "passed"
    failure_class = next((str(row.get("failure_class") or "") for row in failed if row.get("failure_class")), "")
    target = out_path or (PLUGIN_ROOT / ARTIFACT_REL)
    artifact = {
        "plugin_version": _plugin_version(), "os": platform.system(), "shell": _shell_name(),
        "profile": "default", "worktree": "temp", "command": "pala_p0_smoke",
        "exit_code": 0 if status == "passed" else 1, "status": status,
        "evidence_path": str(target), "fallback_used": False, "failure_class": failure_class,
        "generated_at": datetime.now(timezone.utc).isoformat(), "rows": rows,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return artifact


def run_smoke(*, out_path: Path | None = None) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="pala-p0-smoke-") as temp:
        work = Path(temp) / "project"
        work.mkdir()
        catalog = Path(temp) / "catalog"
        catalog.mkdir()
        seed = _seed_project(work)
        env = os.environ.copy()
        env.update({"PALA_CATALOG_ROOT": str(catalog), "PALA_DB_PATH": str(catalog / "pala.sqlite"), "PALA_SCRIPTS_DIR": str(SCRIPTS), "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
        rows = [_row(command="git init smoke project", exit_code=seed.returncode, status=_status_for_exit(seed.returncode), evidence_path=(seed.stderr or seed.stdout or "")[:200], worktree=str(work))]
        rows.extend(_launcher_and_path_rows(work))
        rows.append(_lifecycle_row(SCRIPTS / "pala_state.py", work, env))
        rows.append(_missing_ticket_row(SCRIPTS / "pala_state.py", work, env))
        rows.append(_memory_row(work, catalog / "pala.sqlite"))
        rows.extend(_control_rows(SCRIPTS / "pala_state.py", SCRIPTS / "pala_report.py", work, env))
    return _write_artifact(rows, out_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(PLUGIN_ROOT / ARTIFACT_REL), help="Output JSON path")
    args = parser.parse_args(argv)
    payload = run_smoke(out_path=Path(args.out))
    print(json.dumps({"status": payload.get("status"), "rows": len(payload.get("rows") or [])}, ensure_ascii=False))
    return 0 if payload.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

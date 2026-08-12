#!/usr/bin/env python3
"""Bounded shell-free execution adapter for approved Pala Quality checks."""

from __future__ import annotations

import hashlib
import shutil
import subprocess  # nosec B404
import threading
import time
from pathlib import Path
from typing import BinaryIO

from pala_quality import MAX_CHANGED_FILES, read_ledger, record_result
from pala_quality_discovery import changed_paths, surface_digest
from pala_quality_policy import build_quality_plan
from pala_verification_basis import basis_matches, capture_basis

EXECUTION_AUTHORITY = "pala-quality-runner"
MIN_TIMEOUT_SECONDS = 0.01
MAX_TIMEOUT_SECONDS = 300.0


def _find_check(payload: dict[str, object], check_id: str) -> dict[str, object] | None:
    checks = payload.get("checks") if isinstance(payload.get("checks"), list) else []
    return next(
        (
            item
            for item in checks
            if isinstance(item, dict) and str(item.get("id") or "") == check_id
        ),
        None,
    )


def _current_surface_matches(root: Path, ledger: dict[str, object]) -> bool:
    current_files, _ignored = changed_paths(root)
    recorded_files = [str(item) for item in list(ledger.get("changed_files") or [])]
    return recorded_files == current_files[:MAX_CHANGED_FILES] and str(
        ledger.get("surface_digest") or ""
    ) == surface_digest(root, current_files)


def _drain(stream: BinaryIO, result: dict[str, object]) -> None:
    digest = hashlib.sha256()
    total = 0
    try:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
            total += len(chunk)
    finally:
        stream.close()
    result["sha256"] = digest.hexdigest()
    result["bytes"] = total


def run_approved_check(
    root: Path,
    quality_ticket: str,
    check_id: str,
    *,
    timeout_seconds: float = 120.0,
) -> dict[str, object]:
    """Execute one current approved check and persist only mechanical evidence."""
    root = Path(root).resolve()
    if not MIN_TIMEOUT_SECONDS <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise ValueError(
            f"quality timeout must be between {MIN_TIMEOUT_SECONDS} and {MAX_TIMEOUT_SECONDS} seconds"
        )
    ledger = read_ledger(root, quality_ticket)
    recorded = _find_check(ledger, check_id)
    tier = str(ledger.get("tier") or "ticket")
    approved = _find_check(build_quality_plan(root, tier=tier), check_id)
    if not isinstance(recorded, dict) or not isinstance(approved, dict):
        return {"status": "blocked", "detail": "approved quality check was not found"}
    argv = approved.get("argv")
    if (
        not bool(approved.get("required"))
        or not isinstance(argv, list)
        or not argv
        or not all(isinstance(value, str) and value for value in argv)
    ):
        return {"status": "blocked", "detail": "quality check has no approved executable argv"}
    command = subprocess.list2cmdline(argv)
    if (
        approved.get("command") != command
        or recorded.get("command") != command
        or recorded.get("argv") != argv
    ):
        return {"status": "blocked", "detail": "recorded command differs from approved plan"}
    if not _current_surface_matches(root, ledger):
        return {"status": "blocked", "detail": "quality verification surface drifted"}

    before = capture_basis(root)
    started = time.monotonic()
    stdout_result: dict[str, object] = {}
    stderr_result: dict[str, object] = {}
    resolved_executable = shutil.which(argv[0])
    execution_argv = [resolved_executable, *argv[1:]] if resolved_executable else argv
    try:
        # The argv is re-derived from the current approved project contract.
        process = subprocess.Popen(  # nosec B603
            execution_argv,
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except OSError:
        empty_digest = hashlib.sha256(b"").hexdigest()
        record_result(
            root,
            quality_ticket,
            check_id,
            status="failed",
            command=command,
            exit_code=127,
            detail="approved executable could not be started",
            execution_authority=EXECUTION_AUTHORITY,
            execution_basis=before,
            stdout_sha256=empty_digest,
            stdout_bytes=0,
            stderr_sha256=empty_digest,
            stderr_bytes=0,
            duration_ms=max(0, int((time.monotonic() - started) * 1000)),
        )
        return {"status": "blocked", "detail": "approved executable could not be started"}

    if process.stdout is None or process.stderr is None:
        process.kill()
        raise ValueError("quality runner could not capture process output")
    stdout_thread = threading.Thread(
        target=_drain, args=(process.stdout, stdout_result), daemon=True
    )
    stderr_thread = threading.Thread(
        target=_drain, args=(process.stderr, stderr_result), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()
    timed_out = False
    try:
        exit_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        exit_code = process.wait()
    stdout_thread.join()
    stderr_thread.join()
    duration_ms = max(0, int((time.monotonic() - started) * 1000))
    after = capture_basis(root)
    stable_basis = basis_matches(before, after)
    if timed_out:
        status, recorded_exit, detail = "blocked", 124, "approved quality command timed out"
    elif not stable_basis:
        status, recorded_exit, detail = "blocked", exit_code, "quality command changed verification basis"
    elif exit_code == 0:
        status, recorded_exit, detail = "passed", 0, "approved quality command passed"
    else:
        status, recorded_exit, detail = "failed", exit_code, "approved quality command failed"
    record_result(
        root,
        quality_ticket,
        check_id,
        status=status,
        command=command,
        exit_code=recorded_exit,
        detail=detail,
        execution_authority=EXECUTION_AUTHORITY,
        execution_basis=after if stable_basis else before,
        stdout_sha256=str(stdout_result["sha256"]),
        stdout_bytes=int(stdout_result["bytes"]),
        stderr_sha256=str(stderr_result["sha256"]),
        stderr_bytes=int(stderr_result["bytes"]),
        duration_ms=duration_ms,
    )
    return {
        "status": "passed" if status == "passed" else "blocked",
        "exit_code": recorded_exit,
        "detail": detail,
        "execution_authority": EXECUTION_AUTHORITY,
    }


__all__ = ["EXECUTION_AUTHORITY", "run_approved_check"]

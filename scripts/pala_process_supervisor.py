#!/usr/bin/env python3
"""Bounded lifecycle owner for processes started explicitly by Pala."""

from __future__ import annotations

import hashlib
import os
import secrets
import signal
import socket
import subprocess  # nosec B404
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from pala_privacy import private_data_reason

PROCESS_EVIDENCE_SCHEMA = "pala.process_evidence.v1"


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    class _BasicLimitInformation(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _IoCounters(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _ExtendedLimitInformation(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BasicLimitInformation),
            ("IoInfo", _IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    class _BasicAccountingInformation(ctypes.Structure):
        _fields_ = [
            ("TotalUserTime", ctypes.c_longlong),
            ("TotalKernelTime", ctypes.c_longlong),
            ("ThisPeriodTotalUserTime", ctypes.c_longlong),
            ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
            ("TotalPageFaultCount", wintypes.DWORD),
            ("TotalProcesses", wintypes.DWORD),
            ("ActiveProcesses", wintypes.DWORD),
            ("TotalTerminatedProcesses", wintypes.DWORD),
        ]

    class _WindowsJob:
        def __init__(self) -> None:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            self._kernel32 = kernel32
            kernel32.CreateJobObjectW.restype = wintypes.HANDLE
            self._handle = kernel32.CreateJobObjectW(None, None)
            if not self._handle:
                raise ProcessSupervisorError("PROCESS_JOB_CREATE_FAILED")
            information = _ExtendedLimitInformation()
            information.BasicLimitInformation.LimitFlags = 0x00002000
            configured = kernel32.SetInformationJobObject(
                self._handle,
                9,
                ctypes.byref(information),
                ctypes.sizeof(information),
            )
            if not configured:
                kernel32.CloseHandle(self._handle)
                self._handle = None
                raise ProcessSupervisorError("PROCESS_JOB_CONFIG_FAILED")

        def assign(self, process: subprocess.Popen[bytes]) -> None:
            assigned = self._kernel32.AssignProcessToJobObject(
                self._handle, wintypes.HANDLE(int(process._handle))  # type: ignore[attr-defined]
            )
            if not assigned:
                raise ProcessSupervisorError("PROCESS_JOB_ASSIGN_FAILED")

        def active_processes(self) -> int | None:
            if not self._handle:
                return 0
            information = _BasicAccountingInformation()
            ok = self._kernel32.QueryInformationJobObject(
                self._handle,
                1,
                ctypes.byref(information),
                ctypes.sizeof(information),
                None,
            )
            return int(information.ActiveProcesses) if ok else None

        def close(self) -> None:
            if self._handle:
                self._kernel32.CloseHandle(self._handle)
                self._handle = None

else:
    _WindowsJob = None  # type: ignore[misc,assignment]


class ProcessSupervisorError(ValueError):
    """Sanitized process-lifecycle failure with a stable code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code.replace("_", " ").lower())


@dataclass(frozen=True, slots=True)
class ManagedProcess:
    process_id: str
    pid: int
    generation: int
    command_digest: str
    health_port: int | None


@dataclass(frozen=True, slots=True)
class ProcessEvidence:
    schema_version: str
    process_id: str
    pid: int
    generation: int
    command_digest: str
    health_port: int | None
    status: str
    exit_code: int | None
    finding_codes: tuple[str, ...]
    authority: str = "ProcessSupervisor/read-only"
    can_complete: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "process_id": self.process_id,
            "pid": self.pid,
            "generation": self.generation,
            "command_digest": self.command_digest,
            "health_port": self.health_port,
            "status": self.status,
            "exit_code": self.exit_code,
            "finding_codes": list(self.finding_codes),
            "authority": self.authority,
            "can_complete": False,
        }


@dataclass(frozen=True, slots=True)
class _ProcessSpec:
    argv: tuple[str, ...]
    command_digest: str
    health_port: int | None
    startup_timeout_seconds: float
    capture_output: bool
    cwd: str | None


@dataclass(slots=True)
class _OwnedProcess:
    public: ManagedProcess
    handle: subprocess.Popen[bytes]
    spec: _ProcessSpec
    ownership_id: str
    status: str
    job: object | None


def _command_digest(argv: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for item in argv:
        encoded = item.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _port_available(port: int) -> bool:
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _port_healthy(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(0.05)
        return probe.connect_ex(("127.0.0.1", port)) == 0


class ProcessSupervisor:
    """Own exact child handles; arbitrary PIDs are never an authority input."""

    def __init__(self, *, max_processes: int = 4) -> None:
        if isinstance(max_processes, bool) or not isinstance(max_processes, int):
            raise ProcessSupervisorError("PROCESS_CAPACITY_INVALID")
        if not 1 <= max_processes <= 16:
            raise ProcessSupervisorError("PROCESS_CAPACITY_INVALID")
        self.max_processes = max_processes
        self._supervisor_id = secrets.token_hex(16)
        self._owned: dict[str, _OwnedProcess] = {}

    @property
    def active_count(self) -> int:
        return sum(self._is_active(item) for item in self._owned.values())

    def __enter__(self) -> ProcessSupervisor:
        return self

    def __exit__(self, *_args: object) -> None:
        self.shutdown()

    def _validate_spec(
        self,
        argv: list[str] | tuple[str, ...],
        health_port: int | None,
        startup_timeout_seconds: float,
        capture_output: bool,
        cwd: str | Path | None,
    ) -> _ProcessSpec:
        if not isinstance(argv, (list, tuple)) or not 1 <= len(argv) <= 64:
            raise ProcessSupervisorError("PROCESS_ARGV_INVALID")
        if any(not isinstance(item, str) or not item or len(item) > 4096 for item in argv):
            raise ProcessSupervisorError("PROCESS_ARGV_INVALID")
        normalized = tuple(argv)
        if any(private_data_reason(item) for item in normalized[1:]):
            raise ProcessSupervisorError("PRIVATE_ARGUMENT_REJECTED")
        if health_port is not None and (
            isinstance(health_port, bool)
            or not isinstance(health_port, int)
            or not 1 <= health_port <= 65535
        ):
            raise ProcessSupervisorError("PORT_INVALID")
        if (
            isinstance(startup_timeout_seconds, bool)
            or not isinstance(startup_timeout_seconds, (int, float))
            or not 0.01 <= startup_timeout_seconds <= 30.0
        ):
            raise ProcessSupervisorError("STARTUP_TIMEOUT_INVALID")
        if not isinstance(capture_output, bool):
            raise ProcessSupervisorError("PROCESS_CAPTURE_INVALID")
        normalized_cwd: str | None = None
        if cwd is not None:
            if not isinstance(cwd, (str, Path)):
                raise ProcessSupervisorError("PROCESS_CWD_INVALID")
            candidate = Path(cwd).resolve()
            if not candidate.is_dir():
                raise ProcessSupervisorError("PROCESS_CWD_INVALID")
            normalized_cwd = str(candidate)
        return _ProcessSpec(
            normalized,
            _command_digest(normalized),
            health_port,
            float(startup_timeout_seconds),
            capture_output,
            normalized_cwd,
        )

    def start(
        self,
        argv: list[str] | tuple[str, ...],
        *,
        health_port: int | None = None,
        startup_timeout_seconds: float = 5.0,
        capture_output: bool = False,
        cwd: str | Path | None = None,
    ) -> ManagedProcess:
        spec = self._validate_spec(
            argv, health_port, startup_timeout_seconds, capture_output, cwd
        )
        return self._start_spec(spec, generation=1, process_id=None)

    def _start_spec(
        self,
        spec: _ProcessSpec,
        *,
        generation: int,
        process_id: str | None,
    ) -> ManagedProcess:
        if self.active_count >= self.max_processes:
            raise ProcessSupervisorError("PROCESS_CAPACITY_REACHED")
        if spec.health_port is not None and not _port_available(spec.health_port):
            raise ProcessSupervisorError("PORT_IN_USE")
        ownership_id = secrets.token_hex(16)
        logical_id = process_id or hashlib.sha256(
            f"{self._supervisor_id}:{ownership_id}:{spec.command_digest}".encode()
        ).hexdigest()[:32]
        environment = dict(os.environ)
        environment["PALA_PROCESS_OWNERSHIP_ID"] = ownership_id
        stdout_target = subprocess.PIPE if spec.capture_output else subprocess.DEVNULL
        stderr_target = subprocess.PIPE if spec.capture_output else subprocess.DEVNULL
        try:
            if os.name == "nt":
                handle = subprocess.Popen(  # nosec B603
                    spec.argv,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_target,
                    stderr=stderr_target,
                    shell=False,
                    env=environment,
                    cwd=spec.cwd,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                handle = subprocess.Popen(  # nosec B603
                    spec.argv,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_target,
                    stderr=stderr_target,
                    shell=False,
                    env=environment,
                    cwd=spec.cwd,
                    start_new_session=True,
                )
        except OSError:
            raise ProcessSupervisorError("PROCESS_START_FAILED") from None
        job = None
        if os.name == "nt":
            try:
                job = _WindowsJob()
                job.assign(handle)
            except ProcessSupervisorError:
                handle.kill()
                handle.wait(timeout=3)
                if job is not None:
                    job.close()
                raise
        public = ManagedProcess(
            logical_id, handle.pid, generation, spec.command_digest, spec.health_port
        )
        owned = _OwnedProcess(public, handle, spec, ownership_id, "running", job)
        self._owned[logical_id] = owned
        if spec.health_port is not None:
            deadline = time.monotonic() + spec.startup_timeout_seconds
            while time.monotonic() < deadline:
                if handle.poll() is not None:
                    self._terminate_owned(
                        owned, "startup_exit", "PROCESS_EXITED_DURING_STARTUP"
                    )
                    raise ProcessSupervisorError("PROCESS_EXITED_DURING_STARTUP")
                if _port_healthy(spec.health_port):
                    owned.status = "healthy"
                    break
                time.sleep(0.02)
            else:
                self._terminate_owned(owned, "startup_timeout", "HEALTH_TIMEOUT")
                raise ProcessSupervisorError("HEALTH_TIMEOUT")
        return public

    def _get(self, process_id: str) -> _OwnedProcess:
        owned = self._owned.get(process_id)
        if owned is None:
            raise ProcessSupervisorError("PROCESS_NOT_OWNED")
        return owned

    def inspect(self, process_id: str) -> ProcessEvidence:
        owned = self._get(process_id)
        exit_code = owned.handle.poll()
        if exit_code is None:
            return self._evidence(owned, owned.status, None, ())
        descendants = self._job_active_processes(owned)
        if descendants is None:
            owned.status = "orphan_unknown"
            return self._evidence(
                owned, "orphan_unknown", exit_code, ("PROCESS_TREE_STATE_UNKNOWN",)
            )
        if descendants > 0:
            owned.status = "orphan_detected"
            return self._evidence(
                owned, "orphan_detected", exit_code, ("PROCESS_ORPHAN_DETECTED",)
            )
        owned.status = "unexpected_exit"
        return self._evidence(
            owned, "unexpected_exit", exit_code, ("PROCESS_EXITED_UNEXPECTEDLY",)
        )

    def is_running(self, process_id: str) -> bool:
        owned = self._owned.get(process_id)
        return owned is not None and self._is_active(owned)

    def captured_streams(self, process_id: str) -> tuple[BinaryIO, BinaryIO]:
        """Return pipes only for an exact process launched in capture mode."""
        owned = self._get(process_id)
        if not owned.spec.capture_output:
            raise ProcessSupervisorError("PROCESS_CAPTURE_NOT_ENABLED")
        if owned.handle.stdout is None or owned.handle.stderr is None:
            raise ProcessSupervisorError("PROCESS_CAPTURE_UNAVAILABLE")
        return owned.handle.stdout, owned.handle.stderr

    @staticmethod
    def _validated_wait_timeout(timeout_seconds: float) -> float:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 0.01 <= timeout_seconds <= 300.0
        ):
            raise ProcessSupervisorError("WAIT_TIMEOUT_INVALID")
        return float(timeout_seconds)

    def wait(self, process_id: str, *, timeout_seconds: float) -> ProcessEvidence:
        timeout = self._validated_wait_timeout(timeout_seconds)
        owned = self._get(process_id)
        try:
            owned.handle.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return self._terminate_owned(owned, "timeout", "PROCESS_TIMEOUT")
        return self.inspect(owned.public.process_id)

    def wait_for_exit(
        self, process_id: str, *, timeout_seconds: float
    ) -> ProcessEvidence:
        """Wait for an expected batch exit and release its exact owned group."""
        timeout = self._validated_wait_timeout(timeout_seconds)
        owned = self._get(process_id)
        try:
            exit_code = owned.handle.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return self._terminate_owned(owned, "timeout", "PROCESS_TIMEOUT")
        self._close_owned_group(owned)
        status = "completed" if exit_code == 0 else "failed"
        findings = () if exit_code == 0 else ("PROCESS_EXIT_NONZERO",)
        owned.status = status
        self._owned.pop(owned.public.process_id, None)
        return self._evidence(owned, status, exit_code, findings)

    def stop(self, process_id: str) -> ProcessEvidence:
        owned = self._get(process_id)
        return self._terminate_owned(owned, "stopped", "PROCESS_STOPPED")

    def restart(
        self, process_id: str, *, startup_timeout_seconds: float | None = None
    ) -> ManagedProcess:
        owned = self._get(process_id)
        spec = owned.spec
        if startup_timeout_seconds is not None:
            spec = self._validate_spec(
                spec.argv,
                spec.health_port,
                startup_timeout_seconds,
                spec.capture_output,
                spec.cwd,
            )
        generation = owned.public.generation + 1
        self._terminate_owned(owned, "restarting", "PROCESS_RESTARTED")
        return self._start_spec(spec, generation=generation, process_id=process_id)

    def _terminate_owned(
        self, owned: _OwnedProcess, status: str, finding_code: str
    ) -> ProcessEvidence:
        handle = owned.handle
        if os.name == "nt" and owned.job is not None:
            owned.job.close()  # type: ignore[attr-defined]
        elif os.name != "nt":
            with suppress(ProcessLookupError):
                os.killpg(handle.pid, signal.SIGTERM)  # type: ignore[attr-defined]
        elif self._is_active(owned):
            handle.terminate()
        if handle.poll() is None:
            try:
                handle.wait(timeout=3)
            except subprocess.TimeoutExpired:
                handle.kill()
                handle.wait(timeout=3)
        exit_code = handle.poll()
        owned.status = status
        self._owned.pop(owned.public.process_id, None)
        return self._evidence(owned, status, exit_code, (finding_code,))

    def _close_owned_group(self, owned: _OwnedProcess) -> None:
        """Close the exact group after a batch parent exits; never target a PID input."""
        if os.name == "nt" and owned.job is not None:
            owned.job.close()  # type: ignore[attr-defined]
        elif os.name != "nt":
            with suppress(ProcessLookupError):
                os.killpg(owned.handle.pid, signal.SIGTERM)  # type: ignore[attr-defined]

    def _job_active_processes(self, owned: _OwnedProcess) -> int | None:
        if os.name != "nt" or owned.job is None:
            return 0 if owned.handle.poll() is not None else 1
        return owned.job.active_processes()  # type: ignore[attr-defined,no-any-return]

    def _is_active(self, owned: _OwnedProcess) -> bool:
        active = self._job_active_processes(owned)
        return active is None or active > 0

    def shutdown(self) -> tuple[ProcessEvidence, ...]:
        evidence: list[ProcessEvidence] = []
        for process_id in tuple(self._owned):
            evidence.append(self.stop(process_id))
        return tuple(evidence)

    def _evidence(
        self,
        owned: _OwnedProcess,
        status: str,
        exit_code: int | None,
        finding_codes: tuple[str, ...],
    ) -> ProcessEvidence:
        public = owned.public
        return ProcessEvidence(
            PROCESS_EVIDENCE_SCHEMA,
            public.process_id,
            public.pid,
            public.generation,
            public.command_digest,
            public.health_port,
            status,
            exit_code,
            finding_codes,
        )

    def adopt(self, _pid: int, *, ownership_proof: str | None = None) -> None:
        """Fail closed until a verifiable cross-process ownership handshake exists."""
        del ownership_proof
        raise ProcessSupervisorError("OWNERSHIP_PROOF_REQUIRED")


__all__ = [
    "ManagedProcess",
    "PROCESS_EVIDENCE_SCHEMA",
    "ProcessEvidence",
    "ProcessSupervisor",
    "ProcessSupervisorError",
]

#!/usr/bin/env python3
"""M77 contracts for Pala-owned process identity and bounded cleanup."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_process_supervisor import (  # noqa: E402, I001
    ProcessSupervisor,
    ProcessSupervisorError,
)


SLEEP_CODE = "import time; time.sleep(30)"


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def wait_port_released(port: int, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.02)
    return False


class ProcessSupervisorTests(unittest.TestCase):
    def test_launch_is_shell_free_owned_and_evidence_is_private_safe(self) -> None:
        with ProcessSupervisor(max_processes=2) as supervisor:
            managed = supervisor.start([sys.executable, "-c", SLEEP_CODE])
            evidence = supervisor.inspect(managed.process_id)

            self.assertEqual(evidence.status, "running")
            self.assertGreater(evidence.pid, 0)
            self.assertFalse(evidence.can_complete)
            self.assertNotIn(sys.executable, str(evidence.to_dict()))
            with self.assertRaises(FrozenInstanceError):
                evidence.status = "passed"  # type: ignore[misc]

        self.assertFalse(supervisor.is_running(managed.process_id))

    def test_secret_argv_and_arbitrary_pid_control_fail_closed_without_echo(self) -> None:
        supervisor = ProcessSupervisor()
        with self.assertRaises(ProcessSupervisorError) as private:
            supervisor.start([sys.executable, "-c", SLEEP_CODE, "token=top-secret-value"])
        self.assertEqual(private.exception.code, "PRIVATE_ARGUMENT_REJECTED")
        self.assertNotIn("top-secret", str(private.exception))

        foreign = subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", SLEEP_CODE],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        try:
            with self.assertRaises(ProcessSupervisorError) as not_owned:
                supervisor.stop(str(foreign.pid))
            self.assertEqual(not_owned.exception.code, "PROCESS_NOT_OWNED")
            self.assertIsNone(foreign.poll())
        finally:
            foreign.terminate()
            foreign.wait(timeout=5)

    def test_unexpected_exit_is_typed_and_retains_exact_exit_code(self) -> None:
        with ProcessSupervisor() as supervisor:
            managed = supervisor.start([sys.executable, "-c", "raise SystemExit(7)"])
            evidence = supervisor.wait(managed.process_id, timeout_seconds=3)

        self.assertEqual(evidence.status, "unexpected_exit")
        self.assertEqual(evidence.exit_code, 7)
        self.assertIn("PROCESS_EXITED_UNEXPECTEDLY", evidence.finding_codes)

    def test_expected_batch_exit_is_finalized_as_completed(self) -> None:
        supervisor = ProcessSupervisor()
        managed = supervisor.start(
            [sys.executable, "-c", "print('bounded')"], capture_output=True
        )
        stdout, stderr = supervisor.captured_streams(managed.process_id)
        evidence = supervisor.wait_for_exit(managed.process_id, timeout_seconds=3)
        with stdout, stderr:
            self.assertEqual(
                stdout.read(),
                b"bounded\r\n" if sys.platform == "win32" else b"bounded\n",
            )
            self.assertEqual(stderr.read(), b"")
        self.assertEqual(evidence.status, "completed")
        self.assertEqual(evidence.exit_code, 0)
        self.assertFalse(evidence.can_complete)
        self.assertEqual(supervisor.active_count, 0)

    def test_timeout_cancels_only_owned_process_and_leaves_no_live_record(self) -> None:
        with ProcessSupervisor() as supervisor:
            managed = supervisor.start([sys.executable, "-c", SLEEP_CODE])
            evidence = supervisor.wait(managed.process_id, timeout_seconds=0.05)

            self.assertEqual(evidence.status, "timeout")
            self.assertIn("PROCESS_TIMEOUT", evidence.finding_codes)
            self.assertFalse(supervisor.is_running(managed.process_id))

    def test_cancel_restart_and_capacity_are_bounded(self) -> None:
        with ProcessSupervisor(max_processes=1) as supervisor:
            first = supervisor.start([sys.executable, "-c", SLEEP_CODE])
            with self.assertRaises(ProcessSupervisorError) as capacity:
                supervisor.start([sys.executable, "-c", SLEEP_CODE])
            self.assertEqual(capacity.exception.code, "PROCESS_CAPACITY_REACHED")

            second = supervisor.restart(first.process_id, startup_timeout_seconds=1)
            self.assertEqual(second.generation, 2)
            self.assertNotEqual(first.pid, second.pid)
            stopped = supervisor.stop(second.process_id)
            self.assertEqual(stopped.status, "stopped")
            self.assertFalse(supervisor.is_running(second.process_id))

    def test_port_conflict_blocks_before_launch(self) -> None:
        port = free_port()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", port))
            listener.listen()
            with ProcessSupervisor() as supervisor:
                with self.assertRaises(ProcessSupervisorError) as conflict:
                    supervisor.start(
                        [sys.executable, "-c", SLEEP_CODE],
                        health_port=port,
                        startup_timeout_seconds=0.2,
                    )
                self.assertEqual(conflict.exception.code, "PORT_IN_USE")
                self.assertEqual(supervisor.active_count, 0)

    def test_health_probe_and_tree_cleanup_release_grandchild_listener(self) -> None:
        port = free_port()
        server = (
            "import socket,sys,time;"
            "s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);"
            "s.bind(('127.0.0.1',int(sys.argv[1])));s.listen();time.sleep(30)"
        )
        parent = (
            "import subprocess,sys,time;"
            "subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]]);"
            "time.sleep(30)"
        )
        with ProcessSupervisor() as supervisor:
            managed = supervisor.start(
                [sys.executable, "-c", parent, server, str(port)],
                health_port=port,
                startup_timeout_seconds=3,
            )
            self.assertEqual(supervisor.inspect(managed.process_id).status, "healthy")
            supervisor.stop(managed.process_id)

        self.assertTrue(wait_port_released(port))

    def test_orphan_descendant_is_detected_then_cleaned_by_owned_job(self) -> None:
        child = "import time;time.sleep(30)"
        parent = (
            "import subprocess,sys;"
            "subprocess.Popen([sys.executable,'-c',sys.argv[1]])"
        )
        with ProcessSupervisor() as supervisor:
            managed = supervisor.start([sys.executable, "-c", parent, child])
            evidence = supervisor.wait(managed.process_id, timeout_seconds=3)
            self.assertEqual(evidence.status, "orphan_detected")
            self.assertIn("PROCESS_ORPHAN_DETECTED", evidence.finding_codes)
            cleaned = supervisor.stop(managed.process_id)
            self.assertEqual(cleaned.status, "stopped")
            self.assertFalse(supervisor.is_running(managed.process_id))

    def test_startup_exit_cleans_descendant_before_health_error_returns(self) -> None:
        port = free_port()
        delayed_server = (
            "import socket,sys,time;time.sleep(.2);s=socket.socket();"
            "s.bind(('127.0.0.1',int(sys.argv[1])));s.listen();time.sleep(30)"
        )
        parent = (
            "import subprocess,sys;"
            "subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]])"
        )
        with ProcessSupervisor() as supervisor:
            with self.assertRaises(ProcessSupervisorError) as raised:
                supervisor.start(
                    [sys.executable, "-c", parent, delayed_server, str(port)],
                    health_port=port,
                    startup_timeout_seconds=2,
                )
            self.assertEqual(raised.exception.code, "PROCESS_EXITED_DURING_STARTUP")
            self.assertEqual(supervisor.active_count, 0)
        self.assertTrue(wait_port_released(port))

    def test_repeated_context_shutdown_is_idempotent(self) -> None:
        supervisor = ProcessSupervisor(max_processes=2)
        first = supervisor.start([sys.executable, "-c", SLEEP_CODE])
        second = supervisor.start([sys.executable, "-c", SLEEP_CODE])
        evidence = supervisor.shutdown()
        repeated = supervisor.shutdown()

        self.assertEqual(
            {item.process_id for item in evidence},
            {first.process_id, second.process_id},
        )
        self.assertEqual(repeated, ())
        self.assertEqual(supervisor.active_count, 0)


if __name__ == "__main__":
    unittest.main()

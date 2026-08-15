#!/usr/bin/env python3
"""M80 contracts connecting the approved Quality runner to process ownership."""

from __future__ import annotations

import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


class QualityRunnerSupervisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.quality = importlib.import_module("pala_quality")
        cls.runner = importlib.import_module("pala_quality_runner")

    def initialize(self, root: Path, argv: list[str]) -> tuple[str, str]:
        contract = root / ".pala" / "quality.json"
        contract.parent.mkdir(parents=True)
        contract.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "checks": [
                        {
                            "id": "supervised",
                            "kind": "integration",
                            "argv": argv,
                            "tiers": ["ticket"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        ticket, check_id = "M80-QR", "integration:supervised"
        self.quality.write_ledger(
            root, ticket, self.quality.build_quality_plan(root, tier="ticket")
        )
        return ticket, check_id

    def test_runner_routes_approved_argv_through_process_supervisor(self) -> None:
        calls: list[object] = []

        class FakeSupervisor:
            def __init__(self, *, max_processes: int) -> None:
                calls.append(("init", max_processes))

            def start(
                self,
                argv: list[str],
                *,
                capture_output: bool = False,
                cwd: Path | None = None,
            ):
                calls.append(("start", tuple(argv), capture_output, cwd))
                return SimpleNamespace(process_id="owned-quality-process")

            def captured_streams(self, process_id: str):
                calls.append(("streams", process_id))
                return io.BytesIO(b"approved output"), io.BytesIO(b"")

            def wait_for_exit(self, process_id: str, *, timeout_seconds: float):
                calls.append(("wait", process_id, timeout_seconds))
                return SimpleNamespace(
                    status="completed",
                    exit_code=0,
                    to_dict=lambda: {
                        "authority": "ProcessSupervisor/read-only",
                        "status": "completed",
                        "can_complete": False,
                    },
                )

            def shutdown(self):
                calls.append(("shutdown",))
                return ()

        with tempfile.TemporaryDirectory(prefix="pala-quality-supervised-") as temp:
            root = Path(temp)
            ticket, check_id = self.initialize(
                root, [sys.executable, "-c", "raise SystemExit(0)"]
            )
            with mock.patch.object(self.runner, "ProcessSupervisor", FakeSupervisor):
                result = self.runner.run_approved_check(
                    root, ticket, check_id, timeout_seconds=5
                )

        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["process_evidence"]["can_complete"])
        self.assertIn(("init", 1), calls)
        self.assertTrue(any(call[0] == "start" and call[2] for call in calls))
        self.assertIn(("shutdown",), calls)

    def test_timeout_stops_only_the_supervised_quality_process(self) -> None:
        foreign = subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
        )
        try:
            with tempfile.TemporaryDirectory(prefix="pala-quality-timeout-") as temp:
                root = Path(temp)
                ticket, check_id = self.initialize(
                    root, [sys.executable, "-c", "import time; time.sleep(30)"]
                )
                result = self.runner.run_approved_check(
                    root, ticket, check_id, timeout_seconds=0.02
                )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["exit_code"], 124)
            self.assertIsNone(foreign.poll())
            self.assertEqual(result["process_evidence"]["status"], "timeout")
        finally:
            foreign.terminate()
            foreign.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()

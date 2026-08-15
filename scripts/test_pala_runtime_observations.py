#!/usr/bin/env python3
"""M80 contracts for non-authoritative host/process runtime read models."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_host_capability_broker import observe_codex_host  # noqa: E402, I001
from pala_process_supervisor import ProcessEvidence  # noqa: E402
from pala_runtime_observations import (  # noqa: E402
    RuntimeObservationError,
    read_runtime_observations,
    record_host_observation,
    record_process_observation,
    runtime_observation_path,
)


class RuntimeObservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="pala-observations-")
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.root = base / "project"
        self.root.mkdir()
        subprocess.run(
            ["git", "init", "-q"], cwd=self.root, check=True, capture_output=True
        )
        self.environment = patch.dict(
            os.environ, {**os.environ, "LOCALAPPDATA": str(base / "local")}, clear=True
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    @staticmethod
    def process_evidence(index: int = 1) -> ProcessEvidence:
        return ProcessEvidence(
            "pala.process_evidence.v1",
            f"process-{index:02d}",
            1000 + index,
            1,
            f"{index:064x}",
            None,
            "completed",
            0,
            (),
        )

    def test_absent_read_model_is_honest_and_does_not_create_runtime(self) -> None:
        path = runtime_observation_path(self.root)
        runtime_root = path.parents[1]
        self.assertFalse(runtime_root.exists())

        model = read_runtime_observations(self.root)

        self.assertFalse(runtime_root.exists())
        self.assertEqual(model["host"]["status"], "not-run")
        self.assertEqual(model["processes"]["status"], "not-run")
        self.assertFalse(model["host"]["can_complete"])
        self.assertFalse(model["processes"]["can_complete"])

    def test_validated_host_and_process_evidence_round_trip_without_raw_argv(self) -> None:
        snapshot = observe_codex_host(
            available_tools=["apply_patch", "shell_command"],
            evidence_ref="host/observed-tools",
            max_concurrency=2,
        )
        record_host_observation(self.root, snapshot.to_dict())
        record_process_observation(self.root, self.process_evidence())

        model = read_runtime_observations(self.root)
        encoded = json.dumps(model, sort_keys=True)
        self.assertEqual(model["host"]["status"], "passed")
        self.assertEqual(model["processes"]["status"], "passed")
        self.assertNotIn(sys.executable, encoded)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn("argv", encoded)
        self.assertFalse(model["can_complete"])

    def test_private_or_forged_process_evidence_is_rejected_without_echo(self) -> None:
        forged = self.process_evidence().to_dict()
        forged["finding_codes"] = ["C:\\Users\\owner\\secret.txt"]
        with self.assertRaises(RuntimeObservationError) as raised:
            record_process_observation(self.root, forged)
        self.assertEqual(raised.exception.code, "PROCESS_EVIDENCE_INVALID")
        self.assertNotIn("owner", str(raised.exception))

    def test_process_history_is_bounded_to_eight_latest_items(self) -> None:
        for index in range(12):
            record_process_observation(self.root, self.process_evidence(index + 1))

        model = read_runtime_observations(self.root)
        items = model["processes"]["items"]
        self.assertEqual(len(items), 8)
        self.assertEqual(items[-1]["process_id"], "process-12")


if __name__ == "__main__":
    unittest.main()

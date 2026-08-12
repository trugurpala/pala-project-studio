from __future__ import annotations

import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pala_failure_intelligence import (
    get_failure,
    mark_verified,
    normalize_text,
    record_failure,
    retry_decision,
)


class FailureIntelligenceTests(unittest.TestCase):
    def test_redacts_secrets_paths_and_stable_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "pala.sqlite"
            first = record_failure(
                message="Token=abc123 failed at C:\\Users\\Alice\\tmp_run-12345\\x.py",
                command="py -3 scripts/run.py --password=hunter2",
                failure_class="tool_not_found", path=db,
            )
            second = record_failure(
                message="token=other failed at C:\\Users\\Bob\\tmp_run-99999\\x.py",
                command="py -3 scripts/run.py --password=changed",
                failure_class="tool_not_found", path=db,
            )
            self.assertEqual(first.fingerprint, second.fingerprint)
            self.assertNotIn("abc123", first.normalized_message)
            self.assertNotIn("alice", first.normalized_message)
            self.assertEqual(second.occurrence_count, 2)

    def test_normalization_does_not_store_html_or_raw_command(self) -> None:
        normalized = normalize_text("<script>alert(1)</script> C:\\Users\\owner\\secret.txt")
        self.assertNotIn("C:\\", normalized)
        self.assertIn("<script>", normalized)

    def test_fake_verified_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "pala.sqlite"
            item = record_failure(message="boom", command="tool run", path=db)
            with self.assertRaises(ValueError):
                mark_verified(item.fingerprint, {"status": "passed", "exit_code": 1, "evidence_ref": "x"}, path=db)
            with self.assertRaises(ValueError):
                mark_verified(item.fingerprint, {"status": "done", "exit_code": 0, "evidence_ref": "x"}, path=db)

    def test_verified_requires_exit_zero_and_retry_budget_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "pala.sqlite"
            item = record_failure(message="boom", command="tool run", path=db, retry_budget=2)
            self.assertTrue(retry_decision(item.fingerprint, path=db)["allowed"])
            record_failure(message="boom", command="tool run", path=db, retry_budget=2)
            self.assertFalse(retry_decision(item.fingerprint, path=db)["allowed"])
            verified = mark_verified(item.fingerprint, {"status": "passed", "exit_code": 0, "evidence_ref": "quality://x"}, path=db)
            self.assertEqual(verified.resolution_state, "VERIFIED")

    def test_major_tool_version_change_makes_memory_stale(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "pala.sqlite"
            item = record_failure(message="versioned boom", command="tool run", tool_version="1.4.0", path=db)
            changed = record_failure(message="versioned boom", command="tool run", tool_version="2.0.0", path=db)
            self.assertEqual(changed.freshness, "stale")
            self.assertFalse(retry_decision(item.fingerprint, path=db)["allowed"])

    def test_concurrent_writers_share_one_record(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "pala.sqlite"
            def write(index: int):
                del index
                return record_failure(message="same failure", command="tool run", path=db)
            with ThreadPoolExecutor(max_workers=4) as pool:
                records = list(pool.map(write, range(8)))
            self.assertEqual(len({record.fingerprint for record in records}), 1)
            self.assertEqual(get_failure(records[0].fingerprint, path=db).occurrence_count, 8)


if __name__ == "__main__":
    unittest.main()

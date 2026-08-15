from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pala_failure_intelligence import (
    get_failure,
    list_failures,
    mark_verified,
    normalize_text,
    record_failure,
    retry_decision,
    verified_recipes,
)


class FailureIntelligenceTests(unittest.TestCase):
    def test_redacts_secrets_paths_and_stable_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "pala.sqlite"
            first = record_failure(
                message="Token=abc123 failed at C:\\Users\\Alice\\tmp_run-12345\\x.py",
                command="py -3 scripts/run.py --password=hunter2",
                failure_class="tool_not_found",
                path=db,
            )
            second = record_failure(
                message="token=other failed at C:\\Users\\Bob\\tmp_run-99999\\x.py",
                command="py -3 scripts/run.py --password=changed",
                failure_class="tool_not_found",
                path=db,
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
                mark_verified(
                    item.fingerprint,
                    {"status": "passed", "exit_code": 1, "evidence_ref": "x"},
                    path=db,
                )
            with self.assertRaises(ValueError):
                mark_verified(
                    item.fingerprint,
                    {"status": "done", "exit_code": 0, "evidence_ref": "x"},
                    path=db,
                )

    def test_verified_requires_exit_zero_and_retry_budget_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "pala.sqlite"
            item = record_failure(
                message="boom",
                command="tool run",
                resolution_recipe="run focused test then quality gate",
                path=db,
                retry_budget=2,
            )
            self.assertTrue(retry_decision(item.fingerprint, path=db)["allowed"])
            record_failure(message="boom", command="tool run", path=db, retry_budget=2)
            self.assertFalse(retry_decision(item.fingerprint, path=db)["allowed"])
            basis = {
                "status": "passed",
                "exit_code": 0,
                "evidence_ref": "quality/m78-fi",
                "check_id": "unit:m78-failure-intelligence",
                "execution_authority": "pala-quality-runner",
                "surface_digest": "a" * 64,
            }
            verified = mark_verified(item.fingerprint, basis, current_quality_basis=basis, path=db)
            self.assertEqual(verified.resolution_state, "VERIFIED")
            self.assertEqual(len(verified_recipes(basis, path=db)["items"]), 1)
            stale_basis = {**basis, "surface_digest": "b" * 64}
            self.assertEqual(len(verified_recipes(stale_basis, path=db)["items"]), 0)

    def test_major_tool_version_change_makes_memory_stale(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "pala.sqlite"
            item = record_failure(
                message="versioned boom", command="tool run", tool_version="1.4.0", path=db
            )
            changed = record_failure(
                message="versioned boom", command="tool run", tool_version="2.0.0", path=db
            )
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

    def test_fingerprint_includes_scope_exit_tool_and_platform(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "pala.sqlite"
            base = {
                "message": "same boom",
                "command": "tool run",
                "failure_class": "tool_error",
                "tool": "ruff",
                "platform_name": "windows-x64",
                "relevant_surface": "lint",
                "exit_code": 1,
                "path": db,
            }
            fingerprints = {
                record_failure(**base).fingerprint,
                record_failure(**{**base, "exit_code": 2}).fingerprint,
                record_failure(**{**base, "tool": "mypy"}).fingerprint,
                record_failure(**{**base, "platform_name": "linux-x64"}).fingerprint,
                record_failure(**{**base, "relevant_surface": "typecheck"}).fingerprint,
            }
            self.assertEqual(len(fingerprints), 5)

    def test_bearer_credentials_are_fully_redacted(self) -> None:
        normalized = normalize_text(
            "Author"
            + "ization: "
            + "Bear"
            + "er eyJabcdefghijk.eyJmnopqrstuv.more failed"
        )
        self.assertNotIn("eyj", normalized)
        self.assertNotIn("mnopqrst", normalized)
        self.assertIn("redacted-secret", normalized)

    def test_corrupt_project_refs_do_not_crash_update_or_hide_valid_rows(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "pala.sqlite"
            item = record_failure(
                message="boom", command="tool run", project_ref="project-a", path=db
            )
            conn = sqlite3.connect(db)
            try:
                conn.execute(
                    "UPDATE failure_intelligence SET project_refs_json = ? WHERE fingerprint = ?",
                    ("{broken", item.fingerprint),
                )
                conn.commit()
            finally:
                conn.close()
            repaired = record_failure(
                message="boom", command="tool run", project_ref="project-a", path=db
            )
            model = list_failures(project_ref="project-a", path=db)
            self.assertIn("project-a", repaired.project_refs)
            self.assertEqual(model["status"], "passed")
            self.assertEqual(len(model["items"]), 1)

    def test_project_filter_is_exact_and_limit_applies_after_filter(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "pala.sqlite"
            record_failure(message="a1", command="a run", project_ref="project-a", path=db)
            record_failure(message="b1", command="b run", project_ref="project-b", path=db)
            record_failure(message="a2", command="c run", project_ref="project-a", path=db)
            model = list_failures(project_ref="project-a", limit=1, path=db)
            self.assertEqual(len(model["items"]), 1)
            self.assertEqual(model["items"][0]["project_refs"], ["project-a"])
            self.assertFalse(model["can_complete"])
            self.assertEqual(model["authority"], "FailureIntelligence/read-only")

    def test_verified_recipe_rejects_stale_or_untrusted_quality_basis(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "pala.sqlite"
            item = record_failure(message="boom", command="tool run", path=db)
            basis = {
                "status": "passed",
                "exit_code": 0,
                "evidence_ref": "quality/m78-fi",
                "check_id": "unit:m78-failure-intelligence",
                "execution_authority": "pala-quality-runner",
                "surface_digest": "a" * 64,
            }
            with self.assertRaises(ValueError):
                mark_verified(
                    item.fingerprint,
                    {**basis, "execution_authority": "caller"},
                    current_quality_basis=basis,
                    path=db,
                )
            with self.assertRaises(ValueError):
                mark_verified(
                    item.fingerprint,
                    basis,
                    current_quality_basis={**basis, "surface_digest": "b" * 64},
                    path=db,
                )


if __name__ == "__main__":
    unittest.main()

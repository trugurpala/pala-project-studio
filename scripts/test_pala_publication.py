from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pala_publication import generic_cost_guard, repository_hygiene, secret_scan, version_matrix


class PublicationGovernanceTests(unittest.TestCase):
    def test_current_repository_audit_artifact_is_passed_and_secret_free(self) -> None:
        artifact = Path(__file__).resolve().parent.parent / "artifacts" / "publication" / "repository-audit.json"
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["repository_hygiene"]["tracked_junk"], [])
        self.assertEqual(payload["secret_scan"]["findings"], [])

    def test_secret_file_blocks_without_recording_secret_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token = "github_" + "pat_123456789012345678901234"
            (root / ".env").write_text(f"GITHUB_TOKEN={token}\n", encoding="utf-8")
            result = secret_scan(root)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["findings"][0]["rule"], "github-token")
        self.assertNotIn("github_" + "pat_", json.dumps(result))

    def test_historical_user_path_is_classified_without_becoming_current_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "outputs"
            root.mkdir(parents=True)
            (root / "historical.md").write_text("Historical document C:\\Users\\Owner\\Desktop\\old.txt\n", encoding="utf-8")
            result = secret_scan(root.parent)
        self.assertEqual(result["status"], "passed")
        self.assertIn("outputs/historical.md", result["historical_local_paths"])

    def test_tracked_junk_blocks_but_untracked_junk_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "cache.sqlite").write_bytes(b"local")
            result = repository_hygiene(root)
        self.assertEqual(result["status"], "configured-not-verified")
        self.assertEqual(result["untracked_junk"], ["cache.sqlite"])

    def test_unknown_visibility_and_paid_path_fail_closed(self) -> None:
        self.assertEqual(generic_cost_guard(visibility=None, billing="known-free", requested_path="ci")["status"], "blocked")
        self.assertEqual(generic_cost_guard(visibility="public", billing="known-free", requested_path="larger-runner")["status"], "blocked")
        self.assertEqual(generic_cost_guard(visibility="public", billing="unknown", requested_path="ci")["status"], "configured-not-verified")

    def test_version_4_to_5_blocks_drift_and_ignores_historical_surface(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("Product 4\n", encoding="utf-8")
            (root / "package.json").write_text('{"version":"5"}\n', encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "historical.md").write_text("Historical release 4\n", encoding="utf-8")
            blocked = version_matrix(root, "5", surfaces={"README": "README.md", "package": "package.json"})
            historical = version_matrix(root, "5", surfaces={"old": "docs/historical.md"})
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["required_drift"], ["README"])
        self.assertEqual(historical["surfaces"]["old"]["status"], "HISTORICAL")


if __name__ == "__main__":
    unittest.main()

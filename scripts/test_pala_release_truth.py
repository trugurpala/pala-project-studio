from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pala_publication import current_publication_matrix
from pala_release_truth import drift_lint, publication_matrix, release_truth, remote_preflight

ROOT = Path(__file__).resolve().parent.parent


class ReleaseTruthTests(unittest.TestCase):
    def test_truth_is_a_coherent_candidate_or_verified_public_release(self) -> None:
        truth = release_truth(ROOT)
        self.assertEqual(truth["authority"], "product-identity.json")
        self.assertEqual(truth["product_version"], "1.1.0")
        if truth["remote_publish"] == "passed":
            self.assertEqual(truth["build_release_state"], "VERIFIED")
            self.assertEqual(truth["remote_observed_state"], "PUBLIC RELEASED")
            self.assertEqual(truth["last_published_version"], "1.1.0")
        else:
            self.assertEqual(truth["build_release_state"], "LOCAL RELEASE CANDIDATE VERIFIED")
            self.assertEqual(truth["remote_observed_state"], "NOT PUBLISHED AS 1.1.0")
            self.assertEqual(truth["last_published_version"], "1.0.0")
            self.assertEqual(truth["remote_publish"], "not-run")
        self.assertEqual(truth["real_remote_deploy"], "not-run")

    def test_matrix_and_drift_are_deterministic(self) -> None:
        self.assertEqual(drift_lint(ROOT)["status"], "passed")
        truth = release_truth(ROOT)
        matrix = publication_matrix(ROOT)
        expected_local = (
            "configured-not-verified" if truth["remote_publish"] == "passed" else "passed"
        )
        self.assertEqual(matrix["local_candidate"]["status"], expected_local)
        self.assertEqual(matrix["public_release"]["status"], "passed")
        self.assertEqual(matrix["public_release"]["version"], truth["last_published_version"])
        self.assertEqual(matrix["remote_publish"], truth["remote_publish"])

    def test_current_publication_matrix_has_no_required_version_drift(self) -> None:
        matrix = current_publication_matrix(ROOT)
        self.assertEqual(matrix["status"], "passed")
        self.assertEqual(matrix["release_truth"]["product_version"], "1.1.0")
        self.assertEqual(matrix["release_truth"]["plugin_base_version"], "1.1.0")
        artifact = json.loads((ROOT / "artifacts" / "release" / "publication-matrix.json").read_text(encoding="utf-8"))
        self.assertEqual(artifact["required_drift"], [])

    def test_remote_preflight_fails_closed_without_network(self) -> None:
        result = remote_preflight(ROOT)
        self.assertEqual(result["status"], "configured-not-verified")
        self.assertEqual(result["network"], "not-run")
        self.assertEqual(result["permissions"], "unknown")

    def test_github_preflight_artifact_is_secret_free_and_complete(self) -> None:
        artifact = ROOT / "artifacts" / "publication" / "github-preflight.json"
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertEqual(payload["repository"]["full_name"], "trugurpala/pala-project-studio")
        self.assertEqual(payload["repository"]["visibility"], "public")
        self.assertEqual(payload["repository"]["default_branch"], "main")
        identity = json.loads((ROOT / "product-identity.json").read_text(encoding="utf-8"))
        self.assertEqual(
            payload["latest_release"]["tag"],
            f"v{identity['last_published_version']}",
        )
        self.assertEqual(payload["wiki"]["status"], "not-applicable")
        self.assertEqual(payload["pages"]["status"], "not-applicable")
        serialized = json.dumps(payload, ensure_ascii=True).casefold()
        for marker in ("authorization:", "bearer ", "gho_", "github_pat_"):
            self.assertNotIn(marker, serialized)


if __name__ == "__main__":
    unittest.main()

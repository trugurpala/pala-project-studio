from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pala_m68_closure import closure_report, manifest

ROOT = Path(__file__).resolve().parent.parent


class M68ClosureTests(unittest.TestCase):
    def test_adversarial_closure_is_local_and_secret_safe(self) -> None:
        result = closure_report(ROOT)
        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["xss_escaped"])
        self.assertTrue(result["diagnostic_redaction"])
        self.assertTrue(result["design_advisory_only"])
        self.assertEqual(result["remote_publish"], "passed")
        self.assertEqual(result["network"], "not-run")

    def test_manifest_has_sealed_candidate_shape_without_publication_claim(self) -> None:
        report = manifest(ROOT, source_tests=558, artifact_hash="a" * 64, closure=closure_report(ROOT))
        self.assertEqual(report["status"], "SEALED LOCAL RELEASE CANDIDATE")
        self.assertEqual(report["reproducible_build"]["status"], "passed")
        self.assertEqual(report["remote_publish"], "not-run")
        self.assertEqual(report["real_remote_deploy"], "not-run")


if __name__ == "__main__":
    unittest.main()

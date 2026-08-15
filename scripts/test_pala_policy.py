from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pala_policy import evaluate_profile, validate_pack

ROOT = Path(__file__).resolve().parent.parent


class PolicyPackTests(unittest.TestCase):
    def test_all_packs_validate_and_have_source_freshness_metadata(self) -> None:
        paths = sorted((ROOT / "policies").glob("*.json"))
        self.assertEqual({path.name for path in paths}, {"accessibility.json", "core-quality.json", "release.json"})
        for path in paths:
            result = validate_pack(path)
            self.assertTrue(result["valid"])
            source = json.loads(path.read_text(encoding="utf-8"))["source"]
            self.assertIn("checked_at", source)
            self.assertIn("freshness_days", source)

    def test_profiles_map_without_mutation_and_unknown_stays_honest(self) -> None:
        before = (ROOT / "policies" / "accessibility.json").read_bytes()
        web = evaluate_profile(ROOT / "policies", "Web", now=datetime(2026, 8, 12, tzinfo=timezone.utc))
        python = evaluate_profile(ROOT / "policies", "Python", now=datetime(2026, 8, 12, tzinfo=timezone.utc))
        release = evaluate_profile(ROOT / "policies", "Release", now=datetime(2026, 8, 12, tzinfo=timezone.utc))
        self.assertGreaterEqual(len(web), 2)
        self.assertGreaterEqual(len(python), 2)
        self.assertGreaterEqual(len(release), 2)
        self.assertTrue(all(item.status in {"not-run", "configured-not-verified"} for item in web + python + release))
        self.assertTrue(any(item.source_status == "configured-not-verified" and item.status == "configured-not-verified" for item in web))
        self.assertEqual(before, (ROOT / "policies" / "accessibility.json").read_bytes())

    def test_stale_verified_local_source_becomes_configured_not_verified(self) -> None:
        payload = json.loads((ROOT / "policies" / "release.json").read_text(encoding="utf-8"))
        payload["source"]["status"] = "verified-local"
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "release.json"
            fixture.write_text(json.dumps(payload), encoding="utf-8")
            result = evaluate_profile(
                fixture.parent,
                "Release",
                now=datetime(2028, 8, 12, tzinfo=timezone.utc),
            )
        self.assertTrue(
            any(item.freshness == "stale" and item.status == "configured-not-verified" for item in result)
        )


if __name__ == "__main__":
    unittest.main()

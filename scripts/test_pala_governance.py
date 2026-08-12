from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pala_governance


ROOT = Path(__file__).resolve().parent.parent


class GovernanceTests(unittest.TestCase):
    def test_repository_governance_and_localization_contract(self) -> None:
        result = pala_governance.validate(ROOT)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["global_installation"], "not-performed")

    def test_imported_donor_files_require_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "inventory.json"
            entry = {key: "x" for key in pala_governance.REQUIRED_DONOR_FIELDS}
            entry["source_paths_reviewed"] = ["src"]
            entry["imported_files"] = ["src/file"]
            entry["local_hashes"] = {}
            path.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")
            problems = pala_governance.validate_inventory(path)
            self.assertIn("entry 0 imported files need local hashes", problems)

    def test_ascii_locale_rejects_non_ascii(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "locales").mkdir()
            (root / "locales" / "en.json").write_text(json.dumps({"locale": "en", "canonical": True, "messages": {"x": "X"}}), encoding="utf-8")
            (root / "locales" / "tr-ascii.json").write_text(json.dumps({"locale": "tr-ascii", "canonical": False, "messages": {"x": "ö"}}), encoding="utf-8")
            self.assertIn("tr-ascii message is not ASCII-safe: x", pala_governance.validate_locales(root))


if __name__ == "__main__":
    unittest.main()

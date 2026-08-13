from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_workbench_migration import inventory_legacy, quarantine_transaction


def _owned(root: Path, name: str, version: str = "1.0.0") -> Path:
    target = root / name / version
    target.mkdir(parents=True)
    payload = target / "payload.bin"
    payload.write_bytes(name.encode())
    (target / "install.json").write_text(
        json.dumps({"name": name, "version": version, "sha256": hashlib.sha256(payload.read_bytes()).hexdigest()}),
        encoding="utf-8",
    )
    return target


class WorkbenchMigrationTests(unittest.TestCase):
    def test_inventory_proves_owned_and_preserves_foreign_modified_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _owned(root, "graphify")
            foreign = root / "ollama" / "1.0.0"
            foreign.mkdir(parents=True)
            (foreign / "user.txt").write_text("keep", encoding="utf-8")
            modified = _owned(root, "serena")
            (modified / "payload.bin").write_bytes(b"changed")
            result = inventory_legacy(root)
        by_name = {item["name"]: item for item in result}
        self.assertEqual(by_name["graphify"]["decision"], "quarantine")
        self.assertEqual(by_name["ollama"]["decision"], "preserve")
        self.assertEqual(by_name["serena"]["decision"], "preserve")

    def test_new_workbench_health_is_required_before_any_move(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _owned(root, "graphify")
            result = quarantine_transaction(root, root / "quarantine", workbench_health=False)
            self.assertEqual(result["status"], "blocked")
            self.assertTrue((root / "graphify").exists())

    def test_post_move_health_failure_rolls_every_owned_root_back(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "experts"
            _owned(root, "graphify")
            _owned(root, "codebase-memory")
            result = quarantine_transaction(
                root,
                Path(temp) / "quarantine",
                workbench_health=True,
                post_health=lambda: False,
            )
            self.assertEqual(result["status"], "rolled-back")
            self.assertTrue((root / "graphify").exists())
            self.assertTrue((root / "codebase-memory").exists())

    def test_success_moves_only_proven_owned_and_serena_becomes_lazy_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "experts"
            _owned(root, "graphify")
            _owned(root, "serena")
            foreign = root / "ollama" / "1.0.0"
            foreign.mkdir(parents=True)
            (foreign / "user.txt").write_text("keep", encoding="utf-8")
            result = quarantine_transaction(
                root, Path(temp) / "quarantine", workbench_health=True, post_health=lambda: True
            )
            self.assertEqual(result["status"], "passed")
            self.assertFalse((root / "graphify").exists())
            self.assertTrue((root / "ollama").exists())
            self.assertEqual(result["serena_profile"], "lazy-absent")


if __name__ == "__main__":
    unittest.main()

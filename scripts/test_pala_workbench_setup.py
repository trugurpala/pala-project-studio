from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_workbench_setup import interpret_intent, setup


class WorkbenchSetupTests(unittest.TestCase):
    def test_natural_language_intents_map_to_fixed_modes(self) -> None:
        cases = {
            "Pala workbench kur": "install",
            "professional araçları yükle": "install",
            "workbench guncelle": "update",
            "Pala onar": "repair",
            "Doctor çalıştır": "doctor",
        }
        for value, expected in cases.items():
            self.assertEqual(interpret_intent(value), expected)
        self.assertEqual(interpret_intent("sil ve yayınla"), "unknown")

    def test_unknown_intent_is_noop(self) -> None:
        calls: list[str] = []
        result = setup("unknown", install_codegraph=lambda: calls.append("cg"), install_semgrep=lambda: calls.append("sg"), doctor=lambda: {})
        self.assertEqual(result["status"], "not-run")
        self.assertEqual(calls, [])

    def test_install_is_ordered_idempotent_and_owner_readable(self) -> None:
        calls: list[str] = []
        result = setup(
            "install",
            install_codegraph=lambda: calls.append("cg") or {"state": "exact", "changed": False},
            install_semgrep=lambda: calls.append("sg") or {"state": "exact", "changed": False},
            doctor=lambda: {"healthy": True, "status": "ready"},
        )
        self.assertEqual(calls, ["cg", "sg"])
        self.assertEqual(result["status"], "ready")
        self.assertFalse(result["changed"])
        self.assertEqual(result["owner_message"], "Pala Workbench hazir. Sizden gereken: Hicbir sey.")

    def test_offline_missing_artifact_is_truthful_and_never_healthy(self) -> None:
        result = setup(
            "install",
            install_codegraph=lambda: {"state": "offline", "changed": False},
            install_semgrep=lambda: {"state": "absent", "changed": False},
            doctor=lambda: {"healthy": False, "status": "attention_required"},
            offline=True,
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "offline-artifact-unavailable")
        self.assertFalse(result["browser_opened"])
        self.assertFalse(result["global_path_mutated"])

    def test_offline_semgrep_gap_preserves_changed_codegraph_without_running_doctor(self) -> None:
        calls: list[str] = []
        result = setup(
            "install",
            install_codegraph=lambda: {"state": "exact", "changed": True},
            install_semgrep=lambda: {"state": "offline", "changed": False},
            doctor=lambda: calls.append("doctor") or {"healthy": True},
            offline=True,
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "offline-artifact-unavailable")
        self.assertTrue(result["changed"])
        self.assertEqual(result["semgrep"]["state"], "offline")
        self.assertEqual(calls, [])

    def test_doctor_mode_never_calls_installers(self) -> None:
        calls: list[str] = []
        result = setup(
            "doctor",
            install_codegraph=lambda: calls.append("cg"),
            install_semgrep=lambda: calls.append("sg"),
            doctor=lambda: {"healthy": True, "status": "ready"},
        )
        self.assertEqual(calls, [])
        self.assertEqual(result["status"], "ready")


if __name__ == "__main__":
    unittest.main()

import contextlib, io, json, threading, unittest
from pathlib import Path
import pala_maintenance, pala_workspace

class MaintenanceWorkspaceTests(unittest.TestCase):
    def test_task_contract_is_exact_and_daily(self):
        self.assertEqual(pala_maintenance.TASK_NAME, "Pala Project Studio Maintenance")
        self.assertEqual(pala_maintenance.SCHEDULE, "09:30")
        self.assertFalse(pala_maintenance.run_now()["projects_mutated"])

    def test_help_is_available_without_network(self):
        with self.assertRaises(SystemExit) as raised:
            pala_maintenance.main(["--help"])
        self.assertEqual(raised.exception.code, 0)

    def test_snapshot_is_redacted_and_hooks_unverified(self):
        payload = pala_workspace.snapshot(Path("C:/project"))
        self.assertNotIn("token", payload)
        self.assertEqual(payload["hooks_trust"], "configured-not-verified")
        self.assertEqual(payload["automation"], "explicit-only")

if __name__ == "__main__": unittest.main()

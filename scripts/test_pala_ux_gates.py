from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pala_owner_cockpit import render_control_center
from pala_ux_gates import VIEWPORTS, validate_control_center_markup, visual_digest


class UxGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.html = render_control_center({"project": "UX", "state": "VERIFYING", "next_action": "Review"})

    def test_accessibility_responsive_and_bounded_contracts(self) -> None:
        result = validate_control_center_markup(self.html)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["viewports"], VIEWPORTS)

    def test_visual_digest_is_deterministic_and_read_only(self) -> None:
        first = visual_digest(self.html)
        second = visual_digest(render_control_center({"project": "UX", "state": "VERIFYING", "next_action": "Review"}))
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)


if __name__ == "__main__":
    unittest.main()

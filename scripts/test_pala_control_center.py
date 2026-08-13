from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pala_owner_cockpit import render_control_center, render_owner_cockpit
from pala_control_center_open import open_if_explicit


class ControlCenterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = {
            "project": "<script>alert(1)</script>",
            "state": "VERIFYING",
            "acceptance_verified": 1,
            "acceptance_total": 2,
            "quality": "passed",
            "environment": "local",
            "delivery": "not-run",
            "live_verification": "not-run",
            "blocker": '<img src=x onerror=alert(1)>',
            "next_action": 'M63-T1 & review "focus"',
            "owner_request": "Nothing",
            "evidence_refs": "QE-1",
        }

    def test_required_information_architecture_and_xss_safety(self) -> None:
        html = render_control_center(self.snapshot)
        for heading in ("Home", "Projects", "Current Work", "Known Problems", "Quality", "Policies", "Release", "History", "Advanced"):
            self.assertIn(heading, html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn('<img src=x onerror=alert(1)>', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("prefers-reduced-motion", html)

    def test_owner_cockpit_keeps_legacy_projection_and_control_center(self) -> None:
        html = render_owner_cockpit(self.snapshot, fragment=True)
        self.assertIn("Pala 1.0 Owner Cockpit", html)
        self.assertIn("Pala Control Center", html)
        self.assertNotIn("confidence", html.casefold())

    def test_release_state_uses_owner_language(self) -> None:
        pending = render_control_center({**self.snapshot, "release_status": "pending"})
        blocked = render_control_center({**self.snapshot, "release_status": "blocked"})
        published = render_control_center({**self.snapshot, "release_status": "published"})
        self.assertIn("GitHub publication is ready for the owner's approval.", pending)
        self.assertIn("Publication stopped safely.", blocked)
        self.assertIn("published and remote-verified", published)

    def test_turkish_owner_cards_and_exact_no_request_text(self) -> None:
        html = render_control_center(self.snapshot)
        for heading in ("Neredeyiz?", "Pala ne yapiyor?", "Problem var mi?", "Sizden ne gerekiyor?"):
            self.assertIn(heading, html)
        self.assertIn("Sizden gereken:\nHicbir sey.", html)
        self.assertIn("PALA CONTROL CENTER", html)

    def test_only_explicit_panel_intent_refreshes_and_opens_exactly_once(self) -> None:
        events: list[str] = []
        refresh = lambda: events.append("refresh") or Path("panel.html")
        opener = lambda _path: events.append("open")
        for intent in ("install", "doctor", "rapor", "open", ""):
            self.assertFalse(open_if_explicit(intent, refresh=refresh, opener=opener))
        self.assertEqual(events, [])
        for intent in ("paneli aç", "paneli ac", "  PANELİ   AÇ  "):
            self.assertTrue(open_if_explicit(intent, refresh=refresh, opener=opener))
        self.assertEqual(events, ["refresh", "open"] * 3)

    def test_public_open_instruction_uses_turkish_owner_phrase(self) -> None:
        report_source = (Path(__file__).resolve().parent / "pala_report.py").read_text(encoding="utf-8")
        self.assertIn('explicit intent "paneli aç" is required', report_source)


if __name__ == "__main__":
    unittest.main()

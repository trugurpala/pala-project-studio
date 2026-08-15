from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pala_owner_cockpit import render_control_center, render_owner_cockpit
from pala_control_center_open import open_if_explicit
from pala_report import main as report_main, write_report
from pala_runtime_observations import runtime_observation_path
from pala_view import render as render_status_view


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
            "product_version": "1.1.1",
        }

    def test_required_information_architecture_and_xss_safety(self) -> None:
        html = render_control_center(self.snapshot)
        for heading in ("Home", "Projects", "Current Work", "Known Problems", "Quality", "Policies", "Release", "History", "Advanced"):
            self.assertIn(heading, html)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertNotIn('<img src=x onerror=alert(1)>', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("prefers-reduced-motion", html)

    def test_status_surface_uses_utf8_turkish_for_primary_navigation_and_actions(self) -> None:
        html = render_status_view(
            {
                "root_name": "örnek",
                "root_path": r"C:\\gizli",
                "stamp": "2026-08-15",
            },
            freshness_fn=lambda _value: "fresh",
        )
        encoded = html.encode("utf-8")
        self.assertEqual(encoded.decode("utf-8"), html)
        for text in ("İçeriğe geç", "Pala Kontrol Merkezi", "Açık tema"):
            self.assertIn(text, html)
        self.assertNotIn("??eri?e ge?", html)
        self.assertNotIn("Pala kontrol ?", html)
        self.assertNotIn("g?ster", html)

    def test_control_center_2_renders_owner_read_models_and_dynamic_milestone(self) -> None:
        snapshot = {
            **self.snapshot,
            "milestones": {
                "M78-T1": {"task_status": "DONE", "workflow_lifecycle": "completed"}
            },
            "queue": {"items": [{"ticket": "M78-T2", "status": "IN_PROGRESS"}], "can_complete": False},
            "context_receipts": {"items": [{"validation_status": "passed"}], "can_complete": False},
            "project_history": {"items": [{"lifecycle": "closed"}], "can_complete": False},
            "failure_intelligence": {"items": [{"failure_class": "timeout<script>"}], "can_complete": False},
            "profiles": {"items": [{"profile_kind": "confidential"}], "can_complete": False},
            "host_capabilities": {"items": [{"capability_id": "local_read", "status": "passed"}], "can_complete": False},
            "host_processes": {"items": [{"status": "healthy"}], "can_complete": False},
            "security_release": {"items": [{"status": "not-run"}], "can_complete": False},
        }
        html = render_control_center(snapshot)
        for label in (
            "Queue",
            "Receipts",
            "Failure Intelligence",
            "Profiles",
            "Host Capabilities",
            "Host & Processes",
            "Security & Release",
        ):
            self.assertIn(label, html)
        self.assertIn("Milestone M78-T1", html)
        self.assertNotIn("Milestone M70-T3", html)
        self.assertNotIn("timeout<script>", html)
        self.assertIn("timeout&lt;script&gt;", html)
        self.assertIn('data-can-complete="false"', html)

    def test_read_models_fail_closed_and_redact_private_findings(self) -> None:
        private_finding = ": ".join(("Authorization", "Bearer")) + " " + "-".join(
            ("top", "secret", "value")
        )
        html = render_control_center(
            {
                **self.snapshot,
                "queue": {
                    "items": [{"ticket": "M80-T4"}],
                    "findings": [r"C:\\Users\\Owner\\private.txt"],
                    "can_complete": True,
                },
                "failure_intelligence": {
                    "items": [{"message": "visible only when read-only"}],
                    "findings": [private_finding],
                    "can_complete": False,
                },
            }
        )
        self.assertNotIn("M80-T4", html)
        self.assertNotIn(r"C:\\Users\\Owner", html)
        self.assertNotIn("top-secret-value", html)
        self.assertIn("READ_MODEL_NOT_READ_ONLY", html)
        self.assertIn("private value hidden", html)

    def test_private_paths_are_hidden_and_untrusted_owner_html_is_not_rendered(self) -> None:
        html = render_control_center(
            {**self.snapshot, "providers": r"C:\Users\Owner\private\provider.json"}
        )
        self.assertNotIn(r"C:\Users", html)
        self.assertIn("private value hidden", html)

        rendered = render_status_view(
            {"root_name": "demo", "owner_cockpit_html": "<script>alert('owned')</script>"},
            freshness_fn=lambda _value: "fresh",
        )
        self.assertNotIn("alert('owned')", rendered)

    def test_owner_cockpit_keeps_legacy_projection_and_control_center(self) -> None:
        html = render_owner_cockpit(self.snapshot, fragment=True)
        self.assertIn("Pala 1.1.1 Owner Cockpit", html)
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
        for intent in (
            "paneli aç",
            "paneli ac",
            "  PANELİ   AÇ  ",
            "Pala panelini aç",
            "Pala paneli",
            "Pala Control Center",
        ):
            self.assertTrue(open_if_explicit(intent, refresh=refresh, opener=opener))
        for intent in ("tarayıcı panelini aç", "uygulamanın admin panelini aç"):
            self.assertFalse(open_if_explicit(intent, refresh=refresh, opener=opener))
        self.assertEqual(events, ["refresh", "open"] * 6)

    def test_public_open_instruction_uses_turkish_owner_phrase(self) -> None:
        report_source = (Path(__file__).resolve().parent / "pala_report.py").read_text(encoding="utf-8")
        self.assertIn('explicit intent "paneli aç" is required', report_source)


    def test_real_report_path_bootstraps_control_center_without_project_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m74-no-project-") as temp:
            root = Path(temp)
            target = write_report(root, root / "control-center.html", catalog_root=root)
            html = target.read_text(encoding="utf-8")

        for required in (
            "Pala 1.2.0",
            "PALA CONTROL CENTER",
            "Neredeyiz?",
            "Pala ne yapiyor?",
            "Problem var mi?",
            "Sizden ne gerekiyor?",
        ):
            self.assertIn(required, html)

    def test_real_report_path_keeps_control_center_for_active_project(self) -> None:
        record = {
            "project_id": "service-desk-mini",
            "project_state": "VERIFYING",
            "product_spec": {"title": "Service Desk Mini"},
            "acceptance_matrix": [{"id": "AC-1"}],
            "quality": {"status": "passed"},
            "owner_request": "Nothing",
        }
        with tempfile.TemporaryDirectory(prefix="pala-m74-active-") as temp, patch(
            "pala_product_cli.load_current_project_contract", return_value=record
        ), patch("pala_milestone_truth.current_milestones", return_value={}):
            root = Path(temp)
            html = write_report(
                root, root / "control-center.html", catalog_root=root
            ).read_text(encoding="utf-8")

        self.assertIn("PALA CONTROL CENTER", html)
        self.assertIn("Service Desk Mini", html)
        self.assertIn("Pala 1.2.0", html)

    def test_report_projects_the_canonical_active_task_into_live_queue(self) -> None:
        canonical = {
            "id": "M80-T4",
            "status": "IN_PROGRESS",
            "next_action": "run-m80-t4-quality",
        }
        with tempfile.TemporaryDirectory(prefix="pala-m80-canonical-") as temp, patch(
            "pala_store.WorkflowStore.active_task_contract", return_value=canonical
        ):
            root = Path(temp)
            html = write_report(
                root, root / "control-center.html", catalog_root=root
            ).read_text(encoding="utf-8")

        self.assertIn("M80-T4", html)
        self.assertIn("IN_PROGRESS", html)

    def test_read_only_report_does_not_create_git_runtime_or_database(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m80-readonly-") as temp:
            base = Path(temp)
            root = base / "project"
            root.mkdir()
            subprocess.run(
                ["git", "init", "-q"], cwd=root, check=True, capture_output=True
            )
            with patch.dict(
                os.environ,
                {**os.environ, "LOCALAPPDATA": str(base / "local")},
                clear=True,
            ):
                runtime_root = runtime_observation_path(root).parents[1]
                self.assertFalse(runtime_root.exists())
                write_report(root, root / "control-center.html", catalog_root=root)
                self.assertFalse(runtime_root.exists())
                self.assertFalse((root / "pala.sqlite").exists())

    def test_real_report_path_keeps_control_center_for_unreadable_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m74-corrupt-") as temp, patch(
            "pala_product_cli.load_current_project_contract",
            side_effect=ValueError("synthetic corrupt state"),
        ):
            root = Path(temp)
            html = write_report(
                root, root / "control-center.html", catalog_root=root
            ).read_text(encoding="utf-8")

        self.assertIn("PALA CONTROL CENTER", html)
        self.assertIn("Pala proje durumunu okuyamadi.", html)
        self.assertNotIn("synthetic corrupt state", html)

    def test_real_cli_explicit_panel_intents_open_one_current_control_center(self) -> None:
        for intent in ("paneli aç", "paneli ac", "Pala panelini aç"):
            with self.subTest(intent=intent), tempfile.TemporaryDirectory(
                prefix="pala-m74-open-"
            ) as temp, patch("pala_report.open_report") as opener, patch.object(
                sys,
                "argv",
                [
                    "pala_report.py",
                    "--cwd",
                    temp,
                    "--out",
                    str(Path(temp) / "control-center.html"),
                    "--open",
                    "--intent",
                    intent,
                ],
            ):
                self.assertEqual(report_main(), 0)
                opener.assert_called_once()
                opened = Path(opener.call_args.args[0])
                html = opened.read_text(encoding="utf-8")
                self.assertIn("PALA CONTROL CENTER", html)
                self.assertIn("Pala 1.2.0", html)

    def test_real_cli_without_explicit_open_never_opens_browser(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-m74-silent-") as temp, patch(
            "pala_report.open_report"
        ) as opener, patch.object(
            sys,
            "argv",
            [
                "pala_report.py",
                "--cwd",
                temp,
                "--out",
                str(Path(temp) / "control-center.html"),
            ],
        ):
            self.assertEqual(report_main(), 0)
            opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()

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

from pala_codegraph import evaluate_freshness
from pala_control_center_open import open_if_explicit
from pala_orchestrator import RouteRequest, route
from pala_owner_cockpit import render_control_center
from pala_playwright import validate_browser_evidence
from pala_quality import build_quality_plan
from pala_semgrep import evaluate_findings, language_coverage
from pala_workbench_migration import quarantine_transaction
from pala_workbench_setup import setup


def _owned(root: Path, name: str) -> Path:
    target = root / name / "1.0.0"
    target.mkdir(parents=True)
    payload = target / "payload.bin"
    payload.write_bytes(name.encode("utf-8"))
    (target / "install.json").write_text(
        json.dumps(
            {
                "name": name,
                "version": "1.0.0",
                "sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    return target


class WorkbenchAdversarialMatrixTests(unittest.TestCase):
    def test_quality_plan_maps_the_executable_workbench_migration_matrix(self) -> None:
        plan = build_quality_plan(
            SCRIPTS.parent,
            tier="milestone",
            changed_files=["scripts/pala_workbench_migration.py"],
        )
        check = next(item for item in plan["checks"] if item["id"] == "migration:workbench-adversarial")
        self.assertEqual(
            check["command"],
            "py -3 -m unittest scripts.test_pala_workbench_adversarial -v",
        )
        self.assertTrue(check["required"])
        self.assertFalse(any(item["id"] == "migration:risk-surface" for item in plan["checks"]))

    def test_clean_then_idempotent_install_has_no_ui_path_or_remote_side_effects(self) -> None:
        changed = iter((True, False))

        def run_once() -> dict[str, object]:
            current = next(changed)
            return setup(
                "install",
                install_codegraph=lambda: {"state": "exact", "changed": current},
                install_semgrep=lambda: {"state": "exact", "changed": current},
                doctor=lambda: {"healthy": True, "status": "ready"},
            )

        first = run_once()
        second = run_once()
        self.assertTrue(first["changed"])
        self.assertFalse(second["changed"])
        for result in (first, second):
            self.assertEqual(result["status"], "ready")
            self.assertFalse(result["browser_opened"])
            self.assertFalse(result["helper_ui_opened"])
            self.assertFalse(result["global_path_mutated"])
            self.assertEqual(result["remote_publication"], "not-run")
            self.assertEqual(result["deploy"], "not-run")

    def test_foreign_assets_are_preserved_while_owned_assets_are_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "experts"
            _owned(root, "graphify")
            foreign = root / "ollama" / "1.0.0"
            foreign.mkdir(parents=True)
            sentinel = foreign / "user.txt"
            sentinel.write_text("keep", encoding="utf-8")
            result = quarantine_transaction(
                root,
                Path(temp) / "quarantine",
                workbench_health=True,
                post_health=lambda: True,
            )
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["moved"], ["graphify"])
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")

    def test_offline_missing_artifact_is_blocked_without_false_health(self) -> None:
        calls: list[str] = []
        result = setup(
            "install",
            install_codegraph=lambda: {"state": "offline", "changed": False},
            install_semgrep=lambda: calls.append("semgrep") or {"state": "exact"},
            doctor=lambda: calls.append("doctor") or {"healthy": True},
            offline=True,
        )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "offline-artifact-unavailable")
        self.assertEqual(calls, [])

    def test_failed_post_migration_health_rolls_every_owned_asset_back(self) -> None:
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
            self.assertEqual(result["moved"], [])

    def test_orchestration_uses_semantics_and_never_file_count(self) -> None:
        request = RouteRequest(
            lifecycle_stage="pre-quality",
            risk="high",
            semantic_need="security",
            user_intent="verify",
            task_requires_browser=False,
            explicit_current_docs=False,
        )
        result = route(request, {"security_static": "exact/current/passed", "file_count": "999999"})
        self.assertEqual(result["selected"], ["security_static"])
        self.assertNotIn("file_count", result["inputs"])

    def test_stale_graph_falls_back_and_cannot_be_quality_evidence(self) -> None:
        stale = evaluate_freshness(
            {
                "initialized": True,
                "version": "1.5.0",
                "pendingChanges": {"added": 0, "modified": 1, "removed": 0},
                "worktreeMismatch": None,
                "index": {"state": "complete", "pendingRefs": 0, "reindexRecommended": False},
            },
            sync_exit_code=0,
        )
        self.assertEqual(stale["fallback"], "direct-source")
        self.assertFalse(stale["quality_evidence_eligible"])

    def test_semgrep_coverage_and_findings_remain_separate_advisory_truths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "app.py").write_text("eval(user_input)\n", encoding="utf-8")
            (root / "native.cs").write_text("class Native {}\n", encoding="utf-8")
            coverage = language_coverage(root, {"python"})
        candidate = evaluate_findings(
            {
                "results": [{"check_id": "pala.python.dynamic-eval", "path": "app.py"}],
                "errors": [],
            },
            scan_exit_code=1,
        )
        self.assertIn("csharp", coverage["uncovered_languages"])
        self.assertEqual(coverage["status"], "configured-not-verified")
        self.assertEqual(candidate["authority"], "advisory-candidates")
        self.assertFalse(candidate["blocks_acceptance"])

    def test_playwright_evidence_rejects_missing_or_auto_opened_viewer(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("trace.zip", "page.png", "console.json", "network.har"):
                (root / name).write_bytes(b"evidence")
            base = {
                "trace": "trace.zip",
                "screenshot": "page.png",
                "console": "console.json",
                "network": "network.har",
                "browser_version": "Chromium 140.0",
                "ui_opened": False,
                "trace_viewer_opened": False,
            }
            missing = validate_browser_evidence(root, {**base, "network": "missing.har"})
            auto_opened = validate_browser_evidence(root, {**base, "trace_viewer_opened": True})
        self.assertEqual(missing["status"], "blocked")
        self.assertEqual(auto_opened["status"], "blocked")

    def test_only_explicit_panel_intent_opens_once(self) -> None:
        events: list[str] = []
        refresh = lambda: events.append("refresh") or Path("control-center.html")
        opener = lambda _path: events.append("open")
        for value in ("install", "doctor", "rapor", "open", ""):
            self.assertFalse(open_if_explicit(value, refresh=refresh, opener=opener))
        self.assertTrue(open_if_explicit("paneli aç", refresh=refresh, opener=opener))
        self.assertEqual(events, ["refresh", "open"])

    def test_control_center_is_xss_safe_and_read_only(self) -> None:
        html = render_control_center(
            {
                "project": '<script>alert("x")</script>',
                "state": "VERIFYING",
                "blocker": '<img src=x onerror=alert(1)>',
                "owner_request": "Nothing",
                "evidence_refs": "QE-1",
            }
        )
        self.assertNotIn('<script>alert("x")</script>', html)
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html)
        self.assertNotIn("<form", html.casefold())
        self.assertNotIn("contenteditable", html.casefold())
        self.assertNotIn("<input", html.casefold())

    def test_provider_authority_forgery_cannot_decide_done(self) -> None:
        request = RouteRequest("pre-quality", "high", "security", "DONE", False, False)
        result = route(
            request,
            {
                "security_static": "exact/current/passed",
                "provider_authority": "canonical",
                "completion_authority": "provider",
            },
        )
        self.assertEqual(result["provider_authority"], "advisory")
        self.assertEqual(result["completion_authority"], "Pala Quality Engine")
        self.assertFalse(result["can_decide_done"])


if __name__ == "__main__":
    unittest.main()

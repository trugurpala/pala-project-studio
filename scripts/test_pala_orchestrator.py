from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_orchestrator import RouteRequest, route


class SemanticOrchestratorTests(unittest.TestCase):
    def test_primary_contract_has_no_file_count_input(self) -> None:
        self.assertNotIn("file_count", inspect.signature(RouteRequest).parameters)
        self.assertNotIn("file_count", inspect.signature(route).parameters)

    def test_structural_context_uses_fresh_graph_else_direct_source(self) -> None:
        request = RouteRequest(
            lifecycle_stage="implementation-context", risk="medium",
            semantic_need="structural-code-understanding", user_intent="implement",
            task_requires_browser=False, explicit_current_docs=False,
        )
        fresh = route(request, {"code_intelligence": "exact/current/passed"})
        stale = route(request, {"code_intelligence": "exact/stale/passed"})
        self.assertEqual(fresh["selected"], ["code_intelligence"])
        self.assertEqual(stale["selected"], ["direct-source"])

    def test_security_and_browser_follow_lifecycle_and_project_profile(self) -> None:
        security = route(
            RouteRequest("pre-quality", "high", "security", "verify", False, False),
            {"security_static": "exact/current/passed"},
        )
        browser = route(
            RouteRequest("browser-user-journey", "medium", "browser", "test", True, False),
            {"browser_e2e": "exact/current/passed"},
        )
        self.assertEqual(security["selected"], ["security_static"])
        self.assertEqual(browser["selected"], ["browser_e2e"])

    def test_serena_is_only_after_graph_and_source_insufficiency(self) -> None:
        request = RouteRequest("implementation-context", "high", "symbol-precision", "inspect", False, False)
        normal = route(request, {"symbol_precision": "exact/current/passed"})
        exhausted = route(
            request,
            {"code_intelligence": "blocked", "direct-source": "insufficient", "symbol_precision": "exact/current/passed"},
        )
        self.assertEqual(normal["selected"], ["direct-source"])
        self.assertEqual(exhausted["selected"], ["symbol_precision"])

    def test_context7_is_explicit_optional_and_never_core_health(self) -> None:
        request = RouteRequest("third-party-docs", "low", "current-docs", "research", False, True)
        result = route(request, {"current_docs": "external/current/passed"})
        self.assertEqual(result["selected"], ["current_docs"])
        self.assertFalse(result["affects_core_health"])

    def test_completion_authority_is_always_quality_engine(self) -> None:
        request = RouteRequest("pre-quality", "high", "security", "done", False, False)
        result = route(request, {"security_static": "exact/current/passed"})
        self.assertEqual(result["completion_authority"], "Pala Quality Engine")
        self.assertFalse(result["can_decide_done"])


if __name__ == "__main__":
    unittest.main()

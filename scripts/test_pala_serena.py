from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_serena import SERENA_SHA256, SERENA_VERSION, decide_lazy_fallback


class SerenaLazyProfileTests(unittest.TestCase):
    def test_exact_open_contract_is_pinned(self) -> None:
        self.assertEqual(SERENA_VERSION, "1.7.0")
        self.assertEqual(
            SERENA_SHA256,
            "6dbf1459670d96fb0595f84932adef34260a6fe14ba5135b901fdb3c8c76e891",
        )

    def test_not_selected_until_graph_and_source_are_both_insufficient(self) -> None:
        for graph_ok, source_ok in ((True, True), (True, False), (False, True)):
            result = decide_lazy_fallback(
                codegraph_sufficient=graph_ok,
                direct_source_sufficient=source_ok,
                python_version=(3, 13),
                runtime_state="exact",
                health="passed",
            )
            self.assertFalse(result["selected"])
            self.assertEqual(result["next"], "codegraph" if graph_ok else "direct-source")

    def test_exact_healthy_runtime_is_selected_only_for_symbol_precision(self) -> None:
        result = decide_lazy_fallback(
            codegraph_sufficient=False,
            direct_source_sufficient=False,
            python_version=(3, 13),
            runtime_state="exact",
            health="passed",
        )
        self.assertTrue(result["selected"])
        self.assertEqual(result["purpose"], "read-only-symbol-precision")
        self.assertEqual(result["authority"], "advisory")
        self.assertFalse(result["core_health_required"])
        self.assertEqual(
            set(result["forbidden"]),
            {"memory", "dashboard", "paid-backend", "planning", "autonomous-edit", "completion-authority"},
        )

    def test_unsupported_python_or_unavailable_runtime_falls_back(self) -> None:
        for version, state, health in (
            ((3, 10), "exact", "passed"),
            ((3, 15), "exact", "passed"),
            ((3, 13), "absent", "not-run"),
            ((3, 13), "exact", "blocked"),
        ):
            result = decide_lazy_fallback(
                codegraph_sufficient=False,
                direct_source_sufficient=False,
                python_version=version,
                runtime_state=state,
                health=health,
            )
            self.assertFalse(result["selected"])
            self.assertEqual(result["next"], "direct-source")
            self.assertFalse(result["core_health_required"])


if __name__ == "__main__":
    unittest.main()

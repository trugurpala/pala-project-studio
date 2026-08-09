from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pala_hook
import pala_tokens


class SessionStartHostFitTests(unittest.TestCase):
    def test_hooks_json_matches_char_limit(self) -> None:
        hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        session = hooks["hooks"]["SessionStart"][0]["hooks"][0]
        self.assertEqual(
            int(session["additionalContextLimit"]),
            pala_hook.SESSION_CONTEXT_CHAR_LIMIT,
        )

    def test_token_budget_under_host_hard_cap(self) -> None:
        self.assertLessEqual(pala_hook.SESSION_CONTEXT_TOKEN_BUDGET, 900)
        self.assertLess(pala_hook.SESSION_CONTEXT_TOKEN_BUDGET, 1000)

    def test_session_context_prefers_cold_packet_and_stays_in_budget(self) -> None:
        cold = "COLD\nnext=M30-T1\nstale-context=false\n" + ("x" * 1200)
        out = pala_hook.session_context(
            documents={
                "status": "STATUS.md",
                "plan": "PLAN.md",
                "project": "PROJECT.md",
            },
            workflow={
                "active_ticket": "M30-T1",
                "next_action": "write failing test",
                "dirty": False,
                "blockers": [],
            },
            compacted=False,
            project_kind="software",
            health={
                "plugin": "loaded",
                "python": "ready",
                "git": "ready",
                "hook": "running",
            },
            cold_packet_text=cold,
        )
        msg = out["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(msg.startswith(pala_hook.PRESENCE_LINE))
        self.assertIn("COLD", msg)
        self.assertLessEqual(len(msg), pala_hook.SESSION_CONTEXT_CHAR_LIMIT)
        self.assertLessEqual(
            pala_tokens.approx_tokens(msg),
            pala_hook.SESSION_CONTEXT_TOKEN_BUDGET,
        )


if __name__ == "__main__":
    unittest.main()

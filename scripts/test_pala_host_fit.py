from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_session_start_matcher_covers_restore_sources(self) -> None:
        hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        matcher = hooks["hooks"]["SessionStart"][0]["matcher"]
        for source in ("startup", "resume", "clear", "compact"):
            self.assertIn(source, matcher)

    def test_session_end_timeout_within_codex_clamp(self) -> None:
        # Codex SessionEnd default 1s, hard max 3s; values >3 are clamped with a warning.
        hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        session_end = hooks["hooks"]["SessionEnd"][0]["hooks"][0]
        self.assertLessEqual(int(session_end["timeout"]), 3)
        self.assertEqual(int(session_end["timeout"]), 3)

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
        self.assertIn("next=write failing test", msg)
        self.assertLessEqual(len(msg), pala_hook.SESSION_CONTEXT_CHAR_LIMIT)
        self.assertLessEqual(
            pala_tokens.approx_tokens(msg),
            pala_hook.SESSION_CONTEXT_TOKEN_BUDGET,
        )

    def test_resume_and_compact_prefixes_prefer_restore_orientation(self) -> None:
        docs = {"status": "STATUS.md", "plan": "PLAN.md", "project": "PROJECT.md"}
        wf = {
            "active_ticket": "M30-T1",
            "next_action": "continue restore path",
            "dirty": False,
            "blockers": [],
            "needs_reconcile": True,
        }
        cold = "PALA COLD PACKET\nticket=M30-T1\nnext=continue restore path"
        resume = pala_hook.session_context(
            docs,
            wf,
            compacted=False,
            cold_packet_text=cold,
            source="resume",
        )["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Session resumed", resume)
        self.assertIn("next=continue restore path", resume)
        self.assertIn("PALA COLD PACKET", resume)

        compact = pala_hook.session_context(
            docs,
            wf,
            compacted=True,
            cold_packet_text=cold,
            source="compact",
        )["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Context was compacted", compact)
        self.assertIn("active=M30-T1", compact)
        self.assertIn("next=continue restore path", compact)

    def test_precompact_reconcile_survives_owned_ticket_session_start(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".codex").mkdir()
            (root / pala_hook.MANIFEST).write_text(
                json.dumps(
                    {
                        "managed_by": "pala-project-finisher",
                        "documents": {
                            "project": "PROJECT.md",
                            "plan": "PLAN.md",
                            "status": "STATUS.md",
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / pala_hook.WORKFLOW).write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "active_ticket": "M30-T1",
                        "next_action": "finish restore contract",
                        "dirty": True,
                        "needs_reconcile": False,
                        "blockers": [],
                    }
                ),
                encoding="utf-8",
            )
            (root / "STATUS.md").write_text(
                "# Status\n\n## Şu an tek sonraki iş (owner)\n\n"
                "1. finish restore contract\n",
                encoding="utf-8",
            )
            with patch.object(pala_hook, "git_root", return_value=root):
                with (
                    patch(
                        "sys.stdin",
                        io.StringIO(
                            json.dumps(
                                {
                                    "cwd": temp,
                                    "hook_event_name": "PreCompact",
                                    "session_id": "sess-restore-1",
                                }
                            )
                        ),
                    ),
                    patch("sys.stdout", io.StringIO()),
                ):
                    self.assertEqual(pala_hook.main(), 0)
                workflow = json.loads(
                    (root / pala_hook.WORKFLOW).read_text(encoding="utf-8")
                )
                self.assertTrue(workflow["needs_reconcile"])

                owned = {
                    "ticket": "M30-T1",
                    "next_action": "finish restore contract",
                    "dirty": True,
                }
                session_out = io.StringIO()
                with (
                    patch(
                        "sys.stdin",
                        io.StringIO(
                            json.dumps(
                                {
                                    "cwd": temp,
                                    "hook_event_name": "SessionStart",
                                    "source": "compact",
                                    "session_id": "sess-restore-1",
                                }
                            )
                        ),
                    ),
                    patch("sys.stdout", session_out),
                    patch(
                        "pala_hook.WorkflowStore.active_for_session",
                        return_value=owned,
                    ),
                    patch(
                        "pala_hook.WorkflowStore.heartbeat",
                        return_value=None,
                    ),
                ):
                    self.assertEqual(pala_hook.main(), 0)
                message = json.loads(session_out.getvalue())["hookSpecificOutput"][
                    "additionalContext"
                ]
                self.assertIn("Context was compacted", message)
                self.assertIn("active=M30-T1", message)
                self.assertIn("next=finish restore contract", message)
                self.assertIn("PALA COLD PACKET", message)
                # Disk flag must still be true after merge (not dropped by owned ticket).
                workflow_after = json.loads(
                    (root / pala_hook.WORKFLOW).read_text(encoding="utf-8")
                )
                self.assertTrue(workflow_after["needs_reconcile"])


class VibeFirstSessionTests(unittest.TestCase):
    def test_vibe_doc_states_host_trust_boundary(self) -> None:
        text = (ROOT / "docs" / "VIBE_FIRST_SESSION.md").read_text(encoding="utf-8")
        self.assertIn("hook_safety", text)
        self.assertIn("/hooks", text)
        self.assertIn("Pala burada", text)
        self.assertIn("additionalContext", text)
        self.assertIn("token", text.casefold())

    def test_vibe_doc_explains_forget_restore_honestly(self) -> None:
        text = (ROOT / "docs" / "VIBE_FIRST_SESSION.md").read_text(encoding="utf-8")
        self.assertIn("Codex unuttu", text)
        self.assertIn("cold packet", text.casefold())
        self.assertIn("mid-turn", text.casefold())
        scope = (ROOT / "docs" / "CODEX_SCOPE_AND_LIMITS.md").read_text(encoding="utf-8")
        self.assertIn("SessionStart", scope)
        self.assertIn("yapamaz", scope.casefold())

    def test_skill_points_kontrol_reference(self) -> None:
        skill = (
            ROOT / "skills" / "pala-project-finisher" / "SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertIn("references/kontrol-et.md", skill)
        self.assertIn("cold packet", skill.casefold())
        self.assertNotRegex(skill, r"(?i)enlarges?\s+(context|quota)")
        self.assertLessEqual(len(skill.split()), 480)


if __name__ == "__main__":
    unittest.main()

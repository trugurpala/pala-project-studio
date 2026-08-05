#!/usr/bin/env python3
"""Contract tests for Pala-owned expert-worker routing."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def load_experts():
    spec = importlib.util.spec_from_file_location("pala_experts", SCRIPTS / "pala_experts.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("pala_experts.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pala_experts"] = module
    spec.loader.exec_module(module)
    return module


class ExpertRouterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.experts = load_experts()

    def test_symbol_request_uses_read_only_serena_for_supported_language(self) -> None:
        request = self.experts.ExpertRequest(
            root=ROOT,
            task="symbol",
            languages=("python",),
        )
        decision = self.experts.route(request)
        self.assertEqual(decision.primary, "serena")
        self.assertEqual(decision.data_boundary, "local-read-only")

    def test_document_request_uses_graphify_with_local_semantic_boundary(self) -> None:
        request = self.experts.ExpertRequest(root=ROOT, task="docs")
        decision = self.experts.route(request)
        self.assertEqual(decision.primary, "graphify")
        self.assertEqual(decision.data_boundary, "local-ollama-only")

    def test_large_multilingual_architecture_request_uses_codebase_memory(self) -> None:
        request = self.experts.ExpertRequest(
            root=ROOT,
            task="architecture",
            source_files=5100,
            module_roots=3,
            languages=("python", "typescript", "php"),
        )
        self.assertEqual(self.experts.route(request).primary, "codebase-memory")

    def test_general_large_review_keeps_code_review_graph_as_default(self) -> None:
        request = self.experts.ExpertRequest(
            root=ROOT,
            task="review",
            source_files=1000,
        )
        self.assertEqual(self.experts.route(request).primary, "code-review-graph")

    def test_unsupported_symbol_language_has_honest_fallback(self) -> None:
        request = self.experts.ExpertRequest(
            root=ROOT,
            task="symbol",
            languages=("rust",),
        )
        decision = self.experts.route(request)
        self.assertEqual(decision.primary, "direct")
        self.assertEqual(decision.fallbacks, ("git-rg",))

    def test_evidence_requires_a_repo_relative_path_and_positive_line(self) -> None:
        with self.assertRaises(ValueError):
            self.experts.ExpertEvidence(
                tool="graphify",
                path="../outside.py",
                line=1,
                relation="calls",
                confidence="extracted",
            )
        with self.assertRaises(ValueError):
            self.experts.ExpertEvidence(
                tool="serena",
                path="src/service.py",
                line=0,
                relation="reference",
                confidence="unknown",
            )


class ExpertCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.experts = load_experts()

    def test_graphify_code_command_is_local_and_writes_outside_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            command = self.experts.graphify_command(ROOT, ROOT.parent / "expert-data", semantic=False, state_root=state)
        self.assertEqual(command.args[:2], (str((state / "experts" / "python-bin" / "graphify.exe").resolve()), "extract"))
        self.assertIn("--code-only", command.args)
        self.assertIn("--out", command.args)
        self.assertNotIn("install", command.args)
        self.assertEqual(command.environment["GRAPHIFY_QUERY_LOG_DISABLE"], "1")

    def test_graphify_semantic_command_forces_local_ollama(self) -> None:
        state = ROOT.parent / "Pala"
        command = self.experts.graphify_command(ROOT, ROOT.parent / "expert-data", semantic=True, state_root=state)
        self.assertIn(("--backend", "ollama"), tuple(zip(command.args, command.args[1:])))
        self.assertEqual(command.environment["OLLAMA_MODEL"], "qwen3:4b-instruct")
        self.assertEqual(command.environment["GRAPHIFY_OLLAMA_KEEP_ALIVE"], "0")
        self.assertEqual(command.environment["OLLAMA_HOST"], "127.0.0.1:11435")
        self.assertEqual(command.environment["OLLAMA_MODELS"], str(state / "experts" / "ollama" / "0.32.6" / "models"))

    def test_serena_command_disables_dashboard_and_memories(self) -> None:
        command = self.experts.serena_command(ROOT, ROOT.parent / "serena-home", state_root=ROOT.parent / "Pala")
        self.assertEqual(command.args[0], str(ROOT.parent / "Pala" / "experts" / "python-bin" / "serena.exe"))
        self.assertIn("--project-from-cwd", command.args)
        self.assertIn("no-memories", command.args)
        self.assertIn("planning", command.args)
        self.assertIn("false", command.args)
        self.assertEqual(command.environment["SERENA_HOME"], str((ROOT.parent / "serena-home").resolve()))

    def test_codebase_memory_command_is_one_shot_and_root_bounded(self) -> None:
        command = self.experts.codebase_memory_command(ROOT, "index_repository", state_root=ROOT.parent / "Pala")
        self.assertEqual(command.args[:3], (str(ROOT.parent / "Pala" / "experts" / "codebase-memory" / "0.9.0" / "expanded" / "codebase-memory-mcp.exe"), "cli", "index_repository"))
        self.assertEqual(command.environment["CBM_ALLOWED_ROOT"], str(ROOT.resolve()))
        self.assertNotIn("watch", command.args)


if __name__ == "__main__":
    unittest.main()

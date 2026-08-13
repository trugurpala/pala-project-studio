#!/usr/bin/env python3
"""Current-tree product hygiene contracts for the public Pala repository."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


class PublicRepositoryCleanupTests(unittest.TestCase):
    @staticmethod
    def _visible_files(relative: str) -> list[Path]:
        root = ROOT / relative
        if not root.exists():
            return []
        files = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file()]
        visible: list[Path] = []
        for path in files:
            ignored = subprocess.run(
                ["git", "check-ignore", "-q", "--", str(path.relative_to(ROOT))],
                cwd=ROOT,
            ).returncode == 0
            if not ignored:
                visible.append(path)
        return visible

    def test_readme_first_screen_is_product_first_and_provider_free(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        first_screen = readme.split("## Advanced", maxsplit=1)[0].casefold()
        self.assertIn("provider-independent local software delivery os", first_screen)
        self.assertIn(
            "https://github.com/trugurpala/pala-project-studio eklentisini kur ve guncel oldugunu dogrula.",
            first_screen,
        )
        for internal in (
            "codegraph",
            "semgrep",
            "playwright",
            "serena",
            "context7",
            "marketplace cache",
            "taskcontract",
            "workflowstore",
        ):
            self.assertNotIn(internal, first_screen)

    def test_root_runtime_documents_are_concise_current_contracts(self) -> None:
        limits = {
            "STATUS.md": 80,
            "PLAN.md": 80,
            "PROGRESS.md": 60,
            "DEBUGGING.md": 80,
            "PROJECT.md": 120,
            "GOAL.md": 40,
        }
        for name, limit in limits.items():
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertLessEqual(len(text.splitlines()), limit)
                for stale in ("M43", "M47", "M60", "M70", "M71", "1.0.1"):
                    self.assertNotIn(stale, text)

    def test_historical_diary_and_retired_runtime_files_are_not_current(self) -> None:
        forbidden = (
            "managed-tools.lock.json",
            "scripts/pala_expert_installer.py",
            "scripts/pala_experts.py",
            "scripts/pala_m10.py",
            "docs/plans",
            "docs/superpowers",
            "outputs",
            "reports",
        )
        for relative in forbidden:
            with self.subTest(relative=relative):
                self.assertEqual(self._visible_files(relative), [])
        for path in (ROOT / "docs").glob("PALA_0_*.md"):
            self.fail(f"versioned development narrative remains current: {path.name}")
        for path in (ROOT / "docs").glob("RELEASE_0*.md"):
            self.fail(f"historical release checklist remains current: {path.name}")

    def test_current_artifact_tree_is_release_or_governance_only(self) -> None:
        allowed_roots = {
            "codex-compat", "governance", "publication", "release", "release-1.1.0", "release-1.1.1"
        }
        tracked = subprocess.run(
            ["git", "ls-files", "artifacts"], cwd=ROOT, check=True,
            capture_output=True, text=True,
        ).stdout.splitlines()
        deleted = set(
            subprocess.run(
                ["git", "ls-files", "--deleted", "artifacts"], cwd=ROOT, check=True,
                capture_output=True, text=True,
            ).stdout.splitlines()
        )
        observed = {
            Path(path).parts[1] for path in tracked
            if path not in deleted and len(Path(path).parts) > 1
        }
        self.assertLessEqual(observed, allowed_roots)
        self.assertFalse(any(path.casefold().endswith(".pdf") for path in tracked))

    def test_capability_registry_has_only_current_provider_classes(self) -> None:
        from pala_workbench import default_registry

        definitions = default_registry().contracts
        providers = {item.provider for item in definitions}
        classes = {item.category for item in definitions}
        self.assertEqual(
            classes,
            {"DEFAULT", "PROJECT_PROFILE", "LAZY_FALLBACK", "OPTIONAL_EXTERNAL"},
        )
        for retired in (
            "graphify",
            "codebase-memory",
            "code-review-graph",
            "ollama",
            "qwen",
            "rtk",
            "playwright-mcp",
        ):
            self.assertNotIn(retired, {value.casefold() for value in providers})

    def test_product_identity_is_one_point_one(self) -> None:
        identity = json.loads((ROOT / "product-identity.json").read_text(encoding="utf-8"))
        self.assertEqual(identity["product_version"], "1.1.1")
        self.assertEqual(identity["plugin_version"], "1.1.1")


if __name__ == "__main__":
    unittest.main()

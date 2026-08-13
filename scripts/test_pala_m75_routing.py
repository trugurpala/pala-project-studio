#!/usr/bin/env python3
"""M75 RED contracts for deterministic Pala Control Center host routing."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONTROL_CENTER_SKILL = ROOT / "skills" / "pala-control-center" / "SKILL.md"
PACKAGER_PATH = ROOT / "scripts" / "build_portable.py"

POSITIVE_INTENTS = (
    "paneli aç",
    "paneli ac",
    "pala paneli",
    "pala durumunu göster",
    "pala control center",
    "neredeyiz",
)
NEGATIVE_INTENTS = (
    "tarayıcı panelini aç",
    "uygulamanın admin panelini aç",
    "browser panel",
)


def _load_packager():
    spec = importlib.util.spec_from_file_location("m75_build_portable", PACKAGER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load build_portable.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _frontmatter(path: Path) -> tuple[dict[str, str], str]:
    """Read the small YAML subset used by Codex skill frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise AssertionError(f"missing YAML frontmatter: {path}")
    raw, separator, body = text[4:].partition("\n---\n")
    if not separator:
        raise AssertionError(f"unterminated YAML frontmatter: {path}")

    values: dict[str, str] = {}
    lines = raw.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        key, marker, value = line.partition(":")
        if not marker or key != key.strip():
            raise AssertionError(f"unsupported skill frontmatter line: {line!r}")
        value = value.strip()
        if value in {">", "|-", "|", ">-"}:
            continuation: list[str] = []
            index += 1
            while index < len(lines) and (
                not lines[index].strip() or lines[index][0].isspace()
            ):
                continuation.append(lines[index].strip())
                index += 1
            values[key] = " ".join(continuation).strip()
            continue
        values[key] = value.strip('"\'')
        index += 1
    return values, body


def _discover_skills(plugin_root: Path) -> dict[str, Path]:
    discovered: dict[str, Path] = {}
    for skill_file in sorted((plugin_root / "skills").glob("*/SKILL.md")):
        metadata, _ = _frontmatter(skill_file)
        name = metadata.get("name", "")
        if name:
            discovered[name] = skill_file
    return discovered


class M75ControlCenterRoutingRedTests(unittest.TestCase):
    def test_dedicated_skill_frontmatter_owns_only_pala_panel_intents(self) -> None:
        self.assertTrue(
            CONTROL_CENTER_SKILL.is_file(),
            "M75 needs a dedicated skills/pala-control-center/SKILL.md",
        )
        metadata, _ = _frontmatter(CONTROL_CENTER_SKILL)
        self.assertEqual(metadata.get("name"), "pala-control-center")
        description = " ".join(metadata.get("description", "").casefold().split())

        for intent in POSITIVE_INTENTS:
            self.assertIn(
                intent.casefold(),
                description,
                f"frontmatter must route the Pala-specific intent: {intent}",
            )
        self.assertTrue(
            "do not use" in description or "kullanma" in description,
            "frontmatter must explicitly exclude unrelated panel requests",
        )
        for intent in NEGATIVE_INTENTS:
            self.assertIn(
                intent.casefold(),
                description,
                f"frontmatter must explicitly avoid capturing: {intent}",
            )

    def test_dedicated_skill_is_tiny_read_only_and_reuses_control_center(self) -> None:
        self.assertTrue(
            CONTROL_CENTER_SKILL.is_file(),
            "M75 needs a dedicated skills/pala-control-center/SKILL.md",
        )
        _, body = _frontmatter(CONTROL_CENTER_SKILL)
        normalized = " ".join(body.casefold().split())

        self.assertLessEqual(
            len(body.split()),
            120,
            "the routing skill must stay tiny and not duplicate project-finisher",
        )
        for marker in ("pala_report.py", "--open", "--intent"):
            self.assertIn(marker, body)
        self.assertIn("read-only", normalized)
        self.assertIn("exactly once", normalized)
        self.assertIn("canonical truth", normalized)
        self.assertTrue(
            "helper" in normalized and "provider" in normalized,
            "the skill must prohibit helper/provider UI",
        )
        self.assertNotIn("pala_state.py begin", normalized)
        self.assertNotIn("workflowstore", normalized)

    def test_portable_install_exposes_dedicated_skill_to_host_discovery(self) -> None:
        packager = _load_packager()
        expected_member = (
            "pala-project-studio/skills/pala-control-center/SKILL.md"
        )
        archive_names = {
            name for _, name in packager.archive_entries(ROOT)
        }
        self.assertIn(expected_member, archive_names)

        with tempfile.TemporaryDirectory(prefix="pala-m75-installed-routing-") as temp:
            temp_root = Path(temp)
            archive_path = temp_root / "candidate.zip"
            packager.build_archive(archive_path, ROOT)
            installed_root = temp_root / "installed"
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(installed_root)

            plugin_root = installed_root / "pala-project-studio"
            discovered = _discover_skills(plugin_root)

        self.assertIn("pala-project-finisher", discovered)
        self.assertIn(
            "pala-control-center",
            discovered,
            "a fresh installed plugin must expose the dedicated routing skill",
        )

    def test_normal_installer_status_does_not_open_a_browser_or_helper_ui(self) -> None:
        installer = (ROOT / "scripts" / "Install-Pala.ps1").read_text(encoding="utf-8")
        status_block = installer.split('if ($Mode -eq "Status")', 1)[1].split(
            '$arguments = @()', 1
        )[0]
        self.assertNotIn("--open", status_block)
        self.assertNotIn("Start-Process", installer)
        self.assertNotIn("Invoke-Item", installer)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contract tests for the Pala Project Studio user experience and package."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = PLUGIN_ROOT / "skills" / "pala-project-finisher"
REFERENCE_ROOT = SKILL_ROOT / "references"
PACKAGER_PATH = PLUGIN_ROOT / "scripts" / "build_portable.py"


def load_packager():
    spec = importlib.util.spec_from_file_location("build_portable", PACKAGER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load build_portable.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UserExperienceContractTests(unittest.TestCase):
    def test_readme_exposes_current_release_and_expert_worker_boundary(self) -> None:
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        normalized = " ".join(readme.casefold().split())
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        release_version = manifest["version"].split("+", maxsplit=1)[0]

        self.assertIn(
            "releases/latest/download/"
            f"pala-project-studio-{release_version}.zip",
            readme,
        )
        self.assertIn(
            f"img.shields.io/badge/release-v{release_version}-2ea44f",
            readme,
        )
        self.assertIn(f"releases/tag/v{release_version}", readme)
        self.assertNotIn("img.shields.io/github/v/release/", readme)
        for required in (
            "güvenli uzman işçileri",
            "graphify",
            "serena",
            "codebase-memory",
            "ollama",
            "divan",
        ):
            self.assertIn(required, normalized)

    def test_04_single_door_plan_is_opinionated_and_codex_safe(self) -> None:
        project = (PLUGIN_ROOT / "PROJECT.md").read_text(encoding="utf-8")
        decisions = (PLUGIN_ROOT / "DECISIONS.md").read_text(encoding="utf-8")
        design = (
            PLUGIN_ROOT / "docs" / "PALA_0_4_SINGLE_DOOR.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join((project + decisions + design).casefold().split())

        for required in (
            "tek-kapı",
            "örtük",
            "zaten hazır",
            "external-conflict",
            "atomik",
            "rollback",
            "yeni sohbet",
            "24 saat",
            "hook içinde ağ yok",
            "50 ardışık",
        ):
            self.assertIn(required, normalized)

        self.assertIn("updatedInput", decisions)
        self.assertIn("rtk", normalized)
        self.assertIn("code-review-graph", normalized)
        self.assertIn("context7", normalized)
        self.assertIn("playwright", normalized)

    def test_04_rejects_duplicate_orchestration_owners(self) -> None:
        decisions = (PLUGIN_ROOT / "DECISIONS.md").read_text(encoding="utf-8")
        open_source = (PLUGIN_ROOT / "OPEN_SOURCE.md").read_text(encoding="utf-8")
        normalized = " ".join((decisions + open_source).casefold().split())

        self.assertIn("openspec yalnız zaten kullanan projelerde", normalized)
        self.assertIn("planning-with-files", normalized)
        self.assertIn("ruflo", normalized)
        self.assertIn("kurulmaz", normalized)
        self.assertIn("0.4 dışında", normalized)

    def test_manifest_presents_three_natural_turkish_starters(self) -> None:
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(manifest["version"].startswith("0.6.0+codex."))
        self.assertEqual(
            manifest["repository"],
            "https://github.com/trugurpala/pala-project-studio",
        )
        self.assertEqual(manifest["license"], "MIT")
        self.assertEqual(
            manifest["interface"]["defaultPrompt"],
            [
                "Bu projeyi anlayıp güvenli biçimde tamamla.",
                "Bu projeyi denetle, eksikleri düzelt ve çalıştır.",
                "Bu fikri doğru mimariyle çalışan bir projeye dönüştür.",
            ],
        )

    def test_manifest_turkish_text_decodes_without_mojibake(self) -> None:
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        interface = manifest["interface"]
        decoded = "\n".join(
            [
                manifest["description"],
                interface["shortDescription"],
                interface["longDescription"],
                *interface["defaultPrompt"],
            ]
        )

        self.assertEqual(
            interface["shortDescription"],
            "Projeyi anlar, planlar, uygular ve doğrular.",
        )
        for marker in ("\ufffd", "Ã", "Ä", "Å", "dođrular"):
            self.assertNotIn(marker, decoded)
        for prompt in manifest["interface"]["defaultPrompt"]:
            self.assertLessEqual(len(prompt), 128)
            self.assertNotIn("$", prompt)
        self.assertIn("Türkçe", manifest["interface"]["longDescription"])

    def test_repo_marketplace_exposes_pala_without_personal_profile_assumption(self) -> None:
        path = PLUGIN_ROOT / ".agents" / "plugins" / "marketplace.json"
        marketplace = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(marketplace["name"], "pala-project-studio")
        self.assertEqual(marketplace["interface"]["displayName"], "Pala Project Studio")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "pala-project-studio")
        self.assertEqual(entry["source"], {"source": "local", "path": "./"})
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
        self.assertEqual(entry["category"], "Developer Tools")

    def test_skill_metadata_uses_consistent_brand_and_narrow_implicit_invocation(self) -> None:
        metadata = (SKILL_ROOT / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn('display_name: "Pala Project Studio · Finisher"', metadata)
        self.assertIn(
            'short_description: "Projeyi anlar, tamamlar ve doğrular"', metadata
        )
        self.assertIn("$pala-project-studio:pala-project-finisher", metadata)
        self.assertIn("allow_implicit_invocation: true", metadata)
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("software project", skill)
        self.assertIn("ordinary chat", skill)
        self.assertIn("another specialist skill/plugin", skill)
        self.assertIn("explicitly invoked without Pala", skill)

    def test_orchestrator_is_concise_and_declares_human_contract(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(skill.split()), 450)
        for principle in (
            "Understand before changing.",
            "Choose the smallest correct and sustainable path.",
            "Touch only the necessary scope.",
            "Do not call it complete without evidence.",
        ):
            self.assertIn(principle, skill)
        self.assertIn("(references/specialist-routing.md)", skill)
        self.assertIn("1–3 short lines", skill)
        self.assertIn("user's language", skill)

    def test_task_modes_prevent_unrequested_writes_and_runtime_work(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())
        self.assertIn("Read-only audit/report", skill)
        self.assertIn("Plan-only", skill)
        self.assertIn("Implementation", skill)
        self.assertIn(
            "do not register, begin, edit, or write state",
            normalized,
        )
        self.assertIn(
            "do not implement or run the completion gate",
            normalized,
        )

    def test_specialist_routing_is_conditional_and_current(self) -> None:
        path = REFERENCE_ROOT / "specialist-routing.md"
        if not path.is_file():
            self.fail("specialist-routing.md is missing")
        routing = path.read_text(encoding="utf-8")
        normalized = " ".join(routing.split())
        for required in (
            "supabase:supabase",
            "supabase:supabase-postgres-best-practices",
            "github:github",
            "superpowers:",
            "The user does not need to provide external links",
            "Local Git work alone does not trigger GitHub",
            "stage, commit, push, pull request, tag, release, and deployment",
        ):
            self.assertIn(required, normalized)
        self.assertNotIn("user_metadata", routing)
        self.assertNotIn("security_invoker", routing)

    def test_safety_rules_separate_authorizable_actions_from_absolute_bans(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.split())
        self.assertIn(
            "Never expose secrets, weaken tests, invent data, or misreport "
            "verification.",
            normalized,
        )
        self.assertIn(
            "Require separate explicit authority for commit, push, pull "
            "request, tag, release, and deployment.",
            normalized,
        )

    def test_time_sensitive_codex_and_framework_defaults_are_not_frozen(self) -> None:
        memory = (REFERENCE_ROOT / "project-memory.md").read_text(encoding="utf-8")
        frontend = (REFERENCE_ROOT / "frontend-engineering.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("32 KiB", memory)
        self.assertNotIn("codex --ask-for-approval never", memory)
        self.assertNotIn("server components as the default", frontend)
        self.assertIn("current official guidance", memory)
        self.assertIn("installed framework version", " ".join(frontend.split()))

    def test_hook_status_messages_are_natural_turkish(self) -> None:
        hooks = json.loads(
            (PLUGIN_ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8")
        )
        status_messages = [
            hook["statusMessage"]
            for groups in hooks["hooks"].values()
            for group in groups
            for hook in group["hooks"]
        ]
        self.assertEqual(
            status_messages,
            [
                "Proje durumu yükleniyor",
                "Güvenli komut optimizasyonu kontrol ediliyor",
                "Çalışma bağlamı kaydediliyor",
                "Oturum sahipliği kapatılıyor",
                "İlerleme kaydı kontrol ediliyor",
            ],
        )

    def test_github_reference_excludes_secrets_and_requires_separate_authority(self) -> None:
        text = (REFERENCE_ROOT / "github-persistence.md").read_text(
            encoding="utf-8"
        )
        normalized = " ".join(text.casefold().split())
        for required in (
            "never store tokens",
            "transcripts",
            "commit, push, pull request, release, deployment, and visibility",
            "separate authority",
            "private repository",
        ):
            self.assertIn(required, normalized)

    def test_single_command_verifier_exists(self) -> None:
        self.assertTrue((PLUGIN_ROOT / "scripts" / "verify.py").is_file())

    def test_portable_package_includes_bounded_update_checker(self) -> None:
        packager = load_packager()
        files = packager.source_files(PLUGIN_ROOT)
        self.assertIn(PLUGIN_ROOT / "scripts" / "pala_update.py", files)
        self.assertIn(PLUGIN_ROOT / "managed-tools.lock.json", files)

    def test_windows_single_entry_delegates_to_atomic_installer_core(self) -> None:
        entry = (PLUGIN_ROOT / "Install-Pala.ps1").read_text(encoding="utf-8")
        wrapper = (PLUGIN_ROOT / "scripts" / "Install-Pala.ps1").read_text(
            encoding="utf-8"
        )
        compact = "".join(wrapper.split())

        self.assertIn("scripts\\Install-Pala.ps1", entry)
        self.assertIn(
            'ValidateSet("Install","Doctor","Repair","Update","Uninstall","Status")',
            compact,
        )
        self.assertIn("pala_installer.py", wrapper)
        self.assertIn("pala_expert_installer.py", wrapper)
        self.assertIn("managed-tools.lock.json", wrapper)
        self.assertIn("qwen3:4b-instruct", wrapper)
        self.assertIn("127.0.0.1:11435", wrapper)
        self.assertIn("--dry-run", wrapper)
        self.assertNotIn("Remove-Item -Path $installRoot -Recurse", wrapper)
        self.assertNotIn("Copy-Item -Path (Join-Path $pluginRoot", wrapper)

    def test_windows_installer_contains_expected_ollama_probe_stderr(self) -> None:
        wrapper = (PLUGIN_ROOT / "scripts" / "Install-Pala.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("function Invoke-PalaNativeCapture", wrapper)
        self.assertIn('$ErrorActionPreference = "Continue"', wrapper)
        self.assertIn('Invoke-PalaNativeCapture $ollama @("list")', wrapper)
        self.assertIn('Invoke-PalaNativeCapture $ollama @("pull", "qwen3:4b-instruct")', wrapper)
        self.assertNotIn("& $ollama list 2>&1", wrapper)

    def test_owner_demo_handoff_is_conditional_and_secrets_safe(self) -> None:
        reference = (REFERENCE_ROOT / "owner-demo-handoff.md").read_text(
            encoding="utf-8"
        )
        normalized = " ".join(reference.casefold().split())
        for required in (
            "reports/owner_demo.md",
            "register --demo reports/owner_demo.md",
            "coherent ticket",
            "real browser",
            "not run",
            "never include passwords",
            "payment or identity data",
        ):
            self.assertIn(required, normalized)
        self.assertIn(
            "(references/owner-demo-handoff.md)",
            (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertTrue(
            (SKILL_ROOT / "assets" / "OWNER_DEMO_TEMPLATE.md").is_file()
        )

    def test_github_quality_workflow_is_small_and_pinned(self) -> None:
        workflow = (
            PLUGIN_ROOT / ".github" / "workflows" / "quality.yml"
        ).read_text(encoding="utf-8")
        normalized = " ".join(workflow.split())
        self.assertIn("permissions: contents: read", normalized)
        self.assertIn("cancel-in-progress: true", workflow)
        self.assertIn("matrix:", workflow)
        self.assertIn(
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            workflow,
        )
        self.assertIn(
            "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97",
            workflow,
        )
        self.assertIn("python scripts/verify.py", workflow)
        self.assertNotIn("write-all", workflow)


class PortablePackageContractTests(unittest.TestCase):
    def test_packager_exists(self) -> None:
        self.assertTrue(PACKAGER_PATH.is_file())

    @unittest.skipUnless(PACKAGER_PATH.is_file(), "packager not implemented")
    def test_packager_creates_safe_allowlisted_archive_without_overwrite(
        self,
    ) -> None:
        packager = load_packager()
        with tempfile.TemporaryDirectory(prefix="Pala package test ") as temp:
            output = Path(temp) / "pala.zip"
            entries = packager.build_archive(output, PLUGIN_ROOT)
            self.assertTrue(output.is_file())
            self.assertEqual(entries, sorted(entries, key=str.casefold))

            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()

            self.assertEqual(names, entries)
            self.assertIn(
                "pala-project-studio/.agents/plugins/marketplace.json",
                names,
            )
            self.assertIn(
                "pala-project-studio/.codex-plugin/plugin.json",
                names,
            )
            self.assertIn(
                "pala-project-studio/skills/pala-project-finisher/SKILL.md",
                names,
            )
            self.assertIn(
                "pala-project-studio/scripts/test_plugin_experience.py",
                names,
            )
            self.assertIn("pala-project-studio/Install-Pala.ps1", names)
            self.assertIn("pala-project-studio/scripts/pala_installer.py", names)
            self.assertIn("pala-project-studio/README.md", names)
            self.assertIn("pala-project-studio/PROJECT.md", names)
            self.assertIn("pala-project-studio/DECISIONS.md", names)
            self.assertIn(
                "pala-project-studio/docs/PALA_0_4_SINGLE_DOOR.md", names
            )
            self.assertIn("pala-project-studio/LICENSE", names)
            for name in names:
                path = PurePosixPath(name)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertNotIn("__pycache__", path.parts)
                self.assertNotIn(".ruff_cache", path.parts)
                self.assertNotIn("superpowers", path.parts)
                self.assertFalse(name.endswith((".pyc", ".pem", ".key")))

            with self.assertRaises(FileExistsError):
                packager.build_archive(output, PLUGIN_ROOT)

    @unittest.skipUnless(PACKAGER_PATH.is_file(), "packager not implemented")
    def test_packager_rejects_unsafe_and_case_colliding_names(self) -> None:
        packager = load_packager()
        for value in ("/absolute/file", "../escape", "C:/drive/file"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    packager.validate_archive_name(value)
        with self.assertRaises(ValueError):
            packager.ensure_unique_names(["Root/File.py", "root/file.py"])


if __name__ == "__main__":
    unittest.main()

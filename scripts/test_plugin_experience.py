#!/usr/bin/env python3
"""Contract tests for the Pala Project Studio user experience and package."""

from __future__ import annotations

import importlib.util
import json
import re
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
    def test_agent_contract_names_canonical_task_quality_acceptance_done_flow(self) -> None:
        agents = (PLUGIN_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        normalized_agents = " ".join(agents.casefold().split())
        normalized_skill = " ".join(skill.casefold().split())
        for marker in ("taskcontract", "quality engine", "acceptance", "done", "generated"):
            self.assertIn(marker, normalized_agents)
            self.assertIn(marker, normalized_skill)
        self.assertIn("pala_report", normalized_agents)
        self.assertIn("pala_state.py begin", normalized_agents)
        self.assertIn("pala_report", normalized_skill)
        self.assertIn("begin --ticket", normalized_skill)

    def test_readme_is_product_first_and_advanced_docs_hold_provider_detail(self) -> None:
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        normalized = " ".join(readme.casefold().split())
        architecture = (PLUGIN_ROOT / "docs" / "ARCHITECTURE.md").read_text(
            encoding="utf-8"
        )
        advanced = " ".join(architecture.casefold().split())
        identity = json.loads(
            (PLUGIN_ROOT / "product-identity.json").read_text(encoding="utf-8")
        )
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["version"], identity["plugin_version"])
        release_version = identity["product_version"]
        self.assertIn(release_version, readme)
        self.assertNotIn("img.shields.io/github/v/release/", readme)
        self.assertIn("provider-independent local software delivery os", normalized)
        self.assertIn("## advanced technical details", readme.casefold())
        for required in (
            "codegraph | 1.5.0",
            "semgrep | 1.172.0",
            "playwright | 1.62.1",
            "serena | 1.7.0",
            "context7 | 4.0.2",
        ):
            self.assertIn(required, advanced)

    def test_current_identity_is_one_point_one_without_old_candidate_language(self) -> None:
        identity = json.loads(
            (PLUGIN_ROOT / "product-identity.json").read_text(encoding="utf-8")
        )
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        project = (PLUGIN_ROOT / "PROJECT.md").read_text(encoding="utf-8")
        goal = (PLUGIN_ROOT / "GOAL.md").read_text(encoding="utf-8")
        release = (PLUGIN_ROOT / "docs" / "RELEASE_1.1.1.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(manifest["version"], identity["plugin_version"])
        self.assertIn("Current version: **1.1.1**", readme)
        self.assertNotIn("Yerel yayın adayı **0.8.2**", readme)
        self.assertIn(identity["product_version"], project)
        self.assertIn(identity["product_version"], goal)
        self.assertIn("pala-project-studio-1.1.1.zip", release)

    def test_release_notes_name_the_versioned_portable_asset(self) -> None:
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")
        release = (PLUGIN_ROOT / "docs" / "RELEASE_1.1.1.md").read_text(
            encoding="utf-8"
        )
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        version = str(manifest["version"]).split("+", maxsplit=1)[0]
        self.assertIn(version, readme)
        self.assertIn(f"pala-project-studio-{version}.zip", release)

    def test_current_architecture_is_capability_first_and_codex_safe(self) -> None:
        project = (PLUGIN_ROOT / "PROJECT.md").read_text(encoding="utf-8")
        design = (PLUGIN_ROOT / "docs" / "ARCHITECTURE.md").read_text(
            encoding="utf-8"
        )
        normalized = " ".join((project + design).casefold().split())

        for required in (
            "default",
            "project_profile",
            "lazy_fallback",
            "optional_external",
            "atomic activation",
            "rollback",
            "no global path mutation",
            "quality engine",
        ):
            self.assertIn(required, normalized)

        self.assertNotIn("code-review-graph", normalized)
        self.assertNotIn("graphify", normalized)

    def test_current_open_source_inventory_has_only_supported_workbench(self) -> None:
        open_source = (PLUGIN_ROOT / "OPEN_SOURCE.md").read_text(encoding="utf-8")
        normalized = " ".join(open_source.casefold().split())

        for required in ("codegraph", "semgrep", "playwright", "serena", "context7"):
            self.assertIn(required, normalized)
        for retired in ("graphify", "code-review-graph", "ollama", "qwen", "rtk"):
            self.assertNotIn(retired, normalized)

    def test_manifest_presents_three_natural_turkish_starters(self) -> None:
        identity = json.loads(
            (PLUGIN_ROOT / "product-identity.json").read_text(encoding="utf-8")
        )
        manifest = json.loads(
            (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["version"], identity["plugin_version"])
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
        self.assertEqual(entry["source"], {"source": "local", "path": "."})
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
        self.assertEqual(entry["category"], "Developer Tools")
        self.assertNotEqual(entry["source"]["path"], "")
        self.assertNotEqual(entry["source"]["path"], "./")

    def test_kur_cmd_runs_bypass_install_and_prints_turkish_next_steps(self) -> None:
        kur = (PLUGIN_ROOT / "Kur.cmd").read_text(encoding="utf-8")
        compact = " ".join(kur.split())
        self.assertIn("ExecutionPolicy Bypass", compact)
        self.assertIn(r"scripts\Install-Pala.ps1", kur)
        self.assertIn("-Mode Install", compact)
        lowered = kur.casefold()
        for marker in ("plugins", "/hooks", "yeni bir sohbet"):
            self.assertIn(marker, lowered)

    def test_installer_gui_next_steps_cover_plugins_hooks_and_new_chat(self) -> None:
        installer_path = PLUGIN_ROOT / "scripts" / "pala_installer.py"
        spec = importlib.util.spec_from_file_location(
            "pala_installer_ux", installer_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load pala_installer.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        message = module.install_gui_next_steps_message()
        lowered = message.casefold()
        for marker in ("plugins", "/hooks", "yeni bir sohbet", "sonraki 3 adim"):
            self.assertIn(marker, lowered)
        wrapper = (PLUGIN_ROOT / "scripts" / "Install-Pala.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("Show-PalaGuiNextSteps", wrapper)
        self.assertIn("gui_next_steps", wrapper)
        self.assertIn("Plugins'te Pala", wrapper)

    def test_vibe_install_docs_contain_native_cli_and_forbid_install_myths(
        self,
    ) -> None:
        """Native CLI is primary; Plus-paste / ZIP-upload-as-primary stay myths."""
        marketplace_add = (
            "codex plugin marketplace add trugurpala/pala-project-studio"
        )
        plugin_add = "codex plugin add pala-project-studio@pala-project-studio"
        advanced_docs = (
            PLUGIN_ROOT / "docs" / "VIBE_INSTALL.md",
            PLUGIN_ROOT / "docs" / "VIBE_FIRST_SESSION.md",
        )
        for path in advanced_docs:
            text = path.read_text(encoding="utf-8")
            self.assertIn(marketplace_add, text, path.name)
            self.assertIn(plugin_add, text, path.name)

        vibe_install = (PLUGIN_ROOT / "docs" / "VIBE_INSTALL.md").read_text(
            encoding="utf-8"
        )
        vibe_first = (PLUGIN_ROOT / "docs" / "VIBE_FIRST_SESSION.md").read_text(
            encoding="utf-8"
        )
        readme = (PLUGIN_ROOT / "README.md").read_text(encoding="utf-8")

        # Explicit myth denials in the vibe install bible.
        self.assertIn("metin yapıştır = kurulum", vibe_install)
        self.assertIn("ZIP yükle → Install", vibe_install)
        self.assertIn("ZIP-upload UI yok", vibe_install)
        self.assertRegex(
            vibe_install,
            r"metin yapıştır = kurulum\s*\|\s*\*\*Yok\.\*\*",
        )
        self.assertRegex(
            vibe_install,
            r"ZIP yükle → Install\s*\|\s*\*\*Yok\.\*\*",
        )

        # First-session + README must not sell ZIP-upload / Plus-paste as doors.
        for name, text in (
            ("VIBE_FIRST_SESSION.md", vibe_first),
            ("README.md", readme),
            ("VIBE_INSTALL.md", vibe_install),
        ):
            lowered = text.casefold()
            self.assertNotIn("plus'a yapıştırarak kur", lowered, name)
            self.assertNotIn("chatgpt plus paste install", lowered, name)
            self.assertNotIn("upload the zip to plugins", lowered, name)
            self.assertNotIn("plugins'e zip yükle ve install", lowered, name)

        self.assertRegex(readme, r"ZIP Codex Plugins.e yüklenmez")
        self.assertRegex(
            vibe_first.casefold(),
            r"zip-upload|zip yükleme",
        )
        # Unregistered cwd: SessionStart silent (not a broken install).
        self.assertIn("Kayıtsız klasörde", vibe_first)
        self.assertIn("SessionStart **boş**", vibe_first)
        self.assertIn("Kayıtsız klasör", vibe_install)
        self.assertIn("plugin=drifted", vibe_install)
        self.assertIn("Repair", vibe_install)

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
        # Thin skill for Codex progressive disclosure (detail in references/).
        self.assertLessEqual(len(skill.split()), 480)
        for principle in (
            "Understand before changing.",
            "Choose the smallest correct and sustainable path.",
            "Touch only the necessary scope.",
            "Do not call it complete without evidence.",
        ):
            self.assertIn(principle, skill)
        self.assertIn("(references/specialist-routing.md)", skill)
        self.assertIn("references/kontrol-et.md", skill)
        self.assertIn("1–3 short lines", skill)
        self.assertIn("user's language", skill)

    def test_skill_opens_control_center_only_for_explicit_panel_intent(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        first_surface = skill.split("2. Read", maxsplit=1)[0]
        self.assertIn("pala_report.py --cwd .` first", first_surface)
        self.assertIn("paneli aç", first_surface)
        self.assertIn('--open --intent "<exact intent>"', first_surface)
        self.assertNotIn("pala_report.py --cwd . --open` first", first_surface)

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

    def test_kontrol_et_readonly_checklist_markers(self) -> None:
        """Premium 'pala kontrol et' Codex checklist stays explicit and read-only."""
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        ref = (REFERENCE_ROOT / "kontrol-et.md").read_text(encoding="utf-8")
        for marker in ("kontrol et", "rapor", "denetle", "references/kontrol-et.md"):
            self.assertIn(marker, skill)
        for marker in (
            "Presence",
            "pala_report",
            "discover",
            "STATUS",
            "PLAN",
            "DEBUGGING",
            "pala-status.html",
        ):
            self.assertIn(marker, ref)
        self.assertIn("do not register, begin", ref.casefold())
        for step in ("1.", "2.", "3.", "4.", "5.", "6.", "7."):
            self.assertIn(step, ref)
        self.assertIn("do not register, begin, edit, or write state", skill.casefold())
        self.assertRegex(
            skill,
            r"(?is)do not register.*begin",
        )

    def test_continuity_refs_using_pala_plan_execute_debug(self) -> None:
        """Superpowers-inspired continuity refs stay thin and Pala-shaped."""
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/using-pala.md", skill)
        self.assertLessEqual(len(skill.split()), 480)
        using = (REFERENCE_ROOT / "using-pala.md").read_text(encoding="utf-8")
        plan = (REFERENCE_ROOT / "plan-tickets.md").read_text(encoding="utf-8")
        execute = (REFERENCE_ROOT / "execute-tickets.md").read_text(encoding="utf-8")
        debug = (REFERENCE_ROOT / "debugging-inc.md").read_text(encoding="utf-8")
        for text in (using, plan, execute, debug):
            self.assertLessEqual(len(text.split()), 900)
        for marker in (
            "active ticket only",
            "passed",
            "not-run",
            "blocked",
            "configured-not-verified",
            "plan-tickets.md",
            "execute-tickets.md",
            "debugging-inc.md",
            "quality-gates.md",
        ):
            self.assertIn(marker, using)
        self.assertIn("M*-T*", plan)
        self.assertIn("Kanıt", plan)
        self.assertIn("begin --ticket", execute)
        self.assertIn("INC-", debug)
        self.assertIn("Iron law", debug)
        qg = (REFERENCE_ROOT / "quality-gates.md").read_text(encoding="utf-8")
        self.assertIn("Verification before done", qg)
        self.assertIn("configured-not-verified", qg)
        self.assertIn("do not invent soft", qg.casefold())
        routing = (REFERENCE_ROOT / "specialist-routing.md").read_text(encoding="utf-8")
        self.assertIn("using-pala.md", routing)
        self.assertIn("Claude-only", routing)

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
                "Pala yanınızda",
                "Güvenli komut optimizasyonu kontrol ediliyor",
                "Çalışma bağlamı kaydediliyor",
                "Oturum sahipliği kapatılıyor",
                "İlerleme kaydı kontrol ediliyor",
            ],
        )

    def test_skill_opens_with_presence_and_no_quota_claims(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(skill.casefold().split())
        self.assertIn("pala burada — bu oturumda yanındayım.", normalized)
        self.assertIn("read-only discovery comes first", normalized)
        self.assertIn("no larger context, quota, or speedup claims", normalized)
        for banned in (
            "increases your context window",
            "kota artırır",
            "token büyütür",
            "% faster",
        ):
            self.assertNotIn(banned.casefold(), normalized)

    def test_skill_script_paths_are_marketplace_or_pala_state_not_relative_cwd(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("../../scripts/", skill)
        self.assertNotIn("..\\..\\scripts\\", skill)
        lowered = skill.casefold()
        self.assertTrue(
            "localappdata" in lowered
            or "marketplace\\scripts" in lowered
            or "marketplace/scripts" in lowered
            or "pala_state" in lowered,
            "skill must not tell agents to run ../../scripts/ from project cwd",
        )
        self.assertIn("--goal", skill)

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
        self.assertNotIn(PLUGIN_ROOT / "managed-tools.lock.json", files)
        self.assertIn(PLUGIN_ROOT / "scripts" / "pala_workbench.py", files)
        self.assertIn(PLUGIN_ROOT / "scripts" / "pala_codegraph.py", files)
        self.assertIn(PLUGIN_ROOT / "scripts" / "pala_semgrep.py", files)
        self.assertIn(
            PLUGIN_ROOT / "workbench" / "semgrep" / "requirements-win-amd64.lock",
            files,
        )
        self.assertIn(
            PLUGIN_ROOT / "workbench" / "semgrep" / "rules" / "1.0.0" / "manifest.json",
            files,
        )
        self.assertIn(PLUGIN_ROOT / "docs" / "FORK_PACK.md", files)
        self.assertIn(PLUGIN_ROOT / "docs" / "RELEASE_1.1.0.md", files)
        self.assertIn(PLUGIN_ROOT / "docs" / "RELEASE_1.1.1.md", files)
        self.assertIn(PLUGIN_ROOT / "docs" / "ARCHITECTURE.md", files)
        self.assertIn(PLUGIN_ROOT / "docs" / "QUALITY_ENGINE.md", files)
        self.assertNotIn(PLUGIN_ROOT / "docs" / "RELEASE_0_8_0_CHECKLIST.md", files)
        self.assertIn(
            PLUGIN_ROOT / "examples" / "demo-software-project" / "STATUS.md",
            files,
        )
        self.assertIn(
            PLUGIN_ROOT
            / "examples"
            / "demo-software-project"
            / ".codex"
            / "pala-workflow.json",
            files,
        )
        self.assertIn(PLUGIN_ROOT / "scripts" / "pala_demo.py", files)
        self.assertIn(PLUGIN_ROOT / "scripts" / "pala_self_audit.py", files)

    def test_update_compatibility_contract_is_explicit_and_honest(self) -> None:
        path = PLUGIN_ROOT / "docs" / "PALA_UPDATE_COMPATIBILITY.md"
        self.assertTrue(path.is_file())
        text = " ".join(path.read_text(encoding="utf-8").casefold().split())
        for required in (
            "0.8.0 -> 0.8.2",
            "0.8.1 -> 0.8.2",
            "doğrulanmış legacy pala",
            "modified",
            "external_conflict",
            "professional workbench",
            "retired helper installer",
            "yeni sohbet",
            "sürüm kontrolü kurulum yapmaz",
        ):
            self.assertIn(required, text)

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
        self.assertNotIn("pala_expert_installer.py", wrapper)
        self.assertNotIn("managed-tools.lock.json", wrapper)
        self.assertNotIn("qwen3:4b-instruct", wrapper)
        self.assertNotIn("127.0.0.1:11435", wrapper)
        self.assertIn("--dry-run", wrapper)
        self.assertNotIn("Remove-Item -Path $installRoot -Recurse", wrapper)
        self.assertNotIn("Copy-Item -Path (Join-Path $pluginRoot", wrapper)

    def test_windows_status_mode_propagates_subcommand_exit_codes(self) -> None:
        wrapper = (PLUGIN_ROOT / "scripts" / "Install-Pala.ps1").read_text(
            encoding="utf-8"
        )
        status_start = wrapper.index('if ($Mode -eq "Status")')
        status_block = wrapper[status_start : wrapper.index("$arguments = @()", status_start)]
        self.assertIn("$statusExit = $LASTEXITCODE", status_block)
        self.assertIn("exit $statusExit", status_block)
        self.assertNotIn("exit 0", status_block)

    def test_windows_installer_contains_no_retired_helper_runtime(self) -> None:
        wrapper = (PLUGIN_ROOT / "scripts" / "Install-Pala.ps1").read_text(
            encoding="utf-8"
        )

        for retired in ("InstallExperts", "pala_expert_installer.py", "ollama", "qwen3"):
            self.assertNotIn(retired.casefold(), wrapper.casefold())

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

    def test_scorecard_workflow_is_observational_and_pinned(self) -> None:
        workflow = (
            PLUGIN_ROOT / ".github" / "workflows" / "scorecards.yml"
        ).read_text(encoding="utf-8")
        normalized = " ".join(workflow.split())
        self.assertIn("schedule:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertNotIn("release:", workflow)
        self.assertIn("permissions: read-all", normalized)
        self.assertIn("security-events: write", normalized)
        self.assertIn("id-token: write", normalized)
        self.assertIn(
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            workflow,
        )
        self.assertIn(
            "ossf/scorecard-action@2d1146689b8cda280b9bc96326124645441f03bc",
            workflow,
        )
        self.assertIn("github/codeql-action/upload-sarif@f205ea1c3313d31db17d3d3e8b55d42dc1e6bb6", workflow)


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
            self.assertNotIn("pala-project-studio/scripts/test_plugin_experience.py", names)
            self.assertIn("pala-project-studio/Install-Pala.ps1", names)
            self.assertIn("pala-project-studio/Kur.cmd", names)
            packager_source = PACKAGER_PATH.read_text(encoding="utf-8")
            self.assertIn('plugin_root / "Kur.cmd"', packager_source)
            self.assertIn('plugin_root / "KUR.md"', packager_source)
            if (PLUGIN_ROOT / "KUR.md").is_file():
                self.assertIn("pala-project-studio/KUR.md", names)
            self.assertIn("pala-project-studio/scripts/pala_installer.py", names)
            self.assertIn("pala-project-studio/README.md", names)
            self.assertIn("pala-project-studio/README.tr.md", names)
            self.assertIn("pala-project-studio/docs/RELEASE_1.1.0.md", names)
            self.assertIn("pala-project-studio/docs/RELEASE_1.1.1.md", names)
            self.assertIn("pala-project-studio/docs/ARCHITECTURE.md", names)
            self.assertIn("pala-project-studio/docs/QUALITY_ENGINE.md", names)
            self.assertIn("pala-project-studio/PROJECT.md", names)
            self.assertIn("pala-project-studio/DECISIONS.md", names)
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
    def test_portable_archive_excludes_development_only_surface(self) -> None:
        packager = load_packager()
        names = {
            name
            for _, name in packager.archive_entries(PLUGIN_ROOT)
        }
        self.assertNotIn("pala-project-studio/scripts/test_pala_product.py", names)
        self.assertNotIn(
            "pala-project-studio/docs/RELEASE_0_8_0_CHECKLIST.md",
            names,
        )
        self.assertNotIn(
            "pala-project-studio/docs/plans/active/PALA-1.0-product-completion.md",
            names,
        )
        for retired in (
            "pala-project-studio/managed-tools.lock.json",
            "pala-project-studio/scripts/pala_expert_installer.py",
            "pala-project-studio/scripts/pala_experts.py",
            "pala-project-studio/scripts/pala_m10.py",
        ):
            self.assertNotIn(retired, names)
        for required in (
            "pala-project-studio/Install-Pala.ps1",
            "pala-project-studio/scripts/verify.py",
            "pala-project-studio/README.tr.md",
            "pala-project-studio/docs/RELEASE_1.1.0.md",
            "pala-project-studio/docs/RELEASE_1.1.1.md",
            "pala-project-studio/docs/ARCHITECTURE.md",
            "pala-project-studio/docs/QUALITY_ENGINE.md",
            "pala-project-studio/workbench/semgrep/requirements-win-amd64.lock",
            "pala-project-studio/workbench/semgrep/rules/1.0.0/manifest.json",
            "pala-project-studio/workbench/semgrep/rules/1.0.0/pala-minimal.yml",
        ):
            self.assertIn(required, names)

    @unittest.skipUnless(PACKAGER_PATH.is_file(), "packager not implemented")
    def test_packager_rejects_unsafe_and_case_colliding_names(self) -> None:
        packager = load_packager()
        for value in ("/absolute/file", "../escape", "C:/drive/file"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                packager.validate_archive_name(value)
        with self.assertRaises(ValueError):
            packager.ensure_unique_names(["Root/File.py", "root/file.py"])

    @unittest.skipUnless(PACKAGER_PATH.is_file(), "packager not implemented")
    def test_packager_forbids_secret_shaped_and_sqlite_sources(self) -> None:
        packager = load_packager()
        for relative in (
            Path("scripts/credentials.json"),
            Path("hooks/id_rsa"),
            Path("hooks/id_rsa.pub"),
            Path("skills/secrets.json"),
            Path("data/pala.sqlite"),
            Path("scripts/token.pem"),
        ):
            with self.subTest(relative=str(relative)):
                self.assertTrue(packager.is_forbidden_source(relative))
        self.assertFalse(packager.is_forbidden_source(Path("scripts/pala_quality.py")))
        self.assertFalse(packager.is_forbidden_source(Path("docs/SECURITY.md")))


if __name__ == "__main__":
    unittest.main()

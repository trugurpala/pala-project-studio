#!/usr/bin/env python3
"""Shared local-memory contract for Codex, Cursor, and CLI (M25 / Wave E).

Single-machine SQLite + project files. No cloud sync. Hooks stay Codex-only.
AGENTS.md remains the durable rules source; Cursor rule/skill stay thin.
"""

from __future__ import annotations

from pathlib import Path

import pala_db

HOSTS = frozenset({"codex", "cursor", "cli"})

SHARED_FIELDS = (
    "pala.sqlite path",
    "catalog projects/provisions/events",
    "memory contract",
    "evidence labels",
    "Status HTML via CLI",
)

NEVER_STORE = (
    "secrets",
    "tokens",
    "transcripts",
    "raw chat",
)

# Portable skill must keep these markers (Wave E drift check vs AGENTS contract).
PORTABLE_SKILL_MARKERS = (
    "agents.md",
    "passed",
    "not-run",
    "blocked",
    "configured-not-verified",
    "pala.sqlite",
    "not a codex plugin",
)

# Cursor alwaysApply rule stays a thin reminder, not a second AGENTS.md.
CURSOR_RULE_MAX_BODY_LINES = 16

SURFACE_SPECIFIC = {
    "codex": (
        "marketplace plugin",
        "hooks.json SessionStart/Stop",
        "RTK PreToolUse rewrite",
    ),
    "cursor": (
        "thin skill/rules only",
        "no Codex hook parity claim",
        "CLI Status for DB view",
    ),
    "cli": (
        "Install-Pala / pala_state / pala_report",
        "Doctor host honesty",
        "demo seed / self-audit",
    ),
}


def classify_host_access(host: str) -> dict[str, object]:
    """Hit/miss verdict for shared-store host names (Wave E proof).

    hit  = supported surface that must resolve the same pala.sqlite path
    miss = unsupported / unknown host (no second store invented)
    """
    key = host.strip().casefold()
    if key in HOSTS:
        return {
            "host": key,
            "access": "hit",
            "reason": "supported shared-store surface",
        }
    return {
        "host": key,
        "access": "miss",
        "reason": "unsupported shared-memory host",
    }


def surface_report(host: str, catalog_root: Path | None = None) -> dict[str, object]:
    """Return one host's view of the shared store; all hosts share db_path."""
    verdict = classify_host_access(host)
    if verdict["access"] != "hit":
        raise ValueError(f"unsupported shared-memory host: {host}")
    key = str(verdict["host"])
    db_path = pala_db.db_path_for(catalog_root) if catalog_root else pala_db.default_db_path()
    return {
        "host": key,
        "access": "hit",
        "db_path": str(db_path),
        "catalog_root": str(catalog_root or pala_db.catalog_root()),
        "sync_model": "single_machine_file",
        "cloud_sync": False,
        "shared_fields": list(SHARED_FIELDS),
        "never_store": list(NEVER_STORE),
        "surface_specific": list(SURFACE_SPECIFIC[key]),
        "hooks": "codex_hooks_json" if key == "codex" else "not_applicable",
        "primary_product": "Codex plugin (Cursor/CLI are thin readers of the same store)",
        "claims_codex_plugin": key == "codex",
        "claims_cursor_install": False,
    }


def doctor_store_block(catalog_root: Path | None = None) -> dict[str, object]:
    """Compact Doctor payload: one DB path + host matrix without fake installs."""
    cli = surface_report("cli", catalog_root)
    return {
        "db_path": cli["db_path"],
        "sync_model": cli["sync_model"],
        "cloud_sync": False,
        "hosts": {
            "codex": {
                "role": "primary_plugin",
                "hooks": "codex_hooks_json",
                "install": "Install-Pala.ps1 / marketplace",
            },
            "cursor": {
                "role": "thin_skill_rules",
                "hooks": "not_applicable",
                "install": "portable skill/rules only -- not a Codex plugin install",
            },
            "cli": {
                "role": "same_store_scripts",
                "hooks": "not_applicable",
                "install": "scripts already in repo / portable ZIP",
            },
        },
        "never_store": list(NEVER_STORE),
        "agents_source": "AGENTS.md",
        "cursor_surface": "thin skill/rules only",
    }


def portable_skill_drift(skill_text: str) -> list[str]:
    """Return missing Wave E markers; empty list means skill is aligned."""
    folded = skill_text.casefold()
    return [marker for marker in PORTABLE_SKILL_MARKERS if marker not in folded]


def cursor_rule_body_lines(rule_text: str) -> list[str]:
    """Body lines after YAML frontmatter (--- … ---)."""
    lines = rule_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [line for line in lines if line.strip()]
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    body = lines[end + 1 :] if end is not None else lines
    return [line for line in body if line.strip()]

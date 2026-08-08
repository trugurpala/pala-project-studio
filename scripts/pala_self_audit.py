#!/usr/bin/env python3
"""Fail-closed self-audit for fork readiness, presence UX, and quality gates (M21)."""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pala_demo
import pala_hook
import pala_memory

PLUGIN_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_ROOT_FILES = (
    "README.md",
    "SUPPORT.md",
    "CHANGELOG.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "Install-Pala.ps1",
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    "hooks/hooks.json",
    "docs/VIBE_FIRST_SESSION.md",
    "docs/FORK_PACK.md",
    "docs/README.md",
    "skills/pala-project-finisher/SKILL.md",
    "scripts/pala_hook.py",
    "scripts/pala_demo.py",
    "scripts/pala_self_audit.py",
    "examples/demo-software-project/STATUS.md",
)

BANNED_CLAIM_PATTERNS = (
    re.compile(r"%\s*daha\s*hızlı", re.IGNORECASE),
    re.compile(r"%\s*faster", re.IGNORECASE),
    re.compile(r"token\s*büyüt", re.IGNORECASE),
    re.compile(r"kota\s*artır", re.IGNORECASE),
    re.compile(r"plus\s*install", re.IGNORECASE),
    re.compile(r"enlarges?\s+(your\s+)?(context|quota)", re.IGNORECASE),
)


def _check(name: str, status: str, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def audit_presence(root: Path) -> dict[str, str]:
    hook = (root / "scripts" / "pala_hook.py").read_text(encoding="utf-8")
    skill = (root / "skills" / "pala-project-finisher" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    hooks_json = json.loads((root / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    session = hooks_json["hooks"]["SessionStart"][0]["hooks"][0]
    if pala_hook.PRESENCE_LINE not in hook:
        return _check("presence", "failed", "PRESENCE_LINE missing in pala_hook.py")
    if "pala burada" not in skill.casefold():
        return _check("presence", "failed", "skill missing presence opener")
    if session.get("statusMessage") != "Pala yanınızda":
        return _check("presence", "failed", "SessionStart statusMessage mismatch")
    if int(session.get("additionalContextLimit") or 0) != pala_hook.SESSION_CONTEXT_LIMIT:
        return _check("presence", "failed", "additionalContextLimit mismatch")
    message = pala_hook.session_context(
        {"status": "STATUS.md", "plan": "PLAN.md"},
        {"active_ticket": "DEMO-003", "next_action": "audit"},
        compacted=False,
        health={"plugin": "loaded", "python": "ready", "git": "ready", "hook": "running"},
    )["hookSpecificOutput"]["additionalContext"]
    if not str(message).startswith(pala_hook.PRESENCE_LINE):
        return _check("presence", "failed", "session context missing presence prefix")
    if len(str(message)) > pala_hook.SESSION_CONTEXT_LIMIT:
        return _check("presence", "failed", "session context over limit")
    return _check("presence", "passed", "SessionStart + skill presence ok")


def audit_hook_safety(root: Path) -> dict[str, str]:
    text = (root / "scripts" / "pala_hook.py").read_text(encoding="utf-8")
    lowered = text.casefold()
    for banned in ("urllib", "requests.", "subprocess.run([\"pytest\"", "git push", "npm install"):
        if banned.casefold() in lowered:
            return _check("hook_safety", "failed", f"forbidden pattern: {banned}")
    if "SessionStart" not in text or "additionalContext" not in text:
        return _check("hook_safety", "failed", "SessionStart contract missing")
    return _check("hook_safety", "passed", "hook stays local and non-mutating")


def audit_fork_pack(root: Path) -> dict[str, str]:
    missing = [rel for rel in REQUIRED_ROOT_FILES if not (root / rel).is_file()]
    if missing:
        return _check("fork_pack", "failed", "missing: " + ", ".join(missing[:8]))
    vibe = (root / "docs" / "VIBE_FIRST_SESSION.md").read_text(encoding="utf-8")
    fork = (root / "docs" / "FORK_PACK.md").read_text(encoding="utf-8")
    if "pala burada" not in vibe.casefold() and "yanındayım" not in vibe.casefold():
        return _check("fork_pack", "failed", "VIBE doc missing presence note")
    if "pala_demo.py" not in fork:
        return _check("fork_pack", "failed", "FORK_PACK missing demo seed command")
    return _check("fork_pack", "passed", "fork surface files present")


def audit_demo_seed(root: Path) -> dict[str, str]:
    demo = root / "examples" / "demo-software-project"
    try:
        with tempfile.TemporaryDirectory(prefix="pala-self-audit-") as temp:
            proof = pala_demo.prove_status_html(
                demo_root=demo, catalog_root=Path(temp)
            )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return _check("demo_seed", "failed", str(exc))
    if proof.get("status") != "passed":
        return _check("demo_seed", "failed", str(proof.get("error") or "status html proof failed"))
    events = int((proof.get("seed") or {}).get("events_written") or proof.get("events_written") or 0)
    if events < 3:
        return _check("demo_seed", "failed", "seed did not write three events")
    return _check("demo_seed", "passed", f"events={events}; status_html=passed")


def audit_soft_claims(root: Path) -> dict[str, str]:
    targets = [
        root / "README.md",
        root / "docs" / "VIBE_FIRST_SESSION.md",
        root / "docs" / "FORK_PACK.md",
        root / "skills" / "pala-project-finisher" / "SKILL.md",
        root / "scripts" / "pala_hook.py",
    ]
    hits: list[str] = []
    for path in targets:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in BANNED_CLAIM_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path.name}:{pattern.pattern}")
    if hits:
        return _check("soft_claims", "failed", "; ".join(hits[:5]))
    return _check("soft_claims", "passed", "no soft speed/quota claims")


def audit_debugging_brain(root: Path) -> dict[str, str]:
    """Fail-closed: root DEBUGGING.md must parse as durable error brain."""
    path = root / "DEBUGGING.md"
    if not path.is_file():
        return _check("debugging_brain", "failed", "DEBUGGING.md missing")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return _check("debugging_brain", "failed", str(exc))
    parsed = pala_memory.parse_debugging_brain(text)
    if not parsed.get("ok"):
        return _check("debugging_brain", "failed", str(parsed.get("detail") or "parse failed"))
    count = len(parsed.get("incidents") or [])
    return _check("debugging_brain", "passed", f"incidents={count}")


def audit_agent_tasks(root: Path) -> dict[str, str]:
    """Fail-closed: PLAN.md agent task cards must parse when M24 or M*-T* present."""
    plan_path = root / "PLAN.md"
    if not plan_path.is_file():
        return _check("agent_tasks", "passed", "no PLAN.md")
    try:
        text = plan_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _check("agent_tasks", "failed", str(exc))
    has_m24 = bool(re.search(r"(?m)^##\s+M24\b", text))
    has_task_headings = bool(re.search(r"(?m)^#{4}\s+M\d+-T\d+", text))
    if not has_m24 and not has_task_headings:
        return _check("agent_tasks", "passed", "no task cards")
    parsed = pala_memory.parse_agent_task_cards(text)
    if not parsed.get("ok"):
        return _check("agent_tasks", "failed", str(parsed.get("detail") or "parse failed"))
    cards = parsed.get("cards") or []
    if has_m24 and len(cards) < 3:
        return _check(
            "agent_tasks",
            "failed",
            f"M24 section present but cards={len(cards)}<3",
        )
    return _check("agent_tasks", "passed", f"cards={len(cards)}")


def audit_manifest(root: Path) -> dict[str, str]:
    manifest = json.loads(
        (root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    version = str(manifest.get("version") or "")
    if not version.startswith("0.8."):
        return _check("manifest", "failed", f"expected 0.8.x cachebuster, got {version}")
    market = json.loads(
        (root / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
    )
    plugins = market.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        return _check("manifest", "failed", "marketplace plugins missing")
    return _check("manifest", "passed", version)


def audit_shared_memory(root: Path) -> dict[str, str]:
    decisions = (root / "DECISIONS.md").read_text(encoding="utf-8")
    agents = root / "AGENTS.md"
    shared = root / "scripts" / "pala_shared_memory.py"
    portable = root / "portable" / "cursor" / "SKILL.md"
    rule = root / ".cursor" / "rules" / "pala-memory.mdc"
    shared_doc = root / "docs" / "PALA_SHARED_MEMORY.md"
    if "ADR-017" not in decisions:
        return _check("shared_memory", "failed", "ADR-017 missing from DECISIONS.md")
    if not agents.is_file():
        return _check("shared_memory", "failed", "AGENTS.md missing (single rules source)")
    if not shared.is_file():
        return _check("shared_memory", "failed", "pala_shared_memory.py missing")
    if not portable.is_file():
        return _check("shared_memory", "failed", "portable/cursor/SKILL.md missing")
    if not rule.is_file():
        return _check("shared_memory", "failed", "cursor pala-memory rule missing")
    if not shared_doc.is_file():
        return _check("shared_memory", "failed", "docs/PALA_SHARED_MEMORY.md missing")
    from pala_shared_memory import (
        CURSOR_RULE_MAX_BODY_LINES,
        cursor_rule_body_lines,
        portable_skill_drift,
    )

    skill_text = portable.read_text(encoding="utf-8")
    missing = portable_skill_drift(skill_text)
    if missing:
        return _check(
            "shared_memory",
            "failed",
            "portable skill drift: " + ", ".join(missing),
        )
    skill = skill_text.casefold()
    if "hooks" not in skill:
        return _check("shared_memory", "failed", "portable skill must mention hooks boundary")
    rule_text = rule.read_text(encoding="utf-8")
    body = cursor_rule_body_lines(rule_text)
    if len(body) > CURSOR_RULE_MAX_BODY_LINES:
        return _check(
            "shared_memory",
            "failed",
            f"cursor rule too thick ({len(body)}>{CURSOR_RULE_MAX_BODY_LINES})",
        )
    if "agents.md" not in rule_text.casefold():
        return _check("shared_memory", "failed", "cursor rule must point at AGENTS.md")
    agents_text = agents.read_text(encoding="utf-8").casefold()
    if "adr-017" not in agents_text and "tek kaynak" not in agents_text:
        if "single source" not in agents_text and "multi-host" not in agents_text:
            return _check(
                "shared_memory",
                "failed",
                "AGENTS.md must declare multi-host / single-source role",
            )
    doc = shared_doc.read_text(encoding="utf-8").casefold()
    if "shared_store" not in doc or "hit" not in doc or "miss" not in doc:
        return _check(
            "shared_memory",
            "failed",
            "PALA_SHARED_MEMORY.md must document hit/miss + shared_store",
        )
    return _check("shared_memory", "passed", "ADR-017 + Wave E multi-host proof")


RUNTIME_CHECKS = (
    "presence",
    "hook_safety",
    "soft_claims",
    "manifest",
)


def run_audit(root: Path | None = None, profile: str = "source") -> dict[str, object]:
    root = (root or PLUGIN_ROOT).resolve()
    if profile not in {"source", "runtime"}:
        raise ValueError("profile must be source or runtime")
    builders = {
        "presence": audit_presence,
        "hook_safety": audit_hook_safety,
        "fork_pack": audit_fork_pack,
        "demo_seed": audit_demo_seed,
        "soft_claims": audit_soft_claims,
        "debugging_brain": audit_debugging_brain,
        "agent_tasks": audit_agent_tasks,
        "shared_memory": audit_shared_memory,
        "manifest": audit_manifest,
    }
    if profile == "runtime":
        checks = [builders[name](root) for name in RUNTIME_CHECKS]
    else:
        checks = [builder(root) for builder in builders.values()]
    failed = [item for item in checks if item["status"] == "failed"]
    overall = "failed" if failed else "passed"
    if overall == "passed":
        if profile == "runtime":
            summary_tr = (
                "Pala runtime self-audit geçti: presence, hook_safety, "
                "soft_claims ve manifest kapıları yeşil."
            )
        else:
            summary_tr = (
                "Pala self-audit geçti: presence, fork paketi, demo seed, soft-claim, "
                "debugging-brain ve agent_tasks kapıları yeşil."
            )
    else:
        failed_names = ", ".join(item["name"] for item in failed[:5])
        summary_tr = (
            f"Pala self-audit başarısız: {len(failed)} kapı kırmızı"
            f" ({failed_names})."
        )
    return {
        "status": overall,
        "summary_tr": summary_tr,
        "checks": checks,
        "root": str(root),
        "profile": profile,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--root",
        type=Path,
        default=PLUGIN_ROOT,
        help="Plugin / repo root to audit",
    )
    result.add_argument(
        "--profile",
        choices=("source", "runtime"),
        default="source",
        help="source = full repo gates; runtime = installed marketplace lean gates",
    )
    return result


def run_cli(argv: list[str] | None = None) -> tuple[int, str]:
    args = parser().parse_args(argv)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        payload = run_audit(args.root, profile=args.profile)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(payload["summary_tr"])
    code = 0 if payload["status"] == "passed" else 1
    return code, buffer.getvalue()


def main(argv: list[str] | None = None) -> int:
    code, payload = run_cli(argv)
    sys.stdout.write(payload)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

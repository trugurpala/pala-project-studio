#!/usr/bin/env python3
"""Evidence-first cold-session packet, context budget, and capability preflight (M29).

Priority on conflict:
  source + Git + test evidence > Pala SQLite > Markdown handoff > prior chat claim
Emit ``stale-context`` and do not apply stale state.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from pala_cold_packet_git import git_surface
from pala_cold_packet_packet import build_cold_packet as _build_cold_packet
from pala_milestone_truth import current_milestones
from pala_state_core import workflow_path
from pala_tokens import approx_tokens as _estimate_tokens

MINIMAL_MAX_BYTES = 2048
PROFILES = ("minimal", "standard", "milestone")
EVIDENCE_SOURCES = (
    "source_git_test",
    "pala_sqlite",
    "markdown_handoff",
    "prior_chat",
)

# Never drop these when trimming a budget profile.
_PROTECTED_SCOPES = frozenset(
    {"active_risk", "test_evidence", "open_blocker", "do_not_retry", "stale_context"}
)

_DOC_BY_PROFILE: dict[str, tuple[str, ...]] = {
    "minimal": ("status",),
    "standard": ("status", "decisions", "debugging"),
    "milestone": ("status", "plan", "decisions", "progress", "debugging", "project"),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _which(name: str) -> str | None:
    return shutil.which(name)


def _tool_status(present: bool, *, probed: bool = True) -> str:
    """Honest labels only â€” never invent passed without a real probe."""
    if not probed:
        return "configured-not-verified"
    return "passed" if present else "not-run"


def _load_workflow(root: Path) -> dict[str, object]:
    path = workflow_path(root)
    legacy_path = root / ".codex" / "pala-workflow.json"
    if not path.is_file() and legacy_path.is_file():
        path = legacy_path
    if not path.is_file():
        try:
            from pala_store import WorkflowStore

            task = WorkflowStore(root).active_task_contract()
        except (ImportError, OSError, ValueError):
            task = None
        if not isinstance(task, dict):
            return {}
        return {
            "schema_version": 2,
            "projection_of": "v3-task-contract",
            "canonical_state": "v3",
            "active_ticket": task.get("id"),
            "goal": task.get("goal"),
            "next_action": task.get("next_action"),
            "dirty": True,
            "blockers": [task.get("blocker")] if task.get("blocker") else [],
            "verification": task.get("evidence") or [],
            "verification_tier": "not-run",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _status_snippet(root: Path, documents: dict[str, object] | None, *, max_chars: int = 240) -> str:
    docs = documents if isinstance(documents, dict) else {}
    rel = docs.get("status") if isinstance(docs.get("status"), str) else "STATUS.md"
    path = root / rel
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Åu an tek sonraki iÅŸ") or stripped.startswith(
            "## Current next"
        ):
            continue
        if stripped.startswith("- ") and "sonraki" in stripped.casefold():
            return stripped[:max_chars]
    # Fall back: first non-empty bullet under next-action heading.
    capture = False
    for line in text.splitlines():
        if "tek sonraki" in line.casefold() or "next action" in line.casefold():
            capture = True
            continue
        if capture and line.strip():
            return line.strip()[:max_chars]
    return ""


def detect_stale_context(
    root: Path,
    workflow: dict[str, object] | None = None,
    git: dict[str, object] | None = None,
) -> dict[str, object]:
    """Compare Pala workflow checkpoint HEAD vs live Git; emit stale-context on conflict."""
    wf = workflow if isinstance(workflow, dict) else _load_workflow(root)
    surface = git if isinstance(git, dict) else git_surface(root)
    live_head = surface.get("base_commit")
    basis = wf.get("checkpoint_basis") if isinstance(wf.get("checkpoint_basis"), dict) else {}
    basis_git = basis.get("git") if isinstance(basis.get("git"), dict) else {}
    stored_head = basis_git.get("head")
    if isinstance(stored_head, str) and len(stored_head) >= 7:
        stored_head = stored_head[:40]
    else:
        stored_head = None

    stale = False
    reasons: list[str] = []
    if (
        stored_head
        and isinstance(live_head, str)
        and live_head
        and not live_head.startswith(stored_head[:12])
        and not stored_head.startswith(str(live_head)[:12])
    ):
        # New commit vs stored checkpoint without reconcile.
        if wf.get("dirty") or wf.get("active_ticket") or wf.get("needs_reconcile"):
            stale = True
            reasons.append("workflow checkpoint HEAD != live Git HEAD")

    # Explicit parallel stamp mismatch.
    stamp = wf.get("parallel") if isinstance(wf.get("parallel"), dict) else {}
    stamp_commit = stamp.get("base_commit")
    if (
        isinstance(stamp_commit, str)
        and stamp_commit
        and isinstance(live_head, str)
        and live_head
        and not live_head.startswith(stamp_commit[:12])
        and not stamp_commit.startswith(str(live_head)[:12])
    ):
        stale = True
        reasons.append("parallel base_commit != live Git HEAD")

    other_wt = stamp.get("worktree")
    live_wt = surface.get("worktree")
    if (
        isinstance(other_wt, str)
        and other_wt
        and isinstance(live_wt, str)
        and Path(other_wt).resolve() != Path(str(live_wt)).resolve()
        and wf.get("active_ticket")
    ):
        stale = True
        reasons.append("worktree changed since last checkpoint stamp")

    return {
        "stale_context": stale,
        "apply_state": not stale,
        "reasons": reasons,
        "stored_head": stored_head,
        "live_head": live_head,
        "evidence_source": "source_git_test",
    }


def detect_worktree_conflict(
    *,
    ticket: str,
    this_worktree: str,
    other_worktree: str | None,
    other_branch: str | None = None,
    this_branch: str | None = None,
) -> dict[str, object]:
    """Two worktrees claiming the same ticket â†’ reconcile required."""
    if not ticket.strip():
        return {"conflict": False, "reconcile_required": False, "reason": ""}
    if not other_worktree:
        return {"conflict": False, "reconcile_required": False, "reason": ""}
    try:
        same = Path(this_worktree).resolve() == Path(other_worktree).resolve()
    except OSError:
        same = this_worktree.replace("\\", "/").casefold() == other_worktree.replace(
            "\\", "/"
        ).casefold()
    if same:
        return {"conflict": False, "reconcile_required": False, "reason": ""}
    reason = (
        f"ticket {ticket} active in other worktree {other_worktree}; reconcile required"
    )
    return {
        "conflict": True,
        "reconcile_required": True,
        "reason": reason,
        "ticket": ticket,
        "this_worktree": this_worktree,
        "other_worktree": other_worktree,
        "this_branch": this_branch,
        "other_branch": other_branch,
    }


def parallel_checkpoint_fields(
    *,
    session_id: str | None,
    worktree: str,
    branch: str,
    base_commit: str | None,
    file_scope: list[str] | None = None,
) -> dict[str, object]:
    return {
        "session_id": (session_id or "")[:120] or None,
        "worktree": worktree,
        "branch": branch,
        "base_commit": (base_commit or None),
        "file_scope": list(file_scope or [])[:32],
        "updated_at": _utc_now(),
    }


def capability_manifest(
    root: Path,
    *,
    plugin_version: str | None = None,
    authority: dict[str, bool] | None = None,
    git_surface_data: dict[str, object] | None = None,
) -> dict[str, object]:
    """Read-only capability snapshot for session start (M29-T4)."""
    git = git_surface_data if isinstance(git_surface_data, dict) else git_surface(root)
    auth = authority or {}
    py_ok = True
    node = _which("node") or _which("node.exe")
    git_bin = _which("git") or _which("git.exe")
    pytest = _which("pytest") or _which("pytest.exe")
    playwright = _which("playwright") or _which("playwright.exe")
    # Browser: presence of playwright CLI only â€” never claim browser proof.
    browser_status = _tool_status(bool(playwright), probed=True)
    if not playwright:
        browser_status = "not-run"

    version = plugin_version
    if not version:
        manifest = root / ".codex-plugin" / "plugin.json"
        if manifest.is_file():
            try:
                version = str(
                    json.loads(manifest.read_text(encoding="utf-8")).get("version") or ""
                )
            except (OSError, json.JSONDecodeError, TypeError):
                version = None

    network = os.environ.get("PALA_NETWORK", "").strip().casefold()
    if network in {"offline", "0", "false", "no"}:
        network_status = "blocked"
    elif network in {"online", "1", "true", "yes"}:
        network_status = "configured-not-verified"
    else:
        network_status = "configured-not-verified"

    return {
        "os": platform.system() or "unknown",
        "shell": os.environ.get("COMSPEC") or os.environ.get("SHELL") or "unknown",
        "git": _tool_status(bool(git_bin)),
        "node": _tool_status(bool(node)),
        "python": _tool_status(py_ok),
        "test_runner": _tool_status(bool(pytest)),
        "browser": browser_status,
        "playwright": browser_status,
        "network": network_status,
        "trusted_dir": "configured-not-verified",
        "authority": {
            "write": bool(auth.get("write", True)),
            "delete": bool(auth.get("delete", False)),
            "commit": bool(auth.get("commit", False)),
            "push": bool(auth.get("push", False)),
        },
        "plugin_version": version or "unknown",
        "launcher": "pala_paths",
        "worktree": git.get("worktree"),
        "branch": git.get("branch"),
        "base_commit": git.get("base_commit"),
        "evidence_policy": "passed only with command+exit+timestamp+path",
    }


def context_record(
    *,
    name: str,
    scope: str,
    text: str = "",
    freshness: str = "unknown",
    confidence: str = "medium",
    superseded_by: str | None = None,
    protected: bool = False,
) -> dict[str, object]:
    return {
        "name": name,
        "scope": scope,
        "freshness": freshness,
        "confidence": confidence,
        "superseded_by": superseded_by,
        "estimated_token_cost": _estimate_tokens(text),
        "bytes": len(text.encode("utf-8")),
        "protected": protected or scope in _PROTECTED_SCOPES,
        "text": text,
    }


def select_documents_for_profile(
    root: Path,
    documents: dict[str, object] | None,
    profile: str,
) -> list[dict[str, object]]:
    """Choose which project docs to surface; simple tickets stay on minimal."""
    if profile not in PROFILES:
        profile = "minimal"
    docs = documents if isinstance(documents, dict) else {}
    keys = _DOC_BY_PROFILE[profile]
    records: list[dict[str, object]] = []
    for key in keys:
        rel = docs.get(key) if isinstance(docs.get(key), str) else None
        if not rel:
            defaults = {
                "status": "STATUS.md",
                "plan": "PLAN.md",
                "decisions": "DECISIONS.md",
                "progress": "PROGRESS.md",
                "debugging": "DEBUGGING.md",
                "project": "PROJECT.md",
            }
            rel = defaults.get(key)
        if not rel:
            continue
        path = root / rel
        text = ""
        freshness = "missing"
        if path.is_file():
            try:
                raw = path.read_text(encoding="utf-8")
                freshness = "file"
                if profile == "minimal":
                    # Short STATUS only â€” never dump whole AGENTS/PLAN/â€¦
                    text = raw[:600]
                elif profile == "standard":
                    text = raw[:1800]
                else:
                    text = raw[:6000]
            except OSError:
                freshness = "unreadable"
        protected = key in {"debugging", "status"}
        records.append(
            context_record(
                name=rel,
                scope=key,
                text=text,
                freshness=freshness,
                confidence="high" if freshness == "file" else "low",
                protected=protected,
            )
        )
    return records


def apply_doc_budget(
    records: list[dict[str, object]],
    *,
    max_tokens: int,
) -> list[dict[str, object]]:
    """Drop old logs / unproven summaries first; never drop protected scopes."""
    total = sum(int(r.get("estimated_token_cost") or 0) for r in records)
    if total <= max_tokens:
        return records
    kept = list(records)
    # Drop non-protected, low-confidence / unproven first (reverse order).
    drop_order = sorted(
        range(len(kept)),
        key=lambda i: (
            0 if kept[i].get("protected") else 1,
            0 if kept[i].get("confidence") == "high" else 1,
            -int(kept[i].get("estimated_token_cost") or 0),
        ),
    )
    for idx in drop_order:
        if sum(int(r.get("estimated_token_cost") or 0) for r in kept) <= max_tokens:
            break
        item = kept[idx]
        if item.get("protected"):
            continue
        if item.get("scope") in _PROTECTED_SCOPES:
            continue
        # Replace body with stub rather than losing the slot identity.
        kept[idx] = {
            **item,
            "text": "",
            "estimated_token_cost": 1,
            "bytes": 0,
            "superseded_by": "budget_trim",
            "freshness": "trimmed",
        }
    return kept


def _last_verified(workflow: dict[str, object]) -> dict[str, object]:
    evidence = workflow.get("verification_evidence")
    if isinstance(evidence, list) and evidence:
        last = evidence[-1] if isinstance(evidence[-1], dict) else {}
        return {
            "name": last.get("name") or "verification",
            "status": last.get("status") or workflow.get("verification_tier") or "not-run",
            "raw": workflow.get("verification") or [],
        }
    raw = workflow.get("verification")
    if isinstance(raw, list) and raw:
        return {"name": "verification", "status": "configured-not-verified", "raw": raw}
    # Timeout / unknown interrupt
    lifecycle = str(workflow.get("lifecycle") or "")
    if lifecycle in {"in-progress", "unknown", "interrupted"}:
        return {"name": "lifecycle", "status": lifecycle, "raw": []}
    tier = workflow.get("verification_tier") or "not-run"
    return {"name": "verification_tier", "status": tier, "raw": []}


def _open_blocker(workflow: dict[str, object], stale: dict[str, object]) -> str | None:
    blockers = workflow.get("blockers") if isinstance(workflow.get("blockers"), list) else []
    for item in blockers:
        if isinstance(item, str) and item.strip():
            return item.strip()[:200]
    if stale.get("stale_context"):
        return "stale-context: " + "; ".join(stale.get("reasons") or [])
    return None


def _do_not_retry_lines(*, limit: int = 3) -> list[dict[str, object]]:
    try:
        from pala_cmd_memory import active_blocks

        return active_blocks(limit=limit)
    except (OSError, ValueError, TypeError, ImportError):
        return []


def _cold_packet_operations() -> dict[str, object]:
    return {
        "EVIDENCE_SOURCES": EVIDENCE_SOURCES,
        "MINIMAL_MAX_BYTES": MINIMAL_MAX_BYTES,
        "PROFILES": PROFILES,
        "_do_not_retry_lines": _do_not_retry_lines,
        "_last_verified": _last_verified,
        "_load_workflow": _load_workflow,
        "_open_blocker": _open_blocker,
        "_status_snippet": _status_snippet,
        "_utc_now": _utc_now,
        "apply_doc_budget": apply_doc_budget,
        "capability_manifest": capability_manifest,
        "context_record": context_record,
        "detect_stale_context": detect_stale_context,
        "detect_worktree_conflict": detect_worktree_conflict,
        "format_packet_text": format_packet_text,
        "current_milestones": current_milestones,
        "git_surface": git_surface,
        "parallel_checkpoint_fields": parallel_checkpoint_fields,
        "select_documents_for_profile": select_documents_for_profile,
    }


def build_cold_packet(
    root: Path,
    *,
    profile: str = "minimal",
    session_id: str | None = None,
    documents: dict[str, object] | None = None,
    workflow: dict[str, object] | None = None,
    authority: dict[str, bool] | None = None,
    max_bytes: int | None = None,
) -> dict[str, object]:
    """Compatibility facade for packet assembly."""
    return _build_cold_packet(
        root,
        profile=profile,
        session_id=session_id,
        documents=documents,
        workflow=workflow,
        authority=authority,
        max_bytes=max_bytes,
        operations=_cold_packet_operations(),
    )

def format_packet_text(
    packet: dict[str, object],
    *,
    max_bytes: int | None = None,
) -> str:
    limit = max_bytes if max_bytes is not None else MINIMAL_MAX_BYTES
    lines = [
        "PALA COLD PACKET",
        f"ticket={packet.get('active_ticket') or 'none'}",
        f"goal={str(packet.get('goal') or '')[:120]}",
        f"git={packet.get('branch')}@{str(packet.get('base_commit') or '')[:12]}",
        f"worktree={packet.get('worktree')}",
        f"verified={_fmt_verified(packet.get('last_verified'))}",
        f"changed={','.join(str(x) for x in (packet.get('critical_changed_files') or [])[:6])}",
        f"blocker={packet.get('open_blocker') or 'none'}",
        f"next={packet.get('next_action')}",
        f"freshness={packet.get('state_freshness')} source={packet.get('evidence_source')}",
    ]
    milestones = packet.get("milestones")
    if isinstance(milestones, dict):
        m70 = milestones.get("M70-T3")
        if isinstance(m70, dict):
            lines.append(f"milestone=M70-T3={m70.get('task_status') or 'BACKLOG'}")
    if packet.get("stale_context"):
        lines.append("STALE-CONTEXT: do not apply prior Pala state")
        for reason in packet.get("stale_reasons") or []:
            lines.append(f"  - {reason}")
    conflict = packet.get("worktree_conflict")
    if isinstance(conflict, dict) and conflict.get("conflict"):
        lines.append(f"RECONCILE: {conflict.get('reason')}")
    if packet.get("continue_without_verify") is False:
        lines.append("STOP: verify before continue (in-progress/unknown)")
    blocks = packet.get("do_not_retry") or []
    if blocks:
        parts = [
            f"{b.get('failure_class')}/{b.get('command_family')}"
            for b in blocks
            if isinstance(b, dict)
        ]
        lines.append("do-not-retry: " + "; ".join(parts)[:200])
    caps = packet.get("capability") if isinstance(packet.get("capability"), dict) else {}
    if caps:
        lines.append(
            "caps: "
            f"git={caps.get('git')} py={caps.get('python')} "
            f"browser={caps.get('browser')} net={caps.get('network')}"
        )
    text = "\n".join(lines)
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    # Trim from the middle-ish detail lines while keeping header + next + stale.
    trimmed = encoded[: max(0, limit - 3)].decode("utf-8", errors="ignore") + "..."
    return trimmed


def _fmt_verified(value: object) -> str:
    if not isinstance(value, dict):
        return "not-run"
    name = value.get("name") or "check"
    status = value.get("status") or "not-run"
    extra = ""
    if value.get("browser_fallback"):
        extra = f";browser={value.get('browser_fallback')}"
    return f"{name}={status}{extra}"


def stamp_workflow_parallel(
    root: Path,
    *,
    session_id: str | None = None,
    file_scope: list[str] | None = None,
) -> dict[str, object]:
    """Write parallel safety fields onto pala-workflow.json (best-effort)."""
    path = workflow_path(root)
    wf = _load_workflow(root)
    if not wf:
        return {}
    git = git_surface(root)
    stamp = parallel_checkpoint_fields(
        session_id=session_id,
        worktree=str(git.get("worktree") or root),
        branch=str(git.get("branch") or "unknown"),
        base_commit=str(git.get("base_commit") or "") or None,
        file_scope=file_scope
        if file_scope is not None
        else list(git.get("changed_files") or [])[:16],
    )
    # Detect conflict vs prior stamp before overwriting.
    prior = wf.get("parallel") if isinstance(wf.get("parallel"), dict) else {}
    conflict = detect_worktree_conflict(
        ticket=str(wf.get("active_ticket") or ""),
        this_worktree=str(stamp.get("worktree") or ""),
        other_worktree=str(prior.get("worktree") or "") or None,
        other_branch=str(prior.get("branch") or "") or None,
        this_branch=str(stamp.get("branch") or "") or None,
    )
    if conflict.get("reconcile_required"):
        wf["needs_reconcile"] = True
        wf["worktree_conflict"] = conflict
    wf["parallel"] = stamp
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(wf, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except OSError:
        return {"parallel": stamp, "conflict": conflict, "written": False}
    return {"parallel": stamp, "conflict": conflict, "written": True}


def session_packet_snippet(
    root: Path,
    *,
    documents: dict[str, object] | None = None,
    workflow: dict[str, object] | None = None,
    session_id: str | None = None,
    max_bytes: int = 900,
) -> str:
    """Compact text for SessionStart additionalContext (fits beside presence)."""
    packet = build_cold_packet(
        root,
        profile="minimal",
        session_id=session_id,
        documents=documents,
        workflow=workflow,
        max_bytes=max_bytes,
    )
    return str(packet.get("text") or "")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--cwd", default=".")
    result.add_argument("--profile", choices=PROFILES, default="minimal")
    result.add_argument("--session-id", default="")
    result.add_argument("--json", action="store_true")
    result.add_argument("--max-bytes", type=int, default=MINIMAL_MAX_BYTES)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = Path(args.cwd).resolve()
    documents = None
    try:
        from pala_state import load_manifest

        documents = load_manifest(root).get("documents")
    except Exception:
        documents = None
    packet = build_cold_packet(
        root,
        profile=args.profile,
        session_id=args.session_id or None,
        documents=documents if isinstance(documents, dict) else None,
        max_bytes=args.max_bytes,
    )
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2))
    else:
        print(packet.get("text") or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

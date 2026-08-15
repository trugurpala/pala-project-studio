#!/usr/bin/env python3
"""Discover, register, and validate durable Pala project-state documents."""

from __future__ import annotations

import json
import os
import hashlib
import tempfile
import sys
from datetime import datetime, timezone
from pathlib import Path

from pala_authority import (
    git_common_dir,
    repository_instance,
    runtime_repositories_root,
    shared_state_root,
)

from pala_state_git import (
    GIT_TIMEOUT_SECONDS,
    _run_git_process,
    changed_git_paths,
    checkpoint_commit_materialized,
    git_checkpoint,
    git_diff_paths,
    git_is_ancestor,
    git_paths_snapshot,
    git_root,
    run_git,
    run_git_bytes,
    worktree_entry_digest,
)

SCHEMA_VERSION = 1
MANIFEST = Path(".codex/pala-project.json")
WORKFLOW = Path(".codex/pala-workflow.json")
WORKFLOW_SCHEMA_VERSION = 2
SESSION_KEY_LENGTH = 24
# begin without --session-key still claims a v3 ticket under this local owner
DEFAULT_LOCAL_SESSION = "pala-local"
DEFAULT_INSTRUCTION_LIMIT = 32_768
VERIFICATION_TIERS = ("narrow", "ticket", "milestone", "release", "not-run")
CANDIDATES = {
    "instructions": ("AGENTS.md",),
    "project": (
        "PROJECT.md",
        "docs/SCOPE.md",
        "README.md",
        "docs/codex/PROJECT.md",
    ),
    "plan": (
        "PLAN.md",
        "docs/IMPLEMENTATION_PLAN.md",
        "TASKS.md",
        "ROADMAP.md",
        "docs/codex/PLAN.md",
    ),
    "status": (
        "reports/CURRENT_STATUS.md",
        "STATUS.md",
        "PROJECT_STATE.md",
        "docs/codex/STATUS.md",
    ),
    "progress": (
        "PROGRESS.md",
        "docs/PROGRESS.md",
    ),
    "tooling": (
        "TOOLING_DECISIONS.md",
        "docs/TOOLING_DECISIONS.md",
    ),
    "debugging": (
        "DEBUGGING.md",
        "docs/vibe-os/TROUBLESHOOTING.md",
        "docs/DEBUGGING.md",
    ),
    "decisions": (
        "DECISIONS.md",
        "docs/PRODUCT_DECISIONS.md",
        "docs/adr",
        "docs/codex/DECISIONS.md",
    ),
    "open_source": (
        "OPEN_SOURCE.md",
        "docs/OPEN_SOURCE.md",
        "THIRD_PARTY_NOTICES.md",
        "docs/codex/OPEN_SOURCE.md",
    ),
    "demo": (
        "reports/OWNER_DEMO.md",
        "reports/PATRON_DEMO.md",
        "DEMO.md",
        "docs/DEMO.md",
    ),
}
REQUIRED = ("project", "plan", "status")
VERIFY_STATUS_PASSED_KEYWORDS = ("passed",)
VERIFY_STATUS_FAILED_KEYWORDS = ("failed", "error", "broken", "exception")
EVIDENCE_STATUSES = (
    "passed",
    "not-run",
    "blocked",
    "configured-not-verified",
    "failed",
    "timeout",
)
SOFT_DONE_RE = ("bitti", "done", "complete", "completed", "finished", "ok", "succeeded")
PROJECT_MARKERS = (
    ".codex-plugin/plugin.json",
    "SKILL.md",
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Gemfile",
    "composer.json",
)


def workflow_path(root: Path, *, read_only: bool = False) -> Path:
    """Return the generated workflow projection path for this repository."""
    project_root = Path(root).resolve()
    if read_only and git_common_dir(project_root) is not None:
        return (
            runtime_repositories_root()
            / repository_instance(project_root)
            / "generated"
            / "pala-workflow.json"
        )
    shared = shared_state_root(project_root)
    if shared is not None:
        return shared / "generated" / "pala-workflow.json"
    return project_root / WORKFLOW
FRONTEND_PACKAGES = (
    "next",
    "react",
    "vue",
    "svelte",
    "@angular/core",
    "vite",
    "astro",
)
BACKEND_PACKAGES = (
    "express",
    "fastify",
    "@nestjs/core",
    "hono",
    "koa",
)
BACKEND_PYTHON_MARKERS = ("fastapi", "django", "flask", "litestar", "starlette")
BACKEND_COMPOSER_PACKAGES = (
    "laravel/framework",
    "symfony/framework-bundle",
    "cakephp/cakephp",
    "yiisoft/yii2",
)
IGNORED_DISCOVERY_DIRS = {
    ".codegraph",
    ".git",
    ".next",
    ".nx",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
}
def quality_gate_report(root: Path, ticket: str) -> dict[str, object]:
    """Read a ticket's local quality decision without creating or running it."""
    try:
        import pala_quality

        ledger = pala_quality.quality_ledger_path(root, ticket)
        if not ledger.is_file():
            return {
                "available": False,
                "status": "not-run",
                "next_action": f"initialize quality ledger for {ticket}",
            }
        report = pala_quality.quality_gate(root, ticket)
        return {"available": True, **report}
    except (ImportError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "status": "blocked",
            "next_action": f"repair quality ledger for {ticket}",
            "detail": str(exc)[:240],
        }


def require_quality_gate(root: Path, ticket: str) -> dict[str, object]:
    """Fail closed only when a caller explicitly claims ticket quality."""
    report = quality_gate_report(root, ticket)
    if report.get("status") != "passed":
        action = str(report.get("next_action") or "run required quality gates")
        raise ValueError(f"quality gate blocked for {ticket}; next action: {action}")
    return report


def session_key(session_id: str) -> str:
    """Return a bounded stable key without persisting the raw Codex session id."""
    from pala_models import SessionKey

    return SessionKey.from_session_id(session_id)


def relative(root: Path, path: Path) -> str:
    root_path = root.resolve()
    try:
        return path.resolve().relative_to(root_path).as_posix()
    except ValueError:
        if os.name != "nt":
            raise
        root_parts = tuple(part.casefold() for part in root_path.parts)
        path_parts = tuple(part.casefold() for part in path.resolve().parts)

        def _segment_matches(left: str, right: str) -> bool:
            if left == right:
                return True
            left_short, right_short = left.casefold(), right.casefold()
            if "~" in left_short:
                return right_short.startswith(left_short.split("~", 1)[0])
            if "~" in right_short:
                return left_short.startswith(right_short.split("~", 1)[0])
            return False

        if (
            len(path_parts) >= len(root_parts)
            and all(
                _segment_matches(left, right)
                for left, right in zip(root_parts, path_parts[: len(root_parts)])
            )
            and root_path.exists()
        ):
            return "/".join(path_parts[len(root_parts) :])
        raise



def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        suffix=".tmp",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        newline="\n",
    ) as stream:
        stream.write(json.dumps(payload, ensure_ascii=False, indent=2))
        stream.write("\n")
        temp_path = Path(stream.name)
    temp_path.replace(path)


def bounded_strings(values: list[str], *, limit: int) -> list[str]:
    return [item.strip()[:500] for item in values if item.strip()][:limit]


def context_receipt_read_model(
    payload: object,
    *,
    expected: object | None = None,
    expected_snapshot: object | None = None,
) -> dict[str, object]:
    """Expose only the bounded receipt projection; never mutate workflow state."""
    from pala_context_receipt import receipt_summary

    return receipt_summary(
        payload,
        expected=expected,
        expected_snapshot=expected_snapshot,
    )


def refresh_continuity(
    root: Path,
    *,
    task_contract: dict[str, object] | None = None,
    persist: bool = False,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Build live continuity and optionally persist only validated scalars."""
    from pala_state_documents import professional_project_profile_report

    project_root = Path(root).resolve()
    built = build_registered_continuity_context(
        project_root, task_contract=task_contract
    )
    if built is None:
        manifest = load_manifest(project_root)
        profile_value = manifest.get("project_profile")
        profile_model = professional_project_profile_report(None)
        if isinstance(profile_value, str) and profile_value.strip():
            profile_path = (project_root / profile_value).resolve()
            try:
                payload = json.loads(profile_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    profile_model = professional_project_profile_report(payload)
            except (OSError, json.JSONDecodeError):
                pass
        return {
            "status": "not-run",
            "finding": (
                "ACTIVE_TASK_NOT_AVAILABLE"
                if isinstance(profile_value, str) and profile_value.strip()
                else "PROJECT_PROFILE_NOT_CONFIGURED"
            ),
            "receipt": {"validation_status": "not-run", "can_complete": False},
            "profile": profile_model,
        }
    context = built
    target_db = Path(db_path) if db_path is not None else _continuity_db_path()
    from pala_continuity import persist_context, read_models

    models = read_models(
        project_id=context.profile.project_id,
        repository_id=context.snapshot.repository_id,
        db_path=target_db,
    )
    continuity = (
        persist_context(context, db_path=target_db)
        if persist
        else models["continuity"]
    )
    if (
        not persist
        and continuity.get("validation_status") == "passed"
        and continuity.get("receipt_id") != context.receipt.receipt_id
    ):
        continuity = {
            **continuity,
            "validation_status": "blocked",
            "finding": {
                "code": "CONTINUITY_RECEIPT_STALE",
                "status": "blocked",
                "resolution": "refresh continuity on an explicit lifecycle mutation",
            },
            "can_complete": False,
        }
    history = models["history"]
    return {
        "status": "passed",
        "profile": professional_project_profile_report(context.profile.to_dict()),
        "receipt": context.receipt_read_model(),
        "continuity": continuity,
        "history": history,
        "repository_id": context.snapshot.repository_id,
        "project_id": context.profile.project_id,
        "can_complete": False,
    }


def build_registered_continuity_context(
    root: Path,
    *,
    task_contract: dict[str, object] | None = None,
):
    """Build the ephemeral registered context without persisting its payload."""
    project_root = Path(root).resolve()
    manifest = load_manifest(project_root)
    profile_value = manifest.get("project_profile")
    if not isinstance(profile_value, str) or not profile_value.strip():
        return None
    profile_path = (project_root / profile_value).resolve()
    try:
        profile_path.relative_to(project_root)
    except ValueError as exc:
        raise ValueError("project profile must remain inside project root") from exc
    profile_payload = json.loads(profile_path.read_text(encoding="utf-8"))
    if not isinstance(profile_payload, dict):
        raise ValueError("project profile must be a JSON object")

    if task_contract is None:
        from pala_store import WorkflowStore

        task_contract = WorkflowStore(project_root).active_task_contract()
    if not isinstance(task_contract, dict):
        return None

    source_refs: list[dict[str, str]] = []
    documents = manifest.get("documents")
    if isinstance(documents, dict):
        for purpose in ("project", "plan", "decisions"):
            relative_path = documents.get(purpose)
            if not isinstance(relative_path, str) or not relative_path.strip():
                continue
            source = (project_root / relative_path).resolve()
            try:
                safe_relative = source.relative_to(project_root).as_posix()
            except ValueError as exc:
                raise ValueError("continuity source must remain inside project root") from exc
            digest = file_sha256(source)
            if digest:
                source_refs.append({"path": safe_relative, "digest": digest})

    from pala_continuity import build_context

    next_action = str(task_contract.get("next_action") or "configure-quality")
    return build_context(
        project_root,
        profile_payload=profile_payload,
        task_contract=task_contract,
        source_refs=source_refs,
        capabilities=[],
        verifications=[],
        risk_codes=list(context_risk_codes(task_contract)),
        next_action=next_action,
    )


def context_risk_codes(task_contract: dict[str, object]) -> tuple[str, ...]:
    blocker = task_contract.get("blocker")
    return ("active-task-blocked",) if blocker else ()


def _continuity_db_path() -> Path:
    from pala_catalog import db_path

    return db_path()


def _refresh_continuity_best_effort(
    root: Path, record: dict[str, object]
) -> None:
    task_contract = record.get("task_contract")
    if not isinstance(task_contract, dict):
        return
    try:
        refresh_continuity(root, task_contract=task_contract, persist=True)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        _record_store_event(
            root,
            "continuity",
            detail=f"continuity refresh not-run: {type(exc).__name__}",
        )


def file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def document_fingerprints(
    root: Path, manifest: dict[str, object]
) -> dict[str, dict[str, str | None]]:
    documents = manifest.get("documents")
    if not isinstance(documents, dict):
        return {}
    result: dict[str, dict[str, str | None]] = {}
    for purpose, value in documents.items():
        if not isinstance(purpose, str) or not isinstance(value, str) or not value:
            continue
        path = (root / value).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            continue
        result[purpose] = {"path": value, "sha256": file_sha256(path)}
    return result


def has_failed_verification(entries: list[str]) -> bool:
    for value in entries:
        lowered = value.casefold()
        if any(token in lowered for token in VERIFY_STATUS_FAILED_KEYWORDS):
            return True
    return False


def _normalize_evidence_entries(entries: list[str]) -> list[dict[str, str]]:
    """Parse `name=status` or `name: status` evidence lines."""
    import re

    parsed: list[dict[str, str]] = []
    for raw in entries:
        text = raw.strip()
        if not text:
            continue
        lowered = text.casefold()
        # Soft completion words alone are never evidence.
        if lowered in SOFT_DONE_RE:
            raise ValueError(
                "checkpoint refused: soft done word is not evidence; "
                "use name=passed|not-run|blocked|configured-not-verified"
            )
        match = re.match(
            r"^(?P<name>[^=:]+)[=:]\s*(?P<status>[A-Za-z0-9_-]+)\s*(?P<rest>.*)$",
            text,
        )
        if not match:
            raise ValueError(
                "checkpoint refused: evidence must look like "
                "'unittest=passed' or 'install=configured-not-verified'"
            )
        name = match.group("name").strip()[:120]
        if name.casefold() in SOFT_DONE_RE:
            raise ValueError(
                "checkpoint refused: soft done word is not an evidence name; "
                "use a real gate like 'unittest=passed'"
            )
        status = match.group("status").casefold().replace("_", "-")
        if status not in EVIDENCE_STATUSES:
            raise ValueError(f"unsupported evidence status: {status}")
        if status in {"failed"}:
            raise ValueError("checkpoint refused: verification contains failed status")
        parsed.append(
            {
                "name": name,
                "status": status,
                "detail": match.group("rest").strip()[:200],
            }
        )
    if not parsed:
        raise ValueError("verification evidence is required for checkpoint")
    if not any(item["status"] == "passed" for item in parsed):
        # Allow checkpoint when only blocked/not-run if explicitly present,
        # but require at least one non-soft structured line (already true).
        # Still refuse if every line is soft-adjacent without passed when tier expects work.
        pass
    return parsed



def checkpoint_basis(
    root: Path, manifest: dict[str, object]
) -> dict[str, object]:
    from pala_state_documents import document_fingerprints

    return {
        "documents": document_fingerprints(root, manifest),
        "git": git_checkpoint(root),
    }


def reconciliation_report(
    root: Path,
    manifest: dict[str, object],
    workflow: dict[str, object],
) -> dict[str, object]:
    reasons: list[str] = []
    basis = workflow.get("checkpoint_basis")
    fresh_active_ticket = (
        workflow.get("schema_version") == WORKFLOW_SCHEMA_VERSION
        and workflow.get("dirty") is True
        and workflow.get("needs_reconcile") is False
        and basis is None
    )
    if fresh_active_ticket:
        pass
    elif workflow.get("schema_version") != WORKFLOW_SCHEMA_VERSION or not isinstance(
        basis, dict
    ):
        reasons.append("legacy workflow has no checkpoint basis")
    else:
        previous_documents = basis.get("documents")
        current_documents = document_fingerprints(root, manifest)
        if isinstance(previous_documents, dict):
            for purpose in sorted(set(previous_documents) | set(current_documents)):
                if previous_documents.get(purpose) != current_documents.get(purpose):
                    reasons.append(f"{purpose} changed since checkpoint")
        else:
            reasons.append("checkpoint document basis is missing")

        previous_git = basis.get("git")
        current_git = git_checkpoint(root)
        if isinstance(previous_git, dict):
            commit_materialized = (
                previous_git.get("head") != current_git.get("head")
                and checkpoint_commit_materialized(root, previous_git, current_git)
            )
            if not commit_materialized:
                if previous_git.get("head") != current_git.get("head"):
                    reasons.append("Git HEAD changed since checkpoint")
                if previous_git.get("worktree_sha256") != current_git.get(
                    "worktree_sha256"
                ):
                    reasons.append("working tree changed since checkpoint")
        else:
            reasons.append("checkpoint Git basis is missing")

    if workflow.get("needs_reconcile"):
        reasons.append("workflow was marked for reconciliation")
    return {"needed": bool(reasons), "reasons": list(dict.fromkeys(reasons))}


def load_workflow(root: Path) -> dict[str, object]:
    path = workflow_path(root, read_only=True)
    legacy_path = Path(root).resolve() / WORKFLOW
    if not path.is_file() and legacy_path.is_file():
        path = legacy_path
    try:
        from pala_store import WorkflowStore

        task = WorkflowStore(root).active_task_contract()
    except (ImportError, OSError, RuntimeError, TypeError, ValueError):
        task = None
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") not in (
            1,
            WORKFLOW_SCHEMA_VERSION,
        ):
            raise ValueError("unsupported Pala workflow schema")
    else:
        if not isinstance(task, dict):
            raise ValueError(f"workflow state not found: {path}")
        payload = {
            "schema_version": WORKFLOW_SCHEMA_VERSION,
            "projection_of": "v3-task-contract",
            "canonical_state": "v3",
            "active_ticket": task.get("id"),
            "goal": task.get("goal"),
            "next_action": task.get("next_action"),
            "dirty": True,
            "needs_reconcile": False,
            "blockers": [task.get("blocker")] if task.get("blocker") else [],
            "verification": task.get("evidence") or [],
            "verification_tier": "not-run",
        }
    if isinstance(task, dict):
        payload.update(
            {
                "schema_version": WORKFLOW_SCHEMA_VERSION,
                "projection_of": "v3-task-contract",
                "canonical_state": "v3",
                "active_ticket": task.get("id"),
                "goal": task.get("goal"),
                "lifecycle": task.get("status") or "IN_PROGRESS",
                "next_action": task.get("next_action"),
                "dirty": True,
                "needs_reconcile": False,
                "checkpoint_basis": None,
                "blockers": [task.get("blocker")] if task.get("blocker") else [],
                "verification": task.get("evidence") or [],
                "verification_tier": "not-run",
            }
        )
    return payload


def _record_store_event(
    root: Path,
    kind: str,
    *,
    detail: str = "",
    evidence: str = "",
) -> None:
    """Best-effort history write; never raises into caller workflows."""
    try:
        import pala_db
        from pala_catalog import db_path, _project_id

        pala_db.add_event(
            kind,
            project_id=_project_id(root),
            project_name=root.name,
            detail=detail,
            evidence=evidence,
            path=db_path(),
        )
    except (OSError, RuntimeError, ValueError, TypeError, KeyError, ImportError):
        pass
    except Exception as exc:
        if exc.__class__.__module__ == "sqlite3":
            pass
        else:
            raise


def _emit_debug_gate(root: Path, *, surface: str) -> None:
    """Warn on stderr + record attempt when open INC exist (Wave B)."""
    try:
        from pala_debug_gate import evaluate_gate, record_debug_attempt

        documents: dict[str, object] | None = None
        try:
            documents = dict(load_manifest(root).get("documents") or {})
        except (OSError, ValueError, json.JSONDecodeError):
            documents = {"debugging": "DEBUGGING.md"}
        report = evaluate_gate(root, documents, surface=surface)
        if not report.get("warn"):
            return
        message = str(report.get("message") or "").strip()
        if message:
            print(message, file=sys.stderr)
        for item in report.get("incidents") or []:
            if not isinstance(item, dict):
                continue
            inc_id = str(item.get("id") or "").strip()
            if not inc_id:
                continue
            record_debug_attempt(
                root,
                inc_id,
                detail=f"{surface}: saw open {inc_id}",
                evidence=f"surface={surface}",
            )
    except (OSError, ValueError, TypeError, KeyError, ImportError):
        pass


def complete_recovery_message(ticket: str, *, reason: str = "") -> str:
    """Actionable Turkish recovery when complete cannot find ticket/session."""
    tip = (
        f"complete reddedildi: ticket/oturum kaydÄ± yok veya uyuÅŸmuyor ({ticket}). "
        f"Ã–nce gerekirse register; sonra "
        f'begin --ticket {ticket} --goal "tek sonraki iÅŸ" --session-key <aynÄ±-anahtar> '
        f"(session yoksa begin varsayÄ±lanÄ±: {DEFAULT_LOCAL_SESSION}). Soft-pass yok."
    )
    detail = (reason or "").strip()
    if detail and detail not in tip:
        return f"{tip} ({detail})"
    return tip


def complete_work(root: Path, ticket: str, session: str):
    """Complete a v3 ticket and reconcile only its clean matching v2 row.

    A legacy workflow can retain release ownership after engineering has
    completed.  That action is evidence/owner handoff, not an active ticket.
    Never alter a different, dirty, unreadable, or unsupported legacy row.
    """
    from pala_store import WorkflowStore

    result = WorkflowStore(root).complete(ticket, session)
    if result.status != "completed":
        return result
    _record_store_event(root, "complete", detail=f"{ticket}: canonical task completed")
    try:
        legacy = load_workflow(root)
    except (OSError, ValueError, json.JSONDecodeError):
        return result
    if legacy.get("active_ticket") != ticket or bool(legacy.get("dirty")):
        return result
    legacy["active_ticket"] = None
    legacy["goal"] = None
    legacy["last_completed_ticket"] = ticket
    legacy["completed_at"] = datetime.now(timezone.utc).isoformat()
    legacy["needs_reconcile"] = False
    legacy["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(workflow_path(root), legacy)
    return result


def begin_work(
    root: Path, ticket: str, goal: str, session: str | None = None,
    acceptance: list[str] | None = None,
) -> None:
    if not ticket.strip() or not goal.strip():
        raise ValueError("ticket and goal must be non-empty")
    _emit_debug_gate(root, surface="begin")
    from pala_store import WorkflowStore

    structured_acceptance = [
        {"id": f"AC-{index:02d}", "text": text, "status": "not-run", "evidence_refs": []}
        for index, text in enumerate(acceptance or [], start=1) if text.strip()
    ]
    if session is not None:
        result = WorkflowStore(root).claim(
            ticket=ticket, goal=goal, session=session, acceptance=structured_acceptance,
        )
        if result.status == "owned_by_other":
            raise ValueError("ticket is owned by another active session")
        if result.status == "busy":
            raise ValueError("ticket claim busy; retry begin with the same --session-key")
        _refresh_continuity_best_effort(root, result.record)
        _record_store_event(
            root,
            "begin",
            detail=f"{ticket.strip()}: {goal.strip()}"[:300],
        )
        return

    if WorkflowStore(root).has_dirty_record():
        raise ValueError(
            "active ticket work exists for another session; use --session-key for parallel-safe ownership"
        )
    if workflow_path(root).is_file() or (root / WORKFLOW).is_file():
        existing = load_workflow(root)
        if existing.get("dirty"):
            raise ValueError(
                "active workflow has uncheckpointed dirty work; run checkpoint before begin"
            )
    # Always write a v3 ticket row so complete/session tools can find it.
    claim = WorkflowStore(root).claim(
        ticket=ticket, goal=goal, session=DEFAULT_LOCAL_SESSION,
        acceptance=structured_acceptance,
    )
    if claim.status == "owned_by_other":
        raise ValueError("ticket is owned by another active session")
    if claim.status == "busy":
        raise ValueError("ticket claim busy; retry begin")
    _refresh_continuity_best_effort(root, claim.record)
    payload = {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "projection_of": "v3-ticket-store",
        "canonical_state": "v3",
        "active_ticket": ticket.strip(),
        "goal": goal.strip(),
        "dirty": True,
        "needs_reconcile": False,
        "next_action": None,
        "verification": [],
        "verification_tier": "not-run",
        "blockers": [],
        "checkpoint_basis": None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(workflow_path(root), payload)
    _record_store_event(
        root,
        "begin",
        detail=f"{ticket.strip()}: {goal.strip()}"[:300],
    )


def checkpoint_work(
    root: Path,
    next_action: str,
    verification: list[str],
    blockers: list[str],
    tier: str = "ticket",
    *,
    changed_summary: str = "",
    changed_files: list[str] | None = None,
    session_id: str | None = None,
    quality_ticket: str | None = None,
) -> None:
    from pala_memory import (
        append_status_mismatch,
        ticket_coherence_report,
    )

    _emit_debug_gate(root, surface="checkpoint")
    payload = load_workflow(root)
    if not next_action.strip():
        raise ValueError("next action must be non-empty")
    if tier not in VERIFICATION_TIERS:
        raise ValueError(f"unsupported verification tier: {tier}")
    if has_failed_verification(verification):
        raise ValueError("checkpoint refused: verification contains failed status")
    quality: dict[str, object] | None = None
    if quality_ticket:
        quality = require_quality_gate(root, quality_ticket)
    evidence = _normalize_evidence_entries(verification)
    try:
        manifest = load_manifest(root)
    except (OSError, ValueError, json.JSONDecodeError):
        manifest = {"documents": {}}
    documents = manifest.get("documents") if isinstance(manifest, dict) else {}
    docs = documents if isinstance(documents, dict) else {}
    status_rel = docs.get("status") if isinstance(docs.get("status"), str) else None
    status_text = ""
    if status_rel and (root / status_rel).is_file():
        status_text = (root / status_rel).read_text(encoding="utf-8")
    coherence = ticket_coherence_report(
        {**payload, "next_action": next_action.strip()},
        status_text,
        "",
        allow_expected_transition=True,
    )
    needs_reconcile = bool(coherence.get("mismatch"))
    parallel_stamp: dict[str, object] | None = None
    try:
        from pala_cold_packet import (
            detect_worktree_conflict,
            git_surface,
            parallel_checkpoint_fields,
        )

        git = git_surface(root)
        prior = payload.get("parallel") if isinstance(payload.get("parallel"), dict) else {}
        conflict = detect_worktree_conflict(
            ticket=str(payload.get("active_ticket") or ""),
            this_worktree=str(git.get("worktree") or root),
            other_worktree=str(prior.get("worktree") or "") or None,
            other_branch=str(prior.get("branch") or "") or None,
            this_branch=str(git.get("branch") or "") or None,
        )
        if conflict.get("reconcile_required"):
            needs_reconcile = True
        parallel_stamp = parallel_checkpoint_fields(
            session_id=session_id,
            worktree=str(git.get("worktree") or root),
            branch=str(git.get("branch") or "unknown"),
            base_commit=str(git.get("base_commit") or "") or None,
            file_scope=list(changed_files or git.get("changed_files") or [])[:16],
        )
    except (OSError, ValueError, TypeError, ImportError):
        parallel_stamp = None
    payload.update(
        {
            "schema_version": WORKFLOW_SCHEMA_VERSION,
            "projection_of": "v3-ticket-store",
            "canonical_state": "v3",
            "dirty": False,
            "needs_reconcile": needs_reconcile,
            "next_action": next_action.strip()[:500],
            "verification": bounded_strings(verification, limit=8),
            "verification_evidence": evidence[:8],
            "verification_tier": tier,
            "blockers": bounded_strings(blockers, limit=5),
            "changed_summary": (changed_summary or "")[:500],
            "changed_files": bounded_strings(changed_files or [], limit=16),
            "memory_mismatch": coherence if coherence.get("mismatch") else None,
            "checkpoint_basis": checkpoint_basis(root, manifest),
            "quality_gate": quality,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if parallel_stamp is not None:
        payload["parallel"] = parallel_stamp
    write_json(workflow_path(root), payload)
    # The v2 file is a generated compatibility projection. The v3 store is
    # authoritative and must be released for the default local session too.
    if session_id is None:
        try:
            from pala_store import WorkflowStore

            ticket = str(payload.get("active_ticket") or "")
            if ticket:
                WorkflowStore(root).checkpoint(ticket, DEFAULT_LOCAL_SESSION, next_action)
        except (OSError, ValueError, TypeError, ImportError):
            pass
    if status_rel and coherence.get("mismatch"):
        append_status_mismatch(root / status_rel, coherence)
        _record_store_event(
            root,
            "mismatch",
            detail=str(coherence.get("note") or "ticket mismatch")[:300],
        )
    # Best-effort catalog upsert (local Desktop\Codex); never fails checkpoint.
    try:
        from pala_catalog import upsert_project
        from pala_tool_memory import tool_memory_report

        tools = tool_memory_report(
            profiles=list(manifest.get("profiles", []))
            if isinstance(manifest.get("profiles"), list)
            else []
        )
        upsert_project(
            root,
            phase=str(payload.get("active_ticket") or ""),
            quality_result=tier,
            tools_summary=(
                f"{tools['counts'].get('installed', 0)}ok/"
                f"{tools['counts'].get('not_installed', 0)}missing"
            ),
            next_action=next_action.strip()[:300],
            blockers=list(payload.get("blockers") or []),
        )
    except (OSError, ValueError, TypeError, KeyError):
        pass
    evidence_text = "; ".join(
        f"{item.get('name')}={item.get('status')}" for item in evidence[:4]
    )
    _record_store_event(
        root,
        "checkpoint",
        detail=next_action.strip()[:300],
        evidence=evidence_text[:500],
    )



def load_manifest(root: Path) -> dict[str, object]:
    path = root / MANIFEST
    if not path.is_file():
        raise ValueError(f"project is not registered: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported pala project-state schema")
    if payload.get("managed_by") != "pala-project-finisher":
        raise ValueError("unexpected project-state owner")
    if not isinstance(payload.get("documents"), dict):
        raise ValueError("documents must be an object")
    project_profile = payload.get("project_profile")
    if project_profile is not None:
        if not isinstance(project_profile, str) or not project_profile.strip():
            raise ValueError("project_profile must be a repository-relative path")
        resolved = (root / project_profile).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError("project_profile must remain inside project root") from exc
    return payload


def validate(root: Path) -> int:
    try:
        payload = load_manifest(root)
        documents = payload["documents"]
        errors: list[str] = []
        for purpose in REQUIRED:
            value = documents.get(purpose)
            if not isinstance(value, str) or not value:
                errors.append(f"{purpose}: missing mapping")
                continue
            path = (root / value).resolve()
            try:
                relative(root, path)
            except ValueError:
                errors.append(f"{purpose}: outside project root")
                continue
            if not path.is_file():
                errors.append(f"{purpose}: file not found ({value})")
            elif not path.read_text(encoding="utf-8").strip():
                errors.append(f"{purpose}: file is empty ({value})")
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 2
        print(
            json.dumps(
                {"valid": True, "root": str(root), "documents": documents},
                ensure_ascii=False,
            )
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


def context_report(root: Path, session: str | None = None) -> dict[str, object]:
    manifest = load_manifest(root)
    active_task_contract: dict[str, object] | None = None
    try:
        workflow = load_workflow(root)
    except (OSError, ValueError, json.JSONDecodeError):
        workflow = {}
    if session is not None:
        from pala_store import WorkflowStore

        owned_ticket = WorkflowStore(root).active_for_session(session)
        if owned_ticket is not None:
            candidate_contract = owned_ticket.get("task_contract")
            if isinstance(candidate_contract, dict):
                active_task_contract = candidate_contract
            workflow = {
                "schema_version": WORKFLOW_SCHEMA_VERSION,
                "active_ticket": owned_ticket.get("ticket"),
                "goal": owned_ticket.get("goal"),
                "next_action": owned_ticket.get("next_action"),
                "dirty": owned_ticket.get("dirty"),
                "needs_reconcile": False,
                "checkpoint_basis": None,
                "verification_tier": "not-run",
                "blockers": [],
            }
    if active_task_contract is None:
        try:
            from pala_store import WorkflowStore

            active_task_contract = WorkflowStore(root).active_task_contract()
        except (OSError, ValueError, ImportError):
            active_task_contract = None
    documents = manifest.get("documents")
    safe_documents = documents if isinstance(documents, dict) else {}
    reconciliation = (
        reconciliation_report(root, manifest, workflow)
        if workflow
        else {"needed": True, "reasons": ["workflow state is missing"]}
    )
    from pala_memory import contract_context
    from pala_tool_memory import tool_memory_report

    memory = contract_context(root, safe_documents, workflow)
    tools = tool_memory_report(
        profiles=list(manifest.get("profiles", []))
        if isinstance(manifest.get("profiles"), list)
        else []
    )
    cmd_memory: dict[str, object] = {"blocks": [], "hint": None}
    try:
        from pala_cmd_memory import active_blocks, context_packet_hint

        cmd_memory = {
            "blocks": active_blocks(limit=5),
            "hint": context_packet_hint(limit=3),
        }
    except (OSError, ValueError, TypeError, ImportError):
        pass
    cold_packet: dict[str, object] | None = None
    continuity_model: dict[str, object]
    live_context = None
    try:
        live_context = build_registered_continuity_context(
            root, task_contract=active_task_contract
        )
        continuity_model = refresh_continuity(
            root, task_contract=active_task_contract, persist=False
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        continuity_model = {
            "status": "blocked",
            "finding": "CONTINUITY_READ_MODEL_UNAVAILABLE",
            "can_complete": False,
        }
    try:
        from pala_cold_packet import build_cold_packet

        cold_packet = build_cold_packet(
            root,
            profile="minimal",
            session_id=session,
            documents=safe_documents,
            workflow=workflow if isinstance(workflow, dict) else None,
            context_receipt=(live_context.receipt if live_context else None),
            context_expectation=(live_context.expectation if live_context else None),
        )
    except (OSError, ValueError, TypeError, ImportError):
        cold_packet = None
    return {
        "active_ticket": workflow.get("active_ticket"),
        "goal": workflow.get("goal"),
        "next_action": workflow.get("next_action"),
        "dirty": bool(workflow.get("dirty")),
        "verification_tier": workflow.get("verification_tier", "not-run"),
        "blockers": workflow.get("blockers", []),
        "reconciliation": reconciliation,
        "read_first": safe_documents.get("status"),
        "read_order": memory.get("read_order"),
        "ticket_coherence": memory.get("ticket_coherence"),
        "tool_memory": {
            "counts": tools.get("counts"),
            "total": tools.get("total"),
        },
        "cmd_memory": cmd_memory,
        "cold_packet": cold_packet,
        "continuity": continuity_model,
        "memory_contract_version": memory.get("memory_contract_version"),
        "active_plan": safe_documents.get("plan"),
        "project": safe_documents.get("project"),
    }

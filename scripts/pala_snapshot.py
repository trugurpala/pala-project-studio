"""Build truthful, worktree-aware project snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from pala_models import (
    ProjectSnapshot,
    ReconciliationFinding,
    RepoIdentity,
    TicketView,
    WorktreeIdentity,
)


def _git(root: Path, *args: str, required: bool = True) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        if required:
            raise ValueError("Git is unavailable") from None
        return None
    if result.returncode != 0:
        if required:
            message = result.stderr.strip() or "Git command failed"
            raise ValueError(message)
        return None
    return result.stdout.strip()


def path_digest(path: Path) -> str:
    normalized = os.path.normcase(str(path.resolve())).replace("\\", "/")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def git_identity(root: Path) -> tuple[RepoIdentity, WorktreeIdentity]:
    root = Path(root).resolve()
    common = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    git_dir = _git(root, "rev-parse", "--path-format=absolute", "--git-dir")
    checkout = _git(root, "rev-parse", "--show-toplevel")
    head = _git(root, "rev-parse", "HEAD", required=False)
    branch = _git(root, "symbolic-ref", "--short", "-q", "HEAD", required=False)
    if common is None or git_dir is None or checkout is None:
        raise ValueError("path is not a Git worktree")
    return (
        RepoIdentity(common_dir_digest=path_digest(Path(common))),
        WorktreeIdentity(
            root=str(Path(checkout).resolve()),
            git_dir_digest=path_digest(Path(git_dir)),
            branch=branch or None,
            head=head or None,
        ),
    )


def list_worktrees(root: Path) -> tuple[WorktreeIdentity, ...]:
    output = _git(Path(root), "worktree", "list", "--porcelain", "-z") or ""
    roots: list[Path] = []
    for field in output.split("\0"):
        if field.startswith("worktree "):
            roots.append(Path(field.removeprefix("worktree ")))
    identities: list[WorktreeIdentity] = []
    for worktree_root in roots:
        if not worktree_root.is_dir():
            continue
        try:
            _, identity = git_identity(worktree_root)
        except ValueError:
            continue
        identities.append(identity)
    return tuple(sorted(identities, key=lambda item: item.root.casefold()))


def select_worktree(
    worktrees: tuple[WorktreeIdentity, ...],
    *,
    explicit_git_dir: str | None,
    current_git_dir: str | None,
    owned_git_dir: str | None,
    active_git_dirs: tuple[str, ...],
    checkpoint_git_dir: str | None,
) -> tuple[WorktreeIdentity | None, tuple[ReconciliationFinding, ...]]:
    """Select a continuation target without phase-name or mtime guesses."""

    by_git_dir = {item.git_dir_digest: item for item in worktrees}
    for candidate in (explicit_git_dir, current_git_dir, owned_git_dir):
        if candidate and candidate in by_git_dir:
            return by_git_dir[candidate], ()

    compatible_active = tuple(
        dict.fromkeys(value for value in active_git_dirs if value in by_git_dir)
    )
    if len(compatible_active) == 1:
        return by_git_dir[compatible_active[0]], ()
    if len(compatible_active) > 1:
        finding = ReconciliationFinding(
            code="WORKTREE_AMBIGUOUS",
            severity="error",
            source="v3-tickets",
            expected="one compatible active worktree",
            observed=str(len(compatible_active)),
            action="Choose a worktree explicitly before continuing.",
        )
        return None, (finding,)
    if checkpoint_git_dir and checkpoint_git_dir in by_git_dir:
        return by_git_dir[checkpoint_git_dir], ()
    return None, ()


def _ticket_view(record: dict[str, object]) -> TicketView:
    return TicketView(
        ticket=str(record.get("ticket") or ""),
        goal=str(record.get("goal") or ""),
        lifecycle=str(record.get("lifecycle") or "unknown"),
        dirty=record.get("dirty") is True,
        owner=str(record["owner"]) if record.get("owner") else None,
        worktree_git_dir_digest=(
            str(record["worktree_git_dir_digest"])
            if record.get("worktree_git_dir_digest")
            else None
        ),
        next_action=(str(record["next_action"]) if record.get("next_action") else None),
        verification_tier=str(record.get("verification_tier") or "not-run"),
        blockers=tuple(
            str(item)
            for item in record.get("blockers", [])
            if isinstance(record.get("blockers"), list)
        ),
    )


def build_snapshot(
    root: Path,
    *,
    session: str | None = None,
    explicit_worktree: Path | None = None,
) -> ProjectSnapshot:
    """Build the single immutable state decision consumed by Pala readers."""

    from pala_store import WorkflowStore, session_key

    root = Path(root).resolve()
    try:
        repo, current = git_identity(root)
        worktrees = list_worktrees(root)
    except ValueError:
        repo = None
        current = None
        worktrees = ()
    manifest_path = root / ".codex" / "pala-project.json"
    documents: tuple[tuple[str, str], ...] = ()
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            raw_documents = manifest.get("documents", {})
            if isinstance(raw_documents, dict):
                documents = tuple(
                    sorted(
                        (str(key), str(value))
                        for key, value in raw_documents.items()
                        if isinstance(value, str) and value
                    )
                )
        except (OSError, json.JSONDecodeError):
            documents = ()

    store = WorkflowStore(root)
    state_findings: list[ReconciliationFinding] = []
    try:
        records = store.list_records()
    except ValueError as error:
        records = ()
        state_findings.append(
            ReconciliationFinding(
                "STATE_RECORD_INVALID",
                "error",
                "v3-store",
                "valid JSON ticket records",
                str(error),
                "Repair or quarantine the invalid v3 record before continuing.",
            )
        )
    active_records = tuple(
        item
        for item in records
        if item.get("lifecycle") == "active" and item.get("dirty") is True
    )
    checkpoint_records = tuple(
        item
        for item in records
        if item.get("lifecycle") == "checkpointed" and item.get("dirty") is False
    )
    owned = None
    if session:
        owner = session_key(session)
        owned = next((item for item in active_records if item.get("owner") == owner), None)
    explicit_id = None
    if explicit_worktree is not None:
        _, explicit_identity = git_identity(explicit_worktree)
        explicit_id = explicit_identity.git_dir_digest
    checkpoint_dirs = tuple(
        dict.fromkeys(
            str(item["worktree_git_dir_digest"])
            for item in checkpoint_records
            if item.get("worktree_git_dir_digest")
        )
    )
    selected, selection_findings = select_worktree(
        worktrees,
        explicit_git_dir=explicit_id,
        current_git_dir=current.git_dir_digest if current else None,
        owned_git_dir=(
            str(owned.get("worktree_git_dir_digest"))
            if owned and owned.get("worktree_git_dir_digest")
            else None
        ),
        active_git_dirs=tuple(
            str(item["worktree_git_dir_digest"])
            for item in active_records
            if item.get("worktree_git_dir_digest")
        ),
        checkpoint_git_dir=checkpoint_dirs[0] if len(checkpoint_dirs) == 1 else None,
    )
    active = next(
        (
            item
            for item in active_records
            if selected
            and item.get("worktree_git_dir_digest") == selected.git_dir_digest
        ),
        None,
    )
    if active is None and selected is None and owned is not None:
        active = owned
    if active is None and selected:
        compatible_checkpoints = tuple(
            item
            for item in checkpoint_records
            if item.get("worktree_git_dir_digest") == selected.git_dir_digest
        )
        if len(compatible_checkpoints) == 1:
            active = compatible_checkpoints[0]
        elif len(compatible_checkpoints) > 1:
            state_findings.append(
                ReconciliationFinding(
                    "CHECKPOINT_AMBIGUOUS",
                    "error",
                    "v3-checkpoints",
                    "one checkpoint for the selected worktree",
                    str(len(compatible_checkpoints)),
                    "Choose the continuation ticket explicitly.",
                )
            )
        elif len(checkpoint_records) == 1:
            active = checkpoint_records[0]
    marker = store._migration_path()
    legacy = root / ".codex" / "pala-workflow.json"
    if active is None and not marker.is_file() and legacy.is_file():
        try:
            legacy_payload = json.loads(legacy.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            legacy_payload = {}
        legacy_ticket = legacy_payload.get("active_ticket")
        if legacy_payload.get("schema_version") == 2 and legacy_ticket:
            legacy_dirty = legacy_payload.get("dirty") is True
            active = {
                "ticket": str(legacy_ticket),
                "goal": str(legacy_payload.get("goal") or "legacy v2 fallback"),
                "lifecycle": "active" if legacy_dirty else "checkpointed",
                "dirty": legacy_dirty,
                "owner": None,
                "worktree_git_dir_digest": (
                    current.git_dir_digest if current else None
                ),
                "basis": legacy_payload.get("checkpoint_basis"),
                "next_action": legacy_payload.get("next_action"),
                "verification_tier": legacy_payload.get("verification_tier", "not-run"),
                "blockers": legacy_payload.get("blockers", []),
            }
    findings = [*state_findings, *selection_findings]
    if active:
        active_ticket = str(active.get("ticket") or "")
        document_map = dict(documents)
        status_ticket = _document_ticket(
            root / document_map["status"],
            r"(?im)^\s*-\s*Aktif ticket:\s*([A-Za-z0-9._-]+)",
        ) if "status" in document_map else None
        plan_ticket = _document_ticket(
            root / document_map["plan"],
            r"(?im)^\s*-\s*\[ \]\s*([A-Za-z0-9._-]+)\s*:",
        ) if "plan" in document_map else None
        if status_ticket and status_ticket != active_ticket:
            findings.append(
                ReconciliationFinding(
                    "STATUS_ACTIVE_MISMATCH",
                    "error",
                    "status",
                    active_ticket,
                    status_ticket,
                    "Reconcile the durable status with the active v3 ticket.",
                )
            )
        if status_ticket and plan_ticket and status_ticket != plan_ticket:
            findings.append(
                ReconciliationFinding(
                    "PLAN_STATUS_MISMATCH",
                    "error",
                    "plan",
                    status_ticket,
                    plan_ticket,
                    "Choose one active ticket and update plan/status together.",
                )
            )
        basis = active.get("basis")
        if not isinstance(basis, dict):
            findings.append(
                ReconciliationFinding(
                    "CHECKPOINT_BASIS_MISSING",
                    "error",
                    "checkpoint",
                    "non-null document and Git basis",
                    None,
                    "Re-checkpoint the ticket with fresh evidence.",
                )
            )
        basis_documents = basis.get("documents") if isinstance(basis, dict) else None
        if isinstance(basis_documents, dict):
            for purpose, expected_digest in basis_documents.items():
                value = document_map.get(str(purpose))
                if not value:
                    continue
                expected_hash = (
                    expected_digest.get("sha256")
                    if isinstance(expected_digest, dict)
                    else expected_digest
                )
                path = root / value
                observed_digest = (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                    if path.is_file()
                    else None
                )
                if observed_digest != expected_hash:
                    findings.append(
                        ReconciliationFinding(
                            "DOCUMENT_CHANGED",
                            "error",
                            str(purpose),
                            str(expected_hash) if expected_hash else None,
                            observed_digest,
                            "Reconcile the changed document before claiming more work.",
                        )
                    )
        basis_git = basis.get("git") if isinstance(basis, dict) else None
        if not isinstance(basis_git, dict) and isinstance(basis, dict):
            basis_git = basis
        if isinstance(basis_git, dict) and selected:
            expected_head = basis_git.get("head")
            expected_tree = basis_git.get("worktree_git_dir_digest")
            expected_status = basis_git.get("working_tree_status_digest")
            if expected_head and expected_head != selected.head:
                findings.append(
                    ReconciliationFinding(
                        "GIT_HEAD_CHANGED",
                        "error",
                        "git",
                        str(expected_head),
                        selected.head,
                        "Review commits made after the checkpoint.",
                    )
                )
            if expected_tree and expected_tree != selected.git_dir_digest:
                findings.append(
                    ReconciliationFinding(
                        "WORKTREE_CHANGED",
                        "error",
                        "git",
                        str(expected_tree),
                        selected.git_dir_digest,
                        "Return to the checkpointed worktree or reconcile explicitly.",
                    )
                )
            observed_status = working_tree_status_digest(root)
            if expected_status and observed_status != expected_status:
                findings.append(
                    ReconciliationFinding(
                        "WORKTREE_CONTENT_CHANGED",
                        "error",
                        "git-status",
                        str(expected_status),
                        observed_status,
                        "Review working-tree changes made after the checkpoint.",
                    )
                )
    if marker.is_file() and legacy.is_file():
        findings.append(
            ReconciliationFinding(
                code="LEGACY_V2_OBSOLETE",
                severity="info",
                source="legacy-v2",
                expected="v3 live coordination after migration",
                observed="legacy v2 retained for audit",
                action="Use v3 state; keep the legacy file unchanged for rollback.",
            )
        )
    return ProjectSnapshot(
        schema_version=1,
        repo=repo,
        worktrees=worktrees,
        selected_worktree=selected,
        active_ticket=_ticket_view(active) if active else None,
        documents=documents,
        findings=tuple(findings),
    )


def _document_ticket(path: Path, pattern: str) -> str | None:
    try:
        match = re.search(pattern, path.read_text(encoding="utf-8"))
    except OSError:
        return None
    return match.group(1) if match else None
def working_tree_status_digest(root: Path) -> str | None:
    """Hash Git's bounded status representation without storing project paths."""

    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=normal"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return hashlib.sha256(result.stdout).hexdigest()

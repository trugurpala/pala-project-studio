#!/usr/bin/env python3
"""Pure, worktree-aware project observation for Pala canonical reconciliation."""

from __future__ import annotations

import hashlib
import ntpath
import os
import platform as host_platform
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pala_redaction import redact_remote_url

PROJECT_SNAPSHOT_SCHEMA_VERSION = 1
GIT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class GitResult:
    exit_code: int | None
    stdout: str
    stderr: str
    failure: str | None = None


GitRunner = Callable[..., GitResult]


@dataclass(frozen=True)
class SnapshotFinding:
    code: str
    severity: str
    detail: str
    resolution: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "detail": self.detail,
            "resolution": self.resolution,
        }


@dataclass(frozen=True)
class ProjectSnapshot:
    repository_id: str
    worktree_id: str
    head: str | None
    head_state: str
    branch: str | None
    git_state: str
    changed_count: int | None
    changed_digest: str | None
    linked_worktree_count: int | None
    remote: str | None
    findings: tuple[SnapshotFinding, ...] = ()
    schema_version: int = PROJECT_SNAPSHOT_SCHEMA_VERSION

    @property
    def finding_codes(self) -> tuple[str, ...]:
        return tuple(item.code for item in self.findings)

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, secrets-free value with no absolute path."""
        return {
            "schema_version": self.schema_version,
            "repository_id": self.repository_id,
            "worktree_id": self.worktree_id,
            "head": self.head,
            "head_state": self.head_state,
            "branch": self.branch,
            "git_state": self.git_state,
            "changed_count": self.changed_count,
            "changed_digest": self.changed_digest,
            "linked_worktree_count": self.linked_worktree_count,
            "remote": self.remote,
            "findings": [item.to_dict() for item in self.findings],
            "authority": "read-only-project-observation",
        }


@dataclass(frozen=True)
class SnapshotSelection:
    status: str
    snapshot: ProjectSnapshot | None
    candidates: tuple[str, ...]
    finding: dict[str, object] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
            "candidates": list(self.candidates),
            "finding": dict(self.finding) if self.finding else None,
            "authority": "pala-project-snapshot-selection",
        }


def run_git(
    root: Path,
    *args: str,
    timeout_seconds: float = GIT_TIMEOUT_SECONDS,
) -> GitResult:
    """Run one bounded read-only Git command without a shell."""
    executable = shutil.which("git")
    if executable is None:
        return GitResult(None, "", "", "unavailable")
    try:
        completed = subprocess.run(  # nosec B603 - fixed executable, explicit argv
            [executable, *args],
            cwd=Path(root),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return GitResult(None, "", "", "timeout")
    except OSError:
        return GitResult(None, "", "", "os-error")
    return GitResult(completed.returncode, completed.stdout, completed.stderr)


def _normalized_path_identity(value: str | os.PathLike[str], *, platform: str) -> str:
    raw = os.fspath(value)
    if platform.casefold().startswith("win"):
        return ntpath.normpath(raw).replace("\\", "/").casefold()
    return os.path.normpath(raw).replace("\\", "/")


def path_identity_digest(
    value: str | os.PathLike[str], *, platform: str | None = None
) -> str:
    normalized = _normalized_path_identity(
        value, platform=platform or host_platform.system()
    )
    return hashlib.sha256(normalized.encode("utf-8", errors="surrogateescape")).hexdigest()[:24]


def repository_identity_digest(
    repository_path: str | os.PathLike[str], root_commits: str
) -> str:
    """Prefer stable Git history identity; unborn repositories fall back to path."""
    roots = sorted(
        {line.strip().casefold() for line in root_commits.splitlines() if line.strip()}
    )
    if not roots:
        return path_identity_digest(repository_path)
    basis = "git-root-commits\0" + "\0".join(roots)
    return hashlib.sha256(basis.encode("ascii", errors="strict")).hexdigest()[:24]


def _resolved_git_path(worktree: Path, value: str) -> Path:
    path = Path(value.strip())
    return path.resolve() if path.is_absolute() else (worktree / path).resolve()


def _finding_for_failure(area: str, failure: str | None) -> SnapshotFinding:
    suffix = (failure or "FAILED").replace("-", "_").upper()
    return SnapshotFinding(
        code=f"PROJECT_SNAPSHOT_{area}_{suffix}",
        severity="blocking",
        detail=f"{area.casefold().replace('_', ' ')} observation is unavailable",
        resolution="retry bounded Git observation or choose an evidence-backed worktree",
    )


def _changed_paths(status_output: str) -> list[str]:
    records = status_output.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        status = record[:2]
        value = record[3:] if len(record) >= 3 else ""
        if value:
            paths.append(value)
        if ("R" in status or "C" in status) and index < len(records):
            source = records[index]
            index += 1
            if source:
                paths.append(source)
    return sorted(set(paths), key=str.casefold)


def _safe_relative_path(value: str) -> str | None:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        return None
    return path.as_posix()


def _hash_worktree_entry(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        if path.is_symlink():
            digest.update(b"symlink\0")
            digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
        elif path.is_file():
            digest.update(b"file\0")
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        elif path.exists():
            digest.update(b"non-file\0")
        else:
            digest.update(b"missing\0")
    except OSError as error:
        digest.update(f"unreadable:{error.errno}".encode("ascii", errors="replace"))
    return digest.hexdigest()


def _changed_digest(root: Path, status_output: str) -> tuple[int, str]:
    digest = hashlib.sha256()
    paths = _changed_paths(status_output)
    for raw in paths:
        path = _safe_relative_path(raw)
        if path is None:
            digest.update(b"unsafe-path\0")
            continue
        digest.update(path.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        digest.update(_hash_worktree_entry(root / Path(path)).encode("ascii"))
        digest.update(b"\0")
    return len(paths), digest.hexdigest()


def capture_project_snapshot(
    root: Path,
    *,
    git_runner: GitRunner = run_git,
) -> ProjectSnapshot:
    """Observe one exact worktree without creating Pala runtime/catalog state."""
    requested_root = Path(root).resolve()
    findings: list[SnapshotFinding] = []
    top = git_runner(requested_root, "rev-parse", "--show-toplevel")
    if top.exit_code != 0 or not top.stdout.strip():
        findings.append(_finding_for_failure("GIT_ROOT", top.failure))
        identity = path_identity_digest(requested_root)
        return ProjectSnapshot(
            repository_id=identity,
            worktree_id=identity,
            head=None,
            head_state="unavailable",
            branch=None,
            git_state="unknown",
            changed_count=None,
            changed_digest=None,
            linked_worktree_count=None,
            remote=None,
            findings=tuple(findings),
        )

    worktree = Path(top.stdout.strip()).resolve()
    common = git_runner(worktree, "rev-parse", "--git-common-dir")
    if common.exit_code == 0 and common.stdout.strip():
        repository_basis = _resolved_git_path(worktree, common.stdout)
    else:
        repository_basis = worktree
        findings.append(_finding_for_failure("GIT_COMMON_DIR", common.failure))

    head = git_runner(worktree, "rev-parse", "--verify", "HEAD")
    head_value = head.stdout.strip() if head.exit_code == 0 and head.stdout.strip() else None
    symbolic = git_runner(worktree, "symbolic-ref", "--short", "-q", "HEAD")
    if symbolic.exit_code == 0 and symbolic.stdout.strip():
        branch = symbolic.stdout.strip()
        head_state = "attached" if head_value else "unborn"
    elif head_value:
        branch = None
        head_state = "detached"
    else:
        branch = None
        head_state = "unborn" if head.failure is None else "unavailable"
        if head.failure is not None:
            findings.append(_finding_for_failure("GIT_HEAD", head.failure))

    status = git_runner(
        worktree,
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    )
    if status.exit_code == 0:
        changed_count, changed_digest = _changed_digest(worktree, status.stdout)
        git_state = "dirty" if changed_count else "clean"
    else:
        changed_count = None
        changed_digest = None
        git_state = "unknown"
        findings.append(_finding_for_failure("GIT_STATUS", status.failure))

    worktrees = git_runner(worktree, "worktree", "list", "--porcelain")
    linked_count = None
    if worktrees.exit_code == 0:
        linked_count = sum(
            1 for line in worktrees.stdout.splitlines() if line.startswith("worktree ")
        )
    else:
        findings.append(_finding_for_failure("GIT_WORKTREES", worktrees.failure))

    remote = git_runner(worktree, "config", "--get", "remote.origin.url")
    safe_remote = (
        redact_remote_url(remote.stdout.strip())
        if remote.exit_code == 0 and remote.stdout.strip()
        else None
    )
    roots = git_runner(worktree, "rev-list", "--max-parents=0", "--all")
    root_commits = roots.stdout if roots.exit_code == 0 else ""
    return ProjectSnapshot(
        repository_id=repository_identity_digest(repository_basis, root_commits),
        worktree_id=path_identity_digest(worktree),
        head=head_value,
        head_state=head_state,
        branch=branch,
        git_state=git_state,
        changed_count=changed_count,
        changed_digest=changed_digest,
        linked_worktree_count=linked_count,
        remote=safe_remote,
        findings=tuple(findings),
    )


def _selection_finding(
    code: str, candidates: tuple[str, ...], detail: str
) -> dict[str, object]:
    return {
        "code": code,
        "severity": "blocking",
        "detail": detail,
        "candidate_worktree_ids": list(candidates),
        "resolution": "select one evidence-backed worktree identity explicitly",
    }


def select_project_snapshot(
    snapshots: list[ProjectSnapshot] | tuple[ProjectSnapshot, ...],
    *,
    requested_worktree_id: str | None = None,
) -> SnapshotSelection:
    """Select only an exact candidate; never guess among linked worktrees."""
    unique = {item.worktree_id: item for item in snapshots}
    candidates = tuple(sorted(unique, key=str.casefold))
    repositories = {item.repository_id for item in unique.values()}
    if len(repositories) > 1:
        return SnapshotSelection(
            "needs_decision",
            None,
            candidates,
            _selection_finding(
                "PROJECT_SNAPSHOT_REPOSITORY_MISMATCH",
                candidates,
                "candidate worktrees do not belong to one repository identity",
            ),
        )
    if requested_worktree_id:
        selected = unique.get(requested_worktree_id)
        if selected is not None:
            return SnapshotSelection("selected", selected, candidates, None)
        return SnapshotSelection(
            "needs_decision",
            None,
            candidates,
            _selection_finding(
                "PROJECT_SNAPSHOT_WORKTREE_NOT_FOUND",
                candidates,
                "requested worktree identity is not an observed candidate",
            ),
        )
    if len(unique) == 1:
        return SnapshotSelection("selected", next(iter(unique.values())), candidates, None)
    code = (
        "PROJECT_SNAPSHOT_WORKTREE_UNAVAILABLE"
        if not unique
        else "PROJECT_SNAPSHOT_WORKTREE_AMBIGUOUS"
    )
    detail = (
        "no safe worktree candidate was observed"
        if not unique
        else "multiple worktrees are valid candidates and none was explicitly selected"
    )
    return SnapshotSelection(
        "needs_decision",
        None,
        candidates,
        _selection_finding(code, candidates, detail),
    )

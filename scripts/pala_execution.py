"""Single-host execution coordination layered on R6 lease ownership."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath


def _surface_path(value: str) -> str:
    path = PurePosixPath(value.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("unsafe write surface")
    return path.as_posix()


def _overlaps(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


@dataclass(frozen=True)
class ExecutionClaim:
    task_id: str
    lease_holder: str
    write_surface: tuple[str, ...]
    worktree: str | None
    detached_head: bool


class ExecutionCoordinator:
    """Conflict detector only; WorkflowStore remains the lease owner."""

    def __init__(self) -> None:
        self._claims: dict[str, ExecutionClaim] = {}
        self._candidates: set[str] = set()

    def claim(
        self,
        task_id: str,
        lease_holder: str,
        write_surface: list[str],
        *,
        worktree: str | None = None,
        detached_head: bool = False,
    ) -> ExecutionClaim:
        if not task_id.strip() or not lease_holder.strip() or not write_surface:
            raise ValueError("task, lease and write surface are required")
        surface = tuple(_surface_path(item) for item in write_surface)
        existing = self._claims.get(task_id)
        if existing and existing.lease_holder != lease_holder:
            raise ValueError("task is already claimed")
        for other_id, other in self._claims.items():
            if other_id != task_id and any(
                _overlaps(left, right) for left in surface for right in other.write_surface
            ):
                raise ValueError("write surface conflicts with another claim")
        claim = ExecutionClaim(task_id, lease_holder, surface, worktree, detached_head)
        self._claims[task_id] = claim
        return claim

    def submit_candidate(
        self, task_id: str, lease_holder: str, candidate: dict[str, object]
    ) -> dict[str, object]:
        claim = self._claims.get(task_id)
        if claim is None or claim.lease_holder != lease_holder or not candidate:
            raise ValueError("owned claim and candidate are required")
        self._candidates.add(task_id)
        return {"task_id": task_id, "status": "awaiting_quality", "candidate": dict(candidate)}

    def quality_allows_completion(self, task_id: str, quality_status: str) -> bool:
        return task_id in self._candidates and quality_status == "passed"

"""Deterministic task dependency DAG validation for Pala."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _deps(tasks: Mapping[str, Mapping[str, Any]], task_id: str) -> list[str]:
    value = tasks.get(task_id, {})
    raw = value.get("dependencies", []) if isinstance(value, Mapping) else []
    return [str(item).strip() for item in raw if str(item).strip()]


def validate_dependency_graph(tasks: Mapping[str, Mapping[str, Any]]) -> dict[str, object]:
    """Return a blocked report for unknown references or cycles."""
    errors: list[dict[str, str]] = []
    for task_id in tasks:
        for dependency in _deps(tasks, task_id):
            if dependency not in tasks:
                errors.append({"type": "missing_dependency", "task": task_id, "dependency": dependency})

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str, trail: list[str]) -> None:
        if task_id in visiting:
            start = trail.index(task_id) if task_id in trail else 0
            errors.append({"type": "cycle", "path": " -> ".join(trail[start:] + [task_id])})
            return
        if task_id in visited or task_id not in tasks:
            return
        visiting.add(task_id)
        for dependency in _deps(tasks, task_id):
            visit(dependency, trail + [task_id])
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in tasks:
        visit(str(task_id), [])
    return {"status": "passed" if not errors else "blocked", "errors": errors[:50]}


def dependency_ready(tasks: Mapping[str, Mapping[str, Any]], task_id: str) -> dict[str, object]:
    graph = validate_dependency_graph(tasks)
    if graph["status"] != "passed":
        return {"status": "blocked", "reason": "dependency graph is invalid", "graph": graph}
    if task_id not in tasks:
        return {"status": "blocked", "reason": "task is missing", "task": task_id}
    dependencies = _deps(tasks, task_id)
    unfinished = [item for item in dependencies if str(tasks[item].get("status", "")).upper() != "DONE"]
    if unfinished:
        return {"status": "blocked", "reason": "dependencies are not DONE", "unfinished": unfinished}
    return {"status": "passed", "dependencies": dependencies}

"""Read-only OpenSpec discovery for Pala projects."""

from __future__ import annotations

from pathlib import Path

from pala_adapters import AdapterResult


class OpenSpecAdapter:
    def inspect(self, root: Path) -> AdapterResult:
        base = Path(root) / "openspec"
        specs = base / "specs"
        changes = base / "changes"
        if not specs.is_dir() and not changes.is_dir():
            return AdapterResult("openspec", "missing", False, "OpenSpec artifacts are absent")
        evidence = tuple(
            str(path.relative_to(root))
            for path in (specs, changes)
            if path.is_dir()
        )
        return AdapterResult("openspec", "ready", False, "OpenSpec artifacts discovered", evidence)

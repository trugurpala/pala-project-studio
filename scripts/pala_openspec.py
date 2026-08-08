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

    def bind_active_ticket(
        self, root: Path, active_ticket: str | None
    ) -> AdapterResult:
        """Link OpenSpec presence to the current Pala ticket without a second planner."""
        current = self.inspect(root)
        if current.state != "ready":
            return current
        ticket = (active_ticket or "").strip()
        if not ticket:
            return AdapterResult(
                "openspec",
                "ready",
                False,
                "OpenSpec present; no active Pala ticket to bind",
                current.evidence,
            )
        return AdapterResult(
            "openspec",
            "ready",
            False,
            f"OpenSpec bound to active ticket {ticket} (compatibility only; no second plan system)",
            current.evidence + (f"ticket:{ticket}",),
        )

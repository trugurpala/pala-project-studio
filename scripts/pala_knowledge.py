"""Repository knowledge index and deterministic freshness/link checks."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

KNOWLEDGE_PATHS = ("ARCHITECTURE.md", "docs/adr", "docs/plans/active", "docs/plans/completed", "docs/operations", "docs/generated")
MARKDOWN_LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)")
IGNORED_MARKDOWN_PARTS = {
    ".codegraph",
    ".git",
    ".codex",
    ".venv",
    ".tools",
    "__pycache__",
    "node_modules",
}

def build_index(root: Path) -> dict[str, object]:
    root = Path(root).resolve()
    entries = []
    for relative in KNOWLEDGE_PATHS:
        path = root / relative
        if path.is_dir():
            files = sorted(str(item.relative_to(root)).replace("\\", "/") for item in path.rglob("*") if item.is_file())
            entries.append({"path": relative, "status": "present", "files": files[:200]})
        else:
            entries.append({"path": relative, "status": "present" if path.is_file() else "missing", "files": [relative] if path.is_file() else []})
    return {"status": "passed" if all(item["status"] == "present" for item in entries) else "not-run", "entries": entries}

def lint_task_references(root: Path, task: dict[str, object]) -> dict[str, object]:
    root = Path(root).resolve()
    refs = task.get("architecture_refs", []) if isinstance(task.get("architecture_refs"), list) else []
    missing = [str(ref) for ref in refs if not (root / str(ref)).is_file()]
    acceptance = task.get("acceptance") if isinstance(task.get("acceptance"), list) else []
    return {"status": "passed" if not missing and acceptance else "blocked", "missing_refs": missing, "acceptance_count": len(acceptance)}


def _local_link_target(source: Path, raw: str) -> str | None:
    target = raw.strip().strip("<>").split(" ", 1)[0]
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or target.startswith("#"):
        return None
    value = parsed.path
    if not value or value.startswith("/"):
        return None
    return value.replace("\\", "/")


def lint_markdown_links(root: Path, artifact_root: Path | None = None) -> dict[str, object]:
    """Check relative Markdown links within source or an extracted artifact.

    Remote URLs and fragment-only anchors are intentionally outside this local gate.
    """
    base = Path(artifact_root or root).resolve()
    missing: list[dict[str, str]] = []
    stale: list[dict[str, str]] = []
    checked = 0
    for source in sorted(base.rglob("*.md"), key=lambda item: item.as_posix().casefold()):
        if any(part in IGNORED_MARKDOWN_PARTS for part in source.relative_to(base).parts):
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for match in MARKDOWN_LINK_RE.finditer(text):
            target = _local_link_target(source, match.group(1))
            if target is None:
                continue
            checked += 1
            resolved = (source.parent / target).resolve()
            try:
                resolved.relative_to(base)
            except ValueError:
                missing.append({"source": str(source.relative_to(base)).replace("\\", "/"), "target": target, "reason": "outside artifact root"})
                continue
            if not resolved.exists():
                source_name = str(source.relative_to(base)).replace("\\", "/")
                item = {"source": source_name, "target": target, "reason": "missing"}
                # Historical plans/contracts are reported but never rewritten or made a release blocker.
                if source_name.startswith("docs/history/"):
                    stale.append(item)
                else:
                    missing.append(item)
    return {"status": "passed" if not missing else "blocked", "checked": checked, "missing": missing[:200], "stale": stale[:200], "missing_count": len(missing), "stale_count": len(stale), "root": str(base)}


def lint_artifact_links(source_root: Path, artifact_root: Path) -> dict[str, object]:
    """Run the same link contract against a clean portable/installed root."""
    return lint_markdown_links(source_root, artifact_root=artifact_root)

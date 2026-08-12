"""Explicit source/portable/installed artifact contract."""

from __future__ import annotations

import json
from pathlib import Path

REQUIRED_FILES = (
    ".codex-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    "hooks/hooks.json",
    "scripts/verify.py",
    "scripts/pala_self_audit.py",
    "docs/PALA_0_9_0_OPERATING_SYSTEM.md",
)
FORBIDDEN_NAMES = (".sqlite", "credentials.json", "id_rsa")
IGNORED_ARTIFACT_PARTS = {
    ".git",
    ".codex",
    ".venv",
    ".tools",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "dist",
}


def artifact_contract(root: Path, *, profile: str = "source") -> dict[str, object]:
    root = Path(root).resolve()
    identity = json.loads((root / "product-identity.json").read_text(encoding="utf-8"))
    required = REQUIRED_FILES if profile in {"source", "portable"} else REQUIRED_FILES[:5]
    missing = [item for item in required if not (root / item).is_file()]
    forbidden: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = str(path.relative_to(root)).replace("\\", "/")
        if any(part in IGNORED_ARTIFACT_PARTS for part in Path(relative).parts):
            continue
        if any(
            name in path.name.casefold() for name in FORBIDDEN_NAMES
        ) or path.suffix.casefold() in {".sqlite", ".pyc", ".pem", ".key"}:
            forbidden.append(relative)
    return {
        "status": "passed" if not missing and not forbidden else "blocked",
        "artifact_profile": profile,
        "version": identity["product_version"],
        "plugin_version": identity["plugin_version"],
        "required_files": list(required),
        "missing": missing,
        "forbidden": forbidden[:100],
    }

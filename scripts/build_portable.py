#!/usr/bin/env python3
"""Build a clean, deterministic Pala Project Studio portable archive."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import urllib.parse
import zipfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_ROOT = "pala-project-studio"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
FORBIDDEN_PARTS = {".git", ".ruff_cache", "__pycache__", ".codex"}
FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".pem", ".key", ".sqlite")
FORBIDDEN_BASENAMES = {"credentials.json", "id_rsa"}
# Secret-shaped basenames beyond the exact forbid list (private keys, secrets files).
SECRET_SHAPED_BASENAME = re.compile(
    r"(?i)^(?:id_rsa(?:\.[^.]+)?|credentials(?:\.[^.]+)?|secrets?(?:\.[^.]+)?)$"
)
DEMO_CODEX_PREFIX = ("examples", "demo-software-project", ".codex")


def validate_archive_name(value: str) -> str:
    """Return a safe normalized ZIP member name or raise ValueError."""
    if not value or "\x00" in value or "\\" in value:
        raise ValueError(f"unsafe archive path: {value!r}")
    if WINDOWS_DRIVE.match(value):
        raise ValueError(f"unsafe archive path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"unsafe archive path: {value!r}")
    return path.as_posix()


def ensure_unique_names(names: Iterable[str]) -> None:
    """Reject case-insensitive ZIP member collisions."""
    seen: dict[str, str] = {}
    for name in names:
        normalized = validate_archive_name(name)
        key = normalized.casefold()
        previous = seen.get(key)
        if previous is not None:
            raise ValueError(f"case-insensitive archive collision: {previous!r} and {normalized!r}")
        seen[key] = normalized


def is_demo_codex(path: Path) -> bool:
    """Allow the fork demo's registered .codex state into the portable ZIP."""
    parts = tuple(part.casefold() for part in path.parts)
    prefix = tuple(part.casefold() for part in DEMO_CODEX_PREFIX)
    return len(parts) >= len(prefix) and parts[: len(prefix)] == prefix


def is_forbidden_source(path: Path) -> bool:
    """Return whether a source path must never enter the portable archive."""
    lowered_parts = {part.casefold() for part in path.parts}
    blocked = lowered_parts.intersection({part.casefold() for part in FORBIDDEN_PARTS})
    if blocked:
        if blocked == {".codex"} and is_demo_codex(path):
            pass
        else:
            return True
    if any(part.casefold() == ".env" or part.casefold().startswith(".env.") for part in path.parts):
        return True
    name = path.name
    if name.casefold() in {item.casefold() for item in FORBIDDEN_BASENAMES}:
        return True
    if SECRET_SHAPED_BASENAME.fullmatch(name):
        return True
    return name.casefold().endswith(FORBIDDEN_SUFFIXES)


def source_files(plugin_root: Path) -> list[Path]:
    """Return the allowlisted source files for a portable package."""
    # KUR.md is allowlisted but optional until the docs agent lands it.
    optional = {plugin_root / "KUR.md"}
    candidates = [
        plugin_root / ".agents" / "plugins" / "marketplace.json",
        plugin_root / ".codex-plugin" / "plugin.json",
        plugin_root / "AGENTS.md",
        plugin_root / "DECISIONS.md",
        plugin_root / "Install-Pala.ps1",
        plugin_root / "Kur.cmd",
        plugin_root / "KUR.md",
        plugin_root / "LICENSE",
        plugin_root / "managed-tools.lock.json",
        plugin_root / "OPEN_SOURCE.md",
        plugin_root / "GOAL.md",
        plugin_root / "PROJECT.md",
        plugin_root / "product-identity.json",
        plugin_root / "README.md",
        plugin_root / "README.tr.md",
        plugin_root / "SECURITY.md",
        plugin_root / "SUPPORT.md",
        plugin_root / "CHANGELOG.md",
        plugin_root / "CONTRIBUTING.md",
        plugin_root / "CODE_OF_CONDUCT.md",
        plugin_root / "THIRD_PARTY_NOTICES.md",
        plugin_root / "artifacts" / "governance" / "third-party-inventory.json",
        plugin_root / "locales" / "en.json",
        plugin_root / "locales" / "tr-ascii.json",
        plugin_root / "design" / "tokens.json",
        plugin_root / "policies" / "accessibility.json",
        plugin_root / "policies" / "core-quality.json",
        plugin_root / "policies" / "release.json",
        plugin_root / ".github" / "workflows" / "quality.yml",
        plugin_root / "docs" / "README.md",
        plugin_root / "docs" / "RELEASE_1.0.0.md",
        plugin_root / "docs" / "CODEX_SCOPE_AND_LIMITS.md",
        plugin_root / "docs" / "PALA_0_4_SINGLE_DOOR.md",
        plugin_root / "docs" / "PALA_0_5_MEMORY_CONTRACT.md",
        plugin_root / "docs" / "PALA_0_6_STATUS_SURFACE.md",
        plugin_root / "docs" / "PALA_0_7_LOCAL_STORE.md",
        plugin_root / "docs" / "PALA_0_9_QUALITY_ENGINE.md",
        plugin_root / "docs" / "PALA_0_9_0_OPERATING_SYSTEM.md",
        plugin_root / "docs" / "PALA_0_9_BENCHMARK.md",
        plugin_root / "docs" / "PALA_0_9_1_HARDENING.md",
        plugin_root / "docs" / "PALA_0_9_2_CODE_QUALITY_CONTROL.md",
        plugin_root / "docs" / "PALA_0_9_3_MODULARITY.md",
        plugin_root / "docs" / "PALA_0_9_4_INSTALL_BOUNDARY.md",
        plugin_root / "docs" / "PALA_0_9_5_INSTALL_INTEGRITY.md",
        plugin_root / "docs" / "PALA_EVERYWHERE.md",
        plugin_root / "docs" / "PALA_INTERNAL_PROVISION.md",
        plugin_root / "docs" / "VIBE_INSTALL.md",
        plugin_root / "docs" / "VIBE_FIRST_SESSION.md",
        plugin_root / "docs" / "INSTALL_ARTIFACT_CONTRACT.md",
        plugin_root / "docs" / "CODEX_PLUGIN_CHECKLIST.md",
        plugin_root / "docs" / "PALA_SHARED_MEMORY.md",
        plugin_root / "docs" / "FORK_PACK.md",
        plugin_root / "portable" / "cursor" / "README.md",
        plugin_root / "portable" / "cursor" / "SKILL.md",
        plugin_root / ".cursor" / "rules" / "pala-memory.mdc",
    ]
    for directory in ("hooks", "skills"):
        candidates.extend(path for path in (plugin_root / directory).rglob("*") if path.is_file())
    demo_root = plugin_root / "examples" / "demo-software-project"
    candidates.extend(path for path in demo_root.rglob("*") if path.is_file())
    # The source repository keeps tests and historical release plans for
    # maintainers; the portable artifact is an end-user runtime/install
    # surface and must not ship those development-only files.
    candidates.extend(
        path
        for pattern in ("*.py", "*.ps1")
        for path in (plugin_root / "scripts").glob(pattern)
        if path.is_file() and not path.name.startswith("test_")
    )

    files: list[Path] = []
    for path in candidates:
        if not path.is_file():
            if path in optional:
                continue
            raise FileNotFoundError(f"required package file is missing: {path}")
        if path.is_symlink():
            raise ValueError(f"symbolic links are not portable: {path}")
        relative = path.relative_to(plugin_root)
        if is_forbidden_source(relative):
            continue
        files.append(path)
    return sorted(set(files), key=lambda path: path.as_posix().casefold())


MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def validate_internal_markdown_links(plugin_root: Path) -> list[str]:
    """Return unresolved relative Markdown links on the portable surface."""
    root = Path(plugin_root).resolve()
    files = source_files(root)
    included = {path.resolve() for path in files}
    problems: list[str] = []
    for source in files:
        if source.suffix.casefold() != ".md":
            continue
        text = source.read_text(encoding="utf-8")
        for raw in MARKDOWN_LINK.findall(text):
            target = raw.strip().strip("<>").split(maxsplit=1)[0]
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            relative = urllib.parse.unquote(target.split("#", maxsplit=1)[0])
            resolved = (source.parent / relative).resolve()
            if resolved not in included and not (
                resolved.is_dir() and any(resolved in path.parents for path in included)
            ):
                problems.append(f"{source.relative_to(root).as_posix()} -> {target}")
    return sorted(set(problems), key=str.casefold)


def archive_entries(plugin_root: Path) -> list[tuple[Path, str]]:
    """Map allowlisted sources to safe, collision-free archive names."""
    entries = [
        (
            path,
            validate_archive_name(f"{ARCHIVE_ROOT}/{path.relative_to(plugin_root).as_posix()}"),
        )
        for path in source_files(plugin_root)
    ]
    ensure_unique_names(name for _, name in entries)
    return sorted(entries, key=lambda item: item[1].casefold())


def build_archive(output: Path, plugin_root: Path = PLUGIN_ROOT) -> list[str]:
    """Create a new portable ZIP and return its sorted member names."""
    output = Path(output)
    plugin_root = Path(plugin_root).resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output}")
    if not output.parent.is_dir():
        raise FileNotFoundError(f"output directory does not exist: {output.parent}")

    broken_links = validate_internal_markdown_links(plugin_root)
    if broken_links:
        raise ValueError("portable internal links are unresolved: " + "; ".join(broken_links))
    entries = archive_entries(plugin_root)
    try:
        with zipfile.ZipFile(
            output,
            mode="x",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for source, name in entries:
                info = zipfile.ZipInfo(name, date_time=FIXED_TIMESTAMP)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, source.read_bytes(), compresslevel=9)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return [name for _, name in entries]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New ZIP path. Existing files are never overwritten.",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        entries = build_archive(args.output)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest().upper()
    print(args.output.resolve())
    print(f"entries={len(entries)}")
    print(f"sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

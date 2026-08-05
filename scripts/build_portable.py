#!/usr/bin/env python3
"""Build a clean, deterministic Pala Project Studio portable archive."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_ROOT = "pala-project-studio"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
FORBIDDEN_PARTS = {".git", ".ruff_cache", "__pycache__", ".codex"}
FORBIDDEN_SUFFIXES = (".pyc", ".pyo", ".pem", ".key")


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
            raise ValueError(
                f"case-insensitive archive collision: {previous!r} and "
                f"{normalized!r}"
            )
        seen[key] = normalized


def is_forbidden_source(path: Path) -> bool:
    """Return whether a source path must never enter the portable archive."""
    lowered_parts = {part.casefold() for part in path.parts}
    if lowered_parts.intersection(FORBIDDEN_PARTS):
        return True
    if any(
        part.casefold() == ".env" or part.casefold().startswith(".env.")
        for part in path.parts
    ):
        return True
    return path.name.casefold().endswith(FORBIDDEN_SUFFIXES)


def source_files(plugin_root: Path) -> list[Path]:
    """Return the allowlisted source files for a portable package."""
    candidates = [
        plugin_root / ".agents" / "plugins" / "marketplace.json",
        plugin_root / ".codex-plugin" / "plugin.json",
        plugin_root / "Install-Pala.ps1",
        plugin_root / "LICENSE",
        plugin_root / "OPEN_SOURCE.md",
        plugin_root / "README.md",
        plugin_root / "THIRD_PARTY_NOTICES.md",
        plugin_root / ".github" / "workflows" / "quality.yml",
    ]
    for directory in ("hooks", "skills"):
        candidates.extend(
            path for path in (plugin_root / directory).rglob("*") if path.is_file()
        )
    candidates.extend(
        path
        for pattern in ("*.py", "*.ps1")
        for path in (plugin_root / "scripts").glob(pattern)
        if path.is_file()
    )

    files: list[Path] = []
    for path in candidates:
        if not path.is_file():
            raise FileNotFoundError(f"required package file is missing: {path}")
        if path.is_symlink():
            raise ValueError(f"symbolic links are not portable: {path}")
        relative = path.relative_to(plugin_root)
        if is_forbidden_source(relative):
            continue
        files.append(path)
    return sorted(set(files), key=lambda path: path.as_posix().casefold())


def archive_entries(plugin_root: Path) -> list[tuple[Path, str]]:
    """Map allowlisted sources to safe, collision-free archive names."""
    entries = [
        (
            path,
            validate_archive_name(
                f"{ARCHIVE_ROOT}/{path.relative_to(plugin_root).as_posix()}"
            ),
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

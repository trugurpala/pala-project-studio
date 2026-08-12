#!/usr/bin/env python3
"""Bundle admission, fingerprints, and installed-tree preservation checks."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pala_installer_shared import *

def safe_source_file(relative: Path) -> bool:
    lowered = {part.casefold() for part in relative.parts}
    if lowered.intersection(FORBIDDEN_PARTS):
        return False
    name = relative.name
    if name.casefold().endswith(tuple(FORBIDDEN_SUFFIXES)):
        return False
    if name.casefold() in {item.casefold() for item in FORBIDDEN_BASENAMES}:
        return False
    if SECRET_SHAPED_BASENAME.fullmatch(name):
        return False
    if any(
        part.casefold() == ".env" or part.casefold().startswith(".env.")
        for part in relative.parts
    ):
        return False
    return True


def bundle_files(source: Path) -> list[Path]:
    source = source.resolve()
    candidates: list[Path] = []
    for name in PACKAGE_FILES:
        path = source / name
        if path.is_file():
            candidates.append(path)
    for name in PACKAGE_DIRECTORIES:
        directory = source / name
        if directory.is_dir():
            candidates.extend(path for path in directory.rglob("*") if path.is_file())
    result = []
    for path in candidates:
        if path.is_symlink():
            raise ValueError(f"symbolic links are not installable: {path}")
        relative = path.relative_to(source)
        if safe_source_file(relative):
            result.append(path)
    return sorted(set(result), key=lambda item: item.relative_to(source).as_posix().casefold())


def manifest(source: Path) -> dict[str, object]:
    path = source / ".codex-plugin" / "plugin.json"
    value = read_json(path)
    if value is None:
        raise ValueError(f"invalid plugin manifest: {path}")
    if value.get("name") != OWNER:
        raise ValueError("plugin manifest name does not match Pala")
    version = value.get("version")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("plugin manifest version is missing")
    return value


def validate_bundle(source: Path) -> dict[str, object]:
    source = source.resolve()
    for relative in REQUIRED_FILES:
        if not (source / relative).is_file():
            raise FileNotFoundError(f"required plugin file is missing: {relative}")
    value = manifest(source)
    files = bundle_files(source)
    if not files:
        raise ValueError("plugin bundle is empty")
    for path in files:
        if path.suffix.casefold() == ".py":
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
    return value


def tree_fingerprint(root: Path) -> str:
    """Fingerprint only allowlisted bundle files under an install root.

    Only bytecode inside an explicit ``__pycache__`` directory is runtime junk.
    Any other file is checked separately by the exact installed-file manifest.
    """
    root = root.resolve()
    digest = hashlib.sha256()
    for path in bundle_files(root):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest().upper()


def bundle_file_hashes(root: Path) -> dict[str, str]:
    """Return the exact copied-file manifest used for uninstall protection."""
    root = root.resolve()
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest().upper()
        for path in bundle_files(root)
    }


def is_runtime_artifact(relative: Path) -> bool:
    """Pala-owned runtime leftovers that may appear after installation."""
    return any(part.casefold() == "__pycache__" for part in relative.parts)


def install_has_user_added_files(
    install_root: Path, file_hashes: dict[str, object] | None = None
) -> bool:
    """True when an install tree has an unowned/changed non-runtime entry.

    New installs persist an exact file manifest. That protects files inside
    owned directories too (including `.env`), rather than trusting today's
    mutable directory contents. Legacy installs retain the older fallback.
    """
    install_root = install_root.resolve()
    if not install_root.is_dir():
        return False
    expected = {
        str(path).replace("\\", "/").casefold(): str(digest).casefold()
        for path, digest in (file_hashes or {}).items()
        if isinstance(path, str) and isinstance(digest, str)
    }
    expected_dirs: set[str] = set()
    for relative in expected:
        for parent in Path(relative).parents:
            value = parent.as_posix().casefold()
            if value != ".":
                expected_dirs.add(value)
    legacy_allowed = {
        path.relative_to(install_root).as_posix().casefold()
        for path in bundle_files(install_root)
    }
    for path in install_root.rglob("*"):
        # Never follow a user link: it can point outside this install root.
        if path.is_symlink():
            return True
        relative = path.relative_to(install_root)
        if is_runtime_artifact(relative):
            continue
        key = relative.as_posix().casefold()
        if path.is_dir():
            if expected and key not in expected_dirs:
                return True
            continue
        if expected:
            if key not in expected:
                return True
            if hashlib.sha256(path.read_bytes()).hexdigest().casefold() != expected[key]:
                return True
            continue
        if not safe_source_file(relative) or key not in legacy_allowed:
            return True
    return False


def bundle_fingerprint(source: Path) -> str:
    source = source.resolve()
    digest = hashlib.sha256()
    for path in bundle_files(source):
        relative = path.relative_to(source).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest().upper()

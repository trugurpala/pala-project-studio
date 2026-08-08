#!/usr/bin/env python3
"""Resolve Pala scripts directory for install, env, or checkout."""

from __future__ import annotations

import os
from pathlib import Path


def _as_scripts_dir(candidate: Path) -> Path | None:
    path = candidate.expanduser()
    if (path / "pala_state.py").is_file():
        return path.resolve()
    nested = path / "scripts"
    if (nested / "pala_state.py").is_file():
        return nested.resolve()
    return None


def resolve_pala_scripts_dir() -> Path:
    """Return the directory that contains pala_state.py.

    Order:
    1. ``PALA_SCRIPTS_DIR`` (directory of scripts, or marketplace root)
    2. ``PALA_MARKETPLACE_ROOT`` (+ ``scripts``)
    3. This package directory (dev checkout / installed plugin scripts/)
    4. ``%LOCALAPPDATA%/Pala/marketplace/scripts`` (Windows install default)
    """
    for key in ("PALA_SCRIPTS_DIR", "PALA_MARKETPLACE_ROOT"):
        raw = (os.environ.get(key) or "").strip()
        if not raw:
            continue
        resolved = _as_scripts_dir(Path(raw))
        if resolved is not None:
            return resolved

    here = _as_scripts_dir(Path(__file__).resolve().parent)
    if here is not None:
        return here

    local = os.environ.get("LOCALAPPDATA", "").strip()
    if local:
        market = _as_scripts_dir(Path(local) / "Pala" / "marketplace")
        if market is not None:
            return market

    raise FileNotFoundError(
        "pala scripts dir not resolved; set PALA_SCRIPTS_DIR or install marketplace"
    )


def pala_script(name: str) -> Path:
    """Resolve a script filename under the Pala scripts directory."""
    return resolve_pala_scripts_dir() / name

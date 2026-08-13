#!/usr/bin/env python3
"""One-shot explicit Control Center open gate."""

from __future__ import annotations

import unicodedata
from pathlib import Path


def _normalized(intent: str) -> str:
    value = unicodedata.normalize("NFKD", intent.casefold())
    return " ".join("".join(char for char in value if not unicodedata.combining(char)).split())


def open_if_explicit(intent: str, *, refresh, opener) -> bool:
    if _normalized(intent) not in {
        "paneli ac",
        "pala panelini ac",
        "pala paneli",
        "pala control center",
    }:
        return False
    target = refresh()
    if not isinstance(target, Path):
        target = Path(target)
    opener(target)
    return True

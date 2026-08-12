#!/usr/bin/env python3
"""Small read-only UX contracts for the static owner Control Center."""

from __future__ import annotations

import hashlib
import re

VIEWPORTS = ((320, 568), (768, 1024), (1440, 900))


def validate_control_center_markup(html: str) -> dict[str, object]:
    required = {
        "focus": ":focus-visible",
        "reduced_motion": "prefers-reduced-motion",
        "responsive": "@media (max-width:600px)",
        "bounded_content": "overflow-wrap:anywhere;",
        "landmark": '<section class="pala-control-center"',
    }
    missing = [name for name, marker in required.items() if marker not in html]
    return {"status": "passed" if not missing else "blocked", "missing": missing, "viewports": VIEWPORTS}


def visual_digest(html: str) -> str:
    """Hash stable structure and CSS, excluding dynamic text values."""
    normalized = re.sub(r"\s+", " ", html)
    normalized = re.sub(r">[^<>]{80,}<", "><", normalized)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

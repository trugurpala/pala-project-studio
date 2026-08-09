"""Cheap token approximations for host-budget guards (not product metrics)."""

from __future__ import annotations


def approx_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)

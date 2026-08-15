#!/usr/bin/env python3
"""Shared fail-closed privacy-shape detection for durable Pala contracts."""

from __future__ import annotations

import re

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "secret-assignment",
        re.compile(
            r"(?i)\b(?:api[-_ ]?key|authorization|bearer|credential|password|"
            r"private[-_ ]?key|secret|token)\s*[:=]"
        ),
    ),
    (
        "secret-token",
        re.compile(
            r"(?i)(?:\bAKIA[0-9A-Z]{12,}\b|\bgh[pousr]_[a-z0-9]{12,}\b|"
            r"\bsk-[a-z0-9_-]{12,}\b|eyJ[a-z0-9_-]{10,}\.eyJ[a-z0-9_-]{10,}|"
            r"-----BEGIN [^-]*PRIVATE KEY-----)"
        ),
    ),
    (
        "email",
        re.compile(r"(?i)\b[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,}\b"),
    ),
    ("windows-path", re.compile(r"(?i)(?:^|[^a-z0-9])[a-z]:[\\/]")),
    ("unc-path", re.compile(r"(?:^|\s|=)(?:\\\\|//)[^\\/\s]+[\\/]")),
    (
        "private-posix-path",
        re.compile(r"(?i)(?:^|\s|=)(?:~[/\\]|/(?:etc|home|mnt|root|tmp|users|var|workspace)/)"),
    ),
    ("file-uri", re.compile(r"(?i)\bfile:(?://)?[/\\]")),
    ("credential-uri", re.compile(r"(?i)\b(?:https?|ssh)://[^\s/@:]+:[^\s/@]+@")),
    (
        "transcript",
        re.compile(
            r"(?im)(?:^|\n)\s*(?:user|assistant|system|developer)\s*:|"
            r"[\"']role[\"']\s*:\s*[\"'](?:user|assistant|system|developer)[\"']"
        ),
    ),
    ("control-character", re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")),
)


def private_data_reason(value: str) -> str | None:
    """Return a stable shape name without ever echoing the inspected value."""
    for name, pattern in _PATTERNS:
        if pattern.search(value):
            return name
    return None


def has_private_data(value: str) -> bool:
    return private_data_reason(value) is not None

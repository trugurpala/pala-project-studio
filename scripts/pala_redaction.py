#!/usr/bin/env python3
"""Small, stdlib-only redaction helpers for Pala's local state surfaces."""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit


URL_CANDIDATE = re.compile(r"(?i)(?:https?|ssh|git)://[^\s'\"<>]+")
SCP_REMOTE = re.compile(r"^(?:[^@\s/:]+@)?([a-z0-9.-]+):/?([^\s]+)$", re.IGNORECASE)


def redact_remote_url(value: object) -> str:
    """Return a display/storage-safe remote identity without credentials.

    Git remotes can legally contain ``username:password@``. Pala never needs
    those credentials in its catalog, evidence, or status views, so remove
    userinfo, query strings, and fragments before retaining the identity.
    """
    raw = str(value or "").strip()
    if not raw:
        return ""
    parsed = urlsplit(raw)
    if parsed.scheme and parsed.hostname:
        try:
            port = parsed.port
        except ValueError:
            port = None
        host = parsed.hostname.casefold()
        netloc = host if port is None else f"{host}:{port}"
        return urlunsplit((parsed.scheme.casefold(), netloc, parsed.path.rstrip("/"), "", ""))
    scp = SCP_REMOTE.fullmatch(raw)
    if scp:
        host, path = scp.groups()
        return f"ssh://{host.casefold()}/{path.lstrip('/')}"
    return "[redacted remote]" if "@" in raw else raw


def redact_text(value: object) -> str:
    """Redact URL credentials embedded in a bounded event/status message."""
    return URL_CANDIDATE.sub(lambda match: redact_remote_url(match.group(0)), str(value or ""))

#!/usr/bin/env python3
"""Compatibility facade for durable Pala project-state documents."""

from __future__ import annotations

from pala_state_core import *  # noqa: F401,F403
from pala_state_documents import *  # noqa: F401,F403
from pala_state_cli import main, parser
from pala_state_git import _run_git_process
from pala_state_core import _normalize_evidence_entries

if __name__ == "__main__":
    raise SystemExit(main())

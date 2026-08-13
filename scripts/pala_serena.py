#!/usr/bin/env python3
"""Strictly lazy Serena fallback policy; no default install or activation."""

from __future__ import annotations

SERENA_VERSION = "1.7.0"
SERENA_SHA256 = "6dbf1459670d96fb0595f84932adef34260a6fe14ba5135b901fdb3c8c76e891"
SERENA_URL = (
    "https://files.pythonhosted.org/packages/source/s/serena-agent/"
    "serena_agent-1.7.0-py3-none-any.whl"
)
SUPPORTED_PYTHON = ((3, 11), (3, 12), (3, 13), (3, 14))
FORBIDDEN = (
    "memory", "dashboard", "paid-backend", "planning", "autonomous-edit", "completion-authority",
)


def decide_lazy_fallback(
    *,
    codegraph_sufficient: bool,
    direct_source_sufficient: bool,
    python_version: tuple[int, int],
    runtime_state: str,
    health: str,
) -> dict[str, object]:
    base = {
        "profile": "LAZY_FALLBACK",
        "provider": "serena-agent",
        "version": SERENA_VERSION,
        "license": "MIT",
        "purpose": "read-only-symbol-precision",
        "authority": "advisory",
        "core_health_required": False,
        "forbidden": list(FORBIDDEN),
        "fallback": "direct-source",
        "installation": "on-demand-transaction-only",
    }
    if codegraph_sufficient:
        return {**base, "selected": False, "next": "codegraph", "reason": "graph-sufficient"}
    if direct_source_sufficient:
        return {**base, "selected": False, "next": "direct-source", "reason": "source-sufficient"}
    if python_version not in SUPPORTED_PYTHON:
        return {**base, "selected": False, "next": "direct-source", "reason": "python-unsupported"}
    if runtime_state != "exact" or health != "passed":
        return {**base, "selected": False, "next": "direct-source", "reason": f"runtime-{runtime_state}/{health}"}
    return {**base, "selected": True, "next": "serena", "reason": "symbol-precision-needed"}

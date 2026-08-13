#!/usr/bin/env python3
"""Semantic Professional Workbench routing; providers never decide completion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteRequest:
    lifecycle_stage: str
    risk: str
    semantic_need: str
    user_intent: str
    task_requires_browser: bool
    explicit_current_docs: bool


def _healthy(value: str | None) -> bool:
    return value in {"exact/current/passed", "external/current/passed"}


def route(request: RouteRequest, runtime: dict[str, str]) -> dict[str, object]:
    selected: list[str]
    reason: str
    affects_core = True
    if request.explicit_current_docs and request.semantic_need == "current-docs":
        selected = ["current_docs"] if _healthy(runtime.get("current_docs")) else ["official-docs"]
        reason = "explicit-optional-current-docs"
        affects_core = False
    elif request.task_requires_browser and request.semantic_need == "browser":
        capability = "browser_e2e" if request.lifecycle_stage in {"quality", "browser-user-journey"} else "browser_exploration"
        selected = [capability] if _healthy(runtime.get(capability)) else ["direct-browser-inspection"]
        reason = "explicit-project-browser-profile"
    elif request.semantic_need == "security" or (
        request.risk == "high" and request.lifecycle_stage in {"security", "pre-quality", "pre-release"}
    ):
        selected = ["security_static"] if _healthy(runtime.get("security_static")) else ["project-native-security-tools"]
        reason = "bounded-local-security"
    elif request.semantic_need == "symbol-precision":
        exhausted = runtime.get("direct-source") == "insufficient" and not _healthy(runtime.get("code_intelligence"))
        selected = ["symbol_precision"] if exhausted and _healthy(runtime.get("symbol_precision")) else ["direct-source"]
        reason = "lazy-symbol-precision" if selected == ["symbol_precision"] else "source-first"
        affects_core = False
    elif request.semantic_need in {"structural-code-understanding", "impact"}:
        selected = ["code_intelligence"] if _healthy(runtime.get("code_intelligence")) else ["direct-source"]
        reason = "fresh-graph" if selected == ["code_intelligence"] else "graph-fallback"
    else:
        selected = ["direct-source"]
        reason = "default-source-inspection"
    return {
        "selected": selected,
        "reason": reason,
        "inputs": {
            "lifecycle_stage": request.lifecycle_stage,
            "risk": request.risk,
            "semantic_need": request.semantic_need,
            "user_intent": request.user_intent,
            "task_requires_browser": request.task_requires_browser,
            "explicit_current_docs": request.explicit_current_docs,
        },
        "affects_core_health": affects_core,
        "provider_authority": "advisory",
        "completion_authority": "Pala Quality Engine",
        "can_decide_done": False,
    }

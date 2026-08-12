"""Design-token validation plus cheap host-budget approximations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def approx_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


REQUIRED_LAYERS = ("primitive", "semantic", "component")


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(value, dict):
        return {prefix: value} if prefix else {}
    result: dict[str, Any] = {}
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(child, dict) and "$value" not in child:
            result.update(_flatten(child, path))
        else:
            result[path] = child.get("$value") if isinstance(child, dict) else child
    return result


def validate_token_document(path: Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    problems: list[str] = []
    if not isinstance(payload, dict):
        problems.append("token document must be an object")
        return {"status": "blocked", "problems": problems}
    for layer in REQUIRED_LAYERS:
        if not isinstance(payload.get(layer), dict) or not payload[layer]:
            problems.append(f"missing token layer: {layer}")
    flattened = _flatten({layer: payload.get(layer) for layer in REQUIRED_LAYERS})
    if not flattened:
        problems.append("token document has no values")
    for name, value in flattened.items():
        if not isinstance(value, (str, int, float, bool)):
            problems.append(f"token value must be scalar: {name}")
    return {"status": "passed" if not problems else "blocked", "problems": problems, "token_count": len(flattened)}


def token_drift(path: Path, referenced_tokens: list[str]) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    flattened = _flatten({layer: payload.get(layer) for layer in REQUIRED_LAYERS})
    known = set(flattened)
    unknown = sorted(set(referenced_tokens) - known)
    return {"status": "passed" if not unknown else "blocked", "unknown": unknown}

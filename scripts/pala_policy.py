#!/usr/bin/env python3
"""Validate and evaluate Pala's versioned offline policy packs read-only."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_STATUSES = {"verified-local", "verified", "configured-not-verified"}
VALID_ENFORCEMENT = {"required", "advisory"}
VALID_UNKNOWN = {"configured-not-verified", "blocked"}


@dataclass(frozen=True)
class PolicyResult:
    rule_id: str
    profile: str
    status: str
    severity: str
    enforcement: str
    evidence_required: bool
    message: str
    source_status: str
    freshness: str

    def public(self) -> dict[str, object]:
        return self.__dict__.copy()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"policy pack must be an object: {path}")
    return payload


def validate_pack(path: Path) -> dict[str, object]:
    payload = _load(path)
    required = ("schema_version", "pack_id", "pack_version", "profile", "source", "rules")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"missing policy fields: {', '.join(missing)}")
    source = payload["source"]
    if not isinstance(source, dict) or source.get("status") not in VALID_STATUSES:
        raise ValueError(f"invalid policy source status: {path}")
    if not isinstance(source.get("refs"), list) or not source["refs"]:
        raise ValueError(f"policy source refs are required: {path}")
    rules = payload["rules"]
    if not isinstance(rules, list) or not rules:
        raise ValueError(f"policy rules are required: {path}")
    ids: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError(f"policy rule must be an object: {path}")
        for key in ("id", "title", "category", "severity", "profiles", "enforcement", "evidence_required", "unknown", "message"):
            if key not in rule:
                raise ValueError(f"missing rule field {key}: {path}")
        if rule["id"] in ids:
            raise ValueError(f"duplicate rule id: {rule['id']}")
        ids.add(str(rule["id"]))
        if rule["enforcement"] not in VALID_ENFORCEMENT or rule["unknown"] not in VALID_UNKNOWN:
            raise ValueError(f"invalid rule state: {rule['id']}")
    return {"path": str(path), "pack_id": payload["pack_id"], "rule_count": len(rules), "valid": True}


def _freshness(source: dict[str, Any], now: datetime) -> str:
    if source.get("status") == "configured-not-verified":
        return "unknown"
    try:
        checked = datetime.fromisoformat(str(source["checked_at"]).replace("Z", "+00:00"))
        age_days = (now - checked).total_seconds() / 86400
        return "fresh" if age_days <= int(source.get("freshness_days", 0)) else "stale"
    except (KeyError, TypeError, ValueError):
        return "unknown"


def evaluate_profile(directory: Path, profile: str, *, now: datetime | None = None) -> list[PolicyResult]:
    """Return deterministic advisory results without writing any state."""
    moment = now or datetime.now(timezone.utc)
    results: list[PolicyResult] = []
    for path in sorted(directory.glob("*.json")):
        payload = _load(path)
        validate_pack(path)
        source = payload["source"]
        freshness = _freshness(source, moment)
        for rule in payload["rules"]:
            if profile not in rule["profiles"]:
                continue
            status = "configured-not-verified"
            if source["status"] in {"verified", "verified-local"} and freshness == "fresh":
                status = "not-run"
            results.append(PolicyResult(str(rule["id"]), profile, status, str(rule["severity"]), str(rule["enforcement"]), bool(rule["evidence_required"]), str(rule["message"]), str(source["status"]), freshness))
    return results


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("policies"))
    parser.add_argument("--profile", default="Release")
    args = parser.parse_args()
    for path in sorted(args.directory.glob("*.json")):
        validate_pack(path)
    print(json.dumps([item.public() for item in evaluate_profile(args.directory, args.profile)], ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())

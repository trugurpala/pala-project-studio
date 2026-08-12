#!/usr/bin/env python3
"""Validate donor provenance and the canonical localization contract."""

from __future__ import annotations

import json
import string
from pathlib import Path


REQUIRED_DONOR_FIELDS = {
    "name", "repository", "commit", "license", "source_paths_reviewed",
    "imported_files", "local_hashes", "upstream_purpose", "pala_purpose",
    "modifications", "update_policy", "status", "license_status",
}


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def validate_inventory(path: Path) -> list[str]:
    payload = load_json(path)
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("third-party inventory must contain entries")
    problems: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            problems.append(f"entry {index} is not an object")
            continue
        missing = sorted(REQUIRED_DONOR_FIELDS - set(entry))
        if missing:
            problems.append(f"entry {index} missing: {', '.join(missing)}")
        if entry.get("imported_files") and not entry.get("local_hashes"):
            problems.append(f"entry {index} imported files need local hashes")
        if entry.get("status") == "external-reference" and entry.get("imported_files"):
            problems.append(f"entry {index} external reference cannot import files")
    return problems


def validate_locales(root: Path) -> list[str]:
    english = load_json(root / "locales" / "en.json")
    turkish = load_json(root / "locales" / "tr-ascii.json")
    problems: list[str] = []
    if english.get("canonical") is not True or english.get("locale") != "en":
        problems.append("English locale must be canonical")
    if turkish.get("canonical") is not False or turkish.get("locale") != "tr-ascii":
        problems.append("tr-ascii locale must be optional")
    english_messages = english.get("messages", {})
    turkish_messages = turkish.get("messages", {})
    if not isinstance(english_messages, dict) or not isinstance(turkish_messages, dict):
        return ["locale messages must be objects"]
    if not set(english_messages) <= set(turkish_messages):
        problems.append("tr-ascii must cover every English message")
    allowed = set(string.ascii_letters + string.digits + string.punctuation + " \t\r\n")
    for key, value in turkish_messages.items():
        if not isinstance(value, str) or any(char not in allowed for char in value):
            problems.append(f"tr-ascii message is not ASCII-safe: {key}")
    return problems


def validate(root: Path) -> dict[str, object]:
    inventory_problems = validate_inventory(root / "artifacts" / "governance" / "third-party-inventory.json")
    locale_problems = validate_locales(root)
    return {
        "status": "passed" if not inventory_problems and not locale_problems else "blocked",
        "inventory_problems": inventory_problems,
        "locale_problems": locale_problems,
        "global_installation": "not-performed",
    }


if __name__ == "__main__":
    result = validate(Path(__file__).resolve().parent.parent)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    raise SystemExit(0 if result["status"] == "passed" else 1)

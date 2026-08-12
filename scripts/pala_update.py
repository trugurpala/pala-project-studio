#!/usr/bin/env python3
"""Check Pala releases with a bounded, secrets-free local cache."""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen


CACHE_TTL = timedelta(hours=24)
RELEASE_URL = "https://api.github.com/repos/trugurpala/pala-project-studio/releases/latest"
RELEASE_CACHE_NAME = "release-check-cache.json"
VERSION_PART = re.compile(r"^v?(\d+(?:\.\d+)*)")
ALLOWED_CACHE_KEYS = {
    "checked_at",
    "installed_version",
    "status",
    "available_version",
    "url",
    "asset_name",
    "asset_url",
    "asset_sha256",
    "asset_digest_source",
}


def normalize_version(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw[0] in {"v", "V"}:
        raw = raw[1:]
    return raw.split("+", 1)[0]


def normalize_sha256(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if normalized.lower().startswith("sha256:"):
        normalized = normalized[7:]
    normalized = normalized.strip().replace(" ", "")
    if len(normalized) != 64:
        return None
    lowered = normalized.lower()
    if any(char not in "0123456789abcdef" for char in lowered):
        return None
    return lowered


def release_asset_digest(asset: object) -> str | None:
    if not isinstance(asset, dict):
        return None
    candidate = asset.get("digest") if isinstance(asset.get("digest"), str) else None
    return normalize_sha256(candidate)


def pick_release_asset(payload: dict[str, object]) -> dict[str, object] | None:
    assets = payload.get("assets")
    if not isinstance(assets, list):
        return None
    matches: list[dict[str, object]] = []
    for item in assets:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str):
            continue
        lowered = name.casefold()
        if (
            "pala-project-studio" in lowered
            and lowered.endswith(".zip")
        ):
            matches.append(item)
    if not matches:
        return None
    # Prefer explicit `final` asset, then lexical order for determinism.
    return sorted(
        matches,
        key=lambda item: (0 if str(item.get("name", "")).lower().endswith("-final.zip") else 1, str(item.get("name")).lower()),
    )[0]


def release_asset_record(payload: dict[str, object]) -> dict[str, object] | None:
    asset = pick_release_asset(payload)
    if asset is None or not isinstance(asset, dict):
        return None
    url = asset.get("browser_download_url")
    if not isinstance(url, str):
        return None
    digest = release_asset_digest(asset)
    return {
        "name": str(asset.get("name", "")),
        "url": url,
        "sha256": digest,
        "digest_source": "asset",
    }


def read_cache(path: Path) -> dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return {key: payload.get(key) for key in ALLOWED_CACHE_KEYS if key in payload}


def write_cache(path: Path, payload: dict[str, object]) -> None:
    safe = {
        key: value
        for key, value in payload.items()
        if key in ALLOWED_CACHE_KEYS and (value is None or isinstance(value, str))
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        json.dump(safe, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def version_key(value: object) -> tuple[int, ...] | None:
    if not isinstance(value, str):
        return None
    match = VERSION_PART.match(value.strip().split("+", 1)[0])
    if match is None:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def newer(candidate: object, installed: object) -> bool:
    candidate_key = version_key(candidate)
    installed_key = version_key(installed)
    if candidate_key is None or installed_key is None:
        return False
    width = max(len(candidate_key), len(installed_key))
    return candidate_key + (0,) * (width - len(candidate_key)) > installed_key + (0,) * (
        width - len(installed_key)
    )


def cache_is_fresh(
    cached: dict[str, object] | None, installed_version: str, now: datetime
) -> bool:
    if not cached or cached.get("installed_version") != installed_version:
        return False
    checked_at = cached.get("checked_at")
    if not isinstance(checked_at, str):
        return False
    try:
        checked = datetime.fromisoformat(checked_at)
    except ValueError:
        return False
    if checked.tzinfo is None:
        return False
    elapsed = now - checked.astimezone(timezone.utc)
    return timedelta(0) <= elapsed < CACHE_TTL


def fetch_latest_release() -> dict[str, object]:
    request = Request(
        RELEASE_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Pala-Project-Studio"},
    )
    with urlopen(request, timeout=5) as response:  # nosec B310: fixed HTTPS URL
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("release response is not an object")
    return payload


def result_from_cache(cached: dict[str, object], source: str) -> dict[str, object]:
    return {
        "source": source,
        "status": cached.get("status", "unavailable"),
        "installed_version": cached.get("installed_version"),
        "available_version": cached.get("available_version"),
        "url": cached.get("url"),
        "asset_name": cached.get("asset_name"),
        "asset_url": cached.get("asset_url"),
        "asset_sha256": cached.get("asset_sha256"),
        "asset_digest_source": cached.get("asset_digest_source"),
        "message": (
            "Pala update available"
            if cached.get("status") == "update-available"
            else "Pala is current"
            if cached.get("status") == "current"
            else "remote update check unavailable"
        ),
    }


def check_update(
    installed_version: str,
    cache_path: Path,
    *,
    now: datetime | None = None,
    fetch: Callable[[], dict[str, object]] = fetch_latest_release,
) -> dict[str, object]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cached = read_cache(cache_path)
    if cache_is_fresh(cached, installed_version, now):
        if cached is None:
            raise ValueError("fresh update cache is missing")
        return result_from_cache(cached, "cache")

    try:
        release = fetch()
        available = release.get("tag_name")
        url = release.get("html_url")
        if not isinstance(available, str):
            raise ValueError("release version is missing")
        available_version = normalize_version(available)
        if available_version is None:
            raise ValueError("release version is missing")
        asset = release_asset_record(release)
        payload = {
            "checked_at": now.isoformat(),
            "installed_version": installed_version,
            "status": "update-available" if newer(available, installed_version) else "current",
            "available_version": available_version,
            "url": url if isinstance(url, str) else None,
            "asset_name": asset.get("name") if asset else None,
            "asset_url": asset.get("url") if asset else None,
            "asset_sha256": asset.get("sha256") if asset else None,
            "asset_digest_source": asset.get("digest_source") if asset else None,
        }
    except (OSError, ValueError, json.JSONDecodeError):
        payload = {
            "checked_at": now.isoformat(),
            "installed_version": installed_version,
            "status": "unavailable",
            "available_version": None,
            "url": None,
            "asset_name": None,
            "asset_url": None,
            "asset_sha256": None,
            "asset_digest_source": None,
        }

    write_cache(cache_path, payload)
    return result_from_cache(payload, "remote")


def installed_version(manifest_path: Path) -> str:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Pala manifest cannot be read") from error
    value = payload.get("version") if isinstance(payload, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Pala manifest version is missing")
    return value.split("+", 1)[0]


def default_cache_path() -> Path:
    if os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "Pala" / RELEASE_CACHE_NAME
    state_root = os.environ.get("XDG_STATE_HOME")
    if state_root:
        return Path(state_root) / "pala" / RELEASE_CACHE_NAME
    return Path.home() / ".local" / "state" / "pala" / RELEASE_CACHE_NAME


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("command", choices=("check",))
    result.add_argument("--cache", type=Path, default=default_cache_path())
    result.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).resolve().parent.parent / ".codex-plugin" / "plugin.json",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        version = installed_version(args.manifest)
        result = check_update(version, args.cache)
    except ValueError as error:
        print(json.dumps({"status": "unavailable", "message": str(error)}))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

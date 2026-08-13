#!/usr/bin/env python3
"""Exercise real published Pala release archives against a local candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath


RELEASES = {
    "0.4.4": {
        "url": "https://github.com/trugurpala/pala-project-studio/releases/download/v0.4.4/pala-project-studio-0.4.4.zip",
        "sha256": "F092D2066CE15BC6900C40B09B8AEDDB2939AB779C7178C9DED61092CD254B4F",
    },
    "0.8.0": {
        "url": "https://github.com/trugurpala/pala-project-studio/releases/download/v0.8.0/pala-project-studio-0.8.0.zip",
        "sha256": "3EA17A1CEFF7DEEBF906D03184D9B9F09F800B4B64B4AD0D880AD30C22A6916E",
    },
    "0.8.1": {
        "url": "https://github.com/trugurpala/pala-project-studio/releases/download/v0.8.1/pala-project-studio-0.8.1-final.zip",
        "sha256": "69325B6EE96D59498EC269286449CB25352FB45B9CC6267DC064D8356848FF53",
    },
    "1.0.0": {
        "url": "https://github.com/trugurpala/pala-project-studio/releases/download/v1.0.0/pala-project-studio-1.0.0.zip",
        "sha256": "13173D29431FFAD84038141F8191B10041AC353314A24831B37064F2FAD1306C",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def safe_extract(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as handle:
        for item in handle.infolist():
            normalized = item.filename.replace("\\", "/")
            relative = PurePosixPath(normalized)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"unsafe archive path: {item.filename!r}")
            target = destination.joinpath(*relative.parts)
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with handle.open(item) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    candidates = [
        path.parent.parent
        for path in destination.rglob(".codex-plugin/plugin.json")
    ]
    if len(candidates) != 1:
        raise ValueError("archive must contain exactly one Pala plugin root")
    return candidates[0].resolve()


def candidate_version(root: Path) -> str:
    path = root / ".codex-plugin" / "plugin.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    version = str(value.get("version", ""))
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", version):
        raise ValueError("upgrade candidate must have a release version")
    return version


def download_release(version: str, cache: Path) -> Path:
    item = RELEASES[version]
    destination = cache / Path(str(item["url"])).name
    if destination.is_file() and sha256(destination) == item["sha256"]:
        return destination
    cache.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=cache)
    os.close(descriptor)
    temporary = Path(temp_name)
    try:
        request = urllib.request.Request(str(item["url"]), headers={"User-Agent": "Pala-Upgrade-Matrix"})
        with urllib.request.urlopen(request, timeout=30) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        actual = sha256(temporary)
        if actual != item["sha256"]:
            raise ValueError(f"release {version} SHA-256 mismatch")
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def load_installer(candidate: Path):
    scripts = str((candidate / "scripts").resolve())
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import pala_installer  # type: ignore

    return pala_installer


def seed_managed(installer, old_root: Path, install_root: Path, state_root: Path) -> None:
    installer.copy_bundle(old_root, install_root)
    manifest = json.loads((install_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    installer.atomic_write_json(
        installer.state_path(state_root),
        {
            "schema_version": installer.SCHEMA_VERSION,
            "owner": installer.OWNER,
            "install_root": str(install_root.resolve()),
            "version": manifest["version"],
            "fingerprint": installer.tree_fingerprint(install_root),
            "file_hashes": installer.bundle_file_hashes(install_root),
            "source": installer.OFFICIAL_REPOSITORY,
            "license": "MIT",
            "plugin_id": installer.PLUGIN_ID,
            "installed_at": "2026-08-10T00:00:00+00:00",
            "last_verified_at": "2026-08-10T00:00:00+00:00",
        },
    )


def run_case(
    installer,
    candidate: Path,
    old_root: Path,
    workspace: Path,
    *,
    legacy: bool,
    target_version: str,
) -> dict[str, object]:
    suffix = "legacy" if legacy else "managed"
    case_root = workspace / suffix
    install_root = case_root / "local" / "Pala" / "marketplace"
    state_root = case_root / "local" / "Pala"
    state_markers = {
        "canonical_user_state": state_root / "runtime" / "canonical-user-state.json",
        "project_catalog": state_root / "catalog" / "pala-catalog.json",
        "failure_intelligence": state_root / "runtime" / "failure-intelligence.json",
    }
    if legacy:
        installer.copy_bundle(old_root, install_root)
    else:
        seed_managed(installer, old_root, install_root, state_root)
    for name, marker in state_markers.items():
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            json.dumps({"owner": "user", "surface": name, "keep": True}) + "\n",
            encoding="utf-8",
        )
    before = json.loads((install_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    report = installer.install_bundle(candidate, install_root, state_root)
    after = json.loads((install_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    second = installer.install_bundle(candidate, install_root, state_root)
    doctor_healthy = bool(
        installer.doctor_bundle(candidate, install_root, state_root)["healthy"]
    )
    state_preservation = {
        name: bool(
            marker.is_file()
            and json.loads(marker.read_text(encoding="utf-8")).get("keep") is True
        )
        for name, marker in state_markers.items()
    }
    required_missing = [
        str(path).replace("\\", "/")
        for path in installer.REQUIRED_FILES
        if not (install_root / path).is_file()
    ]
    expected_status = "migrated" if legacy else "updated"
    passed = bool(
        report.get("status") == expected_status
        and str(after).split("+", 1)[0] == target_version.split("+", 1)[0]
        and all(state_preservation.values())
        and not required_missing
        and doctor_healthy
        and second.get("status") == "ready"
        and second.get("changed") is False
    )
    return {
        "mode": suffix,
        "status": "passed" if passed else "blocked",
        "installer_status": report.get("status"),
        "from_version": before,
        "to_version": after,
        "state_marker_preserved": all(state_preservation.values()),
        "state_preservation": state_preservation,
        "second_ensure_current_status": second.get("status"),
        "second_ensure_current_changed": second.get("changed"),
        "doctor_healthy": doctor_healthy,
        "codex_scope": "not-mutated-isolated-bundle-canary",
        "required_missing": required_missing,
    }


def run_matrix(candidate: Path, cache: Path) -> dict[str, object]:
    candidate = candidate.resolve()
    version = candidate_version(candidate)
    installer = load_installer(candidate)
    rows: list[dict[str, object]] = []
    assets: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="pala-real-upgrade-") as temporary:
        workspace = Path(temporary)
        for old_version, item in RELEASES.items():
            archive = download_release(old_version, cache)
            extracted = safe_extract(archive, workspace / f"extract-{old_version}")
            assets.append(
                {
                    "version": old_version,
                    "url": item["url"],
                    "sha256": sha256(archive),
                    "size": archive.stat().st_size,
                }
            )
            rows.append(
                run_case(
                    installer,
                    candidate,
                    extracted,
                    workspace / f"case-{old_version}",
                    legacy=False,
                    target_version=version,
                )
            )
            rows[-1]["source_release"] = old_version
            if old_version in {"0.4.4", "0.8.0"}:
                rows.append(
                    run_case(
                        installer,
                        candidate,
                        extracted,
                        workspace / f"case-{old_version}-legacy",
                        legacy=True,
                        target_version=version,
                    )
                )
                rows[-1]["source_release"] = old_version
    passed = all(row["status"] == "passed" for row in rows)
    return {
        "schema_version": 1,
        "status": "passed" if passed else "blocked",
        "candidate_version": version,
        "candidate_fingerprint": installer.bundle_fingerprint(candidate),
        "assets": assets,
        "rows": rows,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }


def write_result(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=Path.cwd())
    parser.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "pala-upgrade-m45-assets")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run_matrix(args.candidate, args.cache)
    write_result(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

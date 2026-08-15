#!/usr/bin/env python3
"""Exercise real published Pala release archives against a local candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
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
    "1.1.2": {
        "url": "https://github.com/trugurpala/pala-project-studio/releases/download/v1.1.2/pala-project-studio-1.1.2.zip",
        "sha256": "A718AEA977536E5385401F7DEBCB1CDB6CEE005F054A52574B820C263D1962B2",
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
    candidates = [path.parent.parent for path in destination.rglob(".codex-plugin/plugin.json")]
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
        request = urllib.request.Request(
            str(item["url"]), headers={"User-Agent": "Pala-Upgrade-Matrix"}
        )
        with (
            urllib.request.urlopen(request, timeout=30) as response,
            temporary.open("wb") as output,
        ):
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
    manifest = json.loads(
        (install_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
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


def seed_sqlite_continuity(path: Path) -> dict[str, object]:
    """Create a real minimal v2 SQLite/FI row for preservation canaries."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE schema_version (version INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO schema_version(version) VALUES (2)")
        conn.execute(
            """CREATE TABLE failure_intelligence (
                fingerprint TEXT PRIMARY KEY, failure_id TEXT NOT NULL,
                failure_class TEXT NOT NULL, command_family TEXT NOT NULL,
                exception_type TEXT NOT NULL, normalized_message TEXT NOT NULL,
                tool TEXT NOT NULL, tool_version TEXT NOT NULL,
                platform TEXT NOT NULL, runtime_version TEXT NOT NULL,
                relevant_surface TEXT NOT NULL, first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL, occurrence_count INTEGER NOT NULL,
                project_refs_json TEXT NOT NULL, attempts INTEGER NOT NULL,
                root_cause TEXT NOT NULL, resolution_state TEXT NOT NULL,
                resolution_recipe TEXT NOT NULL,
                verification_basis_json TEXT NOT NULL,
                freshness TEXT NOT NULL, retry_budget INTEGER NOT NULL
            )"""
        )
        conn.execute(
            "INSERT INTO failure_intelligence VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "f" * 64,
                "FI-upgrade-canary",
                "upgrade-canary",
                "pala-upgrade-matrix",
                "RuntimeError",
                "sanitized-canary",
                "pala",
                "1.1.2",
                "isolated",
                "3",
                "upgrade-matrix",
                "2026-08-14T00:00:00+00:00",
                "2026-08-14T00:00:00+00:00",
                1,
                '["upgrade-canary"]',
                1,
                "",
                "OBSERVED",
                "",
                "{}",
                "fresh",
                2,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return sqlite_evidence(path)


def sqlite_evidence(path: Path) -> dict[str, object]:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        version = int(conn.execute("SELECT version FROM schema_version").fetchone()[0])
        rows = int(conn.execute("SELECT COUNT(*) FROM failure_intelligence").fetchone()[0])
        failure_id = str(conn.execute("SELECT failure_id FROM failure_intelligence").fetchone()[0])
    finally:
        conn.close()
    return {
        "sha256": sha256(path),
        "schema_version": version,
        "failure_rows": rows,
        "failure_id": failure_id,
    }


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
    database = state_root / "pala.sqlite"
    sqlite_before = seed_sqlite_continuity(database)
    before = json.loads(
        (install_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )["version"]
    report = installer.install_bundle(candidate, install_root, state_root)
    after = json.loads(
        (install_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )["version"]
    second = installer.install_bundle(candidate, install_root, state_root)
    doctor_healthy = bool(installer.doctor_bundle(candidate, install_root, state_root)["healthy"])
    state_preservation = {
        name: bool(
            marker.is_file() and json.loads(marker.read_text(encoding="utf-8")).get("keep") is True
        )
        for name, marker in state_markers.items()
    }
    sqlite_after = sqlite_evidence(database)
    state_preservation["pala_sqlite"] = sqlite_after["sha256"] == sqlite_before["sha256"]
    state_preservation["failure_intelligence"] = bool(
        sqlite_after["failure_rows"] == 1 and sqlite_after["failure_id"] == "FI-upgrade-canary"
    )
    required_missing = [
        str(path).replace("\\", "/")
        for path in installer.REQUIRED_FILES
        if not (install_root / path).is_file()
    ]
    same_base_version = str(before).split("+", 1)[0] == target_version.split("+", 1)[0]
    expected_status = "migrated" if legacy else ("repaired" if same_base_version else "updated")
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
        "sqlite_schema_version": sqlite_after["schema_version"],
        "failure_rows": sqlite_after["failure_rows"],
        "second_ensure_current_status": second.get("status"),
        "second_ensure_current_changed": second.get("changed"),
        "doctor_healthy": doctor_healthy,
        "codex_scope": "not-mutated-isolated-bundle-canary",
        "required_missing": required_missing,
    }


def run_fault_rollback_case(
    installer,
    candidate: Path,
    old_root: Path,
    workspace: Path,
) -> dict[str, object]:
    """Prove an activated upgrade rolls back if durable state cannot be written.

    This is deliberately isolated from a real user profile.  The failure is
    injected at the transaction's final state-write boundary, after the new
    bundle is active, which is the point where rollback protection matters.
    """
    case_root = workspace / "fault-rollback"
    install_root = case_root / "local" / "Pala" / "marketplace"
    state_root = case_root / "local" / "Pala"
    seed_managed(installer, old_root, install_root, state_root)
    database = state_root / "pala.sqlite"
    sqlite_before = seed_sqlite_continuity(database)
    old_fingerprint = installer.tree_fingerprint(install_root)
    installed_manifest = install_root / ".codex-plugin" / "plugin.json"
    old_version = str(
        json.loads(installed_manifest.read_text(encoding="utf-8"))["version"]
    )
    operations = installer._transaction_operations()

    def fail_state_write(_path: Path, _payload: object) -> None:
        raise RuntimeError("intentional upgrade matrix state-write fault")

    operations["atomic_write_json"] = fail_state_write
    fault_raised = False
    try:
        installer.install_bundle_transaction(
            candidate,
            install_root,
            state_root,
            operations=operations,
        )
    except RuntimeError as error:
        fault_raised = str(error) == "intentional upgrade matrix state-write fault"

    sqlite_after = sqlite_evidence(database)
    restored_version = str(
        json.loads(installed_manifest.read_text(encoding="utf-8"))["version"]
    )
    rollback_restored = bool(
        fault_raised
        and installer.tree_fingerprint(install_root) == old_fingerprint
        and restored_version == old_version
        and not list(install_root.parent.glob(".pala-project-studio.rollback-*"))
    )
    sqlite_preserved = sqlite_after["sha256"] == sqlite_before["sha256"]
    failure_intelligence_preserved = bool(
        sqlite_after["failure_rows"] == 1
        and sqlite_after["failure_id"] == "FI-upgrade-canary"
    )
    passed = rollback_restored and sqlite_preserved and failure_intelligence_preserved
    return {
        "status": "passed" if passed else "blocked",
        "fault": "state-write",
        "rollback_restored": rollback_restored,
        "sqlite_preserved": sqlite_preserved,
        "failure_intelligence_preserved": failure_intelligence_preserved,
        "scope": "isolated-temporary-profile",
    }


def run_matrix(
    candidate: Path,
    cache: Path,
    *,
    network_enabled: bool = False,
) -> dict[str, object]:
    """Run only when a release workflow explicitly authorizes public downloads."""
    if not network_enabled:
        raise ValueError("real upgrade matrix requires explicit --network-enabled")
    candidate = candidate.resolve()
    installer = load_installer(candidate)
    rows: list[dict[str, object]] = []
    assets: list[dict[str, object]] = []
    candidate_fingerprint = ""
    with tempfile.TemporaryDirectory(prefix="pala-real-upgrade-") as temporary:
        workspace = Path(temporary)
        # Run every legacy fixture against one immutable local candidate
        # snapshot.  This models the release artifact and prevents an in-flight
        # source edit from mixing bytes between matrix rows.
        candidate_snapshot = workspace / "candidate-1.2.0"
        installer.copy_bundle(candidate, candidate_snapshot)
        version = candidate_version(candidate_snapshot)
        candidate_fingerprint = installer.bundle_fingerprint(candidate_snapshot)
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
                    candidate_snapshot,
                    extracted,
                    workspace / f"case-{old_version}",
                    legacy=False,
                    target_version=version,
                )
            )
            rows[-1]["source_release"] = old_version
            rollback = run_fault_rollback_case(
                installer,
                candidate_snapshot,
                extracted,
                workspace / f"case-{old_version}",
            )
            rollback["source_release"] = old_version
            rollback["mode"] = "fault-rollback"
            rows.append(rollback)
            if old_version in {"0.4.4", "0.8.0"}:
                rows.append(
                    run_case(
                        installer,
                        candidate_snapshot,
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
        "candidate_fingerprint": candidate_fingerprint,
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
    parser.add_argument(
        "--cache", type=Path, default=Path(tempfile.gettempdir()) / "pala-upgrade-m45-assets"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--network-enabled",
        action="store_true",
        help="authorize downloads of SHA-pinned public release archives",
    )
    args = parser.parse_args()
    try:
        payload = run_matrix(
            args.candidate,
            args.cache,
            network_enabled=args.network_enabled,
        )
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as error:
        # CI must retain a bounded, path-free result even when a pinned asset
        # or the isolated transaction cannot be verified.
        payload = {
            "schema_version": 1,
            "status": "blocked",
            "error": type(error).__name__,
            "network_enabled": args.network_enabled,
            "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        }
    write_result(args.output, payload)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

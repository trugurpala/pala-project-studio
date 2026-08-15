#!/usr/bin/env python3
"""Deterministic, private-safe local release candidate evidence for M79."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Any

import build_portable
import pala_db
import pala_installer
from pala_failure_intelligence import get_failure, record_failure

SCHEMA = "pala.final_agency_release.v1"
SBOM_SCHEMA = "http://cyclonedx.org/schema/bom-1.5.schema.json"
_RELEASE_VERSION = re.compile(r"^\d+\.\d+\.\d+$")


def release_identity(root: Path) -> dict[str, str]:
    """Derive every candidate filename from the canonical release identity.

    Historical release artifacts deliberately remain untouched: this function
    only describes the new candidate being built from ``product-identity``.
    """
    root = Path(root).resolve()
    payload = json.loads((root / "product-identity.json").read_text(encoding="utf-8"))
    version = str(payload.get("product_version") or "")
    if not _RELEASE_VERSION.fullmatch(version):
        raise ValueError("product-identity product_version must be a release semver")
    expected_artifact = f"pala-project-studio-{version}.zip"
    declared_artifact = str(payload.get("artifact_name") or "")
    if declared_artifact != expected_artifact:
        raise ValueError("product-identity artifact_name does not match product_version")
    return {
        "version": version,
        "artifact": expected_artifact,
        "sbom": f"pala-project-studio-{version}.cdx.json",
        "inventory": f"pala-project-studio-{version}.inventory.json",
        "manifest": f"pala-project-studio-{version}.manifest.json",
    }


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _npm_components(root: Path) -> list[dict[str, object]]:
    lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
    packages = lock.get("packages") if isinstance(lock, dict) else {}
    if not isinstance(packages, dict):
        raise ValueError("package-lock packages must be an object")
    values: list[dict[str, object]] = []
    for key, item in packages.items():
        if not key or not isinstance(item, dict):
            continue
        name = str(key).removeprefix("node_modules/")
        version = str(item.get("version") or "")
        if not name or not version:
            raise ValueError("locked npm package requires name and version")
        encoded = name.replace("@", "%40", 1) if name.startswith("@") else name
        purl = f"pkg:npm/{encoded}@{version}"
        component: dict[str, object] = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": purl,
            "bom-ref": purl,
            "scope": "optional" if item.get("optional") else "required",
        }
        license_name = str(item.get("license") or "")
        if license_name:
            component["licenses"] = [{"license": {"id": license_name}}]
        integrity = str(item.get("integrity") or "")
        if integrity.startswith("sha512-"):
            component["hashes"] = [{"alg": "SHA-512", "content": integrity[7:]}]
        values.append(component)
    return values


_UV_SECTION = re.compile(r"(?ms)^\[\[package\]\]\s*(.*?)(?=^\[\[package\]\]|\Z)")
_UV_NAME = re.compile(r'(?m)^name = "([^"]+)"$')
_UV_VERSION = re.compile(r'(?m)^version = "([^"]+)"$')


def _python_components(root: Path) -> list[dict[str, object]]:
    text = (root / "uv.lock").read_text(encoding="utf-8")
    values: list[dict[str, object]] = []
    for section in _UV_SECTION.findall(text):
        name_match = _UV_NAME.search(section)
        version_match = _UV_VERSION.search(section)
        if not name_match or not version_match:
            continue
        name, version = name_match.group(1), version_match.group(1)
        if name == "pala-project-studio":
            continue
        purl = f"pkg:pypi/{name}@{version}"
        values.append(
            {
                "type": "library",
                "name": name,
                "version": version,
                "purl": purl,
                "bom-ref": purl,
                "scope": "optional",
            }
        )
    return values


def generate_sbom(root: Path) -> dict[str, object]:
    """Return a deterministic CycloneDX 1.5 SBOM from committed lock files."""
    root = Path(root).resolve()
    version = release_identity(root)["version"]
    components = _npm_components(root) + _python_components(root)
    unique = {str(item["bom-ref"]): item for item in components}
    ordered = [unique[key] for key in sorted(unique, key=str.casefold)]
    serial = uuid.uuid5(uuid.NAMESPACE_URL, f"pala-project-studio:{version}")
    return {
        "$schema": SBOM_SCHEMA,
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "name": "pala-project-studio",
                "version": version,
                "bom-ref": f"pkg:generic/pala-project-studio@{version}",
                "licenses": [{"license": {"id": "MIT"}}],
            },
            "properties": [
                {"name": "pala:authority", "value": "committed-lock-files"},
                {"name": "pala:network", "value": "not-run"},
            ],
        },
        "components": ordered,
    }


def archive_inventory(archive: Path, *, artifact: str) -> dict[str, object]:
    """Hash every regular archive member and reject ambiguous names."""
    files: list[dict[str, object]] = []
    with zipfile.ZipFile(archive) as payload:
        members = [item for item in payload.infolist() if not item.is_dir()]
        build_portable.ensure_unique_names(item.filename for item in members)
        for item in sorted(members, key=lambda value: value.filename.casefold()):
            name = build_portable.validate_archive_name(item.filename)
            data = payload.read(item)
            files.append({"path": name, "sha256": _sha_bytes(data), "size": len(data)})
    return {
        "schema": "pala.artifact_inventory.v1",
        "artifact": artifact,
        "artifact_sha256": _sha_file(archive),
        "entries": len(files),
        "files": files,
    }


def build_release_candidate(
    root: Path,
    output_dir: Path,
    *,
    include_install_canary: bool = False,
    include_self_verification: bool = False,
) -> dict[str, Any]:
    """Build the local RC plus deterministic SBOM, inventory, and manifest."""
    root = Path(root).resolve()
    output_dir = Path(output_dir).resolve()
    identity = release_identity(root)
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = [
        output_dir / identity["artifact"],
        output_dir / identity["sbom"],
        output_dir / identity["inventory"],
        output_dir / identity["manifest"],
    ]
    if any(path.exists() for path in targets):
        raise FileExistsError("release candidate output already exists")

    archive = targets[0]
    build_portable.build_archive(archive, root)
    sbom_bytes = _canonical(generate_sbom(root))
    targets[1].write_bytes(sbom_bytes)
    inventory = archive_inventory(archive, artifact=identity["artifact"])
    inventory_bytes = _canonical(inventory)
    targets[2].write_bytes(inventory_bytes)
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "passed",
        "release_state": "LOCAL RELEASE CANDIDATE VERIFIED",
        "product_version": identity["version"],
        "artifact": identity["artifact"],
        "artifact_sha256": str(inventory["artifact_sha256"]),
        "artifact_entries": int(inventory["entries"]),
        "sbom": identity["sbom"],
        "sbom_sha256": _sha_bytes(sbom_bytes),
        "inventory": identity["inventory"],
        "inventory_sha256": _sha_bytes(inventory_bytes),
        "inventory_entries": int(inventory["entries"]),
        "remote_publish": "not-run",
        "real_remote_deploy": "not-run",
        "authority": "local-m79-release-candidate",
        "can_complete": False,
    }
    if include_install_canary:
        canary = isolated_install_canary(root)
        manifest["install_canary"] = canary
        if canary.get("status") != "passed":
            manifest["status"] = "blocked"
            manifest["release_state"] = "BLOCKED"
    if include_self_verification:
        verification = verify_release_candidate(root, archive)
        manifest["self_verification"] = verification
        if verification.get("status") != "passed":
            manifest["status"] = "blocked"
            manifest["release_state"] = "BLOCKED"
    targets[3].write_bytes(_canonical(manifest))
    return {**manifest, "files": inventory["files"]}


def _extract_verified_portable(archive: Path, destination: Path) -> Path:
    """Extract our own archive only after validating member names and modes."""
    with zipfile.ZipFile(archive) as payload:
        members = [item for item in payload.infolist() if not item.is_dir()]
        build_portable.ensure_unique_names(item.filename for item in members)
        for item in members:
            build_portable.validate_archive_name(item.filename)
            if stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("portable archive contains a symbolic link")
        payload.extractall(destination)
    portable_root = destination / build_portable.ARCHIVE_ROOT
    if not portable_root.is_dir():
        raise ValueError("portable archive has no expected root")
    return portable_root


def _portable_payload_fingerprint(root: Path) -> str:
    """Fingerprint the exact portable allowlist, independent of source-only files."""
    digest = hashlib.sha256()
    for path, name in build_portable.archive_entries(Path(root).resolve()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest().upper()


def verify_release_candidate(root: Path, archive: Path) -> dict[str, object]:
    """Prove source, extracted portable and installed trees remain fingerprint-stable."""
    root = Path(root).resolve()
    archive = Path(archive).resolve()
    if not archive.is_file():
        raise FileNotFoundError(f"release candidate artifact is missing: {archive}")
    with tempfile.TemporaryDirectory(prefix="pala-release-self-verify-") as temporary:
        workspace = Path(temporary)
        source_before = _portable_payload_fingerprint(root)
        pala_installer.validate_bundle(root)
        portable_root = _extract_verified_portable(archive, workspace / "portable")
        portable_before = _portable_payload_fingerprint(portable_root)
        pala_installer.validate_bundle(portable_root)
        install_root = workspace / "profile" / "marketplace"
        state_root = workspace / "profile"
        install = pala_installer.install_bundle(portable_root, install_root, state_root)
        installed_before = pala_installer.tree_fingerprint(install_root)
        doctor = pala_installer.doctor_bundle(portable_root, install_root, state_root)
        source_after = _portable_payload_fingerprint(root)
        portable_after = _portable_payload_fingerprint(portable_root)
        installed_after = pala_installer.tree_fingerprint(install_root)
        source_verified = source_before == source_after
        portable_verified = portable_before == portable_after == source_before
        installed_verified = bool(
            install.get("status") == "installed"
            and doctor.get("healthy")
            and installed_before == installed_after
        )
        drift_free = source_verified and portable_verified and installed_verified
        return {
            "status": "passed" if drift_free else "blocked",
            "source_verified": source_verified,
            "portable_verified": portable_verified,
            "installed_verified": installed_verified,
            "fingerprint_drift_free": drift_free,
            "source_fingerprint": source_after,
            "portable_fingerprint": portable_after,
            "installed_fingerprint": installed_after,
            "scope": "isolated-temporary-profile",
            "can_complete": False,
        }


def self_verify_release_candidate(root: Path, output_dir: Path) -> dict[str, object]:
    """Build an isolated candidate and run the Issue #13 drift regression."""
    result = build_release_candidate(root, output_dir)
    verification = verify_release_candidate(Path(root), Path(output_dir) / str(result["artifact"]))
    return verification


def isolated_install_canary(root: Path) -> dict[str, object]:
    """Exercise install/no-op/fault rollback without touching the user profile."""
    root = Path(root).resolve()
    version = release_identity(root)["version"]
    with tempfile.TemporaryDirectory(prefix="pala-m79-install-") as temporary:
        workspace = Path(temporary)
        install_root = workspace / "profile" / "marketplace"
        state_root = workspace / "profile"
        database = state_root / pala_db.DB_NAME
        record = record_failure(
            message="isolated canary failure",
            command="pala m79 canary",
            failure_class="canary",
            tool="pala",
            tool_version=version,
            platform_name="isolated",
            relevant_surface="release-candidate",
            project_ref="m79-canary",
            path=database,
        )
        sqlite_before = _sha_file(database)

        first = pala_installer.install_bundle(root, install_root, state_root)
        second = pala_installer.install_bundle(root, install_root, state_root)
        doctor_healthy = bool(
            pala_installer.doctor_bundle(root, install_root, state_root)["healthy"]
        )
        installed_before = pala_installer.tree_fingerprint(install_root)

        fault_source = workspace / "fault-source"
        pala_installer.copy_bundle(root, fault_source)
        manifest_path = fault_source / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["version"] = f"{version}-rollback-probe"
        manifest_path.write_bytes(_canonical(manifest))

        operations = pala_installer._transaction_operations()

        def fail_state_write(_path: Path, _payload: object) -> None:
            raise RuntimeError("intentional isolated rollback probe")

        operations["atomic_write_json"] = fail_state_write
        rollback_raised = False
        try:
            pala_installer.install_bundle_transaction(
                fault_source,
                install_root,
                state_root,
                operations=operations,
            )
        except RuntimeError as error:
            rollback_raised = str(error) == "intentional isolated rollback probe"

        rollback_restored = bool(
            rollback_raised
            and installed_before == pala_installer.tree_fingerprint(install_root)
            and not list(install_root.parent.glob(".pala-project-studio.rollback-*"))
        )
        sqlite_preserved = sqlite_before == _sha_file(database)
        failure_preserved = get_failure(record.fingerprint, path=database) is not None
        passed = bool(
            first.get("status") == "installed"
            and second.get("status") == "ready"
            and second.get("changed") is False
            and doctor_healthy
            and rollback_restored
            and sqlite_preserved
            and failure_preserved
        )
        return {
            "status": "passed" if passed else "blocked",
            "first_install": first.get("status"),
            "second_install": second.get("status"),
            "second_changed": second.get("changed"),
            "doctor_healthy": doctor_healthy,
            "rollback_restored": rollback_restored,
            "sqlite_preserved": sqlite_preserved,
            "failure_intelligence_preserved": failure_preserved,
            "scope": "isolated-temporary-profile",
            "remote_publish": "not-run",
            "real_remote_deploy": "not-run",
            "can_complete": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--with-install-canary", action="store_true")
    parser.add_argument("--with-self-verification", action="store_true")
    args = parser.parse_args()
    result = build_release_candidate(
        args.root,
        args.output,
        include_install_canary=args.with_install_canary,
        include_self_verification=args.with_self_verification,
    )
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

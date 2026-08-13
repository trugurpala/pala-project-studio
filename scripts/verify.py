#!/usr/bin/env python3
"""Run Pala's complete local release verification without network access."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PACKAGER = SCRIPTS / "build_portable.py"
# Windows hosted runners can be slower than the local Python environment for
# the full contract suite; retain a bounded fail-closed timeout with headroom.
CONTRACT_TEST_TIMEOUT_SECONDS = 420


def announce(message: str) -> None:
    print(f"[pala] {message}", flush=True)


def validate_json(root: Path) -> None:
    for relative in (
        Path(".agents/plugins/marketplace.json"),
        Path(".codex-plugin/plugin.json"),
        Path("hooks/hooks.json"),
    ):
        path = root / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"JSON root must be an object: {relative}")

    marketplace = json.loads(
        (root / ".agents" / "plugins" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    if marketplace.get("name") != "pala-project-studio":
        raise ValueError("repo marketplace name must be pala-project-studio")
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        raise ValueError("repo marketplace must expose exactly one Pala plugin")
    entry = plugins[0]
    if not isinstance(entry, dict) or entry.get("name") != "pala-project-studio":
        raise ValueError("repo marketplace plugin entry is invalid")
    source = entry.get("source")
    if not isinstance(source, dict) or source != {"source": "local", "path": "."}:
        raise ValueError("repo marketplace must load Pala from the repository root")


def validate_python_syntax(root: Path) -> None:
    scripts = root / "scripts"
    for path in sorted(scripts.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")


def load_code_audit():
    spec = importlib.util.spec_from_file_location(
        "pala_verify_code_audit", SCRIPTS / "pala_code_audit.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("pala_code_audit.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_code_audit(root: Path, *, profile: str) -> None:
    module = load_code_audit()
    payload = module.run_audit(root, profile=profile)
    if payload.get("status") != "passed":
        security = payload.get("security")
        findings = security.get("findings", []) if isinstance(security, dict) else []
        rules = [
            str(item.get("rule"))
            for item in findings
            if isinstance(item, dict) and item.get("rule")
        ]
        raise RuntimeError("code audit failed: " + (", ".join(rules) or "unknown"))


def run_contract_tests(root: Path) -> None:
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "scripts",
        "-p",
        "test_*.py",
        "-v",
    ]
    subprocess.run(
        command,
        cwd=root,
        check=True,
        shell=False,
        timeout=CONTRACT_TEST_TIMEOUT_SECONDS,
    )


def load_packager():
    spec = importlib.util.spec_from_file_location("pala_build_portable", PACKAGER)
    if spec is None or spec.loader is None:
        raise RuntimeError("build_portable.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_reproducible_package(root: Path) -> str:
    packager = load_packager()
    with tempfile.TemporaryDirectory(prefix="pala-verify-") as temp:
        first = Path(temp) / "first.zip"
        second = Path(temp) / "second.zip"
        first_entries = packager.build_archive(first, root)
        second_entries = packager.build_archive(second, root)
        if first_entries != second_entries or first.read_bytes() != second.read_bytes():
            raise RuntimeError("portable package is not reproducible")
        return hashlib.sha256(first.read_bytes()).hexdigest().upper()


def load_self_audit():
    spec = importlib.util.spec_from_file_location(
        "pala_verify_self_audit", SCRIPTS / "pala_self_audit.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("pala_self_audit.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_self_audit(root: Path, *, profile: str = "source") -> None:
    module = load_self_audit()
    payload = module.run_audit(root, profile=profile)
    if payload.get("status") != "passed":
        failed = [
            item["name"]
            for item in payload.get("checks", [])
            if isinstance(item, dict) and item.get("status") == "failed"
        ]
        raise RuntimeError(
            "self-audit failed: " + (", ".join(failed) if failed else "unknown")
        )


def validate_knowledge_links(root: Path) -> None:
    """Release-gate local Markdown links while reporting historical stale links."""
    from pala_knowledge import lint_markdown_links

    report = lint_markdown_links(root)
    if report.get("status") != "passed":
        missing = report.get("missing") or []
        raise RuntimeError(f"knowledge link gate failed: {missing[:5]}")


def validate_artifact_contract(root: Path, *, profile: str) -> None:
    from pala_artifact import artifact_contract

    report = artifact_contract(root, profile=profile)
    if report.get("status") != "passed":
        raise RuntimeError(f"artifact contract failed: {report.get('missing') or report.get('forbidden')}")


def extract_portable_archive(archive_path: Path, destination: Path) -> Path:
    """Validate and extract a Pala portable ZIP into an isolated temporary root."""
    packager = load_packager()
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if not names:
            raise ValueError("portable archive is empty")
        for name in names:
            packager.validate_archive_name(name)
        prefixes = {Path(name).parts[0] for name in names}
        if prefixes != {packager.ARCHIVE_ROOT}:
            raise ValueError("portable archive must contain one Pala root directory")
        forbidden = {
            f"{packager.ARCHIVE_ROOT}/{name}"
            for name in ("STATUS.md", "PLAN.md", "DEBUGGING.md", "PROGRESS.md")
        }
        if forbidden.intersection(names):
            raise ValueError("portable archive contains source-only project state")
        for info in archive.infolist():
            target = destination.joinpath(*Path(info.filename).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
    return destination / packager.ARCHIVE_ROOT


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--mode",
        choices=("source", "portable", "installed"),
        default="source",
        help="source = full gate; portable = ZIP extract gate; installed = lean marketplace gate",
    )
    result.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Root to verify (default: repository root)",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = (args.root or ROOT).resolve()
    # Avoid lasting __pycache__ under installed marketplace roots (issue #13).
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    try:
        if args.mode == "installed":
            announce("Kurulu paket JSON sözleşmeleri kontrol ediliyor")
            validate_json(root)
            announce("Kurulu paket Python sözdizimi kontrol ediliyor")
            validate_python_syntax(root)
            announce("Runtime static code audit")
            run_code_audit(root, profile="runtime")
            announce("Installed knowledge link gate")
            validate_knowledge_links(root)
            validate_artifact_contract(root, profile="installed")
            announce("Runtime self-audit çalıştırılıyor")
            run_self_audit(root, profile="runtime")
            announce("PASSED: installed mode (runtime self-audit)")
            return 0

        if args.mode == "portable":
            if args.root is None or root.suffix.casefold() != ".zip":
                raise ValueError("portable mode requires --root <pala-portable.zip>")
            announce("Taşınabilir ZIP güvenle ayıklanıyor")
            with tempfile.TemporaryDirectory(prefix="pala-portable-verify-") as temp:
                portable_root = extract_portable_archive(root, Path(temp))
                validate_json(portable_root)
                validate_python_syntax(portable_root)
                run_code_audit(portable_root, profile="runtime")
                announce("Portable knowledge link gate")
                validate_knowledge_links(portable_root)
                validate_artifact_contract(portable_root, profile="portable")
                run_self_audit(portable_root, profile="runtime")
            announce("PASSED: portable mode (clean extract + runtime self-audit)")
            return 0

        announce("JSON sözleşmeleri kontrol ediliyor")
        validate_json(root)
        announce("Python sözdizimi kontrol ediliyor")
        validate_python_syntax(root)
        announce("Static code audit")
        run_code_audit(root, profile="source")
        announce("Source knowledge link gate")
        validate_knowledge_links(root)
        validate_artifact_contract(root, profile="source")
        announce("Sözleşme testleri çalıştırılıyor")
        run_contract_tests(root)
        announce("Taşınabilir paket iki kez üretiliyor")
        digest = validate_reproducible_package(root)
        announce("Fork/presence self-audit çalıştırılıyor")
        run_self_audit(root, profile="source")
    except (
        OSError,
        ValueError,
        RuntimeError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        print(f"[pala] FAILED: {error}", file=sys.stderr)
        return 1

    announce(f"PASSED: reproducible_zip_sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

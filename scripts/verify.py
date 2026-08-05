#!/usr/bin/env python3
"""Run Pala's complete local release verification without network access."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
PACKAGER = SCRIPTS / "build_portable.py"


def announce(message: str) -> None:
    print(f"[pala] {message}", flush=True)


def validate_json() -> None:
    for relative in (
        Path(".codex-plugin/plugin.json"),
        Path("hooks/hooks.json"),
    ):
        path = ROOT / relative
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"JSON root must be an object: {relative}")


def validate_python_syntax() -> None:
    for path in sorted(SCRIPTS.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")


def run_contract_tests() -> None:
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
    subprocess.run(command, cwd=ROOT, check=True)


def load_packager():
    spec = importlib.util.spec_from_file_location("pala_build_portable", PACKAGER)
    if spec is None or spec.loader is None:
        raise RuntimeError("build_portable.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_reproducible_package() -> str:
    packager = load_packager()
    with tempfile.TemporaryDirectory(prefix="pala-verify-") as temp:
        first = Path(temp) / "first.zip"
        second = Path(temp) / "second.zip"
        first_entries = packager.build_archive(first, ROOT)
        second_entries = packager.build_archive(second, ROOT)
        if first_entries != second_entries or first.read_bytes() != second.read_bytes():
            raise RuntimeError("portable package is not reproducible")
        return hashlib.sha256(first.read_bytes()).hexdigest().upper()


def main() -> int:
    try:
        announce("JSON sözleşmeleri kontrol ediliyor")
        validate_json()
        announce("Python sözdizimi kontrol ediliyor")
        validate_python_syntax()
        announce("Sözleşme testleri çalıştırılıyor")
        run_contract_tests()
        announce("Taşınabilir paket iki kez üretiliyor")
        digest = validate_reproducible_package()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"[pala] FAILED: {error}", file=sys.stderr)
        return 1

    announce(f"PASSED: reproducible_zip_sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

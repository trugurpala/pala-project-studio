#!/usr/bin/env python3
"""Contract tests for pala_provision (no real network)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

_CATALOG_TMP: tempfile.TemporaryDirectory | None = None
_ENV_PREV: dict[str, str | None] = {}


def setUpModule() -> None:
    global _CATALOG_TMP
    _CATALOG_TMP = tempfile.TemporaryDirectory()
    for name in ("PALA_CATALOG_ROOT", "PALA_DB_PATH", "PALA_PROVISION_REGISTRY"):
        _ENV_PREV[name] = os.environ.get(name)
    os.environ["PALA_CATALOG_ROOT"] = _CATALOG_TMP.name
    os.environ["PALA_DB_PATH"] = str(Path(_CATALOG_TMP.name) / "pala.sqlite")
    os.environ["PALA_PROVISION_REGISTRY"] = str(
        Path(_CATALOG_TMP.name) / "provision-registry.json"
    )


def tearDownModule() -> None:
    global _CATALOG_TMP
    for name, value in _ENV_PREV.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
    if _CATALOG_TMP is not None:
        _CATALOG_TMP.cleanup()
        _CATALOG_TMP = None


def load_module():
    spec = importlib.util.spec_from_file_location(
        "pala_provision", SCRIPT_DIR / "pala_provision.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pala_provision.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pala_provision"] = module
    spec.loader.exec_module(module)
    return module


pala_provision = load_module()


class FakeRunner:
    """Records git invocations; never touches the network."""

    def __init__(self, *, clone_ok: bool = True, fetch_ok: bool = True) -> None:
        self.calls: list[tuple[list[str], str | None]] = []
        self.clone_ok = clone_ok
        self.fetch_ok = fetch_ok

    def __call__(self, cmd, cwd=None, capture_output=True, text=True, check=False):
        argv = list(cmd)
        self.calls.append((argv, None if cwd is None else str(cwd)))
        if argv[:2] == ["git", "clone"] and self.clone_ok:
            dest = Path(argv[3])
            dest.mkdir(parents=True, exist_ok=True)
            (dest / ".git").mkdir(parents=True, exist_ok=True)
            (dest / "PROJECT.md").write_text("# Project\n", encoding="utf-8", newline="\n")
            (dest / "PLAN.md").write_text("# Plan\n", encoding="utf-8", newline="\n")
            (dest / "reports").mkdir(parents=True, exist_ok=True)
            (dest / "reports" / "CURRENT_STATUS.md").write_text(
                "# Current status\n- Next action: test\n",
                encoding="utf-8",
                newline="\n",
            )
            return subprocess.CompletedProcess(argv, 0, stdout="cloned\n", stderr="")
        if argv[:2] == ["git", "clone"]:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="clone failed")
        if argv[:2] == ["git", "fetch"]:
            code = 0 if self.fetch_ok else 1
            return subprocess.CompletedProcess(
                argv, code, stdout="", stderr="" if self.fetch_ok else "fetch failed"
            )
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="unexpected")


class PalaProvisionTests(unittest.TestCase):
    def test_rejects_file_and_shell_meta(self) -> None:
        with self.assertRaises(ValueError):
            pala_provision.validate_git_https_url("file:///tmp/repo.git")
        with self.assertRaises(ValueError):
            pala_provision.validate_git_https_url(
                "https://github.com/org/repo.git; rm -rf /"
            )
        with self.assertRaises(ValueError):
            pala_provision.validate_git_https_url("http://github.com/org/repo.git")

    def test_accepts_https_github(self) -> None:
        url = pala_provision.validate_git_https_url(
            "https://github.com/trugurpala/pala-project-studio.git"
        )
        self.assertTrue(url.startswith("https://"))
        self.assertEqual(
            pala_provision.folder_name_from_url(url), "pala-project-studio"
        )

    def test_dry_run_does_not_call_git_or_write_registry(self) -> None:
        runner = FakeRunner()
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "parent"
            parent.mkdir()
            registry = Path(temp) / "registry.json"
            catalog = Path(temp) / "catalog"
            catalog.mkdir()
            report = pala_provision.provision(
                url="https://github.com/example/demo-repo.git",
                parent=parent,
                dry_run=True,
                register=True,
                catalog_root=catalog,
                registry_path=registry,
                runner=runner,
            )
            self.assertEqual(report["last_status"], "dry-run")
            self.assertEqual(report["git_action"], "would_clone")
            self.assertEqual(report["register_detail"], "would_register")
            self.assertFalse(registry.exists())
            self.assertEqual(runner.calls, [])

    def test_clone_upserts_catalog_and_registry(self) -> None:
        runner = FakeRunner()
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "parent"
            parent.mkdir()
            registry = Path(temp) / "Pala" / "provision-registry.json"
            catalog = Path(temp) / "catalog"
            catalog.mkdir()
            os.environ["PALA_DB_PATH"] = str(catalog / "pala.sqlite")
            os.environ["PALA_CATALOG_ROOT"] = str(catalog)
            report = pala_provision.provision(
                url="https://github.com/example/demo-repo.git",
                parent=parent,
                catalog_root=catalog,
                registry_path=registry,
                runner=runner,
            )
            self.assertTrue(report["git_ok"])
            self.assertEqual(report["git_action"], "clone")
            self.assertEqual(report["last_status"], "provisioned")
            dest = parent / "demo-repo"
            self.assertTrue((dest / ".git").is_dir())
            import pala_db

            rows = pala_db.recent_provisions(path=catalog / "pala.sqlite")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "provisioned")
            catalog_file = catalog / "pala-catalog.json"
            self.assertTrue(catalog_file.is_file())
            projects = json.loads(catalog_file.read_text(encoding="utf-8"))["projects"]
            self.assertEqual(projects[0]["phase"], "provisioned")
            self.assertTrue(any(c[0][:2] == ["git", "clone"] for c in runner.calls))
            events = pala_db.recent_events(limit=5, path=catalog / "pala.sqlite")
            self.assertTrue(any(item["kind"] == "provision" for item in events))

    def test_existing_repo_fetches_without_reset(self) -> None:
        runner = FakeRunner()
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "parent"
            dest = parent / "demo-repo"
            dest.mkdir(parents=True)
            (dest / ".git").mkdir()
            registry = Path(temp) / "registry.json"
            catalog = Path(temp) / "catalog"
            catalog.mkdir()
            report = pala_provision.provision(
                url="https://github.com/example/demo-repo.git",
                parent=parent,
                catalog_root=catalog,
                registry_path=registry,
                runner=runner,
            )
            self.assertEqual(report["git_action"], "fetch")
            self.assertEqual(report["last_status"], "fetched")
            self.assertTrue(any(c[0][:2] == ["git", "fetch"] for c in runner.calls))
            self.assertFalse(any(c[0][:2] == ["git", "clone"] for c in runner.calls))
            self.assertFalse(any("reset" in c[0] for c in runner.calls))

    def test_cli_parser_and_turkish_summary(self) -> None:
        runner = FakeRunner()
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp) / "parent"
            parent.mkdir()
            registry = Path(temp) / "registry.json"
            catalog = Path(temp) / "catalog"
            catalog.mkdir()
            ns = pala_provision.parser().parse_args(
                [
                    "provision",
                    "--url",
                    "https://github.com/example/demo-repo.git",
                    "--parent",
                    str(parent),
                    "--catalog-root",
                    str(catalog),
                    "--registry",
                    str(registry),
                    "--dry-run",
                ]
            )
            self.assertEqual(ns.command, "provision")
            self.assertTrue(ns.dry_run)
            report = pala_provision.provision(
                url="https://github.com/example/demo-repo.git",
                parent=parent,
                dry_run=True,
                catalog_root=catalog,
                registry_path=registry,
                runner=runner,
            )
            summary = pala_provision.turkish_summary(report)
            self.assertIn("Pala iç kurulum", summary)
            self.assertIn("dry-run", summary)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contract tests for Pala-owned expert binary acquisition."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_module():
    spec = importlib.util.spec_from_file_location("pala_expert_installer", ROOT / "scripts" / "pala_expert_installer.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("pala_expert_installer.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pala_expert_installer"] = module
    spec.loader.exec_module(module)
    return module


class ExpertInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.installer = load_module()

    def test_verified_binary_is_owned_and_idempotent(self) -> None:
        payload = b"pala-owned-expert"
        spec = {"version": "1.0", "source_url": "https://example.invalid/expert", "sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            first = self.installer.install_binary("demo", spec, state, fetch=lambda _: payload)
            second = self.installer.install_binary("demo", spec, state, fetch=lambda _: (_ for _ in ()).throw(AssertionError("must not refetch")))
            self.assertEqual(first["state"], "ready")
            self.assertTrue(first["changed"])
            self.assertEqual(second["state"], "ready")
            self.assertFalse(second["changed"])
            self.assertEqual((state / "experts" / "demo" / "1.0" / "payload.bin").read_bytes(), payload)
            self.assertEqual(self.installer.inspect_binary("demo", spec, state)["state"], "ready")

    def test_hash_mismatch_never_activates_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            with self.assertRaises(ValueError):
                self.installer.install_binary("demo", {"version": "1.0", "source_url": "https://example.invalid", "sha256": "0" * 64}, state, fetch=lambda _: b"wrong")
            self.assertFalse((state / "experts" / "demo" / "1.0").exists())

    def test_inspection_reports_missing_and_modified_owned_payload(self) -> None:
        payload = b"pala-owned-expert"
        spec = {"version": "1.0", "source_url": "https://example.invalid/expert", "sha256": hashlib.sha256(payload).hexdigest()}
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            self.assertEqual(self.installer.inspect_binary("demo", spec, state)["state"], "missing")
            self.installer.install_binary("demo", spec, state, fetch=lambda _: payload)
            (state / "experts" / "demo" / "1.0" / "payload.bin").write_bytes(b"modified")
            self.assertEqual(self.installer.inspect_binary("demo", spec, state)["state"], "external_conflict")

    def test_dry_run_does_not_create_expert_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "Pala"
            result = self.installer.install_binary("demo", {"version": "1.0", "source_url": "https://example.invalid", "sha256": "0" * 64}, state, dry_run=True)
            self.assertEqual(result["state"], "would_install")
            self.assertFalse(state.exists())


if __name__ == "__main__":
    unittest.main()

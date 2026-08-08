#!/usr/bin/env python3
"""Contract tests for verify.py --mode source|installed."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pala_installer


def load_verify():
    path = SCRIPTS / "verify.py"
    spec = importlib.util.spec_from_file_location(
        "pala_verify_under_test", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load verify.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["pala_verify_under_test"] = module
    spec.loader.exec_module(module)
    return module


class VerifyModeTests(unittest.TestCase):
    def test_verify_installed_mode_exits_zero_on_copy_bundle(self) -> None:
        verify = load_verify()
        with tempfile.TemporaryDirectory(prefix="pala-verify-installed-") as temp:
            dest = Path(temp) / "install"
            pala_installer.copy_bundle(ROOT, dest)
            code = verify.main(["--mode", "installed", "--root", str(dest)])
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()

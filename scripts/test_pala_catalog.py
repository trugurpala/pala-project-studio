#!/usr/bin/env python3
"""Secrets-free catalog discovery contracts."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import pala_catalog


class CatalogRedactionTests(unittest.TestCase):
    def test_detected_github_remote_drops_userinfo_before_catalog_export(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pala-catalog-") as temp:
            root = Path(temp)
            git = root / ".git"
            git.mkdir()
            (git / "config").write_text(
                "[remote \"origin\"]\n"
                "    url = https://token:secret@github.com/example/private.git\n",
                encoding="utf-8",
            )

            entry = pala_catalog.entry_from_project(root)

            self.assertEqual(entry["github"], "https://github.com/example/private.git")
            self.assertNotIn("token", str(entry))
            self.assertNotIn("secret", str(entry))


if __name__ == "__main__":
    unittest.main()

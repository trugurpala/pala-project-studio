#!/usr/bin/env python3
"""Contract tests for Pala's bounded remote update check."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "pala_update.py"


def load_module():
    spec = importlib.util.spec_from_file_location("pala_update", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("pala_update.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pala_update = load_module()


class PalaUpdateTests(unittest.TestCase):
    def test_release_check_cache_is_separate_from_installer_update_state(self) -> None:
        self.assertEqual(pala_update.default_cache_path().name, "release-check-cache.json")
        self.assertNotEqual(pala_update.default_cache_path().name, "update-cache.json")

    def test_fresh_cache_skips_network_and_reports_current_state(self) -> None:
        now = datetime(2026, 8, 5, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "update.json"
            pala_update.write_cache(
                cache,
                {
                    "checked_at": now.isoformat(),
                    "installed_version": "0.3.3",
                    "status": "current",
                    "available_version": "0.3.3",
                    "url": None,
                },
            )
            fetch = Mock()
            result = pala_update.check_update(
                "0.3.3", cache, now=now + timedelta(hours=23), fetch=fetch
            )

        self.assertEqual(result["source"], "cache")
        self.assertEqual(result["status"], "current")
        fetch.assert_not_called()

    def test_stale_cache_fetches_once_and_writes_atomic_available_update(self) -> None:
        now = datetime(2026, 8, 5, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "update.json"
            fetch = Mock(
                return_value={
                    "tag_name": "v0.4.0",
                    "html_url": "https://github.com/trugurpala/pala-project-studio/releases/tag/v0.4.0",
                }
            )
            result = pala_update.check_update("0.3.3", cache, now=now, fetch=fetch)
            cached = pala_update.read_cache(cache)

        self.assertEqual(result["source"], "remote")
        self.assertEqual(result["status"], "update-available")
        self.assertEqual(result["available_version"], "0.4.0")
        self.assertEqual(cached["status"], "update-available")
        fetch.assert_called_once()

    def test_network_failure_is_nonblocking_and_secrets_free(self) -> None:
        now = datetime(2026, 8, 5, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "update.json"
            result = pala_update.check_update(
                "0.3.3",
                cache,
                now=now,
                fetch=Mock(side_effect=OSError("network unavailable token=hidden")),
            )

        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("token=hidden", str(result))
        self.assertEqual(result["message"], "remote update check unavailable")


if __name__ == "__main__":
    unittest.main()

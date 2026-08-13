from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pala_semgrep import (
    RULE_PACK,
    SEMGREP_SHA256,
    SEMGREP_VERSION,
    build_scan_command,
    build_wheelhouse_manifest,
    bounded_environment,
    evaluate_findings,
    language_coverage,
    probe_health,
    install_transaction,
    render_requirements_lock,
    semgrep_environment,
    verify_rule_pack,
)
from pala_workbench_bootstrap import _requirements_lock
from pala_quality import build_quality_plan
from pala_semgrep_runner import main as runner_main, sanitized_result


def _fake_wheel(path: Path, name: str, version: str) -> Path:
    normalized = name.replace("-", "_")
    wheel = path / f"{normalized}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            f"{normalized}-{version}.dist-info/METADATA",
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
        )
    return wheel


class SemgrepContractTests(unittest.TestCase):
    def test_quality_runner_sanitizes_provider_output_and_uses_exit_status_contract(self) -> None:
        result = {
            "status": "passed",
            "capability_health": {
                "state": "exact",
                "version": SEMGREP_VERSION,
                "health": "passed",
                "integrity": f"sha256:{SEMGREP_SHA256}",
                "ownership": "pala-project-studio",
                "path": "C:/private/runtime",
            },
            "coverage": {"status": "passed", "project_languages": ["python"]},
            "findings": {"scan_exit_code": 0, "finding_count": 0, "error_count": 0},
            "candidate_check_ids": [],
        }
        sanitized = sanitized_result(result)
        self.assertEqual(sanitized["authority"], "Pala Quality Engine runner candidate")
        self.assertNotIn("path", json.dumps(sanitized))
        with patch("pala_semgrep_runner.run_local_scan", return_value=result):
            self.assertEqual(runner_main(["--project", ".", "--state-root", "C:/Pala"]), 0)
        finding = {
            **result,
            "findings": {"scan_exit_code": 1, "finding_count": 1, "error_count": 0},
        }
        with patch("pala_semgrep_runner.run_local_scan", return_value=finding):
            self.assertEqual(runner_main(["--project", ".", "--state-root", "C:/Pala"]), 1)
        with patch("pala_semgrep_runner.run_local_scan", side_effect=RuntimeError("blocked")):
            self.assertEqual(runner_main(["--project", ".", "--state-root", "C:/Pala"]), 2)

    def test_health_probe_preserves_verified_ownership_integrity_and_provenance(self) -> None:
        runtime = {
            "state": "exact",
            "version": SEMGREP_VERSION,
            "health": "passed",
            "integrity": f"sha256:{SEMGREP_SHA256}",
            "ownership": "pala-project-studio",
            "provenance": "https://example.invalid/semgrep.whl",
            "path": "C:/Pala/semgrep",
            "executable": "C:/Pala/semgrep/semgrep.exe",
        }

        class Result:
            returncode = 0
            stdout = f"{SEMGREP_VERSION}\n"
            stderr = ""

        with patch("pala_semgrep.inventory", return_value=runtime), patch(
            "pala_semgrep.subprocess.run", return_value=Result()
        ):
            result = probe_health(Path("C:/Pala"))

        self.assertEqual(result["integrity"], runtime["integrity"])
        self.assertEqual(result["ownership"], runtime["ownership"])
        self.assertEqual(result["provenance"], runtime["provenance"])

    def test_locked_windows_wheel_contract(self) -> None:
        self.assertEqual(SEMGREP_VERSION, "1.172.0")
        self.assertEqual(
            SEMGREP_SHA256,
            "e32868faeb67b241bbd3fabd82a12fba4b467464dedde9da285b9bf78e808ba3",
        )

    def test_wheelhouse_manifest_and_requirements_are_fully_hash_locked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            semgrep = _fake_wheel(root, "semgrep", "1.172.0")
            _fake_wheel(root, "dependency-one", "2.0.0")
            expected = hashlib.sha256(semgrep.read_bytes()).hexdigest()
            manifest = build_wheelhouse_manifest(root, expected_semgrep_sha=expected)
            lock = render_requirements_lock(manifest)
        self.assertEqual(len(manifest["wheels"]), 2)
        self.assertIn(f"semgrep==1.172.0 --hash=sha256:{expected}", lock)
        self.assertIn("dependency-one==2.0.0 --hash=sha256:", lock)
        self.assertEqual(lock.count("--hash=sha256:"), 2)

    def test_bootstrap_has_an_exact_lock_for_every_supported_python_minor(self) -> None:
        for minor in range(10, 15):
            lock = _requirements_lock(ROOT, (3, minor))
            self.assertEqual(lock.name, f"requirements-win-amd64-cp3{minor}.lock")
            lines = lock.read_text(encoding="utf-8").splitlines()
            self.assertGreaterEqual(len(lines), 60)
            self.assertTrue(all(" --hash=sha256:" in line for line in lines))

    def test_local_rule_pack_is_versioned_and_checksum_locked(self) -> None:
        result = verify_rule_pack(ROOT / RULE_PACK)
        self.assertEqual(result["status"], "passed")
        self.assertGreaterEqual(result["rule_count"], 3)
        self.assertEqual(result["version"], "1.0.0")

    def test_scan_is_local_offline_and_metrics_disabled(self) -> None:
        environment = semgrep_environment(Path("C:/Pala/semgrep-state"))
        self.assertEqual(environment["SEMGREP_SEND_METRICS"], "off")
        self.assertEqual(environment["SEMGREP_ENABLE_VERSION_CHECK"], "0")
        self.assertEqual(environment["OTEL_SDK_DISABLED"], "true")
        scrubbed = bounded_environment(
            Path("C:/Pala/semgrep-state"),
            {"SEMGREP_APP_TOKEN": "secret", "PATH": "fixed"},
        )
        self.assertNotIn("SEMGREP_APP_TOKEN", scrubbed)
        self.assertEqual(scrubbed["PATH"], "fixed")
        command = build_scan_command(
            Path("C:/Pala/semgrep.exe"),
            Path("C:/project"),
            Path("C:/Pala/rules.yml"),
            Path("C:/Pala/result.json"),
        )
        flattened = " ".join(command)
        self.assertIn("--metrics off", flattened)
        self.assertIn("--disable-version-check", flattened)
        config_index = command.index("--config")
        self.assertEqual(command[config_index + 1], str(Path("C:/Pala/rules.yml")))
        self.assertIn("--exclude .tools", flattened)
        for forbidden in ("login", "cloud", "registry", "auto"):
            self.assertNotIn(forbidden, flattened.casefold())

    def test_capability_health_and_project_rule_coverage_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "view.ts").write_text("export const ok = true\n", encoding="utf-8")
            coverage = language_coverage(root, {"python", "javascript", "typescript"})
        self.assertEqual(set(coverage["project_languages"]), {"python", "typescript"})
        self.assertEqual(coverage["uncovered_languages"], [])
        self.assertEqual(coverage["status"], "passed")
        self.assertNotIn("capability_health", coverage)

    def test_bundled_tool_runtime_samples_do_not_become_shipping_language_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "app.py").write_text("print('shipping')\n", encoding="utf-8")
            vendored = root / ".tools" / "python" / "tcl" / "pref"
            vendored.mkdir(parents=True)
            (vendored / "TkWin.cs").write_text("third-party runtime sample\n", encoding="utf-8")
            coverage = language_coverage(root, {"python"})
        self.assertEqual(coverage["project_languages"], ["python"])
        self.assertEqual(coverage["uncovered_languages"], [])
        self.assertEqual(coverage["status"], "passed")

    def test_foreign_active_runtime_is_preserved_without_install_takeover(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = root / "state" / "workbench" / "security_static"
            foreign = base / "versions" / "9.9.0"
            foreign.mkdir(parents=True)
            sentinel = foreign / "owner-data.txt"
            sentinel.write_text("keep", encoding="utf-8")
            active = base / "active.json"
            active.write_text('{"owner":"user","version":"9.9.0"}\n', encoding="utf-8")
            result = install_transaction(
                root / "missing-wheelhouse",
                root / "state",
                root / "missing-rules",
                root / "missing.lock",
            )
            self.assertEqual(result["state"], "foreign")
            self.assertFalse(result["changed"])
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            self.assertEqual(json.loads(active.read_text(encoding="utf-8"))["version"], "9.9.0")

    def test_findings_are_candidates_until_current_quality_runner_maps_them(self) -> None:
        payload = {
            "results": [
                {"check_id": "pala.python.dynamic-eval", "path": "app.py", "start": {"line": 3}}
            ],
            "errors": [],
        }
        advisory = evaluate_findings(payload, scan_exit_code=1)
        self.assertEqual(advisory["finding_count"], 1)
        self.assertEqual(advisory["authority"], "advisory-candidates")
        self.assertFalse(advisory["blocks_acceptance"])
        mapped = evaluate_findings(
            payload,
            scan_exit_code=1,
            quality_check_id="security:semgrep-local",
            quality_runner_status="failed",
        )
        self.assertTrue(mapped["blocks_acceptance"])
        self.assertEqual(mapped["authority"], "Pala Quality Engine")

    def test_venv_is_created_at_final_inactive_path_before_atomic_activation(self) -> None:
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wheelhouse = root / "wheelhouse"
            wheelhouse.mkdir()
            rule_pack = root / "rules"
            rule_pack.mkdir()
            lock = root / "requirements.lock"
            lock.write_text("semgrep==1.172.0 --hash=sha256:abc\n", encoding="utf-8")
            created: list[Path] = []

            def create_venv(path: Path) -> None:
                created.append(path)
                scripts = path / "Scripts"
                scripts.mkdir(parents=True)
                (scripts / "python.exe").write_bytes(b"python")
                (scripts / "semgrep.exe").write_bytes(b"semgrep")

            calls = 0

            def run(_command, _environment, _timeout):
                nonlocal calls
                calls += 1
                result = Result()
                if calls == 2:
                    result.stdout = "1.172.0\n"
                return result

            manifest = {
                "wheels": [
                    {"name": "semgrep", "version": "1.172.0", "sha256": "abc", "filename": "semgrep.whl"}
                ]
            }
            with (
                patch("pala_semgrep.build_wheelhouse_manifest", return_value=manifest),
                patch(
                    "pala_semgrep.verify_rule_pack",
                    return_value={"status": "passed", "version": "1.0.0", "rule_ids": ["pala.test"]},
                ),
            ):
                result = install_transaction(
                    wheelhouse,
                    root / "state",
                    rule_pack,
                    lock,
                    run=run,
                    create_venv=create_venv,
                )

            final = root / "state" / "workbench" / "security_static" / "versions" / "1.172.0"
            self.assertEqual(len(created), 1)
            self.assertEqual(created[0].resolve(), (final / "venv").resolve())
            self.assertEqual(result["state"], "exact")
            self.assertTrue((final / "pala-install.json").is_file())
            self.assertFalse(any("stage" in str(path) for path in created))

    def test_quality_contract_maps_the_real_local_runner(self) -> None:
        plan = build_quality_plan(ROOT, tier="ticket")
        check = next(item for item in plan["checks"] if item["id"] == "security:semgrep-local")
        self.assertEqual(
            check["command"],
            "py -3 scripts/pala_semgrep_runner.py --project .",
        )
        self.assertTrue(check["required"])


if __name__ == "__main__":
    unittest.main()

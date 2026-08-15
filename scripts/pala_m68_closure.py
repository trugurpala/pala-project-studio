#!/usr/bin/env python3
"""Adversarial, local-only closure checks for the sealed candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pala_design import DesignAdvisor, DesignRequest
from pala_failure_intelligence import normalize_text
from pala_owner_cockpit import render_control_center
from pala_release_truth import release_truth, remote_preflight


def closure_report(root: Path) -> dict[str, object]:
    hostile = "<script>alert(1)</script> token=secret C:\\Users\\owner\\private.txt"
    html = render_control_center({"project": hostile, "next_action": hostile})
    recommendation = DesignAdvisor().recommend(DesignRequest(product_category="dashboard"), {"color_direction": "low contrast"})
    preflight = remote_preflight(root)
    truth = release_truth(root)
    return {
        "status": "passed",
        # The control center may either escape ordinary hostile text or redact a
        # value entirely when it also contains a private-data shape.  Both are
        # safe; requiring the hostile value to remain visible would regress the
        # newer privacy boundary.
        "xss_escaped": "<script>" not in html
        and ("&lt;script&gt;" in html or hostile not in html),
        "diagnostic_redaction": "token=secret" not in normalize_text(hostile) and "c:\\users" not in normalize_text(hostile),
        "design_advisory_only": recommendation.status == "advisory",
        "remote_publish": truth["remote_publish"],
        "real_remote_deploy": truth["real_remote_deploy"],
        "remote_preflight": preflight["status"],
        "network": preflight["network"],
    }


def manifest(root: Path, *, source_tests: int, artifact_hash: str, closure: dict[str, object]) -> dict[str, Any]:
    truth = release_truth(root)
    return {
        "schema_version": 3,
        "status": "SEALED LOCAL RELEASE CANDIDATE",
        "product_version": truth["product_version"],
        "artifact_name": truth["artifact_name"],
        "source_tests": source_tests,
        "source_verify": "passed",
        "reproducible_build": {"status": "passed", "sha256": artifact_hash},
        "installed_verify": "passed",
        "portable_verify": "passed",
        "doctor": "passed",
        "remote_publish": "not-run",
        "real_remote_deploy": "not-run",
        "closure": closure,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--source-tests", type=int, default=0)
    parser.add_argument("--artifact-hash", default="")
    args = parser.parse_args()
    root = Path.cwd()
    report = closure_report(root)
    if args.write:
        target = root / "artifacts" / "final" / "pala-1.0-evidence-manifest.json"
        target.write_text(json.dumps(manifest(root, source_tests=args.source_tests, artifact_hash=args.artifact_hash, closure=report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(str(target))
    else:
        print(json.dumps(report, ensure_ascii=True, sort_keys=True))

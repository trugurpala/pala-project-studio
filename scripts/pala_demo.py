#!/usr/bin/env python3
"""Seed the fork-ready demo project into a local Pala catalog (M21)."""

from __future__ import annotations

import argparse
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pala_catalog
import pala_db

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DEMO_ROOT = PLUGIN_ROOT / "examples" / "demo-software-project"

REQUIRED_RELATIVE = (
    "AGENTS.md",
    "PROJECT.md",
    "PLAN.md",
    "STATUS.md",
    "PROGRESS.md",
    "DECISIONS.md",
    "TOOLING_DECISIONS.md",
    "DEBUGGING.md",
    Path(".codex") / "pala-project.json",
    Path(".codex") / "pala-workflow.json",
)


def validate_demo_root(demo_root: Path) -> None:
    if not demo_root.is_dir():
        raise ValueError(f"demo root is not a directory: {demo_root}")
    missing = [str(rel) for rel in REQUIRED_RELATIVE if not (demo_root / rel).is_file()]
    if missing:
        raise ValueError("demo fixture incomplete: " + ", ".join(missing))


def _workflow(demo_root: Path) -> dict[str, object]:
    payload = json.loads(
        (demo_root / ".codex" / "pala-workflow.json").read_text(encoding="utf-8")
    )
    if not isinstance(payload, dict):
        raise ValueError("pala-workflow.json must be an object")
    return payload


def seed(*, demo_root: Path, catalog_root: Path) -> dict[str, object]:
    """Write project row, three timeline events, and one sample provision."""
    demo_root = demo_root.resolve()
    catalog_root = catalog_root.resolve()
    validate_demo_root(demo_root)
    catalog_root.mkdir(parents=True, exist_ok=True)

    workflow = _workflow(demo_root)
    active = str(workflow.get("active_ticket") or "").strip() or "DEMO-003"
    next_action = str(workflow.get("next_action") or "").strip()
    if not next_action:
        next_action = f"Continue {active}"

    stored = pala_catalog.upsert_project(
        demo_root,
        catalog_dir=catalog_root,
        phase="M2 — Status surface demo",
        quality_result="unit=passed; status=not-run",
        tools_summary="demo seed",
        next_action=f"{active}: {next_action}",
        blockers=[],
    )
    db = pala_db.db_path_for(catalog_root)
    project_id = str(stored.get("id") or "")
    project_name = str(stored.get("name") or demo_root.name)

    events = (
        ("register", "Demo memory documents registered", "fixture=examples/demo-software-project"),
        ("begin", f"Began {active}", f"ticket={active}"),
        (
            "checkpoint",
            "Checkpoint before Status panel confirmation",
            "unit=passed; status=not-run",
        ),
    )
    written = 0
    for kind, detail, evidence in events:
        pala_db.add_event(
            kind,
            project_id=project_id,
            project_name=project_name,
            detail=detail,
            evidence=evidence,
            path=db,
        )
        written += 1

    provision = pala_db.upsert_provision(
        source_url="https://example.invalid/pala-demo-pack",
        install_path=str(demo_root),
        status="demo-seeded",
        pala_version="0.8.0-demo",
        registered=True,
        path=db,
    )

    return {
        "status": "passed",
        "demo_root": str(demo_root),
        "catalog_root": str(catalog_root),
        "db_path": str(db),
        "events_written": written,
        "project": {
            "id": project_id,
            "name": project_name,
            "active_ticket": active,
            "next_action": next_action,
            "path": stored.get("path"),
        },
        "provision_id": provision.get("id"),
    }


def prove_status_html(*, demo_root: Path, catalog_root: Path) -> dict[str, object]:
    """Seed demo then prove Status HTML shows ticket + timeline (DEMO-003/004)."""
    import pala_report

    seeded = seed(demo_root=demo_root, catalog_root=catalog_root)
    active = str((seeded.get("project") or {}).get("active_ticket") or "").strip()
    if not active:
        active = "DEMO-003"
    markup = pala_report.render_html(
        demo_root.resolve(),
        catalog_root=catalog_root.resolve(),
        update={"status": "current", "installed_version": "0.8.0-demo"},
    )
    missing: list[str] = []
    if "Şimdi:" not in markup:
        missing.append("Şimdi")
    if active not in markup:
        missing.append(active)
    for label in ("kayit", "basla", "checkpoint"):
        if label not in markup:
            missing.append(label)
    if "Hata beyni" not in markup:
        missing.append("Hata beyni")
    if missing:
        return {
            "status": "failed",
            "error": "status html missing: " + ", ".join(missing),
            "seed": seeded,
            "html": markup,
        }
    return {
        "status": "passed",
        "seed": seeded,
        "html": markup,
        "events_written": seeded.get("events_written"),
        "active_ticket": active,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    seed_parser = sub.add_parser("seed", help="Seed demo project into a catalog root")
    seed_parser.add_argument(
        "--demo-root",
        type=Path,
        default=DEFAULT_DEMO_ROOT,
        help="Path to examples/demo-software-project",
    )
    seed_parser.add_argument(
        "--catalog-root",
        type=Path,
        default=None,
        help="Catalog directory (default: Desktop/Codex or PALA_CATALOG_ROOT)",
    )
    return result


def run_cli(argv: list[str] | None = None) -> tuple[int, str]:
    args = parser().parse_args(argv)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        if args.command == "seed":
            catalog = args.catalog_root or pala_db.catalog_root()
            try:
                payload = seed(demo_root=args.demo_root, catalog_root=catalog)
            except ValueError as exc:
                print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False))
                return 2, buffer.getvalue()
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0, buffer.getvalue()
    return 2, buffer.getvalue()


def main(argv: list[str] | None = None) -> int:
    code, payload = run_cli(argv)
    sys.stdout.write(payload)
    return code


if __name__ == "__main__":
    raise SystemExit(main())

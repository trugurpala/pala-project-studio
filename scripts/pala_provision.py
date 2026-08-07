#!/usr/bin/env python3
"""Clone or refresh a git HTTPS repo and record it in Pala's local registry."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

SCHEMA_VERSION = 1
REGISTRY_NAME = "provision-registry.json"
SHELL_META = re.compile(r"[;|&`$()<>\\\"'\n\r\t]")
ALLOWED_HOST_HINTS = (
    "github.com",
    "gitlab.com",
    "bitbucket.org",
    "codeberg.org",
    "git.",
)
RunFn = Callable[..., subprocess.CompletedProcess[str]]


def default_parent() -> Path:
    return Path.home() / "Desktop" / "Cursor"


def default_registry_path() -> Path:
    override = os.environ.get("PALA_PROVISION_REGISTRY")
    if override:
        return Path(override)
    profile = Path(os.environ.get("USERPROFILE", Path.home()))
    local = Path(os.environ.get("LOCALAPPDATA", profile / "AppData" / "Local"))
    return local / "Pala" / REGISTRY_NAME


def pala_version() -> str:
    plugin = Path(__file__).resolve().parent.parent / ".codex-plugin" / "plugin.json"
    try:
        payload = json.loads(plugin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown"
    version = payload.get("version")
    return str(version) if version else "unknown"


def validate_git_https_url(url: str) -> str:
    """Accept only https git-like URLs; reject file:// and shell metacharacters."""
    raw = (url or "").strip()
    if not raw:
        raise ValueError("url is required")
    if SHELL_META.search(raw):
        raise ValueError("url contains unsafe shell metacharacters")
    if raw.casefold().startswith("file:"):
        raise ValueError("file:// URLs are not allowed")
    parsed = urlparse(raw)
    if parsed.scheme.casefold() != "https":
        raise ValueError("only https:// git URLs are allowed")
    if not parsed.netloc or not parsed.path or parsed.path in ("/", ""):
        raise ValueError("url must include host and repository path")
    host = parsed.netloc.casefold()
    path = parsed.path
    looks_git = (
        path.casefold().endswith(".git")
        or any(hint in host for hint in ALLOWED_HOST_HINTS)
        or path.count("/") >= 2
    )
    if not looks_git:
        raise ValueError("url does not look like a git repository HTTPS URL")
    return raw.rstrip("/")


def folder_name_from_url(url: str, override: str | None = None) -> str:
    if override:
        name = override.strip()
        if not name or SHELL_META.search(name) or "/" in name or "\\" in name:
            raise ValueError("invalid --name folder")
        if name in (".", ".."):
            raise ValueError("invalid --name folder")
        return name
    path = urlparse(url).path.rstrip("/")
    leaf = path.rsplit("/", 1)[-1]
    if leaf.casefold().endswith(".git"):
        leaf = leaf[:-4]
    leaf = re.sub(r"[^a-zA-Z0-9._-]+", "-", leaf).strip("-._")
    if not leaf:
        raise ValueError("could not derive folder name from url")
    return leaf


def _load_registry(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "installs": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": SCHEMA_VERSION, "installs": []}
    if not isinstance(payload, dict):
        return {"schema_version": SCHEMA_VERSION, "installs": []}
    installs = payload.get("installs")
    if not isinstance(installs, list):
        installs = []
    return {"schema_version": SCHEMA_VERSION, "installs": installs}


def _write_registry(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def upsert_registry(
    *,
    registry_path: Path,
    source_url: str,
    installed_path: Path,
    status: str,
    version: str | None = None,
) -> dict[str, object]:
    payload = _load_registry(registry_path)
    installs = list(payload.get("installs", []))
    entry = {
        "source_url": source_url,
        "installed_path": str(installed_path.resolve()),
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "pala_version": version or pala_version(),
        "last_status": status[:80],
    }
    replaced = False
    target = str(installed_path.resolve())
    for idx, existing in enumerate(installs):
        if not isinstance(existing, dict):
            continue
        if existing.get("installed_path") == target or existing.get("source_url") == source_url:
            merged = dict(existing)
            merged.update(entry)
            installs[idx] = merged
            entry = merged
            replaced = True
            break
    if not replaced:
        installs.append(entry)
    out = {"schema_version": SCHEMA_VERSION, "installs": installs}
    _write_registry(registry_path, out)
    return entry


def run_git(
    args: list[str],
    *,
    cwd: Path | None = None,
    runner: RunFn | None = None,
) -> subprocess.CompletedProcess[str]:
    run = runner or subprocess.run
    return run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def clone_or_fetch(
    url: str,
    dest: Path,
    *,
    dry_run: bool = False,
    runner: RunFn | None = None,
) -> dict[str, object]:
    """Clone if missing; if present, fetch only (no destructive reset)."""
    if dry_run:
        action = "would_fetch" if dest.exists() else "would_clone"
        return {"action": action, "path": str(dest), "ok": True, "detail": "dry-run"}
    if dest.exists():
        if not (dest / ".git").exists():
            return {
                "action": "error",
                "path": str(dest),
                "ok": False,
                "detail": "destination exists but is not a git repository",
            }
        result = run_git(["fetch", "--prune"], cwd=dest, runner=runner)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "git fetch failed").strip()[:300]
            return {"action": "fetch", "path": str(dest), "ok": False, "detail": detail}
        return {"action": "fetch", "path": str(dest), "ok": True, "detail": "fetched"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = run_git(["clone", url, str(dest)], runner=runner)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "git clone failed").strip()[:300]
        return {"action": "clone", "path": str(dest), "ok": False, "detail": detail}
    return {"action": "clone", "path": str(dest), "ok": True, "detail": "cloned"}


def maybe_register(root: Path, *, enabled: bool, dry_run: bool) -> dict[str, object]:
    if not enabled:
        return {"attempted": False, "ok": True, "detail": "skipped"}
    if dry_run:
        return {"attempted": True, "ok": True, "detail": "would_register"}
    from pala_state import register as state_register

    args = Namespace(
        instructions=None,
        project=None,
        plan=None,
        status=None,
        progress=None,
        tooling=None,
        debugging=None,
        decisions=None,
        open_source=None,
        demo=None,
    )
    code = state_register(args, root)
    if code == 0:
        return {"attempted": True, "ok": True, "detail": "registered"}
    return {"attempted": True, "ok": False, "detail": f"register_exit_{code}"}


def turkish_summary(report: dict[str, object]) -> str:
    lines = [
        "Pala iç kurulum (provision)",
        "===========================",
        f"URL: {report.get('source_url')}",
        f"Hedef: {report.get('installed_path')}",
        f"Git işlemi: {report.get('git_action')} ({report.get('git_detail')})",
        f"Durum: {report.get('last_status')}",
        f"Kayıt (--register): {report.get('register_detail')}",
        f"Katalog: {report.get('catalog_path')}",
        f"Yerel kayıt: {report.get('registry_path')}",
    ]
    if report.get("dry_run"):
        lines.append("Not: dry-run — dosya/git yazılmadı.")
    lines.append("")
    return "\n".join(lines)


def provision(
    *,
    url: str,
    parent: Path,
    name: str | None = None,
    register: bool = False,
    dry_run: bool = False,
    catalog_root: Path | None = None,
    registry_path: Path | None = None,
    runner: RunFn | None = None,
) -> dict[str, object]:
    safe_url = validate_git_https_url(url)
    folder = folder_name_from_url(safe_url, name)
    dest = (parent / folder).resolve()
    reg_path = registry_path or default_registry_path()

    git_result = clone_or_fetch(safe_url, dest, dry_run=dry_run, runner=runner)
    register_result = {"attempted": False, "ok": True, "detail": "skipped"}
    catalog_entry: dict[str, object] | None = None
    catalog_file = ""
    status = "dry-run" if dry_run else ("error" if not git_result["ok"] else git_result["action"])

    if git_result["ok"] and not dry_run:
        register_result = maybe_register(dest, enabled=register, dry_run=False)
        if register and not register_result["ok"]:
            status = "provisioned_register_failed"
        elif git_result["action"] == "clone":
            status = "provisioned"
        else:
            status = "fetched"

        from pala_catalog import catalog_path, upsert_project

        cdir = catalog_root
        catalog_entry = upsert_project(
            dest,
            catalog_dir=cdir,
            phase="provisioned",
            next_action="Install-Pala Doctor veya pala_state register/begin",
            tools_summary="provision",
        )
        catalog_file = str(catalog_path(cdir))
        upsert_registry(
            registry_path=reg_path,
            source_url=safe_url,
            installed_path=dest,
            status=status,
        )
    elif dry_run:
        status = "dry-run"
        register_result = maybe_register(dest, enabled=register, dry_run=True)
        from pala_catalog import catalog_path

        catalog_file = str(catalog_path(catalog_root))
    else:
        if not dry_run:
            upsert_registry(
                registry_path=reg_path,
                source_url=safe_url,
                installed_path=dest,
                status="error",
            )

    report: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "source_url": safe_url,
        "installed_path": str(dest),
        "git_action": git_result.get("action"),
        "git_detail": git_result.get("detail"),
        "git_ok": bool(git_result.get("ok")),
        "last_status": status,
        "register_detail": register_result.get("detail"),
        "register_ok": bool(register_result.get("ok")),
        "catalog_path": catalog_file,
        "catalog_entry": catalog_entry,
        "registry_path": str(reg_path),
        "pala_version": pala_version(),
        "dry_run": dry_run,
    }
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="URL ver → yerel klasöre clone/fetch → Pala katalog + kayıt"
    )
    result.add_argument(
        "command",
        nargs="?",
        default="provision",
        choices=("provision",),
        help="Yalnız 'provision' komutu (varsayılan)",
    )
    result.add_argument("--url", required=True, help="HTTPS git URL")
    result.add_argument(
        "--parent",
        default=str(default_parent()),
        help="Üst klasör (varsayılan: Desktop/Cursor)",
    )
    result.add_argument("--name", default="", help="Klasör adı (URL'den türetilir)")
    result.add_argument(
        "--register",
        action="store_true",
        help="Clone sonrası pala_state.register (stub'larla)",
    )
    result.add_argument("--dry-run", action="store_true", help="Yazmadan önizle")
    result.add_argument(
        "--catalog-root",
        default="",
        help="pala-catalog.json kökü (yoksa PALA_CATALOG_ROOT / Desktop/Codex)",
    )
    result.add_argument(
        "--registry",
        default="",
        help="provision-registry.json yolu (yoksa %%LOCALAPPDATA%%/Pala/)",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = provision(
            url=args.url,
            parent=Path(args.parent),
            name=args.name or None,
            register=bool(args.register),
            dry_run=bool(args.dry_run),
            catalog_root=Path(args.catalog_root) if args.catalog_root else None,
            registry_path=Path(args.registry) if args.registry else None,
        )
    except ValueError as exc:
        print(f"Hata: {exc}", file=sys.stderr)
        return 2
    print(turkish_summary(report), end="")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report.get("git_ok") and not report.get("dry_run"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

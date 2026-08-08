#!/usr/bin/env python3
"""Failed command / path memory guard (M29-T2).

Records tool attempts in SQLite, surfaces prior resolutions, and blocks
blind retries of the same failure_class + command_family + environment.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

FAILURE_CLASSES = (
    "wrong_plugin_script_path",
    "tool_not_found",
    "trusted_repo",
    "browser_unavailable",
    "permission_policy",
    "no_network",
    "timeout_hook",
)

_SCRIPT_PATH_HINTS = (
    "../../scripts/",
    "..\\..\\scripts\\",
    "scripts/pala_",
    "pala_report.py",
    "pala_state.py",
    "file not found",
    "cannot find the path",
    "no such file",
)


def normalize_command_family(command: str) -> str:
    """Collapse a command line to a stable family token."""
    text = (command or "").strip().casefold()
    if not text:
        return "unknown"
    # Drop python launcher noise.
    text = re.sub(r"^(py\s+-3|python(?:3)?|python\.exe)\s+", "", text)
    text = text.replace("\\", "/")
    # Relative ../../scripts/... → script basename family.
    match = re.search(r"(pala_[a-z0-9_]+\.py)", text)
    if match:
        return match.group(1)
    # First token path basename.
    first = text.split()[0]
    name = Path(first).name
    return name[:120] if name else "unknown"


def detect_environment(
    *,
    os_name: str | None = None,
    shell: str | None = None,
    profile: str | None = None,
) -> dict[str, str]:
    return {
        "os": (os_name or platform.system() or "unknown")[:40],
        "shell": (shell or os.environ.get("COMSPEC") or os.environ.get("SHELL") or "unknown")[
            :40
        ],
        "profile": (profile or os.environ.get("PALA_PROFILE") or "default")[:80],
    }


def classify_failure(
    *,
    command: str = "",
    stderr: str = "",
    exit_code: int = 1,
    hint: str | None = None,
) -> str:
    """Map a failed run to a closed failure_class set."""
    if hint and hint in FAILURE_CLASSES:
        return hint
    blob = f"{command}\n{stderr}".casefold()
    if any(token in blob for token in ("../../scripts", "..\\..\\scripts")):
        return "wrong_plugin_script_path"
    if "trusted" in blob and "repo" in blob:
        return "trusted_repo"
    if "browser" in blob and ("unavailable" in blob or "not found" in blob):
        return "browser_unavailable"
    if "permission" in blob or "access is denied" in blob or "eacces" in blob:
        return "permission_policy"
    if "network" in blob or "offline" in blob or "nameresolution" in blob:
        return "no_network"
    if "timeout" in blob and "hook" in blob:
        return "timeout_hook"
    if any(token in blob for token in _SCRIPT_PATH_HINTS) and (
        "not found" in blob or "no such file" in blob or exit_code != 0
    ):
        if "pala_" in blob or "scripts" in blob:
            return "wrong_plugin_script_path"
        return "tool_not_found"
    if "not found" in blob or "is not recognized" in blob:
        return "tool_not_found"
    return "tool_not_found"


def default_resolution(failure_class: str, command_family: str) -> str:
    if failure_class == "wrong_plugin_script_path":
        return (
            "Use plugin-root launcher (pala_paths / PALA_SCRIPTS_DIR / "
            r"%LOCALAPPDATA%\Pala\marketplace\scripts); never ../../scripts from cwd"
        )
    if failure_class == "tool_not_found":
        return f"Resolve {command_family} via PATH or Pala marketplace scripts dir"
    if failure_class == "trusted_repo":
        return "Trust the repo in Codex /hooks UI before re-running hooks"
    if failure_class == "browser_unavailable":
        return "Skip browser proof; record configured-not-verified"
    if failure_class == "permission_policy":
        return "Stop; request explicit authority for the blocked path"
    if failure_class == "no_network":
        return "Stay offline-safe; do not invent remote success"
    if failure_class == "timeout_hook":
        return "Do not auto-retry hooks; shorten SessionStart work"
    return "Read DEBUGGING.md; do not blind-retry"


def _db_path() -> Path | None:
    try:
        import pala_db

        return pala_db.default_db_path()
    except Exception:
        return None


def record_failure(
    *,
    command: str,
    exit_code: int = 1,
    stderr: str = "",
    cwd: str = "",
    failure_class: str | None = None,
    resolution: str = "",
    fallback: str = "",
    scope: str = "session",
    project_id: str = "",
    os_name: str | None = None,
    shell: str | None = None,
    profile: str | None = None,
    path: Path | None = None,
    mirror_event: bool = True,
) -> dict[str, object]:
    """Persist a failed attempt and return the stored row + guard metadata."""
    import pala_db

    env = detect_environment(os_name=os_name, shell=shell, profile=profile)
    family = normalize_command_family(command)
    klass = classify_failure(
        command=command, stderr=stderr, exit_code=exit_code, hint=failure_class
    )
    prior = pala_db.find_tool_attempt(
        failure_class=klass,
        command_family=family,
        os_name=env["os"],
        shell=env["shell"],
        profile=env["profile"],
        path=path,
    )
    reso = (resolution or "").strip() or (
        str(prior.get("resolution") or "") if prior else ""
    ) or default_resolution(klass, family)
    fall = (fallback or "").strip() or (
        str(prior.get("fallback") or "") if prior else ""
    )
    row = pala_db.upsert_tool_attempt(
        command_family=family,
        failure_class=klass,
        cwd=cwd,
        os_name=env["os"],
        shell=env["shell"],
        profile=env["profile"],
        exit_code=exit_code,
        resolution=reso,
        fallback=fall,
        scope=scope,
        freshness="repeat" if prior else "fresh",
        project_id=project_id,
        path=path,
    )
    if mirror_event:
        try:
            pala_db.add_event(
                "tool_attempt",
                project_id=project_id,
                detail=f"{klass}:{family} exit={exit_code} n={row.get('repeat_count')}"[
                    :300
                ],
                evidence=(reso or fall)[:500],
                path=path,
            )
        except (OSError, ValueError, TypeError):
            pass
    return {
        "attempt": row,
        "is_repeat": bool(prior) or int(row.get("repeat_count") or 1) > 1,
        "prior_resolution": reso,
        "failure_class": klass,
        "command_family": family,
    }


def guard_retry(
    *,
    command: str,
    failure_class: str | None = None,
    stderr: str = "",
    approve_retry: bool = False,
    os_name: str | None = None,
    shell: str | None = None,
    profile: str | None = None,
    path: Path | None = None,
) -> dict[str, object]:
    """Block blind retries of the same failure signature unless approved."""
    import pala_db

    env = detect_environment(os_name=os_name, shell=shell, profile=profile)
    family = normalize_command_family(command)
    klass = classify_failure(
        command=command, stderr=stderr, exit_code=1, hint=failure_class
    )
    prior = pala_db.find_tool_attempt(
        failure_class=klass,
        command_family=family,
        os_name=env["os"],
        shell=env["shell"],
        profile=env["profile"],
        path=path,
    )
    if prior is None:
        return {
            "allowed": True,
            "do_not_retry": False,
            "require_approval": False,
            "prior": None,
            "message": "",
            "failure_class": klass,
            "command_family": family,
        }
    resolution = str(prior.get("resolution") or default_resolution(klass, family))
    if approve_retry:
        return {
            "allowed": True,
            "do_not_retry": True,
            "require_approval": False,
            "prior": prior,
            "message": f"approved retry after prior {klass}: {resolution}",
            "failure_class": klass,
            "command_family": family,
        }
    return {
        "allowed": False,
        "do_not_retry": True,
        "require_approval": True,
        "prior": prior,
        "message": (
            f"do not retry {klass}/{family}: prior resolution — {resolution}. "
            "Pass --approve-retry to override."
        ),
        "failure_class": klass,
        "command_family": family,
    }


def append_debugging_summary(
    root: Path,
    *,
    failure_class: str,
    command_family: str,
    resolution: str,
    documents: dict[str, object] | None = None,
) -> Path | None:
    """Append a short human summary so agents see the guard in DEBUGGING.md."""
    docs = documents if isinstance(documents, dict) else {}
    rel = docs.get("debugging") if isinstance(docs.get("debugging"), str) else None
    path = root / (rel or "DEBUGGING.md")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    line = (
        f"- {stamp}: do not retry `{failure_class}` / `{command_family}` — "
        f"prior: {resolution[:180]}"
    )
    try:
        if path.is_file():
            text = path.read_text(encoding="utf-8")
        else:
            text = (
                "# Debugging log\n\n"
                "## Format\n\n"
                "See Pala DEBUGGING contract.\n\n"
                "## Incidents\n\n"
            )
        marker = "## Command memory"
        if marker not in text:
            if not text.endswith("\n"):
                text += "\n"
            text += f"\n{marker}\n\n{line}\n"
        else:
            # Avoid duplicate identical lines.
            if line in text:
                return path
            text = text.rstrip() + f"\n{line}\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path
    except OSError:
        return None


def active_blocks(
    *,
    limit: int = 5,
    path: Path | None = None,
) -> list[dict[str, object]]:
    """Recent failure memories that should suppress blind retries."""
    import pala_db

    rows = pala_db.list_tool_attempts(limit=limit, path=path)
    return [
        {
            "failure_class": row.get("failure_class"),
            "command_family": row.get("command_family"),
            "resolution": row.get("resolution"),
            "repeat_count": row.get("repeat_count"),
            "do_not_retry": True,
        }
        for row in rows
        if int(row.get("repeat_count") or 0) >= 1
    ]


def context_packet_hint(
    *,
    limit: int = 3,
    path: Path | None = None,
    max_len: int = 160,
) -> str | None:
    """Compact do-not-retry line for context / SessionStart (token-light)."""
    blocks = active_blocks(limit=limit, path=path)
    if not blocks:
        return None
    parts = []
    for item in blocks[:limit]:
        klass = item.get("failure_class") or "?"
        family = item.get("command_family") or "?"
        parts.append(f"{klass}/{family}")
    message = "do not retry: " + "; ".join(parts)
    if len(message) > max_len:
        message = message[: max_len - 3] + "..."
    return message


def remember_and_guard(
    *,
    root: Path,
    command: str,
    exit_code: int = 1,
    stderr: str = "",
    failure_class: str | None = None,
    approve_retry: bool = False,
    documents: dict[str, object] | None = None,
    path: Path | None = None,
) -> dict[str, object]:
    """High-level API: block repeats; on first failure record + DEBUGGING note."""
    decision = guard_retry(
        command=command,
        failure_class=failure_class,
        stderr=stderr,
        approve_retry=approve_retry,
        path=path,
    )
    if not decision.get("allowed"):
        prior = decision.get("prior") if isinstance(decision.get("prior"), dict) else {}
        return {
            **decision,
            "recorded": False,
            "attempt": prior,
            "hint": context_packet_hint(path=path),
        }
    recorded = record_failure(
        command=command,
        exit_code=exit_code,
        stderr=stderr,
        cwd=str(root),
        failure_class=failure_class or str(decision.get("failure_class") or ""),
        path=path,
    )
    append_debugging_summary(
        root,
        failure_class=str(recorded.get("failure_class") or ""),
        command_family=str(recorded.get("command_family") or ""),
        resolution=str(recorded.get("prior_resolution") or ""),
        documents=documents,
    )
    return {
        "allowed": True,
        "do_not_retry": True,
        "require_approval": True,
        "recorded": True,
        "attempt": recorded.get("attempt"),
        "prior_resolution": recorded.get("prior_resolution"),
        "failure_class": recorded.get("failure_class"),
        "command_family": recorded.get("command_family"),
        "message": str(recorded.get("prior_resolution") or ""),
        "hint": context_packet_hint(path=path),
        "prior": decision.get("prior"),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record", help="Record a failed command attempt")
    record.add_argument("--cmd", required=True)
    record.add_argument("--exit-code", type=int, default=1)
    record.add_argument("--stderr", default="")
    record.add_argument("--cwd", default=".")
    record.add_argument("--failure-class", choices=FAILURE_CLASSES)
    record.add_argument("--resolution", default="")
    record.add_argument("--fallback", default="")
    record.add_argument("--approve-retry", action="store_true")
    record.add_argument("--json", action="store_true")
    guard = sub.add_parser("guard", help="Check whether a retry is allowed")
    guard.add_argument("--cmd", required=True)
    guard.add_argument("--failure-class", choices=FAILURE_CLASSES)
    guard.add_argument("--stderr", default="")
    guard.add_argument("--approve-retry", action="store_true")
    guard.add_argument("--json", action="store_true")
    hint = sub.add_parser("hint", help="Emit compact do-not-retry hint")
    hint.add_argument("--json", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "hint":
        text = context_packet_hint()
        if args.json:
            print(json.dumps({"hint": text, "blocks": active_blocks()}, ensure_ascii=False))
        else:
            print(text or "")
        return 0
    if args.command == "guard":
        decision = guard_retry(
            command=args.cmd,
            failure_class=args.failure_class,
            stderr=args.stderr,
            approve_retry=args.approve_retry,
        )
        if args.json:
            print(json.dumps(decision, ensure_ascii=False, indent=2))
        else:
            print(decision.get("message") or ("allowed" if decision.get("allowed") else "blocked"))
        return 0 if decision.get("allowed") else 2
    if args.command == "record":
        root = Path(args.cwd).resolve()
        decision = guard_retry(
            command=args.cmd,
            failure_class=args.failure_class,
            stderr=args.stderr,
            approve_retry=args.approve_retry,
        )
        if not decision.get("allowed"):
            if args.json:
                print(json.dumps(decision, ensure_ascii=False, indent=2))
            else:
                print(str(decision.get("message") or "blocked"), file=sys.stderr)
            return 2
        recorded = record_failure(
            command=args.cmd,
            exit_code=args.exit_code,
            stderr=args.stderr,
            cwd=str(root),
            failure_class=args.failure_class,
            resolution=args.resolution,
            fallback=args.fallback,
        )
        append_debugging_summary(
            root,
            failure_class=str(recorded.get("failure_class") or ""),
            command_family=str(recorded.get("command_family") or ""),
            resolution=str(recorded.get("prior_resolution") or ""),
        )
        payload = {**recorded, "hint": context_packet_hint()}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(
                f"recorded {payload.get('failure_class')}/{payload.get('command_family')} "
                f"n={payload.get('attempt', {}).get('repeat_count')}"
            )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

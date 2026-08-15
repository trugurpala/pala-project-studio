#!/usr/bin/env python3
"""CLI ownership for Pala state commands."""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

import pala_state_core as core
import pala_state_documents as documents

class _PalaArgumentParser(argparse.ArgumentParser):
    """Turkish-friendly errors for required begin --goal (and related) flags."""

    def error(self, message: str) -> None:  # type: ignore[override]
        text = str(message or "")
        lowered = text.casefold()
        if "--goal" in lowered or (
            "goal" in lowered and ("required" in lowered or "zorunlu" in lowered)
        ):
            text = (
                'begin iÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â§in --goal zorunlu. '
                'ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“rnek: begin --ticket T1 --goal "tek sonraki iÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸"'
            )
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {text}\n")


def parser() -> argparse.ArgumentParser:
    result = _PalaArgumentParser(description=__doc__)
    subparsers = result.add_subparsers(
        dest="command", required=True, parser_class=_PalaArgumentParser
    )
    for command in ("discover", "validate", "instructions", "context", "memory"):
        child = subparsers.add_parser(command)
        child.add_argument("--cwd", default=".")
        if command == "context":
            child.add_argument("--session-key")
        if command == "memory":
            child.add_argument("--session-key")
    register_parser = subparsers.add_parser("register")
    register_parser.add_argument("--cwd", default=".")
    register_parser.add_argument("--instructions")
    register_parser.add_argument("--project")
    register_parser.add_argument("--plan")
    register_parser.add_argument("--status")
    register_parser.add_argument("--decisions")
    register_parser.add_argument("--open-source", dest="open_source")
    register_parser.add_argument("--demo")
    register_parser.add_argument(
        "--project-profile",
        help="Repository-relative ProjectProfile v1 JSON source",
    )
    begin_parser = subparsers.add_parser(
        "begin",
        help="Start a ticket; --goal zorunlu",
    )
    begin_parser.add_argument("--cwd", default=".")
    begin_parser.add_argument("--ticket", required=True)
    begin_parser.add_argument(
        "--goal",
        required=True,
        help='Zorunlu hedef. ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“rnek: begin --ticket T1 --goal "tek sonraki iÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€¦Ã‚Â¸"',
    )
    begin_parser.add_argument("--session-key")
    begin_parser.add_argument(
        "--acceptance", action="append", default=[],
        help="Repeatable structured acceptance criterion; required for authoritative completion",
    )
    checkpoint_parser = subparsers.add_parser("checkpoint")
    checkpoint_parser.add_argument("--cwd", default=".")
    checkpoint_parser.add_argument("--next-action", required=True)
    checkpoint_parser.add_argument("--verification", action="append", default=[])
    checkpoint_parser.add_argument("--blocker", action="append", default=[])
    checkpoint_parser.add_argument("--session-key")
    checkpoint_parser.add_argument("--ticket")
    checkpoint_parser.add_argument(
        "--quality-ticket",
        help="Quality ledger'i passed olmadan bu checkpoint'i passed sayma",
    )
    checkpoint_parser.add_argument(
        "--tier", choices=core.VERIFICATION_TIERS, default="ticket"
    )
    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--cwd", default=".")
    doctor_parser.add_argument("--session-key")
    verification_parser = subparsers.add_parser("record-verification")
    verification_parser.add_argument("--cwd", default=".")
    verification_parser.add_argument("--ticket", required=True)
    verification_parser.add_argument("--session-key", required=True)
    verification_parser.add_argument("--status", required=True)
    verification_parser.add_argument("--command", dest="verification_command", required=True)
    verification_parser.add_argument("--error", default="")
    for command in ("recover", "complete"):
        child = subparsers.add_parser(command)
        child.add_argument("--cwd", default=".")
        child.add_argument("--ticket", required=True)
        child.add_argument("--session-key", required=True)
        if command == "complete":
            child.add_argument(
                "--quality-ticket",
                help="Bu ticket icin quality ledger passed olmadan complete yapma",
            )
    close_parser = subparsers.add_parser("close-project")
    close_parser.add_argument("--cwd", default=".")
    close_parser.add_argument("--ticket", required=True)
    close_parser.add_argument("--summary", required=True)
    close_parser.add_argument("--final-commit", required=True)
    close_parser.add_argument("--release-ref")
    close_parser.add_argument("--risk-code", action="append", default=[])
    close_parser.add_argument("--lesson", action="append", default=[])
    close_parser.add_argument("--authority-ref", required=True)
    reopen_parser = subparsers.add_parser("reopen-project")
    reopen_parser.add_argument("--cwd", default=".")
    reopen_parser.add_argument("--ticket", required=True)
    reopen_parser.add_argument("--closure-id", required=True)
    reopen_parser.add_argument("--authority-ref", required=True)
    debug_gate_parser = subparsers.add_parser("debug-gate")
    debug_gate_parser.add_argument("--cwd", default=".")
    debug_gate_parser.add_argument(
        "--surface",
        default="begin",
        choices=("session", "begin", "checkpoint", "complete"),
    )
    debug_gate_parser.add_argument("--json", action="store_true")
    debug_gate_parser.add_argument("--record-attempt", metavar="INC_ID")
    debug_gate_parser.add_argument("--attempt-detail", default="")
    return result


def _memory_command(args: argparse.Namespace, root: Path) -> int:
    try:
        from pala_memory import plain_memory_report

        try:
            report = core.context_report(root, getattr(args, "session_key", None))
            document_map = dict(core.load_manifest(root).get("documents") or {})
            workflow = {
                "active_ticket": report.get("active_ticket"),
                "next_action": report.get("next_action"),
            }
            tool_counts = None
            tool_memory = report.get("tool_memory")
            if isinstance(tool_memory, dict) and isinstance(
                tool_memory.get("counts"), dict
            ):
                tool_counts = tool_memory["counts"]
            coherence = report.get("ticket_coherence")
            mismatch = (
                isinstance(coherence, dict) and bool(coherence.get("mismatch"))
            )
        except (OSError, ValueError, json.JSONDecodeError):
            discovery = documents.discover(root)
            document_map = dict(discovery.get("documents") or {})
            workflow = {}
            tool_counts = None
            mismatch = False
        print(
            plain_memory_report(
                root,
                documents=document_map,
                workflow=workflow,
                tool_counts=tool_counts,
            ),
            end="",
        )
        return 1 if mismatch else 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


def _v3_command(args: argparse.Namespace, root: Path) -> int:
    if args.command == "record-verification":
        from pala_store import WorkflowStore

        try:
            result = WorkflowStore(root).record_verification(
                args.ticket, args.session_key, args.status, args.verification_command, args.error
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(json.dumps({"status": result.status, "record": result.record}, ensure_ascii=False))
        return 0 if result.status in {"recorded", "blocked"} else 2
    if args.command in {"recover", "complete"}:
        from pala_store import WorkflowStore

        if args.command == "complete":
            try:
                if args.quality_ticket:
                    core.require_quality_gate(root, args.quality_ticket)
                    mapped = WorkflowStore(root).sync_quality_evidence(
                        args.ticket, args.session_key, args.quality_ticket
                    )
                    if mapped.status != "mapped":
                        print(f"quality acceptance mapping refused: {mapped.status}", file=sys.stderr)
                        return 2
                from pala_debug_gate import complete_fail_closed

                changed: list[str] = []
                verification: list[object] = []
                try:
                    document_map = dict(core.load_manifest(root).get("documents") or {})
                except (OSError, ValueError, json.JSONDecodeError):
                    document_map = {"debugging": "DEBUGGING.md"}
                try:
                    workflow = core.load_workflow(root)
                    raw_changed = workflow.get("changed_files") or []
                    if isinstance(raw_changed, list):
                        changed = [str(item) for item in raw_changed]
                    raw_verify = workflow.get("verification_evidence") or workflow.get(
                        "verification"
                    ) or []
                    if isinstance(raw_verify, list):
                        verification = list(raw_verify)
                except (OSError, ValueError, json.JSONDecodeError):
                    pass
                # Session ticket store may also hold verification.
                try:
                    record = WorkflowStore(root)._read(
                        WorkflowStore(root)._ticket_path(args.ticket)
                    )
                    if isinstance(record, dict):
                        store_verify = record.get("verification") or []
                        if isinstance(store_verify, list) and store_verify:
                            verification = list(store_verify)
                        store_changed = record.get("changed_files") or []
                        if isinstance(store_changed, list) and store_changed:
                            changed = [str(item) for item in store_changed]
                except (OSError, ValueError, TypeError, AttributeError):
                    pass
                decision = complete_fail_closed(
                    root,
                    documents=document_map,
                    changed_files=changed,
                    verification=verification,
                    enabled=True,
                )
                if not decision.get("allowed"):
                    print(str(decision.get("reason") or "complete refused"), file=sys.stderr)
                    return 2
            except (OSError, ValueError, TypeError, ImportError) as exc:
                print(str(exc), file=sys.stderr)
                return 2
        try:
            result = (
                core.complete_work(root, args.ticket, args.session_key)
                if args.command == "complete"
                else WorkflowStore(root).recover(args.ticket, args.session_key)
            )
        except ValueError as exc:
            reason = str(exc)
            if args.command == "complete" and (
                "not found" in reason.casefold() or "ticket" in reason.casefold()
            ):
                print(
                    core.complete_recovery_message(args.ticket, reason=reason),
                    file=sys.stderr,
                )
            else:
                print(reason, file=sys.stderr)
            return 2
        if args.command == "complete" and result.status not in {"completed"}:
            if result.status in {"owned_by_other", "busy"}:
                print(
                    core.complete_recovery_message(
                        args.ticket,
                        reason=f"status={result.status}",
                    ),
                    file=sys.stderr,
                )
            print(
                json.dumps(
                    {"status": result.status, "record": result.record},
                    ensure_ascii=False,
                )
            )
            return 2
        print(json.dumps({"status": result.status, "record": result.record}, ensure_ascii=False))
        return 0 if result.status in {"recovered", "completed"} else 2


def _checkpoint_command(args: argparse.Namespace, root: Path) -> int:
    if args.quality_ticket:
        try:
            core.require_quality_gate(root, args.quality_ticket)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if args.session_key:
        if not args.ticket:
            print("ticket is required with --session-key", file=sys.stderr)
            return 2
        legacy_active = False
        workflow_paths = (core.workflow_path(root), Path(root).resolve() / core.WORKFLOW)
        if any(path.is_file() for path in workflow_paths):
            try:
                legacy = core.load_workflow(root)
                legacy_active = legacy.get("active_ticket") == args.ticket and bool(
                    legacy.get("dirty")
                )
            except (OSError, ValueError, json.JSONDecodeError):
                legacy_active = False
        if legacy_active and not args.verification:
            print(
                "verification evidence is required when session checkpoint closes a matching workflow",
                file=sys.stderr,
            )
            return 2
        from pala_store import WorkflowStore

        result = WorkflowStore(root).checkpoint(
            args.ticket, args.session_key, args.next_action
        )
        if result.status == "checkpointed":
            task_contract = result.record.get("task_contract")
            if isinstance(task_contract, dict):
                with contextlib.suppress(
                    OSError, ValueError, TypeError, json.JSONDecodeError
                ):
                    core.refresh_continuity(
                        root, task_contract=task_contract, persist=True
                    )
        if result.status == "checkpointed" and legacy_active:
            try:
                core.checkpoint_work(
                    root,
                    args.next_action,
                    args.verification,
                    args.blocker,
                    args.tier,
                    session_id=args.session_key,
                    quality_ticket=args.quality_ticket,
                )
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 2
        print(json.dumps({"status": result.status, "record": result.record}, ensure_ascii=False))
        return 0 if result.status == "checkpointed" else 2
    try:
        core.load_manifest(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not args.verification:
        print("verification evidence is required for checkpoint", file=sys.stderr)
        return 2
    try:
        core.checkpoint_work(
            root,
            args.next_action,
            args.verification,
            args.blocker,
            args.tier,
            quality_ticket=args.quality_ticket,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(str(root / core.WORKFLOW))
    return 0


def _project_lifecycle_command(args: argparse.Namespace, root: Path) -> int:
    """Run an explicit project-history mutation without task completion authority."""
    from pala_continuity import close_context, reopen_context
    from pala_store import WorkflowStore

    try:
        record = WorkflowStore(root).ticket_record(args.ticket)
        task_contract = (
            record.get("task_contract") if isinstance(record, dict) else None
        )
        if not isinstance(task_contract, dict):
            raise ValueError("canonical task record is required")
        status = str(task_contract.get("status") or "")
        if args.command == "close-project" and status != "DONE":
            raise ValueError("project closure requires a canonical DONE task")
        if args.command == "reopen-project" and status not in {
            "CLAIMED",
            "IN_PROGRESS",
            "REOPENED",
        }:
            raise ValueError("project reopen requires an active canonical task")
        context = core.build_registered_continuity_context(
            root, task_contract=task_contract
        )
        if context is None:
            raise ValueError("live registered continuity context is required")
        db_path = core._continuity_db_path()
        if args.command == "close-project":
            result = close_context(
                context,
                summary=args.summary,
                final_commit=args.final_commit,
                release_ref=args.release_ref,
                risk_codes=args.risk_code,
                lessons=args.lesson,
                authority_ref=args.authority_ref,
                db_path=db_path,
            )
        else:
            result = reopen_context(
                context,
                closure_id=args.closure_id,
                authority_ref=args.authority_ref,
                db_path=db_path,
            )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"status": "passed", "history": result}, ensure_ascii=False))
    return 0


def main() -> int:
    args = parser().parse_args()
    root = core.git_root(Path(args.cwd))
    if args.command == "discover":
        print(json.dumps(documents.discover(root), ensure_ascii=False, indent=2))
        return 0
    if args.command == "instructions":
        print(
            json.dumps(
                documents.configured_instruction_report(root, Path(args.cwd)),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    if args.command == "register":
        return documents.register(args, root)
    if args.command == "context":
        try:
            print(
                json.dumps(
                    core.context_report(root, args.session_key), ensure_ascii=False, indent=2
                )
            )
            return 0
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
    if args.command == "memory":
        return _memory_command(args, root)
    if args.command == "begin":
        try:
            core.begin_work(root, args.ticket, args.goal, args.session_key, args.acceptance)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(str(root / core.WORKFLOW))
        return 0
    if args.command == "checkpoint":
        return _checkpoint_command(args, root)
    if args.command in {"record-verification", "recover", "complete"}:
        return _v3_command(args, root)
    if args.command in {"close-project", "reopen-project"}:
        return _project_lifecycle_command(args, root)
    if args.command == "doctor":
        payload = documents.doctor_report(root, session=args.session_key)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload["healthy"] else 2
    if args.command == "debug-gate":
        from pala_debug_gate import main as debug_gate_main

        argv = ["--cwd", str(root), "--surface", args.surface]
        if args.json:
            argv.append("--json")
        if args.record_attempt:
            argv.extend(["--record-attempt", args.record_attempt])
        if args.attempt_detail:
            argv.extend(["--attempt-detail", args.attempt_detail])
        return debug_gate_main(argv)
    return core.validate(root)

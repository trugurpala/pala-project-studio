#!/usr/bin/env python3
"""Read-only, dependency-free security and maintainability audit for Pala code.

This is deliberately a small hard gate.  It does not replace a project's
native linters or external scanners; it protects the shipped Pala scripts even
when those tools are unavailable.  Security violations fail the audit.
Maintainability findings are explicit advisory evidence, never a false green.
"""

from __future__ import annotations

import argparse
import ast
import json
from collections.abc import Iterable
from pathlib import Path

SCHEMA_VERSION = 1
PROFILES = ("source", "runtime")
MAX_MODULE_LINES = 800
MAX_FUNCTION_LINES = 120
MAX_FUNCTION_BRANCHES = 30
NETWORK_MODULES = frozenset({"urllib", "http", "socket", "requests"})
PROCESS_CALLS = frozenset(
    {
        "subprocess.run",
        "subprocess.Popen",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
    }
)
DANGEROUS_CALLS = frozenset(
    {
        "eval",
        "exec",
        "os.system",
        "os.popen",
        "pickle.load",
        "pickle.loads",
        "marshal.loads",
    }
)


def _source_files(root: Path) -> list[Path]:
    scripts = root / "scripts"
    if not scripts.is_dir():
        return []
    return [
        path
        for path in sorted(scripts.glob("*.py"))
        if not path.name.startswith("test_")
    ]


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _branch_count(node: ast.AST) -> int:
    branches = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        ast.Match,
        ast.BoolOp,
    )
    return sum(isinstance(item, branches) for item in ast.walk(node))


class _SecurityVisitor(ast.NodeVisitor):
    def __init__(self, relative_path: str) -> None:
        self.relative_path = relative_path
        self.violations: list[dict[str, object]] = []
        self.process_without_timeout: list[int] = []
        self.imports: set[str] = set()

    def _add(self, rule: str, node: ast.AST, detail: str) -> None:
        self.violations.append(
            {
                "rule": rule,
                "path": self.relative_path,
                "line": int(getattr(node, "lineno", 1)),
                "detail": detail,
            }
        )

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            self.imports.add(node.module.split(".", 1)[0])
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node.func)
        if name in DANGEROUS_CALLS:
            self._add(
                "dangerous-call", node, f"{name} is not allowed in shipped Pala code"
            )
        if name in PROCESS_CALLS:
            shell_value: ast.expr | None = next(
                (item.value for item in node.keywords if item.arg == "shell"), None
            )
            if isinstance(shell_value, ast.Constant) and shell_value.value is True:
                self._add(
                    "subprocess-shell", node, "subprocess shell=True is not allowed"
                )
            elif shell_value is not None and not (
                isinstance(shell_value, ast.Constant) and shell_value.value is False
            ):
                self._add(
                    "subprocess-shell",
                    node,
                    "subprocess shell must be omitted or literal False",
                )
            if not any(item.arg == "timeout" for item in node.keywords):
                self.process_without_timeout.append(int(getattr(node, "lineno", 1)))
        self.generic_visit(node)


def _source_secret_violations(
    path: Path, relative_path: str
) -> list[dict[str, object]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return [
            {
                "rule": "unreadable-source",
                "path": relative_path,
                "line": 1,
                "detail": str(error)[:160],
            }
        ]
    # Split the examples so this audit does not flag its own detection rules.
    markers = (
        "-----BEGIN " + "PRIVATE KEY-----",
        "gh" + "p_",
        "github" + "_pat_",
    )
    return [
        {
            "rule": "embedded-secret",
            "path": relative_path,
            "line": text[:match].count("\n") + 1,
            "detail": "secret-shaped literal is not allowed in shipped Pala code",
        }
        for marker in markers
        for match in [text.find(marker)]
        if match >= 0
    ]


def _parse_file(
    path: Path, relative_path: str
) -> tuple[ast.Module | None, list[dict[str, object]]]:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=relative_path), []
    except (OSError, SyntaxError, UnicodeError) as error:
        return None, [
            {
                "rule": "invalid-source",
                "path": relative_path,
                "line": 1,
                "detail": str(error)[:160],
            }
        ]


def _maintenance_candidates(
    tree: ast.Module, path: Path, relative_path: str
) -> dict[str, list[dict[str, object]]]:
    lines = len(path.read_text(encoding="utf-8").splitlines())
    modules: list[dict[str, object]] = []
    functions: list[dict[str, object]] = []
    if lines > MAX_MODULE_LINES:
        modules.append(
            {"path": relative_path, "lines": lines, "limit": MAX_MODULE_LINES}
        )
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        end = int(getattr(node, "end_lineno", node.lineno))
        length = end - int(node.lineno) + 1
        branches = _branch_count(node)
        if length > MAX_FUNCTION_LINES or branches > MAX_FUNCTION_BRANCHES:
            functions.append(
                {
                    "path": relative_path,
                    "name": node.name,
                    "line": int(node.lineno),
                    "lines": length,
                    "branches": branches,
                }
            )
    return {"modules": modules, "functions": functions}


def _hook_network_violations(visitor: _SecurityVisitor) -> list[dict[str, object]]:
    if visitor.relative_path != "scripts/pala_hook.py":
        return []
    banned = sorted(visitor.imports.intersection(NETWORK_MODULES))
    if not banned:
        return []
    return [
        {
            "rule": "hook-network-import",
            "path": visitor.relative_path,
            "line": 1,
            "detail": "hook may not import network modules: " + ", ".join(banned),
        }
    ]


def _summary(status: str, security_count: int, maintenance_count: int) -> str:
    if status == "failed":
        return f"Pala code audit blocked: {security_count} hard security finding(s)."
    if maintenance_count:
        return (
            "Pala code audit hard security checks passed; "
            f"{maintenance_count} maintainability candidate(s) remain advisory."
        )
    return (
        "Pala code audit passed: hard security and maintainability budgets are clear."
    )


def run_audit(
    root: Path | None = None, *, profile: str = "source"
) -> dict[str, object]:
    """Return deterministic, secrets-free audit evidence without writes or execution."""
    if profile not in PROFILES:
        raise ValueError(f"unsupported audit profile: {profile}")
    target = (root or Path(__file__).resolve().parent.parent).resolve()
    security: list[dict[str, object]] = []
    modules: list[dict[str, object]] = []
    functions: list[dict[str, object]] = []
    unbounded_processes: list[dict[str, object]] = []
    files = _source_files(target)
    for path in files:
        relative_path = _relative(target, path)
        security.extend(_source_secret_violations(path, relative_path))
        tree, parse_errors = _parse_file(path, relative_path)
        security.extend(parse_errors)
        if tree is None:
            continue
        visitor = _SecurityVisitor(relative_path)
        visitor.visit(tree)
        security.extend(visitor.violations)
        security.extend(_hook_network_violations(visitor))
        unbounded_processes.extend(
            {"path": relative_path, "line": line}
            for line in visitor.process_without_timeout
        )
        if profile == "source":
            candidates = _maintenance_candidates(tree, path, relative_path)
            modules.extend(candidates["modules"])
            functions.extend(candidates["functions"])
    security.sort(
        key=lambda item: (str(item["path"]), int(item["line"]), str(item["rule"]))
    )
    modules.sort(key=lambda item: (-int(item["lines"]), str(item["path"])))
    functions.sort(
        key=lambda item: (
            -max(int(item["lines"]), int(item["branches"])),
            str(item["path"]),
            int(item["line"]),
        )
    )
    unbounded_processes.sort(key=lambda item: (str(item["path"]), int(item["line"])))
    maintenance_count = len(modules) + len(functions)
    status = "failed" if security else "passed"
    return {
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "status": status,
        "security": {"status": status, "findings": security},
        "maintainability": {
            "status": "attention_required" if maintenance_count else "passed",
            "module_limit": MAX_MODULE_LINES,
            "function_line_limit": MAX_FUNCTION_LINES,
            "function_branch_limit": MAX_FUNCTION_BRANCHES,
            "modules": modules,
            "functions": functions,
        },
        "process_hygiene": {
            "status": "attention_required" if unbounded_processes else "passed",
            "without_timeout": unbounded_processes,
        },
        "files_scanned": len(files),
        "summary": _summary(status, len(security), maintenance_count),
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parent.parent
    )
    result.add_argument("--profile", choices=PROFILES, default="source")
    return result


def main(argv: Iterable[str] | None = None) -> int:
    args = parser().parse_args(argv)
    payload = run_audit(args.root, profile=args.profile)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

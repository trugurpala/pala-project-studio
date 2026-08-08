#!/usr/bin/env python3
"""Deterministic, local-first routing for Pala-owned expert workers."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path, PurePath
from typing import Literal

Task = Literal["review", "impact", "symbol", "docs", "architecture"]
SUPPORTED_SERENA_LANGUAGES = frozenset({"python", "javascript", "typescript", "php", "powershell"})


@dataclass(frozen=True)
class ExpertRequest:
    root: object
    task: Task
    query: str = ""
    changed_files: int = 0
    source_files: int = 0
    module_roots: int = 0
    languages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.task not in {"review", "impact", "symbol", "docs", "architecture"}:
            raise ValueError("unsupported expert task")
        if min(self.changed_files, self.source_files, self.module_roots) < 0:
            raise ValueError("expert counts cannot be negative")
        object.__setattr__(self, "languages", tuple(language.casefold() for language in self.languages))


@dataclass(frozen=True)
class ExpertDecision:
    primary: str
    fallbacks: tuple[str, ...]
    reason: str
    data_boundary: str


@dataclass(frozen=True)
class ExpertEvidence:
    tool: str
    path: str
    line: int
    relation: str
    confidence: Literal["extracted", "inferred", "ambiguous", "unknown"]
    symbol: str = ""

    def __post_init__(self) -> None:
        candidate = PurePath(self.path)
        if candidate.is_absolute() or ".." in candidate.parts or not self.path.strip():
            raise ValueError("evidence path must be repo-relative")
        if self.line < 1:
            raise ValueError("evidence line must be positive")
        if self.confidence not in {"extracted", "inferred", "ambiguous", "unknown"}:
            raise ValueError("unsupported evidence confidence")


@dataclass(frozen=True)
class ExpertCommand:
    args: tuple[str, ...]
    environment: dict[str, str]


def pala_state_root() -> Path:
    profile = Path(os.environ.get("USERPROFILE", Path.home()))
    return Path(os.environ.get("LOCALAPPDATA", profile / "AppData" / "Local")) / "Pala"


def expert_executable(name: str, state_root: Path | None = None) -> Path:
    root = (state_root or pala_state_root()).resolve() / "experts"
    locations = {
        "graphify": root / "python-bin" / "graphify.exe",
        "serena": root / "python-bin" / "serena.exe",
        "code-review-graph": root / "python-bin" / "code-review-graph.exe",
        "codebase-memory": root / "codebase-memory" / "0.9.0" / "expanded" / "codebase-memory-mcp.exe",
        "ollama": root / "ollama" / "0.32.6" / "expanded" / "ollama.exe",
    }
    try:
        return locations[name]
    except KeyError as error:
        raise ValueError("unsupported expert executable") from error


def ollama_environment(state_root: Path | None = None) -> dict[str, str]:
    root = (state_root or pala_state_root()).resolve()
    return {
        "OLLAMA_HOST": "127.0.0.1:11435",
        "OLLAMA_MODELS": str(root / "experts" / "ollama" / "0.32.6" / "models"),
        "OLLAMA_KEEP_ALIVE": "0",
    }


def graphify_command(root: Path, data_root: Path, *, semantic: bool, state_root: Path | None = None) -> ExpertCommand:
    root = root.resolve()
    output = data_root.resolve()
    args = [str(expert_executable("graphify", state_root)), "extract", str(root), "--out", str(output)]
    environment = {"GRAPHIFY_QUERY_LOG_DISABLE": "1"}
    if semantic:
        args.extend(["--backend", "ollama", "--model", "qwen3:4b-instruct", "--max-concurrency", "1"])
        environment.update(ollama_environment(state_root))
        environment.update({"OLLAMA_MODEL": "qwen3:4b-instruct", "GRAPHIFY_OLLAMA_KEEP_ALIVE": "0"})
    else:
        args.append("--code-only")
    return ExpertCommand(tuple(args), environment)


def serena_command(root: Path, home: Path, *, state_root: Path | None = None) -> ExpertCommand:
    del root
    return ExpertCommand(
        (str(expert_executable("serena", state_root)), "start-mcp-server", "--project-from-cwd", "--context", "codex", "--mode", "no-memories", "--mode", "planning", "--open-web-dashboard", "false"),
        {"SERENA_HOME": str(home.resolve())},
    )


def codebase_memory_command(root: Path, action: str, *, state_root: Path | None = None) -> ExpertCommand:
    if action not in {"index_repository", "search_graph", "trace_path", "detect_changes", "get_architecture"}:
        raise ValueError("unsupported codebase-memory action")
    resolved = root.resolve()
    return ExpertCommand(
        (str(expert_executable("codebase-memory", state_root)), "cli", action, "--repo-path", str(resolved)),
        {"CBM_ALLOWED_ROOT": str(resolved)},
    )


def graph_eligible(source_files: int, changed_files: int, module_roots: int) -> bool:
    return source_files >= 1000 or changed_files >= 50 or module_roots >= 4


def codebase_memory_eligible(request: ExpertRequest) -> bool:
    return (
        request.source_files >= 5000
        or request.module_roots >= 10
        or len(set(request.languages)) >= 3
    )


def route(request: ExpertRequest) -> ExpertDecision:
    if request.task == "docs":
        return ExpertDecision("graphify", ("git-rg",), "document or mixed corpus requested", "local-ollama-only")
    if request.task == "symbol":
        if set(request.languages).intersection(SUPPORTED_SERENA_LANGUAGES):
            return ExpertDecision("serena", ("git-rg",), "supported symbol navigation requested", "local-read-only")
        return ExpertDecision("direct", ("git-rg",), "no Pala-managed language server supports this symbol request", "local-read-only")
    if request.task == "architecture" and codebase_memory_eligible(request):
        return ExpertDecision("codebase-memory", ("code-review-graph", "git-rg"), "large or multilingual architecture request", "local-read-only")
    if request.task in {"review", "impact", "architecture"} and graph_eligible(
        request.source_files, request.changed_files, request.module_roots
    ):
        return ExpertDecision("code-review-graph", ("git-rg",), "bounded graph threshold reached", "local-read-only")
    return ExpertDecision("direct", ("git-rg",), "focused work is cheaper with direct source inspection", "local-read-only")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("route", "status"))
    parser.add_argument("--task", choices=("review", "impact", "symbol", "docs", "architecture"), default="review")
    parser.add_argument("--source-files", type=int, default=0)
    parser.add_argument("--changed-files", type=int, default=0)
    parser.add_argument("--module-roots", type=int, default=0)
    parser.add_argument("--language", action="append", default=[])
    parser.add_argument("--query", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    request = ExpertRequest(
        root=".", task=args.task, query=args.query, source_files=args.source_files,
        changed_files=args.changed_files, module_roots=args.module_roots, languages=tuple(args.language),
    )
    if args.action == "status":
        payload = {"managed_languages": sorted(SUPPORTED_SERENA_LANGUAGES), "routing": asdict(route(request))}
    else:
        payload = asdict(route(request))
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

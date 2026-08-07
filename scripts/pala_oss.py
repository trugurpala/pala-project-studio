#!/usr/bin/env python3
"""Deterministic, network-free OSS contribution policy and publish gates for Pala."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = 1
POSITIVE_LABEL_WEIGHTS = {
    "good first issue": 30,
    "help wanted": 20,
    "bug": 10,
    "documentation": 8,
    "docs": 8,
    "tests": 6,
    "test": 6,
}
COMPLEXITY_LABEL_PENALTIES = {
    "breaking change": 25,
    "epic": 20,
    "rfc": 15,
    "needs design": 15,
}
SAFE_SLUG = re.compile(r"^[A-Za-z0-9_.-]+$")
SAFE_REF = re.compile(r"^[A-Za-z0-9._/-]+$")
SAFE_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
COMMIT_SHA = re.compile(r"^[0-9a-fA-F]{40}$")

AI_FORBIDDEN_PATTERNS = (
    r"\bno\s+(?:generative\s+)?ai(?:[- ]generated)?\s+contributions?\b",
    r"\bai(?:[- ]generated)?\s+contributions?\s+(?:are|is)\s+(?:not\s+accepted|not\s+allowed|not\s+permitted|prohibited|forbidden)\b",
    r"\bdo\s+not\s+use\s+(?:generative\s+)?ai\b",
    r"\bmust\s+not\s+use\s+(?:generative\s+)?ai\b",
    r"\bgenerative\s+ai\s+(?:is\s+)?(?:not\s+allowed|not\s+permitted|prohibited|forbidden)\b",
)
AI_DISCLOSURE_PATTERNS = (
    r"\bdisclos(?:e|ure).{0,40}\bai\b",
    r"\bai\s+assistance.{0,40}\bdisclos",
    r"\bai[- ]generated.{0,40}\bdisclos",
)
ASSIGNMENT_PATTERNS = (
    r"\bmust\s+be\s+assigned\b",
    r"\bwait\s+(?:until|to\s+be)\s+assigned\b",
    r"\bdo\s+not\s+start.{0,60}\bassigned\b",
    r"\bask\s+(?:a\s+maintainer\s+)?to\s+assign\b",
)
ISSUE_FIRST_PATTERNS = (
    r"\bopen\s+an?\s+issue\s+before\b",
    r"\bdiscuss.{0,60}\bbefore\s+(?:opening|submitting)\s+(?:a\s+)?(?:pr|pull request)\b",
)
CLA_PATTERNS = (
    r"\bcontributor\s+license\s+agreement\b",
    r"\bcla\b",
)
DCO_PATTERNS = (
    r"\bdeveloper\s+certificate\s+of\s+origin\b",
    r"\bdco\b",
    r"\bsigned-off-by\b",
)
TEST_PATTERNS = (
    r"\btests?\s+(?:are\s+)?required\b",
    r"\badd\s+(?:a\s+)?tests?\b",
    r"\btest\s+coverage\b",
)


def _contains(patterns: Sequence[str], text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _labels(issue: Mapping[str, Any]) -> list[str]:
    result: list[str] = []
    raw = issue.get("labels", [])
    if not isinstance(raw, list):
        return result
    for item in raw:
        if isinstance(item, str):
            result.append(item.casefold().strip())
        elif isinstance(item, Mapping):
            name = item.get("name")
            if isinstance(name, str):
                result.append(name.casefold().strip())
    return result


def _security_sensitive(labels: Sequence[str]) -> bool:
    """Conservatively keep security-labelled work out of the automatic flow."""
    for label in labels:
        normalized = " ".join(label.casefold().replace("_", " ").replace("-", " ").split())
        if (
            "security" in normalized
            or "vulnerability" in normalized
            or normalized == "cve"
            or normalized.startswith("cve ")
        ):
            return True
    return False


def _assignees(issue: Mapping[str, Any]) -> list[str]:
    result: list[str] = []
    raw = issue.get("assignees", [])
    if not isinstance(raw, list):
        return result
    for item in raw:
        if isinstance(item, str):
            result.append(item.casefold().strip())
        elif isinstance(item, Mapping):
            login = item.get("login")
            if isinstance(login, str):
                result.append(login.casefold().strip())
    return result


def analyze_policy(files: Mapping[str, str]) -> dict[str, Any]:
    """Extract bounded contribution signals without executing repository content."""
    normalized: dict[str, str] = {}
    for raw_name, raw_content in files.items():
        if not isinstance(raw_name, str) or not isinstance(raw_content, str):
            continue
        name = raw_name.replace("\\", "/").strip()
        if not name or len(name) > 240:
            continue
        normalized[name] = raw_content[:200_000]

    joined = "\n\n".join(
        f"--- {name} ---\n{content}" for name, content in sorted(normalized.items())
    )
    ai_forbidden = _contains(AI_FORBIDDEN_PATTERNS, joined)
    ai_disclosure_required = _contains(AI_DISCLOSURE_PATTERNS, joined)

    ai_policy = "forbidden" if ai_forbidden else (
        "disclosure_required" if ai_disclosure_required else "unknown"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "source_files": sorted(normalized),
        "ai_policy": ai_policy,
        "assignment_required": _contains(ASSIGNMENT_PATTERNS, joined),
        "issue_first": _contains(ISSUE_FIRST_PATTERNS, joined),
        "cla_required": _contains(CLA_PATTERNS, joined),
        "dco_required": _contains(DCO_PATTERNS, joined),
        "tests_expected": _contains(TEST_PATTERNS, joined),
    }


def score_issue(
    issue: Mapping[str, Any],
    policy: Mapping[str, Any],
    actor: str | None = None,
) -> dict[str, Any]:
    """Return an explainable suitability score for one candidate issue."""
    blockers: list[str] = []
    reasons: list[str] = []
    labels = _labels(issue)
    label_set = set(labels)
    assignees = _assignees(issue)
    actor_key = actor.casefold().strip() if isinstance(actor, str) and actor.strip() else None

    if str(issue.get("state", "open")).casefold() != "open":
        blockers.append("issue_not_open")
    if policy.get("ai_policy") == "forbidden":
        blockers.append("repository_forbids_ai_contributions")
    if _security_sensitive(labels):
        blockers.append("security_sensitive_issue")

    open_prs = issue.get(
        "open_pull_requests",
        issue.get("linked_prs", issue.get("pull_requests", [])),
    )
    if isinstance(open_prs, list) and open_prs:
        blockers.append("existing_pull_request")

    if assignees and (actor_key is None or actor_key not in assignees):
        blockers.append("assigned_to_someone_else")
    if bool(policy.get("assignment_required")) and actor_key not in assignees:
        blockers.append("assignment_required_before_work")

    score = 20
    for label, weight in POSITIVE_LABEL_WEIGHTS.items():
        if label in label_set:
            score += weight
            reasons.append(f"label:{label}:+{weight}")
    for label, penalty in COMPLEXITY_LABEL_PENALTIES.items():
        if label in label_set:
            score -= penalty
            reasons.append(f"label:{label}:-{penalty}")

    title = str(issue.get("title", ""))
    body = str(issue.get("body", ""))
    combined = f"{title}\n{body}".casefold()

    if len(body.strip()) >= 120:
        score += 5
        reasons.append("described_issue:+5")
    if any(token in combined for token in ("reproduce", "steps to reproduce", "expected behavior", "actual behavior")):
        score += 7
        reasons.append("reproduction_signal:+7")
    if any(token in combined for token in ("test", "regression", "failing case")):
        score += 5
        reasons.append("test_signal:+5")
    if bool(policy.get("tests_expected")):
        reasons.append("repository_expects_tests")
    if bool(policy.get("cla_required")):
        reasons.append("cla_required")
    if bool(policy.get("dco_required")):
        reasons.append("dco_required")
    if policy.get("ai_policy") == "disclosure_required":
        reasons.append("ai_disclosure_required")

    score = max(0, min(100, score))
    if blockers:
        score = 0

    return {
        "schema_version": SCHEMA_VERSION,
        "decision": "blocked" if blockers else "eligible",
        "score": score,
        "blockers": sorted(set(blockers)),
        "reasons": reasons,
    }


def contribution_fingerprint(request: Mapping[str, Any]) -> str:
    """Hash only review-relevant, secrets-free fields for approval invalidation."""
    gates = request.get("gates", [])
    normalized_gates: list[dict[str, str]] = []
    if isinstance(gates, list):
        for gate in gates:
            if not isinstance(gate, Mapping):
                continue
            name = str(gate.get("name", ""))[:120]
            status = str(gate.get("status", ""))[:40].casefold()
            required = "true" if bool(gate.get("required", True)) else "false"
            normalized_gates.append({"name": name, "status": status, "required": required})

    payload = {
        "schema_version": SCHEMA_VERSION,
        "repository": str(request.get("repository", ""))[:200],
        "issue_number": str(request.get("issue_number", ""))[:40],
        "base_branch": str(request.get("base_branch", ""))[:120],
        "head_branch": str(request.get("head_branch", ""))[:120],
        "diff_sha256": str(request.get("diff_sha256", "")).casefold(),
        "commit_sha": str(request.get("commit_sha", "")).casefold(),
        "gates": sorted(normalized_gates, key=lambda item: (item["name"], item["status"], item["required"])),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def publish_gate(request: Mapping[str, Any], expected_fingerprint: str) -> dict[str, Any]:
    """Fail closed unless a human-approved draft-PR request is unchanged and verified."""
    blockers: list[str] = []

    action = str(request.get("action", "")).casefold()
    if action != "draft_pr":
        blockers.append("only_draft_pr_is_allowed")
    if not bool(request.get("human_approved")):
        blockers.append("human_approval_required")
    if not bool(request.get("worktree_clean")):
        blockers.append("worktree_must_be_clean")

    commit_sha = str(request.get("commit_sha", ""))
    if not COMMIT_SHA.fullmatch(commit_sha):
        blockers.append("valid_commit_sha_required")

    current = contribution_fingerprint(request)
    if not expected_fingerprint or current != expected_fingerprint.casefold():
        blockers.append("approval_fingerprint_changed")

    gates = request.get("gates", [])
    if not isinstance(gates, list) or not gates:
        blockers.append("verification_evidence_required")
    else:
        for gate in gates:
            if not isinstance(gate, Mapping):
                blockers.append("invalid_gate_record")
                continue
            if bool(gate.get("required", True)):
                status = str(gate.get("status", "")).casefold()
                if status != "passed":
                    blockers.append(f"required_gate_not_passed:{str(gate.get('name', 'unknown'))[:80]}")

    upstream_blockers = request.get("blockers", [])
    if isinstance(upstream_blockers, list) and upstream_blockers:
        blockers.append("contribution_has_open_blockers")

    return {
        "schema_version": SCHEMA_VERSION,
        "allowed": not blockers,
        "action": "draft_pr",
        "fingerprint": current,
        "blockers": sorted(set(blockers)),
    }


def _lockfiles(root: Path) -> bool:
    candidates = (
        "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
        "poetry.lock", "uv.lock", "Pipfile.lock",
        "go.sum", "Cargo.lock", "composer.lock", "Gemfile.lock",
    )
    return any((root / name).is_file() for name in candidates)


def tool_plan(root: Path) -> dict[str, Any]:
    """Discover optional local quality helpers without installing or executing them."""
    root = Path(root)
    workflows = root / ".github" / "workflows"
    tools = {
        "git": shutil.which("git"),
        "gh": shutil.which("gh"),
        "osv-scanner": shutil.which("osv-scanner"),
        "zizmor": shutil.which("zizmor"),
    }
    gates: list[dict[str, Any]] = []

    if _lockfiles(root):
        gates.append({
            "name": "dependency-vulnerability",
            "tool": "osv-scanner",
            "available": bool(tools["osv-scanner"]),
            "argv": ["osv-scanner", "scan", "source", "--recursive", "."],
            "required": False,
        })
    if workflows.is_dir() and any(workflows.glob("*.y*ml")):
        gates.append({
            "name": "github-actions-security",
            "tool": "zizmor",
            "available": bool(tools["zizmor"]),
            "argv": ["zizmor", ".github/workflows"],
            "required": False,
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "tools": {name: bool(path) for name, path in tools.items()},
        "optional_gates": gates,
    }


def _safe_identifier(label: str, value: str) -> str:
    if not SAFE_SLUG.fullmatch(value) or value in {".", ".."} or value.startswith("-"):
        raise ValueError(f"unsafe {label}")
    return value


def _safe_ref(label: str, value: str) -> str:
    if (
        not SAFE_REF.fullmatch(value)
        or value.startswith(("/", "-"))
        or value.endswith("/")
        or ".." in value
        or "//" in value
        or value.endswith(".lock")
    ):
        raise ValueError(f"unsafe {label}")
    return value


def write_plan(
    repository: str,
    actor: str,
    branch: str,
    *,
    base_branch: str = "main",
) -> dict[str, Any]:
    """Build argv-only GitHub write actions; execution remains a separate authority."""
    if not SAFE_REPO.fullmatch(repository):
        raise ValueError("repository must be owner/name")
    owner, repo_name = repository.split("/", 1)
    _safe_identifier("repository owner", owner)
    _safe_identifier("repository name", repo_name)
    _safe_identifier("actor", actor)
    _safe_ref("branch", branch)
    _safe_ref("base_branch", base_branch)
    fork_url = f"https://github.com/{actor}/{repo_name}.git"

    def step(authority: str, argv: list[str]) -> dict[str, Any]:
        return {
            "authority": authority,
            "requires_explicit_authority": True,
            "argv": argv,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "requires_explicit_authority": True,
        "steps": [
            step("fork", ["gh", "repo", "fork", repository, "--clone=false"]),
            step("push", ["git", "push", fork_url, f"HEAD:refs/heads/{branch}"]),
            step(
                "pull_request",
                [
                    "gh", "pr", "create", "--draft",
                    "--repo", repository,
                    "--base", base_branch,
                    "--head", f"{actor}:{branch}",
                ],
            ),
        ],
    }


def _load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)

    policy = sub.add_parser("policy", help="Analyze repository contribution-policy text from JSON mapping.")
    policy.add_argument("--input", required=True, type=Path)

    score = sub.add_parser("score", help="Score one issue candidate.")
    score.add_argument("--issue", required=True, type=Path)
    score.add_argument("--policy", required=True, type=Path)
    score.add_argument("--actor")

    fingerprint = sub.add_parser("fingerprint", help="Create the human-approval fingerprint.")
    fingerprint.add_argument("--request", required=True, type=Path)

    gate = sub.add_parser("publish-check", help="Validate a draft-PR publish request.")
    gate.add_argument("--request", required=True, type=Path)
    gate.add_argument("--fingerprint", required=True)

    doctor = sub.add_parser("doctor", help="Discover optional local OSS contribution helpers.")
    doctor.add_argument("--cwd", default=".", type=Path)

    write = sub.add_parser("write-plan", help="Create non-executing gh argv for fork and draft PR.")
    write.add_argument("--repository", required=True)
    write.add_argument("--actor", required=True)
    write.add_argument("--branch", required=True)
    write.add_argument("--base", default="main")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "policy":
        result = analyze_policy(_load_json(args.input))
    elif args.command == "score":
        result = score_issue(_load_json(args.issue), _load_json(args.policy), args.actor)
    elif args.command == "fingerprint":
        result = {"fingerprint": contribution_fingerprint(_load_json(args.request))}
    elif args.command == "publish-check":
        result = publish_gate(_load_json(args.request), args.fingerprint)
    elif args.command == "doctor":
        result = tool_plan(args.cwd)
    elif args.command == "write-plan":
        result = write_plan(args.repository, args.actor, args.branch, base_branch=args.base)
    else:
        raise AssertionError(args.command)

    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

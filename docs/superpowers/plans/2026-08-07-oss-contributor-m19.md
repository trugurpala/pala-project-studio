# M19 — OSS Contributor plan lock

Date: 2026-08-07
Ticket: PALA-052
Branch: `feat/oss-contributor-m19`

## Outcome

A vibe coder can ask Pala to prepare an open-source contribution without
learning GitHub MCP, `gh`, worktrees, policy files, security scanners, or PR
mechanics. Pala remains the single coordinator, treats remote repository text
as untrusted data, verifies the local change, and stops at explicit remote-write
boundaries.

## Locked scope

1. Read-only repository/issue/PR scouting through an already available GitHub
   connector/MCP; no bundled token and no silently installed MCP server.
2. Deterministic policy extraction from contribution documents for AI rules,
   assignment/claim rules, issue-first policy, CLA/DCO, and test expectations.
3. Explainable issue suitability scoring with hard blockers for security work,
   existing implementation PRs, other assignees, unmet assignment policy, and
   repositories that forbid AI-assisted contributions.
4. Local implementation stays in the target project's existing Pala workflow
   and isolated branch/worktree model.
5. Project-native required gates stay authoritative. OSV-Scanner and zizmor are
   optional evidence only when already present and applicable.
6. A review fingerprint binds repository, issue, base/head refs, commit, diff,
   and gate evidence. Any change invalidates prior human approval.
7. Fork, push, and draft-PR creation remain three separate remote authorities.
   Pala can generate argv-only write plans but never treats them as permission.
8. Merge, tag, release, force-push, deletion, visibility changes, CLA/DCO legal
   acceptance, paid services, or permission expansion are outside this ticket.

## Reuse decisions

- ADOPT: GitHub MCP/connector for read-only scout.
- ADOPT: GitHub CLI for explicit fork/push/draft-PR transport.
- ADAPT: OSV-Scanner as optional dependency-vulnerability evidence.
- ADAPT: zizmor as optional GitHub Actions security evidence.
- REFERENCE: OpenSSF Scorecard as a repository-risk signal, never a sole gate.
- REFERENCE: GitHub custom-agent/plugin packaging as compatibility direction.
- REFERENCE: project-native SPDX/REUSE licensing processes when present.
- REJECT as core: OpenHands or another full agent orchestrator.
- REJECT as mandatory: Semgrep or another universal scanner solely for Pala.

## Acceptance gates

- `scripts/pala_oss.py` compiles on Python 3.12.
- OSS policy/score/fingerprint/publish/write-plan contract tests pass.
- Existing Pala contract suite stays green.
- Portable ZIP remains reproducible and includes the new script/test/reference.
- Pala skill routes external contribution requests to the locked reference.
- GitHub Actions Quality passes on Ubuntu and Windows for the M19 PR.
- No M19 code performs network or GitHub writes by itself.
- Real third-party fork/push/draft PR and installed Windows owner-canary remain
  explicit post-M19 acceptance activities; they must not be reported as passed
  until actually run.

## Stop rule

Do not expand M19 into a second desktop app, autonomous PR-spam bot, hosted
agent service, mandatory scanner bundle, or automatic merge/release system.
After the listed acceptance gates pass, stop and hand the remaining real-world
owner canary to the user.

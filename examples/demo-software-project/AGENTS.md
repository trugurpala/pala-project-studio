# Demo Software Project — agent rules

Fictional sample for Pala fork demos. Not a real product codebase.

## Purpose

- Before editing, pick a single task ID from `PLAN.md` (e.g. `DEMO-005-A`).
- Keep one active ticket and one next action across Codex sessions.
- Prefer evidence labels: `passed` | `not-run` | `blocked` | `configured-not-verified`.
- Never claim larger context windows or quotas.

## Memory read order

`AGENTS.md` → `STATUS.md` → `PROGRESS.md` → active ticket in `PLAN.md` →
`TOOLING_DECISIONS.md` → `DEBUGGING.md` → git.

## Safety

- No secrets in this tree.
- Commit, push, release, and deploy need separate explicit authority.
- Hooks must not start tests, builds, or network calls.

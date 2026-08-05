# Durable Project Memory

Prefer existing documents and register their real paths:

| Purpose | Common candidates | Fallback |
| --- | --- | --- |
| Instructions | `AGENTS.override.md`, `AGENTS.md` | `AGENTS.md` |
| Product | `PROJECT.md`, `docs/SCOPE.md`, README | `docs/codex/PROJECT.md` |
| Plan | `PLAN.md`, `docs/IMPLEMENTATION_PLAN.md`, `TASKS.md`, `ROADMAP.md` | `docs/codex/PLAN.md` |
| Status | `STATUS.md`, `PROGRESS.md`, `reports/CURRENT_STATUS.md` | `docs/codex/STATUS.md` |
| Decisions | `DECISIONS.md`, `docs/PRODUCT_DECISIONS.md`, `docs/adr/` | `docs/codex/DECISIONS.md` |
| Open source | `OPEN_SOURCE.md`, `docs/OPEN_SOURCE.md`, notices | `docs/codex/OPEN_SOURCE.md` |

The product document owns users, outcome, scope, non-goals, architecture,
trust boundaries, and definition of done. The plan owns ordered milestones and
coherent tickets. Expand only the active ticket to exact files, interfaces,
tests, commands, dependencies, acceptance evidence, and one lifecycle state.

The short status checkpoint contains the current milestone/ticket, last
completed outcome, working-tree summary, real verification evidence, blockers,
exactly one next action, and timestamp. Read status first; do not load the full
plan merely to discover what is active.

`AGENTS.md` stores stable behavior, not changing project status. Consult
current official guidance for Codex when instruction precedence, configuration,
limits, or reload behavior matters. Keep volatile detail in registered
documents.

Run `register` once with the selected paths, `begin` before implementation, and
`checkpoint --tier narrow|ticket|milestone|release` after a coherent outcome.
Run `context` at session start. Workflow schema v2 stores bounded evidence plus
hashes of registered documents and a Git fingerprint. A changed plan, status,
HEAD, or worktree after checkpoint requires reconciliation; it must not trigger
automatic re-planning or testing.

The generated state files may be committed only when they are secrets-free and
repository policy allows it. See
[github-persistence.md](github-persistence.md) before remote persistence.

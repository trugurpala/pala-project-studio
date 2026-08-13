# Durable Project Memory

Prefer existing documents and register their real paths:

| Purpose | Common candidates | Fallback |
| --- | --- | --- |
| Instructions | `AGENTS.override.md`, `AGENTS.md` | `AGENTS.md` |
| Product | `PROJECT.md`, `docs/SCOPE.md`, README | `docs/codex/PROJECT.md` |
| Plan | `PLAN.md`, `docs/IMPLEMENTATION_PLAN.md`, `TASKS.md`, `ROADMAP.md` | `docs/codex/PLAN.md` |
| Status | `reports/CURRENT_STATUS.md`, `STATUS.md`, `PROJECT_STATE.md` | `reports/CURRENT_STATUS.md` |
| Progress | `PROGRESS.md`, `docs/PROGRESS.md` | `PROGRESS.md` |
| Tooling | `TOOLING_DECISIONS.md`, `docs/TOOLING_DECISIONS.md` | `TOOLING_DECISIONS.md` |
| Debugging | `DEBUGGING.md`, `docs/vibe-os/TROUBLESHOOTING.md`, `docs/DEBUGGING.md` | `DEBUGGING.md` |
| Decisions | `DECISIONS.md`, `docs/PRODUCT_DECISIONS.md`, `docs/adr/` | `docs/codex/DECISIONS.md` |
| Open source | `OPEN_SOURCE.md`, `docs/OPEN_SOURCE.md`, notices | `docs/codex/OPEN_SOURCE.md` |
| Owner demo | `reports/OWNER_DEMO.md`, `DEMO.md` | `reports/OWNER_DEMO.md` |

`DEBUGGING.md` is the durable error brain: read it before repeating a known
failure; append `### INC-…` entries with Symptoms, Root cause, Fix criteria,
Proved by, Related files, Date, Status. Parser: `pala_memory.parse_debugging_brain`.
SessionStart exposes `debug_open=N`; Status HTML shows a “Hata beyni” line.

## Project Memory Contract (0.5)

Forced bootstrap order every Implementation session:

1. `AGENTS.md`
2. Status (`reports/CURRENT_STATUS.md` preferred)
3. `PROGRESS.md`
4. Active plan — active ticket section only
5. `TOOLING_DECISIONS.md`
6. `DEBUGGING.md`
7. Git status (`--short --branch`)

Run `context --cwd .` and follow `read_order`. Do not trust chat history over these files.
See [project-memory-contract.md](project-memory-contract.md) and
`docs/ARCHITECTURE.md`.

The product document owns users, outcome, scope, non-goals, architecture,
trust boundaries, and definition of done. The plan owns ordered milestones and
coherent tickets. When `PLAN.md` uses agent task cards, each card may list:
**ID**, **Sahip ajan**, **Amaç**, **Dosyalar**, **Bitti sayılır**,
**Bağımlılık**, **Kanıt** — one ID per agent turn; respect owner and file
ownership. Expand only the active ticket to exact files, interfaces,
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
Evidence lines must look like `unittest=passed` or `install=configured-not-verified`.
Soft words (`done`, `bitti`, `ok`) alone are refused. Run `context` at session start.
Workflow schema v2 stores bounded evidence plus
hashes of registered documents and a Git fingerprint. A changed plan, status,
HEAD, or worktree after checkpoint normally requires reconciliation. Ticket vs
next-action mismatches are written into CURRENT_STATUS. One safe
exception exists: a descendant commit that exactly materializes the
checkpointed path/content snapshot and leaves no other working-tree change is
accepted as the same outcome. A later, divergent, or extra commit still
requires reconciliation. Neither case may trigger automatic re-planning or
testing.

The generated state files may be committed only when they are secrets-free and
repository policy allows it. See
[github-persistence.md](github-persistence.md) before remote persistence.

# Pala 0.5 — Project Memory Contract

Pala 0.5 makes durable folder memory the source of truth between sessions.

## Forced bootstrap order

Every Implementation-mode session reads, in order:

1. `AGENTS.md` (stable behavior)
2. Status (`reports/CURRENT_STATUS.md` preferred)
3. `PROGRESS.md`
4. Active plan (active ticket section only)
5. `TOOLING_DECISIONS.md`
6. `DEBUGGING.md` (or registered troubleshooting path) — durable error brain
   with `## Format` and optional `### INC-…` incidents (root cause, symptoms,
   fix criteria, proved-by commands, related files, date, status).
7. Git status (`--short --branch`)

Chat history is never the source of truth. Fail-closed parse lives in
`scripts/pala_memory.py` (`parse_debugging_brain`) and self-audit
`debugging_brain`.

## Tool memory statuses

| Status | Meaning |
| --- | --- |
| `installed` | Present and probe-verified |
| `recommended` | Profile suggests it; not installed |
| `installed_unverified` | Appears present; probe missing/failed |
| `not_installed` | Absent |
| `unavailable` | Host/platform cannot use it |

These are separate from ticket verification statuses.

## Evidence-gated “done”

Checkpoint evidence uses: `passed`, `not-run`, `blocked`, `configured-not-verified`, `failed`, `timeout`.  
Soft “bitti/done/ok” without a structured check is refused.

## Ticket coherence

Before/after checkpoint, Pala compares `active_ticket` with the recorded next work. Mismatch is written into workflow + `CURRENT_STATUS.md`.

## Agent task cards (optional)

`PLAN.md` may list optional agent task cards (`M*-T*` / ticket IDs) with fields:
**ID**, **Sahip ajan**, **Amaç**, **Dosyalar**, **Bitti sayılır**, **Bağımlılık**,
**Kanıt**. Before implementation read `STATUS.md`, then the active cards in
`PLAN.md`, then `DEBUGGING.md`. Each agent turn picks exactly one ID; respect
owner and file ownership; do not re-plan closed cards. Evidence uses
`passed|not-run|blocked|configured-not-verified`.

## Cross-project catalog

Optional local index: `C:\Users\Pala-Pc\Desktop\Codex\pala-catalog.json` (secrets-free). Not required for portable install.

## Limits

- SessionStart message ≤ 800 characters; paths and scalars only.
- Hooks never run tests, builds, network, or GitHub mutations.
- See the bundled current contract in [PALA_SHARED_MEMORY.md](PALA_SHARED_MEMORY.md).

## Visual surface (future phase)

A visual surface (a local, read-only status screen or dashboard) is not
permanently excluded. It stays behind a phase gate (see `DECISIONS.md` ADR-013):
single-door install, local-first, secrets-free, no hook/network change, and the
deterministic scripts remain the single source of truth. The first friendly step
is enriching readable outputs such as `pala_state.py memory` and
`pala_catalog.py summary`, not adding a server.

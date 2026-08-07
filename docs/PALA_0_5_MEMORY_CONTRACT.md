# Pala 0.5 — Project Memory Contract

Pala 0.5 makes durable folder memory the source of truth between sessions.

## Forced bootstrap order

Every Implementation-mode session reads, in order:

1. `AGENTS.md` (stable behavior)
2. Status (`reports/CURRENT_STATUS.md` preferred)
3. `PROGRESS.md`
4. Active plan (active ticket section only)
5. `TOOLING_DECISIONS.md`
6. `DEBUGGING.md` (or registered troubleshooting path)
7. Git status (`--short --branch`)

Chat history is never the source of truth.

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

## Cross-project catalog

Optional local index: `C:\Users\Pala-Pc\Desktop\Codex\pala-catalog.json` (secrets-free). Not required for portable install.

## Limits

- SessionStart message ≤ 800 characters; paths and scalars only.
- Hooks never run tests, builds, network, or GitHub mutations.
- See [2026-08-07-project-memory-contract-design.md](../superpowers/specs/2026-08-07-project-memory-contract-design.md).

# Project Memory Contract (skill detail)

Follow this after SessionStart / `pala_state.py context`.

## Read order (mandatory)

1. Instructions (`AGENTS.md`)
2. Status (`reports/CURRENT_STATUS.md` preferred)
3. Progress (`PROGRESS.md`)
4. Active plan — only the active ticket section
5. Tooling (`TOOLING_DECISIONS.md`)
6. Debugging (`DEBUGGING.md`)
7. Git status

## Tool honesty

Record tools as: `installed`, `recommended`, `installed_unverified`,
`not_installed`, or `unavailable`. Never treat “configured” as verified.

## Checkpoint evidence

Each checkpoint must answer:

- What changed?
- Which files changed?
- Which checks passed / not-run / blocked / configured-not-verified?
- What is the single next action?

Refuse soft completion words alone (`done`, `bitti`, `ok`).

## Ticket coherence

If active ticket and next work disagree, write the mismatch into
`CURRENT_STATUS.md` and reconcile before new implementation.

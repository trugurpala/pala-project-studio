# Project Memory Contract (skill detail)

Follow this after SessionStart / `pala_state.py context`.

## Read order (mandatory)

1. Instructions (`AGENTS.md`)
2. Status (`reports/CURRENT_STATUS.md` preferred)
3. Progress (`PROGRESS.md`)
4. Active plan — only the active ticket section
5. Tooling (`TOOLING_DECISIONS.md`)
6. Debugging (`DEBUGGING.md`) — durable error brain; read before repeating a
   known failure; append `### INC-…` with Symptoms, Root cause, Fix criteria,
   Proved by, Related files, Date, Status (no secrets/transcripts).
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

## Task cards (optional)

When `PLAN.md` lists agent task cards, each card may include: **ID**,
**Sahip ajan**, **Amaç**, **Dosyalar**, **Bitti sayılır**, **Bağımlılık**,
**Kanıt**. One agent turn selects exactly one ID; respect owner and file
ownership; do not reopen closed cards.

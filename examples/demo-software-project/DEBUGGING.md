# Demo Software Project — Debugging

Durable error brain for the demo fixture. Read before repeating a known failure.
No secrets or transcripts.

## Format

Each incident uses heading `### INC-YYYYMMDD-slug` and these fields:
Symptoms, Root cause, Fix criteria, Proved by, Related files, Date, Status.

## Incidents

### INC-20260808-demo-soft-done
- **Symptoms:** Status looks “done” after soft ok/bitti without gate labels.
- **Root cause:** Soft completion words used instead of evidence labels.
- **Fix criteria:** Prefer `passed|not-run|blocked|configured-not-verified`.
- **Proved by:** Re-seed demo and check STATUS evidence table
- **Related files:** `STATUS.md`, `AGENTS.md`, `DEBUGGING.md`
- **Date:** 2026-08-08
- **Status:** fixed (`passed` demo contract note)

### INC-20260808-demo-empty-status
- **Symptoms:** Status looks empty after catalog move.
- **Root cause:** Wrong `PALA_CATALOG_ROOT` / `--catalog-root`.
- **Fix criteria:** Re-run demo seed against temp or Desktop/Codex catalog root.
- **Proved by:** `py -3 scripts/pala_demo.py seed` with explicit catalog root
- **Related files:** `STATUS.md`, `scripts/pala_demo.py`
- **Date:** 2026-08-08
- **Status:** fixed (`passed` seed path documented)

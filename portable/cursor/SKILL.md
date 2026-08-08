---
name: pala-shared-memory
description: "Use in Cursor (or any agentskills host) to read Pala project memory and the shared local pala.sqlite catalog. Not a Codex plugin install. No hooks, no marketplace, no context/quota claims."
---

# Pala Shared Memory (Cursor / portable)

Thin reader for the **same** machine-local Pala store that Codex uses.

## Human opener

Pala burada — bu oturumda yanındayım. (Cursor ince yüzey; Not a Codex plugin install.)

## Do

1. Read `AGENTS.md` → `STATUS.md` → `PROGRESS.md` → active ticket in `PLAN.md` → `TOOLING_DECISIONS.md` → `DEBUGGING.md` → git.
2. Pick one task ID from `PLAN.md` when `M*-T*` / `DEMO-*-*` cards exist.
3. Open Status via CLI (same DB):  
   `py -3 scripts/pala_report.py --cwd .`  
   Optional: `--open`
4. Confirm store path: Doctor / memory text shows one `pala.sqlite` (default under Desktop\Codex). Override: `PALA_DB_PATH` / `PALA_CATALOG_ROOT`.
5. Evidence labels only: `passed` | `not-run` | `blocked` | `configured-not-verified`.

## Do not

- Claim Codex SessionStart hooks run inside Cursor.
- Claim Install-Pala installed a Cursor plugin (Not a Codex plugin install).
- Write secrets, tokens, or transcripts into `pala.sqlite`.
- Start tests/builds/network from any hook fantasy — there are no Cursor Pala hooks.
- Invent a second cloud sync DB.

## Primary product

Codex Work remains first-class. This skill only shares **memory contract + local store**.

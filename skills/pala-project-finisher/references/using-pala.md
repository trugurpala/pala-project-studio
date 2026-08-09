# Using Pala (continuity ritual)

Pala is project memory + plan + evidence for Codex — not a larger context
window or quota. Follow this ritual before implementation.

## Before any edit

1. Presence / cold packet: `pala_report.py --cwd .` (or SessionStart packet).
2. Read order: AGENTS → STATUS → PROGRESS → **active ticket only** → TOOLING →
   DEBUGGING → git (`pala_state.py context` / `read_order`).
3. Pick **exactly one** ticket ID (`M*-T*` / PLAN card). Do not re-plan closed
   or already-evidenced cards.
4. Load the matching process ref:
   - New design / unclear outcome → [plan-tickets.md](plan-tickets.md)
   - Approved ticket, implementing → [execute-tickets.md](execute-tickets.md)
   - Bug / test failure → [debugging-inc.md](debugging-inc.md) **before** fixes
   - About to say done / checkpoint → [quality-gates.md](quality-gates.md)
5. Announce in one short line: mode + ticket ID (e.g. "Execute M31-T1").

## Hard stops

- Soft `done` / `bitti` / `ok` is not evidence.
- Labels only: `passed` | `not-run` | `blocked` | `configured-not-verified`.
- Mid-turn forget (no SessionStart): re-read STATUS/PLAN or ask for a cold
  packet — do not fake continuous memory.
- Commit / push / PR / tag / release / deploy need separate explicit authority.
- Hooks never start tests, builds, or network calls.

## Optional Superpowers

If `superpowers:*` skills are installed, use them only for gaps these refs do
not cover. Pala owns STATUS/PLAN/INC/evidence and SessionStart continuity.
Do not claim Claude-only subagent or companion flows as Codex/Pala features.

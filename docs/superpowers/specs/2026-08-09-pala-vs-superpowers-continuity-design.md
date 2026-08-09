# Design: Pala vs Superpowers — continuity gaps (adopt / skip)

**Date:** 2026-08-09  
**Branch:** `feat/m30-vibe-codex-host-fit`  
**Upstream studied:** [obra/superpowers](https://github.com/obra/superpowers) (README + skills)  
**Authority:** Local improve + ZIP; no push / PR / tag.

## What Superpowers is (honest)

Composable **process skills** (brainstorm → plan → TDD → execute → verify →
finish branch) plus a meta skill `using-superpowers` that forces skill
invocation before work. On **Codex**, current Superpowers packaging is largely
**skill discovery** (`~/.agents/skills/` symlink); SessionStart bootstrap hooks
were tried then removed / emptied for Codex. Continuity across sessions is
therefore mostly "re-read the skill + plan markdown," not a project memory
store.

## What Pala already beats (keep; do not copy)

| Axis | Pala | Superpowers (Codex) |
| --- | --- | --- |
| Cross-session project state | `pala.sqlite` + STATUS/PLAN + SessionStart cold packet | Skill text + optional plan files |
| Compact / resume | Host hooks: SessionStart (`startup|resume|clear|compact`) + PreCompact reconcile | Skill re-discovery; Codex hooks largely empty |
| Evidence vocabulary | `passed|not-run|blocked|configured-not-verified` | "Run the command" prose |
| Durable bug brain | `DEBUGGING.md` `### INC-…` + debug gate | systematic-debugging skill (ephemeral unless user files it) |
| Token honesty | No window/quota claims; char/token budgets documented | Methodology claims, not host cold-packet budgets |
| Hook safety | Hooks never start test/build/network | N/A on Codex path without hooks |

## What we adopt (adapted — not wholesale)

1. **Using ritual** — thin `using-pala.md`: check process refs before coding;
   announce mode; one ticket ID. Not "1% chance → must invoke skill" theatre.
2. **Plan / execute checklists** — `plan-tickets.md` + `execute-tickets.md`
   mapped to Pala `M*-T*` cards (files, Kanıt, single next action). No forced
   subagent MCP / visual companion / telemetry.
3. **Verification before done** — iron gate in `quality-gates.md` with Pala
   evidence labels (fix soft `failed` / `not run` drift).
4. **Systematic debugging routing** — `debugging-inc.md` maps 4 phases → INC-
   fields; skill routes bugs there first.

## What we deliberately skip

- Copying Superpowers skill tree into Pala marketplace
- Claiming Claude Code–only subagent / companion flows as Codex features
- Mandatory git worktrees / finishing-branch auto-merge menus as Pala core
- SessionStart that only injects "use skills" without project cold packet
- Telemetry / visual companion servers
- Fat SKILL.md (>480 words) — detail stays in `references/`

## Success criteria

- Design note + references + SKILL pointer + contract tests `passed`
- Focused unittest + `verify.py` when feasible
- STATUS / CHANGELOG updated; local commit; Desktop final ZIP + SHA
- `/hooks` trust and push remain owner (`configured-not-verified` / not asked)

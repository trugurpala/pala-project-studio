# Pala — Cursor / portable thin surface

Codex remains the primary Pala product. This folder is the **M25** thin
surface for Cursor (and other agentskills hosts).

| Path | Role |
| --- | --- |
| `portable/cursor/SKILL.md` | Copy or point an agentskills-compatible host at this skill |
| `.cursor/rules/pala-memory.mdc` | In-repo Cursor rule for this checkout |

Same machine store: `%USERPROFILE%\Desktop\Codex\pala.sqlite`  
(`PALA_DB_PATH` / `PALA_CATALOG_ROOT`). See ADR-017 and
`docs/PALA_SHARED_MEMORY.md` (hit/miss + Doctor `shared_store`).

Durable rules: repo-root `AGENTS.md` (single source). This skill stays thin.

**Not included:** Codex `hooks.json`, marketplace install, RTK PreToolUse.

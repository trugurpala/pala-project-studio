# Pala shared memory (ADR-017 / Wave E)

Single-machine store shared by **Codex + Cursor + CLI**. No cloud sync.

## Layers

| Layer | Role |
| --- | --- |
| `AGENTS.md` | Durable agent rules — **single source** |
| Project files | `STATUS` / `PLAN` / `PROGRESS` / `DEBUGGING` (working memory) |
| `pala.sqlite` | Machine-local catalog + events (`PALA_DB_PATH` / `PALA_CATALOG_ROOT`) |
| Cursor rule | Thin reminder only (`.cursor/rules/pala-memory.mdc`) |
| Portable skill | Thin agentskills reader (`portable/cursor/SKILL.md`) |

Codex remains the primary product (marketplace + `hooks.json`). Cursor does not
get Codex hook parity and must never claim “Pala Cursor plugin installed”.

## Hit / miss (same SQLite)

| Access | Meaning | Evidence |
| --- | --- | --- |
| **hit** | Host is `codex`, `cursor`, or `cli` → same `db_path` under the same env / catalog root | `pala_shared_memory.surface_report` / `classify_host_access` → `access=hit` |
| **miss** | Unknown host (e.g. ChatGPT Plus paste) → no invented second store | `classify_host_access` → `access=miss`; `surface_report` raises |

Overrides:

- `PALA_DB_PATH` — absolute sqlite path for all hosts
- `PALA_CATALOG_ROOT` — catalog directory; default DB is `<root>/pala.sqlite`
- Explicit `catalog_root=` argument — same path for every host in that call

Never store: secrets, tokens, transcripts, raw chat.

## Doctor `shared_store` surface

Install Doctor (`pala_installer.doctor` / `Install-Pala Doctor`) and
`pala_state` status JSON expose a `shared_store` block from
`pala_shared_memory.doctor_store_block()`:

```json
{
  "db_path": "…/pala.sqlite",
  "sync_model": "single_machine_file",
  "cloud_sync": false,
  "hosts": {
    "codex": { "role": "primary_plugin", "hooks": "codex_hooks_json", "install": "…" },
    "cursor": { "role": "thin_skill_rules", "hooks": "not_applicable", "install": "… not a Codex plugin install" },
    "cli": { "role": "same_store_scripts", "hooks": "not_applicable", "install": "…" }
  },
  "never_store": ["secrets", "tokens", "transcripts", "raw chat"],
  "agents_source": "AGENTS.md",
  "cursor_surface": "thin skill/rules only"
}
```

If the shared-memory module cannot load, Doctor still returns a block with
`cloud_sync: false` and an `error` string — it does not invent a healthy Cursor
plugin install.

CLI memory text (`pala_memory`) prints the same `db_path` under “Ortak store”.

## Drift checks

Self-audit `shared_memory` (source profile) requires:

1. ADR-017 in `DECISIONS.md`
2. `AGENTS.md` multi-host / single-source note
3. `portable/cursor/SKILL.md` markers (evidence labels, `AGENTS.md`, sqlite, no Codex plugin claim)
4. Thin Cursor rule that points at `AGENTS.md`
5. This document (`docs/PALA_SHARED_MEMORY.md`) with hit/miss + `shared_store`

Contract tests: `scripts/test_pala_shared_memory.py`.

## See also

- ADR-017 in `DECISIONS.md`
- `docs/PALA_EVERYWHERE.md`
- `docs/PALA_0_5_MEMORY_CONTRACT.md`
- `docs/PALA_0_7_LOCAL_STORE.md`

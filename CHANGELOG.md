# Changelog

All notable changes to Pala Project Studio are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows the plugin manifest (`0.x.y+codex.…`) and GitHub tags `v0.x.y`.

## [Unreleased]

### Added
- M30 vibe Codex host-fit: `scripts/pala_tokens.py` approx-token helper;
  `scripts/test_pala_host_fit.py`; `references/kontrol-et.md` for thin skill.
- M29 Gate 0 P0 smoke runner `scripts/pala_p0_smoke.py` →
  `artifacts/codex-compat/p0-smoke.json` (launcher, lifecycle, fail-closed,
  path-memory, kontrol-et statuses).
- M29-T2 command/path failure memory: `scripts/pala_cmd_memory.py` + SQLite
  `tool_attempts` (block blind retries; `--approve-retry`; DEBUGGING summary;
  context/SessionStart `do not retry` hint).
- M29-T1/T3/T4 cold-session packet: `scripts/pala_cold_packet.py`
  (evidence-first ≤2 KB minimal profile; `stale-context`; doc budgets
  minimal|standard|milestone; capability preflight; parallel worktree
  checkpoint fields). Wired into SessionStart + `pala_state context`.

### Changed
- SessionStart dual budget: `SESSION_CONTEXT_CHAR_LIMIT=1800` +
  `SESSION_CONTEXT_TOKEN_BUDGET=900` (under Codex ~1000-token additionalContext
  hard cap); cold packet preferred over legacy health prose.
- Skill body thinned (≤480 words); numbered `kontrol et` checklist moved to
  `references/kontrol-et.md`.
- `docs/CODEX_SCOPE_AND_LIMITS.md` refreshed 2026-08-09 for host caps.
- Skill/report/state guidance stays plugin-root-aware via `pala_paths`
  (no `../../scripts` from project cwd).

### Evidence (M30 vibe Codex host-fit — 2026-08-09)
- Branch `feat/m30-vibe-codex-host-fit`; focused unittest Ran 68 / OK.
- `py -3 scripts/verify.py --mode installed` exit 0.
- Gate0 `pala_p0_smoke.py` exit 0; 9/9; SHA-256
  `6FE7A3EC63D850BE8DE145EB260A0E401170D08FAB4C85A1BC5C50DD69680AEB`.
- Tam verify source full = `not-run`.
- Hooks UI `configured-not-verified`; soft “A/B fixed” yok.

### Evidence (source application close — Codex conditional acceptance)
- Gate0+M29 kaynak kabul; yeni P1 yok; push/PR/release/install bu turda yok.
- Source SHA `10dd7de617d7198e06ea2f42ec3829fbd215a532` (working tree dirty).
- `p0-smoke.json` SHA-256 `a5ce3bbf9c6d1dce285858a367964b1d6c48bc135ab944cc8f0feb231c0cbcda`.
- Gate 0: `py -3 scripts/pala_p0_smoke.py` exit 0; overall passed 9/9.
- Combined unittest Ran 69 / OK exit 0
  (`test_pala_cold_packet` + `cmd_memory` + `p0_friction` + `debug_gate` + `memory`).
- `py -3 scripts/verify.py --mode installed` exit 0.
- Tam verify source full = `not-run`.
- Marketplace on Codex machine still `0.8.0+…` = canlı doğrulanmamış;
  Hooks UI `configured-not-verified`; soft “A/B fixed” yok.

## [0.8.1] - 2026-08-08

### Added
- M25 shared memory: ADR-017, `pala_shared_memory.py`, Doctor `shared_store`,
  `portable/cursor/` skill + `.cursor/rules/pala-memory.mdc`.
- Wave E multi-host proof: hit/miss helpers, portable skill drift audit,
  `docs/PALA_SHARED_MEMORY.md` (Doctor `shared_store` surface).
- M10 canary module `pala_m10.py` (RTK lock/rewrite, MCP pins, OpenSpec bind,
  code-review-graph uv suite membership).
- Runtime install verification: `pala_self_audit --profile runtime`,
  `verify.py --mode installed`, `docs/INSTALL_ARTIFACT_CONTRACT.md`.
- Cold-start timing script `pala_cold_start.py` (milliseconds only; no %).
- Demo `DEMO-005` owner handoff (`reports/OWNER_DEMO.md`).
- `docs/CODEX_PLUGIN_CHECKLIST.md` + artifact E2E CI smoke job.

### Changed
- `code-review-graph` included in Pala uv-isolated expert suite.
- Closed stale GitHub PR `#5` (superseded by mainline 0.5–0.8.0).
- Doctor self-audit hint points at `--profile runtime` for marketplace roots.

### Fixed
- Issue #13: `tree_fingerprint` hashes allowlisted bundle files only; `__pycache__`
  no longer false-`drifted` healthy installs.
- `PYTHONUTF8` code-intel test no longer fails when parent env already sets it.

### Evidence
- GitHub tag/release `v0.8.1`: `not-run` (owner yetkisi ayrı)
- Primary download stays on published `v0.8.0` until release.
- Source application phase closed under Codex conditional acceptance
  (Gate0+M29); see [Unreleased] Evidence bindings for fresh SHA/hashes.

## [0.8.0] - 2026-08-08

### Added
- Chat presence trust line on SessionStart + skill Human Contract
  (`Pala burada — bu oturumda yanındayım.`; chip `Pala yanınızda`).
- Fork demo pack: `examples/demo-software-project/`, `pala_demo.py seed`,
  `docs/FORK_PACK.md`.
- Fail-closed `pala_self_audit.py` wired into `verify.py`; Doctor
  `self_audit=configured-not-verified` until verify runs.
- Durable error brain: parseable `DEBUGGING.md` + SessionStart `debug_open` +
  Status “Hata beyni” line.
- Demo Status HTML proof after seed (`pala_demo.prove_status_html`).
- PLAN agent task card parser (`parse_agent_task_cards`) and self-audit
  `agent_tasks` gate for multitask release readiness.

### Fixed
- Doctor `hooks_next_step` no longer confuses file `hook_safety=passed` with
  Codex UI `/hooks` trust.
- `Install-Pala` Doctor label prints `hook_safety=` explicitly.
- README release badge stays honest until GitHub publish is real.

### Documentation
- Vibe first-session + fork pack paths.
- Human M23 release checklist: `docs/RELEASE_0_8_0_CHECKLIST.md`.
- M24 multitask: PLAN task cards, AGENTS “Çoklu ajan / görev kartı”, vibe/fork
  pointers, demo ajan→görev örneği.
- World-standard GitHub surface (SUPPORT, CHANGELOG, PR template, docs index)
  carried from 0.7.1 line.

### Evidence
- Release: https://github.com/trugurpala/pala-project-studio/releases/tag/v0.8.0
- Target: `c192ff3`
- ZIP SHA-256: `3EA17A1CEFF7DEEBF906D03184D9B9F09F800B4B64B4AD0D880AD30C22A6916E`

## [0.7.1] - 2026-08-07

### Added
- Windows Codex PATH discovery when `codex` is not on PATH.
- Doctor `plugin_ready` vs `experts_ready` split.
- `docs/PALA_EVERYWHERE.md` distribution contract.
- `docs/VIBE_FIRST_SESSION.md` first-10-minutes path.

### Evidence
- Release: https://github.com/trugurpala/pala-project-studio/releases/tag/v0.7.1
- ZIP SHA-256: `4CD388A40392B7C8AAE0A1A742307993F829F116FB3D4F08989FB1A009230A9D`

## [0.7.0] - 2026-08-07

### Added
- Local SQLite store (`pala.sqlite`) for catalog, provisions, events.
- Status HTML timeline panel (server-free).
- ADR-015 local store decision.

## [0.6.0] - 2026-08-07

### Added
- Server-free local HTML status page as first session surface.
- CSS-only sidebar, freshness badges, update banner.
- ADR-013 / ADR-014 visual-surface phase.

## [0.5.0] - 2026-08-07

### Added
- Project memory contract (ADR-012).
- Plain-language `pala_state memory` CLI.
- Friendly Status mode wiring.

## [0.4.4] - prior

### Notes
- 0.4.x single-door Windows install, Doctor/Repair/Update, managed experts.
- See git history and `PROGRESS.md` for M1–M19 evidence.

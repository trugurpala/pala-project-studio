# Changelog

All notable changes to Pala Project Studio are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows the plugin manifest (`0.x.y+codex.…`) and GitHub tags `v0.x.y`.

## [Unreleased]

### Notes
- M25 (Cursor/CLI ortak hafıza) DRAFT — uygulama yok.

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

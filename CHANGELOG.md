# Changelog

All notable changes to Pala Project Studio are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows the plugin manifest (`0.x.y+codex.…`) and GitHub tags `v0.x.y`.

## [Unreleased]

### Fixed
- Doctor `hooks_next_step` no longer confuses file `hook_safety=passed` with Codex UI `/hooks` trust.
- `Install-Pala` Doctor label prints `hook_safety=` explicitly.

### Documentation
- Vibe first-session paste path clarified (`docs/VIBE_FIRST_SESSION.md`).
- World-standard GitHub surface: SUPPORT, CHANGELOG, PR template, docs index.

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

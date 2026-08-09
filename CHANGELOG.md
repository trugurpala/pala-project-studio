# Changelog

All notable changes to Pala Project Studio are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows the plugin manifest (`0.x.y+codex.…`) and GitHub tags `v0.x.y`.

## [Unreleased]

M30 vibe/Codex host-fit close + vibe-install UX (Codex-native first) + local
0.8.1 release ground (no GitHub tag yet).

### Added
- Pala↔Superpowers continuity design + refs (`using-pala`, plan/execute tickets, debugging→INC-) and verification-before-done gate wording.
- Delivery Quality Engine: read-only project-native gate discovery,
  ignored per-ticket evidence ledger, safe artefact references, truthful
  `passed`/`blocked` decision, and five-signal Status HTML.
- Source, portable-ZIP, and installed-package verification profiles;
  `verify.py --mode portable` extracts and verifies an archive safely.
- Internal 20-source pattern intake matrix in `docs/PALA_0_9_BENCHMARK.md`;
  patterns are evaluated, not copied or installed.
- Approx-token helper `scripts/pala_tokens.py` and host-fit contracts
  `scripts/test_pala_host_fit.py`.
- Thin-skill companion `skills/pala-project-finisher/references/kontrol-et.md`.
- Owner release ground: `docs/RELEASE_0.8.1_CHECKLIST.md`, design
  `docs/superpowers/specs/2026-08-09-m30-close-081-local-release-design.md`.
- Vibe-install UX: `docs/VIBE_INSTALL.md`, root `KUR.md` + `Kur.cmd`
  (Bypass → Install-Pala), Turkish 3-step GUI next-steps after Install.
- Prior wave carry-forward still landing with this branch: Gate0
  `pala_p0_smoke.py`, cmd memory, cold packet, shared memory, M10, install
  artifact contract (see 0.8.1 section for the shipped narrative).

### Changed
- Skill points at `references/using-pala.md`; specialist-routing prefers Pala continuity refs before optional `superpowers:`.
- SessionStart dual budget under Codex ~1000-token `additionalContext` hard
  cap: `SESSION_CONTEXT_CHAR_LIMIT=1800`, `SESSION_CONTEXT_TOKEN_BUDGET=900`;
  cold packet preferred over long health prose; `hooks.json` limit synced.
- Skill body kept ≤480 words (progressive disclosure); kontrol checklist lives
  in the reference file.
- `docs/CODEX_SCOPE_AND_LIMITS.md` refreshed 2026-08-09; clarifies
  `additionalContextLimit` is Pala **char-sync**, not the host token-spill
  semantic (clip still approx-token ≤900).
- STATUS rewritten for 2026-08-09 truth; Vibe path points at release checklist.
- Install story: Codex-native CLI first (`marketplace add` + `plugin add`);
  ZIP/`Kur.cmd` secondary offline toolkit. Marketplace local `path` is `"."`
  (not `"./"`). README / `VIBE_FIRST_SESSION` / `PALA_EVERYWHERE` / release
  checklist aligned; Plus-paste and ZIP-upload-as-primary stay myths.
- Vibe honesty: unregistered cwd → SessionStart silent; Doctor
  `plugin_next_step` for `plugin=drifted` (Repair/Update/sync).
- Context restore honesty: SessionStart matcher `startup|resume|clear|compact`;
  resume/clear/compact prefixes; cold-packet path always surfaces `next=`;
  Turkish “Codex unuttu → ne olur” in `VIBE_FIRST_SESSION` + `CODEX_SCOPE`;
  skill mid-turn re-read line (no fake continuous memory).

### Fixed
- Packaging allowlist refuses `credentials.json`, `id_rsa` / secret-shaped
  basenames, and `*.sqlite` in both portable ZIP and install bundle paths.
- Checkpoint / commit materialization no longer treats
  `.codex/plugin-data/**` (v3 tickets) as user working-tree changes — same
  exclusion class as `.codex/pala-workflow.json`.
- Uninstall again refuses user-added non-junk files beside the allowlist
  (`status=modified`) while `__pycache__` junk still does not block uninstall
  or mark drift (issue #13).
- Uninstall also refuses user-added symlinks rather than following or deleting
  them.
- SessionStart owned-ticket merge no longer drops PreCompact `needs_reconcile`
  (restore path after compact + dirty ticket).

### Evidence (local close — 2026-08-09)
- Branch `feat/m30-vibe-codex-host-fit`; push/PR/tag **not run** (owner).
- Context-restore focused unittest
  (`test_pala_host_fit` + `PalaHookTests` + `test_plugin_experience`):
  Ran 59 / OK (`passed`).
- Full source `verify.py`: `passed` (Ran 349 / OK, skipped=1;
  reproducible_zip SHA-256
  `6E51FFFB8A5765EA92B05504885D69AD601E2D7E25987FD04F5F88090B548CFC`).
- Final Desktop ZIP: `pala-project-studio-0.8.1-final.zip`
  SHA-256 `5C2DF2733EE54B82D12B34D93523A2EA4833B7E4C628CBE9D93C0188D5AE0E01`
  (136 entries).
- Hooks UI trust: `configured-not-verified`. Soft “A/B fixed”: yok.

## [0.8.1] - 2026-08-08

Source/manifest prep on mainline waves; **GitHub tag still `not-run`** until
owner runs `docs/RELEASE_0.8.1_CHECKLIST.md`. Primary public download remains
`v0.8.0` until then.

### Added
- M25 shared memory: ADR-017, `pala_shared_memory.py`, Doctor `shared_store`,
  `portable/cursor/` skill + `.cursor/rules/pala-memory.mdc`,
  `docs/PALA_SHARED_MEMORY.md`.
- M10 canary `pala_m10.py` (RTK lock/rewrite, MCP pins, OpenSpec bind,
  code-review-graph uv suite).
- Runtime install verification: `pala_self_audit --profile runtime`,
  `verify.py --mode installed`, `docs/INSTALL_ARTIFACT_CONTRACT.md`.
- Cold-start timing `pala_cold_start.py` (ms only; no %).
- Status HTML a11y decision strip + report open hint.
- M28 debug gate; M29 cold packet, cmd memory, Gate0 smoke.
- Demo owner handoff + stop scenarios; Codex plugin checklist; CI artifact smoke YAML.

### Changed
- `code-review-graph` in Pala uv-isolated expert suite.
- Doctor self-audit hint points at `--profile runtime` for marketplace roots.
- Skill/report paths marketplace-aware via `pala_paths` (no project-cwd
  `../../scripts`).

### Fixed
- Issue #13: allowlisted `tree_fingerprint`; `__pycache__` no false `drifted`.
- `PYTHONUTF8` code-intel test idempotent when parent env already sets it.
- Doctor JSON print survives cp1254 consoles (`emit_json`).

### Evidence
- GitHub tag/release `v0.8.1`: `not-run`.
- Live mini A/B on Pala-Pc (0.8.1 temp profile): path-not-repeated + complete
  fail-closed/close `passed`; soft full-product A/B fixed **yok**.
- See Unreleased for M30 host-fit close digests.

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

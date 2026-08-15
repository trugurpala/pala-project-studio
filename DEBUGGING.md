# Debugging log

## Format

Required fields: Symptoms, Root cause, Fix criteria, Proved by, Related files,
Date, Status. Keep data sanitized and use canonical evidence labels.

## Incidents

### INC-20260815-m80-windows-symlink-capability
- **Symptoms:** Local canaries skip with WinError 1314; branch CI created links, installer rejection passed, but portable rejection raised no error.
- **Root cause:** The portable test replaced `source_files`, bypassing its only link check; `archive_entries` trusted the injected list.
- **Fix criteria:** The archive boundary independently rejects every link; both required Windows canaries and branch CI exit 0.
- **Proved by:** focused release suite 8/8 passed with one local privilege skip; required Windows canaries passed in run 31883582516.
- **Related files:** installer/release-candidate tests and Quality workflow.
- **Date:** 2026-08-15
- **Status:** fixed (`passed`)

### INC-20260815-m80-root-document-budget

- **Symptoms:** The replacement full verifier stopped because new M81 incidents grew `DEBUGGING.md` to 86/80 lines.
- **Root cause:** Fixed history stayed in the active projection while new branch-CI incidents were added.
- **Fix criteria:** Keep immutable public baseline history concise, mark imported WIP current evidence `not-run`, and keep STATUS/PLAN/PROGRESS/DEBUGGING within 80/80/60/80 lines without relaxing tests.
- **Proved by:** focused document contract and replacement full verifier (763 tests, exit 0).
- **Related files:** `STATUS.md`, `PLAN.md`, `PROGRESS.md`, `DEBUGGING.md`, `scripts/test_pala_repo_cleanup.py`.
- **Date:** 2026-08-15
- **Status:** fixed (`passed`)

### INC-20260815-m44-windows-plugin-host-bootstrap

- **Symptoms:** Existing Plugins/hooks UI did not show newly installed Pala; launcher discovery selected a denied WindowsApps executable.
- **Root cause:** Host snapshot predated install/config; the active session also retains its pre-update plugin snapshot.
- **Fix criteria:** Installed 1.2.0 Doctor/resolver/self-audit pass, then trust `/hooks` and observe 1.2.0 in a fresh session.
- **Proved by:** installed 1.2.0 plugin/cache/marketplace, resolver, Doctor, runtime self-audit and installed verifier `passed`; fresh-session UI observation `configured-not-verified`.
- **Related files:** `scripts/Install-Pala.ps1`, `scripts/pala_installer_codex.py`, installed marketplace.
- **Date:** 2026-08-15
- **Status:** open (`configured-not-verified`)

### INC-20260815-m81-playwright-browser-path
- **Symptoms:** Branch browser job installed Chromium in the runner cache, then looked for it below `node_modules`.
- **Root cause:** `PLAYWRIGHT_BROWSERS_PATH=0` was applied only when test config loaded, after the CI install step.
- **Fix criteria:** Install and run share one explicit browser path; generated-page E2E exits 0.
- **Proved by:** CI contract and real local Chromium journey `passed`; browser install step passed in run 31883582516.
- **Related files:** Quality workflow and release-candidate CI contract.
- **Date:** 2026-08-15
- **Status:** fixed (`passed`)

### INC-20260815-m81-posix-orphan-observation
- **Symptoms:** Ubuntu source verify classified a live descendant as `unexpected_exit`, not `orphan_detected`.
- **Root cause:** POSIX active-process lookup returned zero as soon as the owned parent exited and never inspected its process group.
- **Fix criteria:** Observe only the owned process group, detect its live descendant, and clean it without foreign PID targeting.
- **Proved by:** Linux Docker and Windows focused suites 11/11, then Ubuntu verify in run 31883582516 `passed`.
- **Related files:** process supervisor and focused contracts.
- **Date:** 2026-08-15
- **Status:** fixed (`passed`)

### INC-20260815-m81-roadmap-card-count
- **Symptoms:** Full verifier failed self-audit after the explicit M81 remediation card raised the parsed roadmap total from seven to eight.
- **Root cause:** The repository contract still asserted the earlier exact card count.
- **Fix criteria:** Self-audit and its repository contract agree on all eight current cards without weakening card parsing.
- **Proved by:** focused self-audit contract and replacement full verifier (763 tests, exit 0).
- **Related files:** `PLAN.md`, `scripts/test_pala_self_audit.py`.
- **Date:** 2026-08-15
- **Status:** fixed (`passed`)

### INC-20260815-m81-posix-python-launcher
- **Symptoms:** Branch browser job installed Chromium successfully, then failed with `spawnSync py ENOENT` on Ubuntu.
- **Root cause:** The real generated-page journey invoked the Windows-only `py -3` launcher.
- **Fix criteria:** The journey selects a deterministic platform Python launcher and exits 0 on Ubuntu and Windows.
- **Proved by:** run 31883582516 browser job 95009422370 `blocked`; launcher contracts 7/7, real journey 1/1, full verifier 764 tests and final branch run 31883864441 `passed`.
- **Related files:** generated-page Playwright journey and its launcher contract.
- **Date:** 2026-08-15
- **Status:** fixed (`passed`)

Historical incidents and public-release evidence remain in Git history and
Failure Intelligence; only active failures are projected here.

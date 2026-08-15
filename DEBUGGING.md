# Debugging log

## Format

Required fields: Symptoms, Root cause, Fix criteria, Proved by, Related files,
Date, Status. Keep data sanitized and use canonical evidence labels.

## Incidents

### INC-20260815-m80-cross-os-zip-metadata
- **Symptoms:** Equal Windows/Linux payloads produced different ZIP SHA-256 values.
- **Root cause:** `ZipInfo.create_system` inherited host defaults (0 versus 3).
- **Fix criteria:** Pin ZIP creator metadata and compare two real host builds.
- **Proved by:** Windows + Linux Docker builds, 211 entries, equal `FCA481DD...CA4330F` SHA.
- **Related files:** `scripts/build_portable.py`, release-candidate tests.
- **Date:** 2026-08-15
- **Status:** fixed (`passed`)

### INC-20260815-m80-windows-symlink-capability
- **Symptoms:** Windows symlink canaries skip with WinError 1314 on this profile.
- **Root cause:** The local host lacks symlink privilege; product behavior was not executed.
- **Fix criteria:** Required Windows CI must create and reject both package and installed-tree links.
- **Proved by:** local required mode exits nonzero; branch CI is `not-run` before the authorized push.
- **Related files:** installer/release-candidate tests and Quality workflow.
- **Date:** 2026-08-15
- **Status:** open (`configured-not-verified`)

### INC-20260815-m80-source-secret-fixtures

- **Symptoms:** Live repository secret scan blocked three test modules on bearer-shaped literals.
- **Root cause:** Redaction fixtures embedded complete credential syntax in source text.
- **Fix criteria:** Assemble fixtures at runtime; do not exempt tests; retain a blocking real-fixture regression.
- **Proved by:** full-repo secret scan and runtime bearer regression (2 tests, exit 0).
- **Related files:** Control Center, Failure Intelligence, broker and publication tests.
- **Date:** 2026-08-15
- **Status:** fixed (`passed`)

### INC-20260815-m80-m75-test-isolation

- **Symptoms:** `scripts.test_pala_m75_completion` failed alone but appeared green after another module.
- **Root cause:** Local imports relied on an earlier test mutating `sys.path`.
- **Fix criteria:** Bootstrap the scripts path locally and pass observed host/receipt inputs.
- **Proved by:** isolated M75 completion suite (9 tests, exit 0) and Ruff (exit 0).
- **Related files:** `scripts/test_pala_m75_completion.py`.
- **Date:** 2026-08-15
- **Status:** fixed (`passed`)

### INC-20260815-m80-policy-stale-fixture

- **Symptoms:** Full verification failed the stale verified-source policy contract.
- **Root cause:** The test reused the now-truthful unverified 1.2.0 release source as a verified fixture.
- **Fix criteria:** Build a private verified-local stale fixture without changing release truth.
- **Proved by:** focused policy and debugging contracts, then the full verifier.
- **Related files:** `scripts/test_pala_policy.py`, `policies/release.json`, `DEBUGGING.md`.
- **Date:** 2026-08-15
- **Status:** fixed (`passed`)

### INC-20260815-m80-root-document-budget

- **Symptoms:** `py -3 scripts/verify.py` stopped because STATUS (87/80), PROGRESS (61/60) and DEBUGGING (90/80) exceeded concise root-document budgets.
- **Root cause:** Imported M76--M79 narrative and historical evidence were retained as current projections instead of concise, evidence-scoped read models.
- **Fix criteria:** Keep immutable public baseline history concise, mark imported WIP current evidence `not-run`, and keep STATUS/PLAN/PROGRESS/DEBUGGING within 80/80/60/80 lines without relaxing tests.
- **Proved by:** focused document tests (29, exit 0) and `py -3 scripts/verify.py` (733 tests, reproducible ZIP, exit 0).
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

Historical incidents and public-release evidence remain in Git history and
Failure Intelligence; only active failures are projected here.

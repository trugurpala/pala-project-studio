# Debugging log

## Format

Each incident includes Symptoms, Root cause, Fix criteria, Proved by,
Related files, Date, Status. Never store secrets, credentials, transcripts, tokens, or
customer data. Labels: `passed|not-run|blocked|configured-not-verified`.

## Incidents

### INC-20260813-release-ci-portability

- **Symptoms:** GitHub Quality failed on Linux and Windows while local release gates passed.
- **Root cause:** tests assumed local `.mcp.json`, Windows spelling/separators.
- **Fix criteria:** portable assertions; local source and exact CI commit pass.
- **Proved by:** focused tests + source verify passed; CI run `31674469025` passed.
- **Related files:** `scripts/test_pala_playwright.py`, `scripts/test_pala_semgrep.py`.
- **Date:** 2026-08-13
- **Status:** fixed (`passed` contract)

### INC-20260813-m74-control-center-bootstrap

- **Symptoms:** An explicit `paneli ac` request opened one generated status HTML file, but a clean installation with no registered project did not contain the Pala Control Center or its four owner questions.
- **Root cause:** `pala_report.build_status_model()` delegated the owner fragment to `pala_product_cli.public_status()`, which raised when no canonical ProductContract existed; the report caught that error and replaced the complete fragment with an empty string. The retained projection also hard-coded `Pala 1.0 Owner Cockpit`.
- **Fix criteria:** the real report-generation path renders canonical product identity and a complete read-only Control Center for no-project, active-project, and unreadable-project states; explicit panel intents open it once and ordinary flows open nothing.
- **Proved by:** RED `py -3 -m unittest scripts.test_pala_control_center.ControlCenterTests.test_real_report_path_bootstraps_control_center_without_project_contract -v` = exit 1 before the fix; GREEN `py -3 -m unittest scripts.test_pala_control_center -v` = exit 0 (11/11).
- **Related files:** `scripts/pala_report.py`, `scripts/pala_product_cli.py`, `scripts/pala_owner_cockpit.py`, `scripts/test_pala_control_center.py`, `artifacts/release-1.1.1/m74-red.json`.
- **Date:** 2026-08-13
- **Status:** fixed

### INC-20260813-m74-installed-codegraph-runner

- **Root cause:** CodeGraph lifecycle lacked a packaged Quality-runner CLI; the
  self-test created it in marketplace, correctly causing ownership drift.
- **Symptoms:** Doctor `plugin=modified`; diff was `pala_codegraph_runner.py`.
- **Fix criteria:** packaged bounded runner, explicit state root, stale fail-close,
  Quality discovery, and fresh install without marketplace writes.
- **Proved by:** `py -3 -m unittest scripts.test_pala_codegraph.CodeGraphContractTests.test_quality_runner_requires_current_graph_and_supports_explicit_state_root -v`; `py -3 scripts/pala_codegraph_runner.py --project .`.
- **Related files:** `pala_codegraph_runner.py`, its tests, `.pala/quality.json`.
- **Date:** 2026-08-13
- **Status:** fixed

### INC-20260813-m74-public-bootstrap-and-routing

- **Symptoms:** Public `1.1.1` lacked Workbench; routing varied; completion
  reached `PACKAGE_READY` with required providers blocked.
- **Root cause:** plugin-only bootstrap, broad routing, missing environment gate.
- **Fix criteria:** From a genuinely empty Codex and Pala state, the single URL
  instruction installs plugin plus required Pala core providers, second install
  is a proved no-op, Doctor exits `0`, and exact `paneli aç` always invokes one
  complete Control Center. Product completion must remain blocked whenever a
  required core provider is absent or blocked.
- **Proved by:** public 1.1.1 readback passed; Doctor exit 2; native routing and
  required providers blocked while installed sample Quality passed.
- **Related files:** `artifacts/release-1.1.1/public-install-canary.json`, `scripts/pala_installer.py`, `scripts/pala_product_cli.py`, `skills/pala-project-finisher/SKILL.md`.
- **Date:** 2026-08-13
- **Attempts:** Real canaries found exact bootstrap adoption, VERIFIED retry, and
  `Pala panelini aç` guard gaps; all now fail closed outside exact contracts.
- **Proved by:** 16 focused/9 adversarial tests, 659 source tests, fresh Doctor,
  no-op, 3 positive/2 negative routes, canonical Quality 24/24: all passed.
- **CI portability:** Ubuntu correctly cannot install the Windows-x64 managed
  Workbench; its real-install contract is now explicitly Windows-only while
  cross-platform source/portable contracts continue to run on Ubuntu.
- **Status:** fixed (`passed` local candidate; public canary `not-run`)

Historical incidents remain in Git/Failure Intelligence; new failures stay here.

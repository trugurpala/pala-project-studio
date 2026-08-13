# Debugging log

## Format

Each `### INC-...` entry must include: Symptoms, Root cause, Fix criteria,
Proved by, Related files, Date, Status. Never store secrets, credentials,
transcripts, tokens, or real customer data. Evidence labels are `passed`,
`not-run`, `blocked`, and `configured-not-verified`.

## Incidents

### INC-20260813-release-ci-portability

- **Symptoms:** GitHub Quality failed on Linux and Windows while local release gates passed.
- **Root cause:** two tests assumed a machine-local `.mcp.json`, Windows path spelling,
  or Windows separators instead of testing the portable contracts.
- **Fix criteria:** all three assertions are platform-independent; source verify passes
  locally and the exact follow-up `main` commit is green on Linux and Windows CI.
- **Proved by:** `py -3 -m unittest scripts.test_pala_playwright scripts.test_pala_semgrep -v`
  = `passed`; `py -3 scripts/verify.py --mode source` = `passed`; GitHub Quality
  run `31674469025` on the follow-up main commit = `passed`.
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

- **Root cause:** the candidate plugin exposed CodeGraph lifecycle internals but
  did not package a stable Quality-runner CLI. The installed Codex self-test
  created that missing wrapper inside its own marketplace tree, correctly
  causing Doctor ownership drift after the run.
- **Symptoms:** candidate Doctor reported `plugin=modified`; exact file diff was
  the added `scripts/pala_codegraph_runner.py` (plus expected versioned source
  changes), not runtime `__pycache__`.
- **Fix criteria:** package the bounded runner in source, accept explicit
  `--state-root`, fail closed on stale/failed graph state, include it in current
  Quality discovery, and complete a fresh install without marketplace writes.
- **Proved by:** `py -3 -m unittest scripts.test_pala_codegraph.CodeGraphContractTests.test_quality_runner_requires_current_graph_and_supports_explicit_state_root -v`; `py -3 scripts/pala_codegraph_runner.py --project .`.
- **Related files:** `scripts/pala_codegraph_runner.py`,
  `scripts/test_pala_codegraph.py`, `.pala/quality.json`.
- **Date:** 2026-08-13
- **Status:** fixed

### INC-20260813-m74-public-bootstrap-and-routing

- **Symptoms:** A clean public Codex profile installed/enabled `1.1.1`, but
  isolated Doctor returned exit `2`, `healthy=false`, `plugin_ready=false`, and
  no Workbench state. CodeGraph was absent and Semgrep blocked. Exact `paneli
  aç` passed once but asked which panel was intended in a second empty
  workspace. The installed-skill self-test reached `PACKAGE_READY` anyway.
- **Root cause:** The public URL flow installs the Codex plugin only; it does not
  bootstrap the Pala bundle/Workbench. The skill description does not make the
  no-project panel intent a deterministic routing trigger, and completion can omit required core
  health checks from its generated Quality contract.
- **Fix criteria:** From a genuinely empty Codex and Pala state, the single URL
  instruction installs plugin plus required Pala core providers, second install
  is a proved no-op, Doctor exits `0`, and exact `paneli aç` always invokes one
  complete Control Center. Product completion must remain blocked whenever a
  required core provider is absent or blocked.
- **Proved by:** public release readback SHA-256 = `passed`; public plugin
  inventory = installed/enabled `1.1.1`; isolated `pala_installer.py doctor`
  exit `2`; empty-workspace native panel retry = `blocked`; installed Decision
  Log Mini Quality = `passed` while CodeGraph=`absent` and Semgrep=`blocked`.
- **Related files:** `artifacts/release-1.1.1/public-install-canary.json`, `scripts/pala_installer.py`, `scripts/pala_product_cli.py`,
  `skills/pala-project-finisher/SKILL.md`.
- **Date:** 2026-08-13
- **Status:** open (`blocked`)

Verified historical incidents remain available in Git history and in Failure
Intelligence. New reproducible failures are recorded here only while active.

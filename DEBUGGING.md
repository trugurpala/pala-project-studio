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
  = `passed`; GitHub Quality follow-up = `not-run`.
- **Related files:** `scripts/test_pala_playwright.py`, `scripts/test_pala_semgrep.py`.
- **Date:** 2026-08-13
- **Status:** configured-not-verified

Verified historical incidents remain available in Git history and in Failure
Intelligence. New reproducible failures are recorded here only while active.

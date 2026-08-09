# Pala 0.9 — Delivery Quality Engine

Pala 0.9 turns a completed-looking ticket into an evidence-backed delivery
decision. It is local-first: it discovers only commands and scanners that are
already part of the project or already installed. It never installs packages,
uses the network, runs a deploy hook, or lets a hook execute a quality gate.

## Flow

```text
discover changed surface -> read-only plan -> local evidence ledger
  -> explicit command run -> result + artefact -> checkpoint/release decision
```

The engine knows these gate kinds: `unit`, `lint`, `typecheck`, `build`,
`integration`, `browser`, `security`, `dependency`, `migration`, and
`runtime-smoke`. A missing command is not `passed`: it remains `not-run`,
`blocked`, or `configured-not-verified`.

## Ticket flow

```powershell
# 1. Inspect only: no commands run and no files written.
py -3 scripts/pala_quality.py plan --cwd C:\project --tier ticket

# 2. Create / refresh the ignored local ledger for the active ticket.
py -3 scripts/pala_quality.py init --cwd C:\project --ticket M31-T1 --tier ticket

# 3. Run the selected project-native command yourself, then record its fact.
py -3 scripts/pala_quality.py record --cwd C:\project --ticket M31-T1 `
  --check unit:test --status passed --command "npm run test" --exit-code 0

# 4. Read the truthful delivery decision.
py -3 scripts/pala_quality.py status --cwd C:\project --ticket M31-T1
```

Evidence lives at `.codex/plugin-data/pala/v3/quality/<ticket>.json`, which is
ignored by Git. It records the risk surface, selected checks, exact approved
command, exit code, timestamp, and an optional artefact path inside the project.
It does not accept a secret-shaped command or detail, an artefact outside the
project, or `passed` without exit code `0`. Reopening a ticket retains evidence
only for an unchanged, identical gate and the same changed-surface digest. A
content change at the same file path invalidates an earlier pass.

## Project-owned quality contract

Discovery is deliberately conservative. A repository can declare its own safe,
shell-free gates in `.pala/quality.json`; each command is an `argv` array rather
than a shell string. This lets a project expose its real source verification,
migration check, or offline scanner without Pala guessing a command from a
framework name or CI text.

```json
{
  "schema_version": 1,
  "checks": [
    {
      "id": "source-verify",
      "kind": "integration",
      "argv": ["py", "-3", "scripts/verify.py", "--mode", "source"],
      "tiers": ["ticket", "milestone", "release"]
    }
  ]
}
```

Generated/vendor/runtime trees are skipped during discovery and listed as
ignored paths when relevant, so they do not make an unrelated project look like
a Python/UI change or inflate the risk surface. A detected Playwright config
without an explicit project-owned browser command is shown as
`configured-not-verified`, never silently omitted.

## Delivery boundary

Development can continue while a gate is red or missing. A quality claim is
different: add `--quality-ticket <ticket>` to checkpoint or complete and Pala
fails closed until every required gate is `passed`.

```powershell
py -3 scripts/pala_state.py checkpoint --cwd C:\project --ticket M31-T1 `
  --quality-ticket M31-T1 --tier ticket --verification "passed: reviewed" `
  --next-action "owner handoff"
```

`pala_report.py` reads the ledger and puts five safe signals in Status HTML:
active ticket, risk level, quality coverage, last missing/failed gate, and one
next action. It deliberately does not render command output, raw logs, or
secrets.

## Browser and security rules

Browser coverage becomes required only when the project has a UI *and* an
existing Playwright configuration/command. Pala does not add Playwright. The
recommended project-owned CI settings are Chromium, retries in CI,
`trace: 'on-first-retry'`, video/screenshot on failure, and an HTML report.

Security and dependency checks use an existing project-owned script or a simple
existing CI command only when its named scanner is already installed. An
unavailable scanner is `configured-not-verified`, never a pass. `osv-scanner`
is more restrictive: a CI mention is configuration evidence only because its
normal scan may use the network; Pala requires an explicit project-owned,
offline contract command before it can become a runnable gate. Configured
scripts that look destructive are blocked for manual review rather than
selected as a Pala gate.

Pala also strips remote-URL userinfo, query strings, and fragments before a
remote reaches the local catalog, SQLite provision history, event timeline, or
Status HTML. Clone input containing URL credentials is rejected; use the Git
credential manager instead.

## Measurement contract

No targets are claimed before two real projects establish a baseline. Track:

- Critical-flow evidence completeness: completed tickets with every required
  gate backed by evidence / completed tickets.
- Release gate pass rate and regression escape rate.
- Median time-to-green per comparable ticket type and environment.

Guardrails are absolute: zero false `passed`, zero unsupported release/deploy
claim, and zero user-data loss.

## Package profiles

```powershell
py -3 scripts/verify.py                                      # source
py -3 scripts/verify.py --mode portable --root C:\pala.zip  # clean extract
py -3 scripts/verify.py --mode installed --root <marketplace>
```

The portable check rejects unsafe archive paths and source-only state documents;
the installed check remains lean. Uninstall refuses to remove a modified tree,
including a user-added symlink. Pala-owned bytecode cache remains harmless.

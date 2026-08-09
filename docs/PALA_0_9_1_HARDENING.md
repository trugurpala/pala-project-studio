# Pala 0.9.1 — Delivery Integrity Hardening Plan

## Product decision

Pala competes as a delivery control system for a solo builder, not as a large
prompt collection. Its differentiator is that every ticket can answer: what
changed, which checks actually ran, what evidence exists, what is still missing,
and whether it is safe to call the work ticket-ready or release-ready.

This plan adopts patterns, not source code or third-party skills:

| Pattern source | Narrow Pala use |
| --- | --- |
| [Superpowers](https://github.com/obra/superpowers) | thin vertical slices and verification before completion |
| [Agent Brain](https://github.com/rohitg00/agentbrain) | evidence artefacts, review, and handoff rather than prose-only completion |
| [OpenSpec](https://github.com/Fission-AI/OpenSpec) / [Spec Kit](https://github.github.com/spec-kit/) | acceptance criteria → implementation plan → checks traceability |
| [Playwright](https://playwright.dev/docs/test-configuration) | real user-flow artefacts only when a project already owns that flow |
| [Agent Skills](https://github.com/agentskills/agentskills) | thin, progressive-disclosure extension surface |
| [OpenSSF Scorecard](https://github.com/ossf/scorecard) | release-review signals, never an automatic release claim |
| [Trail of Bits agent guidance](https://github.com/trailofbits/claude-code-config) | hooks are not a security boundary; isolate browser and redact artefacts |

## P0 — implemented in this slice

1. **Evidence freshness:** a SHA-256 changed-surface digest binds an evidence
   ledger to file content, not merely the file-name list. Same-path changes
   invalidate earlier `passed` evidence.
2. **Truthful discovery:** vendor/runtime outputs are bounded and ignored;
   Playwright config without a project command becomes
   `configured-not-verified`; a scanner name in CI never lets Pala invent a
   command. OSV remains non-runnable unless the project explicitly describes a
   safe offline command.
3. **Project-native contract:** `.pala/quality.json` accepts only a short
   `argv` command list and explicit tiers. Invalid shell-like input fails closed.
4. **Secrets boundary:** remote URLs are normalized before local catalog,
   SQLite, event, and Status surfaces; historical rows are scrubbed on local
   store open. Provisioning rejects credentials in a URL and redacts a remote
   echoed by a Git error.

## Prioritized next work

| Priority | Outcome | Evidence of completion |
| --- | --- | --- |
| P1 | **Delivery contract** mapping acceptance criteria and critical user flows to required gates, artefacts, rollback notes, and owner demo | ticket cannot claim `release-ready` with an unmapped critical criterion |
| P1 | **Decision-first Status**: separate `Not assessed`, `Ticket ready`, `Release-ready`, and `Blocked`; list required gate names and one copyable next action | a green `1/1` ticket view cannot look like a release decision |
| P1 | **Reviewer packet**: concise diff/risk/criteria/evidence/known-limitations handoff | owner can review a ticket without raw logs or secrets |
| P2 | **Fixture evaluation corpus** spanning Node, Python, UI/no-UI, migration, scanner, and malformed contracts | false-`passed` regressions caught before packaging |
| P2 | **Browser isolation policy**: isolated profile, redacted traces/screenshots, explicit human permission for any browser state | no authenticated Chrome state enters evidence |
| P3 | **Advisory architecture adapters** for common stacks, opt-in and contract-tested | better native discovery without a Pala-owned framework registry |

## Guardrails

- No cloud memory, daemon, automatic package installation, automatic deploy,
  commit, push, PR, release, or browser-state reuse.
- A missing, failed, blocked, or unverified gate can never be represented as
  `passed`.
- Two real projects establish performance baselines before any speed target is
  claimed.
- Package, portable extract, installed mode, and uninstall integrity remain
  independent verification profiles.

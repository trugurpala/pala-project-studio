# Pala progress

## Immutable baseline

- Public `v1.1.2` release history: `passed`.
- M76--M79 implementation is retained as imported WIP; current canonical task,
  Quality and release evidence for its historical claims: `not-run`.

## Current program

- M44-T1 installed 1.2.0 plugin/cache/marketplace, resolver, Doctor, runtime
  self-audit and installed verifier: `passed`; fresh 1.2.0 session presence and
  `/hooks` UI trust: `configured-not-verified`.
- M80-T1 canonical reconciliation and hermetic source Quality: `passed` (733 tests, reproducible ZIP, exit 0).
- M80-T1 full local verifier before remediation: `blocked` by root-document budgets.
- M80-T2 continuity production wiring and canonical Quality: `passed` (12/12).
- M80-T3 host/process Quality wiring: `passed` (7/7).
- M80-T4 live Control Center/privacy: `passed` (10/10).
- M80-T5 local package/upgrade Quality: 7/8 `passed`; current source verifier
  is `passed` (763 tests, 5 expected skips); Windows branch symlink canary is
  `configured-not-verified`.
- Initial branch CI run 31882450222 passed cross-OS artifact/hash and the real
  upgrade matrix, then exposed three portability regressions (`blocked`).
- M81-T1 fixed symlink archive validation, Playwright cache alignment and POSIX
  orphan detection; focused cross-platform tests and full source verifier `passed`.
- Replacement run 31883582516 passed 7/8 jobs, including the required Windows
  symlink canary and both OS verifies; its only failure was the Ubuntu-only `py`
  launcher. Cross-platform launcher contracts, real E2E and the 764-test source
  verifier now `passed`.
- Final functional commit `071dbcd` passed all 8/8 branch jobs in run
  31883864441: browser, Windows symlink smoke, both OS verifies, real upgrade,
  deterministic builds and exact cross-OS hash comparison.
- M80-T6 final local Quality/branch-CI handoff: `not-run`.

Branch/commit/push and branch-CI monitoring are authorized. PR, tag, public
release and deploy remain unauthorized and `not-run`.
The functional release surface ends at `071dbcd` and is on origin with green
branch CI. Canonical completion remains the external WorkflowStore/Quality truth.
Labels: `passed` | `not-run` | `blocked` | `configured-not-verified`.

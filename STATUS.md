# Pala current status

- Public baseline: `v1.1.2` (`passed` historical release evidence).
- Git basis: `codex/pala-1.2.0-release-ready`; release-ready commits through `2ae2c02` are on origin; final browser-launcher remediation is local WIP.
- Canonical authority: TaskContract -> WorkflowStore -> Pala Quality Engine.
- Canonical active task: `M81-T1`; M80-T5 is checkpointed at 7/8 pending replacement branch CI.
- External acceptance: `M44-T1` fresh-session hook visibility is `configured-not-verified`.

## Current evidence

- Installed 1.2.0 plugin/cache/marketplace, resolver, Workbench Doctor, runtime self-audit and installed verifier: `passed` (fresh 2026-08-15 evidence).
- Fresh 1.2.0 Codex session presence and `/hooks` UI trust: `configured-not-verified`; the current session loaded the pre-update 1.1.2 snapshot.
- Required narrow gate: `passed` (128 tests, exit 0; 2026-08-15).
- Current network-free source verifier: `passed` (764 tests, 5 expected skips, reproducible ZIP `8F576CAF...33AC`, exit 0; 2026-08-15).
- M80-T2 continuity Quality: `passed` (12/12 required checks, trusted runner, exit 0; 2026-08-15).
- M80-T3 host/process Quality: `passed` (7/7 required checks, supervised execution, exit 0; 2026-08-15).
- M80-T4 live Control Center/privacy Quality: `passed` (10/10 required checks, supervised execution, exit 0; 2026-08-15).
- M80-T5 local package/upgrade evidence was 7/8; the required Windows symlink branch canary passed in run 31883582516 and awaits canonical Quality mapping.
- Branch CI run 31882450222 proved deterministic cross-OS hashes and the real upgrade matrix, then `blocked` on symlink archive validation, Playwright cache lookup and POSIX orphan observation.
- M81 focused fixes: Windows/Linux supervisor 11/11, release candidate 8/8, real Chromium 1/1 and required Ruff checks `passed`; replacement branch CI `not-run`.
- Run 31883582516 passed 7/8 jobs; only the Ubuntu `py` launcher failed. Cross-platform launcher contracts 7/7, real E2E 1/1 and the 764-test full verifier now `passed`; final branch CI `not-run`.
- M76--M79 code is imported local WIP. Its historical `DONE`, count and release claims are `not-run` until current TaskContract and Quality evidence exist.
- Remote `main` CI evidence applies only to public baseline; it does not validate imported WIP.

## Delivery truth

The public `v1.1.2` release remains immutable history. The local 1.2.0 artifact,
SBOM, inventory, self-verification and upgrade matrix are ready; M80-T5 stays
incomplete until the passed symlink canary is mapped and final branch CI proves all jobs.
Push through `2ae2c02` is `passed`; launcher commit/push and final CI are `not-run`.
PR, tag, release and deploy remain outside authority and are `not-run`.

Evidence labels: `passed` | `not-run` | `blocked` |
`configured-not-verified`.

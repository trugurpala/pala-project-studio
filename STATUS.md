# Pala current status

- Public baseline: `v1.1.2` (`passed` historical release evidence).
- Git basis: `codex/pala-1.2.0-release-ready`; release-source commit `66cb1ef` is on origin and branch run 31885899213 is `passed`.
- Canonical authority: TaskContract -> WorkflowStore -> Pala Quality Engine.
- Canonical active task: `M82-T1`; M80-T1--T6 and M81-T1 are `DONE`.
- External acceptance: `M44-T1` fresh-session hook visibility is `configured-not-verified`.

## Current evidence

- Installed 1.2.0 plugin/cache/marketplace, resolver, Workbench Doctor, runtime self-audit and installed verifier: `passed` (fresh 2026-08-15 evidence).
- Fresh 1.2.0 Codex session presence and `/hooks` UI trust: `configured-not-verified`; the current session loaded the pre-update 1.1.2 snapshot.
- Required narrow gate: `passed` (128 tests, exit 0; 2026-08-15).
- Current network-free source verifier: `passed` (765 tests, 5 expected skips, reproducible ZIP `F0ABDF67...A8068F`, exit 0; 2026-08-15).
- M80-T2 continuity Quality: `passed` (12/12 required checks, trusted runner, exit 0; 2026-08-15).
- M80-T3 host/process Quality: `passed` (7/7 required checks, supervised execution, exit 0; 2026-08-15).
- M80-T4 live Control Center/privacy Quality: `passed` (10/10 required checks, supervised execution, exit 0; 2026-08-15).
- M80-T5 source/package/upgrade evidence and the required Windows symlink canary passed; canonical basis freshness remains owned by the Quality ledger.
- Branch CI run 31882450222 proved deterministic cross-OS hashes and the real upgrade matrix, then `blocked` on symlink archive validation, Playwright cache lookup and POSIX orphan observation.
- M81 focused fixes: Windows/Linux supervisor 11/11, release candidate 8/8, launcher contracts 7/7, real Chromium 1/1 and required Ruff checks `passed`.
- Final branch run 31883864441 on `071dbcd` passed all 8/8 jobs: browser, Windows symlink smoke, both OS verifies, real upgrade, deterministic builds and exact cross-OS hashes.
- Branch-head run 31884221216 on `a3bcd53` also passed 8/8; final release Quality is 62/62 on the same clean basis.
- M82 red-first UTF-8 contract, 54 focused Python contracts, fatal lint, real offline Chromium, 765-test source verifier and branch run 31885899213 (8/8): `passed`.
- M76--M79 code is imported local WIP. Its historical `DONE`, count and release claims are `not-run` until current TaskContract and Quality evidence exist.
- Remote `main` CI evidence applies only to public baseline; it does not validate imported WIP.

## Delivery truth

The public `v1.1.2` release remains immutable history. The local 1.2.0 artifact,
SBOM, inventory, self-verification, upgrade matrix and M80-T6 handoff are ready.
M82-T1 source correction is locally and remotely clean; only final canonical Quality mapping remains. `/hooks` trust remains a separate human acceptance.
PR, tag, release and deploy remain outside authority and are `not-run`.

Evidence labels: `passed` | `not-run` | `blocked` |
`configured-not-verified`.

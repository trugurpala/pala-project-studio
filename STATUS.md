# Pala current status

- Public baseline: `v1.1.2` (`passed` historical release evidence).
- Git basis: `codex/pala-1.2.0-release-ready`; source commit `f54883f`; remaining changes are canonical handoff documents.
- Canonical authority: TaskContract -> WorkflowStore -> Pala Quality Engine.
- Canonical active task: `M80-T5`; recovered lease, Quality is `blocked` at 7/8.
- External acceptance: `M44-T1` fresh-session hook visibility is `configured-not-verified`.

## Current evidence

- Installed 1.2.0 plugin/cache/marketplace, resolver, Workbench Doctor, runtime self-audit and installed verifier: `passed` (fresh 2026-08-15 evidence).
- Fresh 1.2.0 Codex session presence and `/hooks` UI trust: `configured-not-verified`; the current session loaded the pre-update 1.1.2 snapshot.
- Required narrow gate: `passed` (128 tests, exit 0; 2026-08-15).
- Current network-free source verifier: `passed` (763 tests, 5 expected skips, reproducible ZIP, exit 0; 2026-08-15).
- M80-T2 continuity Quality: `passed` (12/12 required checks, trusted runner, exit 0; 2026-08-15).
- M80-T3 host/process Quality: `passed` (7/7 required checks, supervised execution, exit 0; 2026-08-15).
- M80-T4 live Control Center/privacy Quality: `passed` (10/10 required checks, supervised execution, exit 0; 2026-08-15).
- M80-T5 local package/upgrade evidence: `passed` for 7/8 required checks; Windows symlink branch canary is `configured-not-verified`.
- M76--M79 code is imported local WIP. Its historical `DONE`, count and release claims are `not-run` until current TaskContract and Quality evidence exist.
- Remote `main` CI evidence applies only to public baseline; it does not validate imported WIP.

## Delivery truth

The public `v1.1.2` release remains immutable history. The local 1.2.0 artifact,
SBOM, inventory, self-verification and upgrade matrix are ready; M80-T5 stays
incomplete until authorized Windows branch CI proves the required symlink canary.
Source commit is `passed`; push and branch CI are `not-run` under granted authority.
PR, tag, release and deploy remain outside authority and are `not-run`.

Evidence labels: `passed` | `not-run` | `blocked` |
`configured-not-verified`.

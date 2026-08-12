# Pala 0.9.3 — Modularity and quality ratchet

## Decision

Pala's own static audit found a real maintainability signal in the status
renderer: presentation, styling, and section composition shared one module.
M33-T1 separates those responsibilities without changing the public renderer
entry point or introducing a UI framework, server, external asset, or package
dependency.

## Ownership

| Module | Owner |
| --- | --- |
| `pala_view.py` | Model-to-page orchestration, public `render()` entry point, and static local-only page shell |
| `pala_view_sections.py` | Escaped, privacy-preserving status sections and delivery cards |
| `pala_code_audit.py` | Dependency-free hard security and maintainability review |

The HTML contract stays source-owned: no network, no raw ledger logs, no raw
secret, and no default exposure of local paths or provision URLs.

## Ratchet

1. `pala_code_audit.py --profile source` is a required source verification
   step. Hard security findings fail the gate; maintainability findings remain
   explicit `attention_required` work, never a hidden pass.
2. M33-T1 brings the high-touch `pala_view.py` root under the 800-line review
   trigger through focused extraction. It does not claim every historical
   module is now small.
3. Existing view contract tests protect delivery decision, required gate list,
   privacy-by-default, temporary-project suppression, and keyboard focus.
4. Ruff and Bandit remain isolated developer audit tools, not portable-runtime
   dependencies. Their historical baseline is triaged incrementally instead
   of being silently ignored or globally auto-fixed.

## Zero-test discovery guard

M33-T1 exposed a quality-plan false positive: bare `unittest discover` can
exit successfully while discovering no tests in a non-package `scripts/`
directory. The engine now selects one explicit conventional start directory
(`tests`, `test`, or `scripts`) and the `test_*.py` pattern. If test files use
multiple or unknown roots, it emits `configured-not-verified` with one action
to add a project-owned quality contract instead of inventing a passing command.

Discovery also ignores `artifacts/`, including local WIP payloads, so old
reports or copied fixtures cannot change a project's test, UI, or risk plan.

## Deferred, separate tickets

- `pala_quality`: policy-level `build_quality_plan` branch split (M35 only
  separates repository observation from policy/ledger/CLI ownership).
- `pala_state`: workflow reconciliation command and larger ownership split.
  M37 closes only its fixed-argv Git timeout inventory; lifecycle, SQLite and
  CLI ownership remain a separate modularity decision.
- Installer: M40 separates the external Codex bridge; integrity, rollback, and
  user-file preservation remain a separately owned core boundary.

These do not belong in the renderer ticket: unrelated cleanup would make
evidence less precise and increase regression risk.

## M35 — Quality discovery boundary

`pala_quality_discovery.py` now owns bounded, read-only project observation:
package/CI metadata, changed-surface digest, Git summary, and Python/UI shape.
`pala_quality.py` remains the small public orchestrator for policy, optional
quality contracts, ledger persistence, gate decisions, and CLI commands.

Every internal Git observation uses a resolved executable with fixed arguments,
`shell=False`, and a five-second timeout. A missing or timed-out Git executable
returns the existing conservative empty/unknown observation instead of hanging
the quality-plan command. No project test, build, scanner, network command, or
hook is executed by this boundary.

The static audit now protects both facts: the main quality orchestrator stays
below the 800-line review trigger, and it has no process call without a timeout.
The remaining large functions/modules remain visible as advisory work; M35 does
not claim that the entire codebase is small or lint-clean.

## M38 — Cold-packet read-only observation boundary

`pala_cold_packet_git.py` owns one small responsibility: bounded, local Git
observation for a cold-session packet. `pala_cold_packet.py` retains packet
policy, document budgeting, capability presentation, and lifecycle decisions.

The boundary resolves `git`, uses fixed arguments with `shell=False`, and has a
five-second timeout. A missing or timed-out command produces an unknown
observation. In particular, a missing `git status` result is `dirty: null`,
never `dirty: false`; a partial snapshot asks for Git verification before work
continues. The packet passes its one snapshot to capability reporting, so it
does not create a second, inconsistent set of Git subprocesses.

The same local-only boundary applies to the optional `uv tool dir --bin` probe
and the GitHub router's `origin` URL read. They fail to their existing
unavailable/unknown fallback and never trigger installation, network access, or
remote writes.

M38 intentionally does not add a blind timeout to release verification,
benchmarking, P0 smoke, or optional graph build/update. Those commands need
their own explicit timeout evidence and fail-closed result contracts instead of
being mechanically changed.

## M39 — State Git/checkpoint observation owner

`pala_state_git.py` now owns only the bounded, local Git and checkpoint
observation primitives: repository root, text/binary reads, changed-path and
worktree digests, checkpoint material, ancestry, and commit materialization.
`pala_state.py` re-exports those public helpers, so the CLI, hook, and existing
callers keep the same import and result contract.

The state module retains workflow/document policy: checkpoint basis,
reconciliation, SQLite lifecycle, and CLI decisions still belong to it. This is
an ownership extraction, not a behavior rewrite. The Git owner keeps fixed
arguments, `shell=False`, the five-second bound, NUL-safe path handling, and
the conservative missing/timeout fallbacks already covered by M37.

The installer now treats `scripts/pala_state_git.py` as a required runtime
file. A truncated custom bundle therefore fails before install, while the
portable packager's existing `scripts/*.py` allowlist carries the sibling into
every portable artifact.

M39 deliberately leaves the larger state lifecycle/SQLite/CLI split and the
installer's transaction/integrity core for separately designed tickets. The
state core is smaller, but it is not falsely presented as below the 800-line
review trigger.

## M40 — Installer external Codex bridge

`pala_installer_codex.py` owns the external boundary: Codex executable
discovery, fixed-argv JSON calls, marketplace inventory, cache comparison,
trusted legacy migration, add/update rollback, and removal. The bridge receives
identity, manifest-reading, and tree-fingerprint behavior as callbacks; it does
not import the installer core or duplicate its integrity policy.

`pala_installer.py` keeps its public API as thin wrappers and dynamically loads
the exact sibling bridge file using a cache key derived from its own path. This
prevents a source, portable, or installed tree from accidentally reusing another
tree's helper in direct-file loading scenarios. The bridge's Codex process call
is explicitly `shell=False` and retains the existing 30-second timeout.

Bundle validation now requires the bridge helper. A missing helper fails before
installation; portable packaging includes it through the existing scripts
allowlist. Bundle integrity, exact user-file protection, atomic replacement,
and rollback remain in the installer core and were not mixed into this refactor.

## M42 — Quality plan policy ownership

`pala_quality_policy.py` now owns only the deterministic, no-execution policy
that turns an already-observed repository into a quality plan. Its contract,
native-command, browser, scanner, and changed-surface helpers remain
local-first: they do not run a project command, install a tool, contact a
network service, or use a hook.

`pala_quality.py` remains the public facade for `build_quality_plan`, the
evidence ledger, deterministic gate decision, and command-line interface. The
facade re-exports the plan API so callers do not need to know about the new
owner. This boundary deliberately does not change which gates are required or
when a result can be `passed`.

The installer requires all three quality runtime siblings (facade,
discovery, policy). The portable packager already includes shipped scripts, but
the explicit installer contract makes a truncated bundle fail before it can
claim a usable quality engine.

The Status page also labels its `n/n` read-order figure as **working-context
readiness**, with an explicit note that it is neither project progress nor a
delivery decision. Delivery stays governed by the separately visible decision
card and its required evidence gates; no soft completion percentage is inferred
from available context files.

## M43-T6 — Cold packet and hook session ownership

`pala_cold_packet_packet.py` owns evidence-first packet assembly, while the
public `pala_cold_packet.py` facade supplies the established stale-state, Git,
budget, and formatting helpers. This preserves one Git snapshot and existing
test patch points without letting assembly become a single review-sized
function.

`pala_hook_session.py` owns bounded SessionStart context rendering. The hook
facade retains the public `session_context()` API and separates PreCompact,
SessionStart, SessionEnd, and Stop event dispatch into small handlers. Neither
owner invokes tests, builds, installs, network calls, or hook configuration.
Both siblings are mandatory installer runtime files, so a truncated bundle is
rejected before staging or replacement can mutate an installation.

Because hook files are a high-risk changed surface, the project-owned quality
contract explicitly requires the local, shell-free `pala_code_audit.py --root
.` security gate at milestone and release tiers. This is an evidence plan only:
the hook still never executes the audit, test suite, build, or a network call.

## M43-T7 — Status view CSS and document ownership

`pala_view.py` is now a compatibility facade that preserves the public
`render()` import. `pala_view_styles.py` owns the full local stylesheet, and
`pala_view_layout.py` owns model normalization, page document assembly,
navigation, project panels, and catalog rows. `pala_view_sections.py` remains
the owner of independently testable decision and section markup.

The extraction is deliberately output-preserving: it keeps the existing
privacy, keyboard, delivery-decision, localStorage-only preference, and
no-progress-claim contracts. Both new runtime siblings are installer-required;
a truncated custom bundle therefore fails before any staging or replacement.

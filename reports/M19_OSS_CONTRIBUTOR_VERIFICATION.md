# M19 OSS Contributor Verification

Date: 2026-08-07
Ticket: PALA-052
Branch: `feat/oss-contributor-m19`
Pull request: #6

## Result

**M19 source acceptance: PASS.**

The implementation preserves Pala's single-door, local-first architecture and
adds a deterministic OSS contribution layer without bundling a second agent
platform or silently installing remote services.

## Verified behavior

- `scripts/pala_oss.py` is stdlib-only and contains no network or GitHub write
  execution.
- Focused OSS contract suite: **15/15 passed**.
- Repository contribution text is bounded untrusted data; it is never executed
  or interpolated into shell commands.
- Policy parsing distinguishes AI prohibition and disclosure requirements,
  assignment/claim rules, issue-first rules, CLA/DCO and test expectations.
- Candidate scoring blocks security-sensitive work, an existing implementation
  PR, another assignee, an unmet assignment rule and repositories that forbid
  AI-assisted contributions.
- Approval fingerprint binds the reviewed repository/issue/base/head/commit,
  diff evidence and gate evidence. A changed review surface invalidates prior
  approval.
- Publish gate is fail-closed and permits only a draft PR after human approval,
  a clean worktree, a valid commit, all required gates passed and no open
  blockers. A required `not-run` gate is rejected.
- Fork, push and pull-request operations are represented as three separate
  explicit authorities and argv arrays, not shell strings.
- Normal slash-containing refs such as `fix/issue-123` are accepted; traversal,
  option-like refs, doubled separators and `.lock` refs are rejected.
- OSV-Scanner and zizmor are optional evidence only when already available and
  applicable; their absence never breaks Pala core.
- Pala's skill routes external contribution work to the locked
  `oss-contribution.md` reference.
- The orchestrator skill was reduced from an intermediate 493-word regression
  to **434 words**, preserving the existing <=450-word contract and all required
  routing/safety phrases.
- `scripts/verify.py` compiles all `scripts/*.py`, discovers all
  `scripts/test_*.py`, validates product JSON and checks portable-package
  reproducibility.
- `scripts/build_portable.py` automatically includes the new script/test and
  `skills/` reference through the standard package path.
- Branch comparison against `main` is behind 0 at the M19 acceptance point and
  the feature diff is limited to the intended OSS implementation/documentation
  surface; manifest version, installer, hook manifest and managed-tool locks
  were not changed by M19.

## Full GitHub Quality evidence

Quality run `31131516966` (#36) completed successfully on both matrix jobs:

- Windows Server 2025 / Python 3.12.10: **169 tests passed**.
- Ubuntu 24.04 / Python 3.12.13: **169 tests passed**.
- Windows same-environment reproducible ZIP SHA-256:
  `6FEF66592E544F6C4FF1314E68FFE8AA934CD83A9F731462D9A72B9772398F07`.
- Ubuntu same-environment reproducible ZIP SHA-256:
  `1AF2C40FAC26064BBAC03704073E27CA030A33FCAA19611FEEC9F282AD751CF3`.

A second independent pull-request Quality run `31155100116` (#37) also
completed with conclusion **success**.

The platform-specific ZIP hashes are not asserted to be equal across operating
systems; the existing reproducibility contract requires byte-for-byte equality
between repeated builds in the same environment, and that contract passed on
both matrix jobs.

## Post-M19 external acceptance

### Installed owner Windows/Codex canary

This connected environment cannot launch the owner's actual Windows desktop,
install the branch into that profile, or open a fresh Codex Desktop session.

Result: **NOT_RUN**.

### Real third-party contribution canary

No unrelated upstream repository was used as a live publication canary in this
source milestone. A real fork/push/draft-PR affects an external community and
may involve repository-specific policy or CLA/DCO acceptance.

Result: **NOT_RUN**.

These are post-M19 real-world acceptance activities. They are not reported as
PASS until actually run, but they no longer block the M19 source acceptance.

## Completion boundary

M19 source implementation and repository Quality acceptance are complete.
Merge may proceed as the delivery action. Release/tag/version changes remain a
separate milestone because M19 intentionally did not modify the product version
or release contract.

# M19 OSS Contributor Verification

Date: 2026-08-07
Ticket: PALA-052
Branch: `feat/oss-contributor-m19`
Draft PR: #6

## Verified in this implementation session

- `scripts/pala_oss.py` is stdlib-only and contains no network or GitHub write execution.
- Focused contract suite: **15/15 passed**.
- Policy parser distinguishes AI prohibition, disclosure requirement, assignment,
  DCO, CLA, issue-first and test-expectation signals, including common
  `not allowed` / `not permitted` AI-ban wording.
- Candidate scoring blocks security-sensitive work with conservative
  security/vulnerability/CVE label matching, existing open implementation PRs,
  other assignees, unmet assignment requirements and repositories that forbid
  AI-assisted contributions.
- Repository/issue text is handled as bounded data; it is never interpolated
  into a shell command.
- Approval fingerprint changes when the reviewed diff evidence changes.
- Publish gate permits only a draft PR and requires human approval, a clean
  worktree, a 40-hex commit, all required gates passed, no open blockers and an
  unchanged fingerprint. A required `not-run` gate is explicitly rejected.
- Fork, push and pull-request actions are represented as three separate
  authorities, each marked as requiring explicit authority, and as argv arrays
  rather than shell strings.
- Normal slash-containing refs such as `fix/issue-123` are accepted; traversal,
  leading option-like refs, doubled separators and `.lock` refs are rejected.
- OSV-Scanner and zizmor discovery is optional and performs no installation or
  execution.
- Pala's skill routes external contribution requests to the locked
  `oss-contribution.md` reference.
- The orchestrator skill was re-counted after the M19 routing change. An initial
  493-word regression would have broken the existing 450-word contract; the
  skill was reduced to **434 words** while preserving required safety and
  routing phrases.
- README EOF newline was normalized after PR diff review.
- Existing `scripts/verify.py` compiles every `scripts/*.py`, discovers every
  `scripts/test_*.py`, validates product JSON and builds the portable archive
  twice for byte-for-byte reproducibility.
- Existing `scripts/build_portable.py` includes all Python/PowerShell files in
  `scripts/` and recursively includes `skills/`, so `pala_oss.py`, its tests and
  the OSS contribution reference are automatically covered by the standard
  package path.

## Not yet passed

### Full GitHub Quality workflow

`quality.yml` is configured for pull requests and runs `python scripts/verify.py`
on Ubuntu and Windows. Draft PR #6 was opened and subsequently synchronized,
closed and reopened through the connected GitHub integration. No workflow run
was created for the branch. The available GitHub connector exposes workflow
read/rerun operations but not a new `workflow_dispatch` operation.

Result: **BLOCKED_EXTERNAL_TRIGGER**, not PASS.

Do not bypass this by writing directly to `main` merely to trigger Actions.

### Installed Windows owner canary

The new source has not been installed into the owner's real Windows Codex
profile and exercised from a fresh Codex conversation.

Result: **NOT_RUN**.

### Real third-party contribution canary

No external repository has been forked and no external branch or draft PR has
been published. This remains an explicit owner-facing real-world acceptance
step because repository policy, identity, possible CLA/DCO acceptance and
upstream community impact are external actions.

Result: **NOT_RUN**.

## Completion boundary

M19 source implementation is ready for the remaining acceptance gates, but the
ticket must not be recorded as fully completed until the full repository Quality
workflow runs successfully. Merge, release, tag, external PR publication and
legal acceptance remain separately authorized actions.

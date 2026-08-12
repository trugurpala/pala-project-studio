# Pala 0.9.0 — Project Operating System

Pala's canonical local state is the v3 ticket/store layer. `STATUS.md`, cold
packets, Workspace and handoff are read models; they are not a second source of
truth. A task must be claimed by one owner, verified with real evidence, and
only then may enter `DONE`.

GitHub observation is read-only: connector, local `gh`, then redacted git
fallback. Missing remote capability is `not-run`; it never becomes a fake pass.
Issue, PR, review, check, branch-protection and CODEOWNERS writes are outside
Pala's authority. Hook trust remains `configured-not-verified` until a human
confirms it in Codex `/hooks`.

## Hardening contract

The v4 task snapshot adds an explicit `assignee` and a repository-global
single-host `lease`. A Git worktree resolves the shared authority under the
Git common directory; non-Git fixtures remain local. A stale heartbeat becomes
`orphaned`/`needs_decision`; it is never silently handed to another session.
The raw session identifier is not stored: only a bounded hash is persisted.

Acceptance is machine-checkable when expressed as items:

```yaml
acceptance:
  - id: AC-01
    text: the gate passes
    status: passed
    evidence_refs: [EV-abc]
```

Every structured item must be `passed` and reference a passed evidence record.
Verification also records `head_sha`, index, worktree and changed-surface
digests. A changed surface invalidates the old proof. `write_scope` and
`deny_scope` are authorization/verification policy; they are not an operating
system sandbox and do not claim to intercept every host editor operation.

Dependencies are a DAG: missing references and cycles block `READY`, and every
dependency must be `DONE`. Retry policy defaults to two repeated verification
failures before a blocker is recorded. `DONE` is never inferred from words such
as “bitti” or from a worker handoff alone.

The release gate checks source, portable and installed Markdown links as well
as runtime files. Historical plans may report `stale` references but are not
rewritten. Pala 0.9 is a **single-host** coordination system; multiple PCs do
not share an atomic lease. A future coordination adapter may be added in 1.x.

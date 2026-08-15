# Pala 1.2.0 candidate

Pala 1.2.0 is a local release candidate. Public `v1.1.2` remains the immutable
baseline; no tag, GitHub Release, publication, or deployment is implied here.

## Candidate scope

- Connect project snapshot, profile, receipt, and history to the canonical
  TaskContract, WorkflowStore, and Quality Engine flow.
- Use observed host capabilities and owned process supervision for execution.
- Render bounded, privacy-safe Control Center read models.
- Produce deterministic package, SBOM, inventory, and isolated install
  evidence for `pala-project-studio-1.2.0.zip`.

## Upgrade and release evidence

The candidate accepts real upgrade evidence only when the SHA-pinned public
`0.4.4`, `0.8.0`, `0.8.1`, `1.0.0`, and `1.1.2` archives upgrade to `1.2.0` in
isolated profiles. The checks cover state continuity, a no-op second install,
Doctor health, and rollback. See [update compatibility](PALA_UPDATE_COMPATIBILITY.md).

Until every required current Quality check exits zero, this candidate is
`configured-not-verified`. Remote publication and deploy are `not-run` and
require separate explicit authority.

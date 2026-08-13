# Pala current status

- Product version: `1.1.0`
- Branch: `main`
- Local release candidate: `passed`
- Current work: clean-main public release preparation
- Last published version: `1.0.0`
- Public `v1.1.0`: `not-run`
- Real remote deploy: `not-run`
- Canonical authority: TaskContract → WorkflowStore → Pala Quality Engine

The current source, portable package, installed profile, Workbench providers,
Windows upgrade cases, Control Center policy, and Doctor were verified before
repository cleanup. Cleanup intentionally invalidates that evidence; the full
release gate must run again before push, tag, or publication.

Next action: complete the clean-tree release gate and publish only after the
exact pushed `main` commit has green GitHub Actions.

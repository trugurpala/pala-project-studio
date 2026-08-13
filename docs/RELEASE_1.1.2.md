# Pala 1.1.2

Pala 1.1.2 is the M75 public-bootstrap and completion-safety patch release.

## Fixed

- One natural installation journey now bootstraps the plugin, runtime bundle,
  required CodeGraph and Semgrep providers, and verifies full Doctor health.
- A second identical request is a Pala-owned transactional no-op only when all
  required installation dimensions are current.
- The dedicated `pala-control-center` skill deterministically routes explicit
  Pala panel intents from empty workspaces while preserving unrelated panels.
- Canonical `DONE` and `PACKAGE_READY` require task-scoped, Pala Doctor-owned
  environment/capability evidence in addition to Quality evidence.

## Artifact

The release asset is `pala-project-studio-1.1.2.zip` with its SHA-256 and
sanitized evidence manifest. Public publication remains separate from deploy.

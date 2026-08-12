# Pala 0.9.4 — Core install / expert boundary

## Decision

Pala's core installer is local-first. `Install`, `Update`, and `Repair` install
and validate only the portable Pala bundle by default. They do not download
expert workers, launch a model server, or fetch a model.

An owner may explicitly request the optional local code-intelligence workers:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Repair -InstallExperts
```

That is a separate network/download action. It is never inferred from a normal
core repair.

## Truthfulness rule

An optional worker can be missing, blocked, or fail its integrity check without
turning a verified core install into a false failure. The installer gives one
safe message, continues to Doctor, and returns the core result. It does not
show raw worker output, URLs, or credentials; it also does not start the local
model after a failed expert install.

`Doctor` reports `expert_prerequisites_ready` (Node + uv) separately from
`experts_ready` (the five Pala-managed workers are actually present and
verified), `plugin_ready`, and `healthy`. A green core is not a claim that
every optional expert exists.

## Why this matters

This protects the solo developer's normal workflow: repair the product quickly,
verify it locally, and decide separately whether a heavyweight local RAG/code
analysis tool is worth its disk, network, and review cost.

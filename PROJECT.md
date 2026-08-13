# Pala Project Studio

Pala is a **Provider-Independent Local Software Delivery OS** for people who
want an AI-assisted software project to remain understandable, resumable,
verifiable, and publishable without giving one provider control of the product.

Current identity: `1.1.2`. Machine-readable identity lives in
`product-identity.json`.

## Primary outcome

A user can describe a new product or point Pala at an existing repository.
Pala discovers the effective instructions, turns intent into durable scope,
claims one canonical task, selects only needed capabilities, implements within
the authorized surface, maps mechanical quality evidence to acceptance, and
prepares a reproducible package.

## Product capabilities

- **Kod anlayışı:** fresh structural context with direct-source fallback.
- **Güvenlik:** bounded local analysis plus project-native security authority.
- **Tarayıcı doğrulama:** project-profile evidence without automatic UI.
- **Quality Engine:** the sole completion-evidence authority.
- **Failure Intelligence:** verified, sanitized failure memory.
- **ReleaseTruth:** separate build, publication, and deployment truth.
- **Control Center:** one read-only owner surface in Turkish-first language.

## Trust boundaries

- TaskContract owns task semantics and DONE eligibility.
- WorkflowStore owns persistence and leases.
- The Pala Quality Engine owns verification evidence.
- Generated status, cockpit, handoff, and cold packets are read models.
- Providers are advisory and never decide completion.
- Hooks never run tests, builds, network calls, or remote mutations.
- Commit, push, PR, tag, release, visibility, billing, and deploy are separate
  owner-authorized actions.
- Credentials, transcripts, customer data, caches, and machine-local state do
  not enter source or release packages.

## Supported platform

The managed Workbench target is Windows x64. Unsupported platforms are reported
truthfully and use safe fallbacks rather than appearing healthy.

Advanced provider, lifecycle, integrity, and fallback contracts are documented
in `docs/ARCHITECTURE.md`.

# Project Intake

Classify before proposing architecture:

| Kind | Evidence | Default action |
| --- | --- | --- |
| Existing | Working source, package metadata, tests, or runtime | Preserve conventions and extend the narrow owner |
| Partial | Scaffold or UI exists but the requested core flow is incomplete | Reuse the sound parts; replace only proven dead ends |
| Greenfield | No meaningful implementation exists | Select architecture, then scaffold one vertical slice |

Read the effective instruction chain for every target subtree, not only the
repository root. Inspect the working tree before editing and preserve unrelated
user changes.

Write or reconcile a compact product contract:

- primary user and job;
- real core workflow from entry to observable result;
- required surfaces and states;
- inputs, outputs, persistence, integrations, and trust boundaries;
- scope, non-goals, platform and operational constraints;
- exact acceptance evidence: commands, URL/process, and interactions;
- external decisions or credentials that can block completion.

Separate requested facts from assumptions. A hashtag such as Next.js, SaaS,
dashboard, Tailwind, React, or open source is a discovery signal. It becomes a
constraint only when the user explicitly requires it or the existing project
already depends on it.

Ask one question only when the answer changes product scope, safety, cost,
external writes, or an irreversible architecture decision. Otherwise record a
reversible assumption and keep moving.

Completion is the requested usable outcome, not the number of generated files.
For a complex product, identify the smallest end-to-end slice that proves the
architecture before expanding breadth.

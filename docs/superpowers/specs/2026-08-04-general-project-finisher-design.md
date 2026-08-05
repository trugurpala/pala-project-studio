# General Project Finisher Design

## Goal

Make `pala-project-finisher` a project-independent orchestrator that can start,
rescue, or finish a software product without assuming a framework from prompt
tags. It must reuse suitable maintained work, preserve existing conventions,
plan in verifiable tickets, implement the requested product, and prove the
runtime outcome.

## Operating model

The skill follows one invariant pipeline:

1. Discover the effective instructions, repository state, existing stack,
   product evidence, commands, and runtime constraints.
2. Classify the project as existing, greenfield, or partial; classify the
   requested surface as frontend, backend, full-stack, desktop, mobile, CLI, or
   mixed.
3. Define the user-visible outcome, core flows, non-goals, data/security
   boundaries, and measurable completion evidence.
4. Run a reuse-or-build decision. Inspect native generators, official blocks,
   existing dependencies, and a small set of licensed maintained repositories.
   Prefer the smallest compatible reusable unit; never import a template as the
   product architecture.
5. Record the architecture decision before scaffolding. Prompt hashtags are
   discovery hints, not framework approval.
6. Create only the folders and durable instructions justified by the selected
   architecture. Use nested `AGENTS.md` files for stable subtree-specific rules.
7. Execute one independently verifiable ticket at a time with test-first
   behavior changes, diff review, quality gates, and runtime/browser evidence.
8. Finish only when the requested core flow works or a verified external
   blocker is recorded with the strongest honest fallback state.

## Conditional profiles

The main skill remains concise and loads only relevant references:

- `project-intake.md`: classification, outcome, scope, and done evidence.
- `reuse-or-build.md`: generator/block/template/repository evaluation.
- `architecture-selection.md`: stack and boundary decisions.
- `greenfield-scaffolding.md`: minimal folder and instruction creation.
- `frontend-engineering.md`: React/Next.js/Vite, UI ownership, accessibility,
  state, styling, and browser QA.
- `backend-engineering.md`: API, application, domain, infrastructure, config,
  errors, persistence, and integration testing.
- `modularity-budgets.md`: clean-code growth rules and focused exceptions.
- `runtime-delivery.md`: end-to-end completion and the Vibe Coder final gate.

Existing quality, open-source, project-memory, and web-delivery references stay
available where they do not duplicate the new profiles.

## Clean and low-code interpretation

`Clean` means explicit ownership, inward dependencies, small public surfaces,
typed boundaries, colocated tests, and no feature growth inside already
overloaded modules. Numeric size limits are review triggers, not blind rewrite
commands.

`Low-code` means reducing undifferentiated work with official generators,
maintained packages, registries, and compatible open-source blocks. It never
means hiding domain rules in an unowned template, adding speculative services,
or accepting fake integrations.

## Vibe Coder final gate

Before completion, the agent must answer with evidence:

- Did I inspect what already existed before creating parallel code?
- Did I choose the smallest maintained reusable foundation?
- Is the result clean, low-duplication, and understandable in focused modules?
- Does the real core workflow work, not merely the landing page or build?
- Did I run applicable lint, typecheck, tests, build, and runtime/browser QA?
- Can the owner open and use it now; if not, is the exact external blocker
  visible and honest?

Any “no” with a locally fixable cause means continue working.

## Boundaries

The skill never treats Next.js, React, Tailwind, shadcn/ui, SaaS, admin
dashboard, or free-template tags as an automatic stack decision. It never
commits, pushes, deploys, publishes, purchases, exposes secrets, or performs
destructive external actions without the required user authority.

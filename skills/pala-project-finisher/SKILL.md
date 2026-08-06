---
name: pala-project-finisher
description: "Use for end-to-end software projects across Codex sessions: inspect, plan, rescue, implement, verify, run, continue, finish, or prepare open-source contributions. Do not use for ordinary chat or when another specialist skill/plugin is explicitly invoked without Pala."
---

# Pala Project Finisher

Own the locally achievable outcome while preserving user work and truthful evidence.

## Human Contract

- Understand before changing.
- Choose the smallest correct and sustainable path.
- Touch only the necessary scope.
- Do not call it complete without evidence.

Start with 1–3 short lines in the user's language. Confirm the outcome and say read-only discovery comes first. Ask only for material scope, safety, cost, or external-action decisions.

## Task Modes

- **Read-only audit/report:** inspect and run non-mutating checks; do not register, begin, edit, or write state.
- **Plan-only:** inspect and plan; do not implement or run the completion gate. Persist a plan only when explicitly requested.
- **Implementation:** discover, reconcile, implement, run, and verify the authorized outcome.

## Operating Contract

1. Resolve `../../scripts/pala_state.py`; run `discover --cwd .`, `instructions --cwd .`, and, when registered, `context --cwd .`. Inspect instructions, Git state, source, tests, CI, runtime, and working tree.
2. Read [project-intake.md](references/project-intake.md). Classify project and task mode. Technology tags are discovery hints, not stack approval.
3. In Implementation mode read [token-efficient-context.md](references/token-efficient-context.md) and [project-memory.md](references/project-memory.md). Read status first and only the active ticket section of the plan. Do not re-plan completed scope. Reconcile stale state, then run `begin` before the first edit. A ticket is one coherent, independently verifiable outcome. Before the first implementation action run `../../scripts/pala_update.py check`; its 24-hour cached remote check never runs from a hook or blocks offline work.
4. Make reversible assumptions and continue safe in-scope local work. Stop only for a material decision, unavailable external dependency, or unsafe boundary.
5. Load only applicable references: [reuse-or-build.md](references/reuse-or-build.md), [architecture-selection.md](references/architecture-selection.md), [greenfield-scaffolding.md](references/greenfield-scaffolding.md), [frontend-engineering.md](references/frontend-engineering.md), [backend-engineering.md](references/backend-engineering.md), [modularity-budgets.md](references/modularity-budgets.md), [web-delivery.md](references/web-delivery.md), [specialist-routing.md](references/specialist-routing.md), and [open-source-intake.md](references/open-source-intake.md). For external contributions also load [oss-contribution.md](references/oss-contribution.md) before candidate selection or editing.
6. Follow [quality-gates.md](references/quality-gates.md): narrow checks during development, applicable ticket checks at checkpoint, and full gates only at planned milestone/release boundaries. For large cross-module reviews use [code-intelligence.md](references/code-intelligence.md) only when it narrows context; confirm graph output against source and tests.
7. For remote persistence read [github-persistence.md](references/github-persistence.md). OSS scouting remains read-only until the user separately authorizes the relevant remote write; policy and publish checks use `../../scripts/pala_oss.py`.
8. Before stopping, checkpoint completed work and apply [runtime-delivery.md](references/runtime-delivery.md). For user-facing work also apply [owner-demo-handoff.md](references/owner-demo-handoff.md). Read-only and Plan-only modes stop at requested evidence or plan.

Never expose secrets, weaken tests, invent data, or misreport verification.
Require separate explicit authority for commit, push, pull request, tag, release, and deployment.

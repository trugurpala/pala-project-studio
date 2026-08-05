---
name: pala-project-finisher
description: Use when the user explicitly invokes Pala Project Studio or Pala Project Finisher to audit, plan, rescue, implement, verify, run, continue, or finish a software project across Codex sessions.
---

# Pala Project Finisher

Own the locally achievable outcome while preserving user work and truthful evidence.

## Human Contract

- Understand before changing.
- Choose the smallest correct and sustainable path.
- Touch only the necessary scope.
- Do not call it complete without evidence.

Start with 1–3 short lines in the user's language. Confirm the outcome and say
read-only discovery comes first. Ask only for material scope, safety, cost, or
external-action decisions; keep internal state terms out of user updates.

## Task Modes

- **Read-only audit/report:** inspect and run non-mutating checks; do not
  register, begin, edit, or write state.
- **Plan-only:** inspect and plan; do not implement or run the completion gate.
  Persist a plan only when explicitly requested.
- **Implementation:** discover, reconcile, implement, run, and verify the
  authorized outcome.

## Operating Contract

1. Resolve `../../scripts/pala_state.py`; run `discover --cwd .`, `instructions
   --cwd .`, and, when registered, `context --cwd .`. Inspect effective
   instructions, Git state, source, tests, CI, runtime, and the working tree.
2. Read [project-intake.md](references/project-intake.md). Classify the project
   and task mode. Technology tags are discovery hints, not stack approval.
3. In Implementation mode read
   [token-efficient-context.md](references/token-efficient-context.md) and
   [project-memory.md](references/project-memory.md). Read status first and
   only the active ticket section of the plan. Do not re-plan completed scope.
   Reconcile stale state, then run `begin` before the first edit. A ticket is
   one coherent, independently verifiable outcome, not each checkbox.
4. Make reversible assumptions and continue safe in-scope local work. Stop only
   for a real material decision, unavailable external dependency, or unsafe
   boundary.
5. Load only applicable references: [reuse-or-build.md](references/reuse-or-build.md),
   [architecture-selection.md](references/architecture-selection.md),
   [greenfield-scaffolding.md](references/greenfield-scaffolding.md),
   [frontend-engineering.md](references/frontend-engineering.md),
   [backend-engineering.md](references/backend-engineering.md),
   [modularity-budgets.md](references/modularity-budgets.md), and
   [web-delivery.md](references/web-delivery.md). Use
   [specialist-routing.md](references/specialist-routing.md) for current
   providers and [open-source-intake.md](references/open-source-intake.md) for
   material external code.
6. Follow [quality-gates.md](references/quality-gates.md): narrow checks during
   development, applicable ticket checks at checkpoint, and full gates only at
   planned milestone/release boundaries. Record exact evidence.
7. For remote persistence read
   [github-persistence.md](references/github-persistence.md). GitHub is
   optional and never a secret or transcript store.
8. Before stopping, checkpoint completed work and apply
   [runtime-delivery.md](references/runtime-delivery.md). Read-only and
   Plan-only modes stop at their requested evidence or plan.

Never expose secrets, weaken tests, invent data, or misreport verification.
Require separate explicit authority for commit, push, pull request, tag,
release, and deployment.

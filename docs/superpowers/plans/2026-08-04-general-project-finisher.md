# General Project Finisher Implementation Plan

> Historical 0.2 implementation record. It is superseded by the root
> `PLAN.md`; paths and one-time authority constraints below are not active
> instructions for current work.

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Pala Project Finisher reliably discover, decide, reuse, scaffold,
implement, and run new or existing software projects without hard-coded stack
assumptions.

**Architecture:** Keep one concise orchestrator skill and route decisions to
conditional reference profiles. Add static contract tests for required routing,
project independence, Vibe Coder completion, and reference size so future edits
cannot silently weaken the workflow.

**Tech Stack:** Markdown Agent Skills, Python `unittest`, Codex command hooks,
and a local development marketplace.

## Global Constraints

- Modify only the selected plugin source and its local development cache.
- Do not modify the active application repository.
- Do not commit, push, release, or deploy.
- Keep `SKILL.md` concise and load technology profiles conditionally.
- Preserve existing project conventions before introducing a new architecture.
- Treat technology tags as discovery hints, never automatic approval.

---

### Task 1: General behavior contract

**Files:**
- Modify: `scripts/test_pala_tools.py`
- Modify: `skills/pala-project-finisher/SKILL.md`

**Interfaces:**
- Consumes: current skill text and existing unit-test suite.
- Produces: a concise orchestrator that routes intake, reuse, architecture,
  scaffolding, engineering, modularity, and runtime completion.

- [x] Add tests asserting that every conditional profile is linked directly
      from `SKILL.md`, project-specific terms are absent, tags are not stack
      approval, and the final gate requires a usable runtime.
- [x] Run `py -3 -m unittest scripts.test_pala_tools -v` and confirm the new
      tests fail because the references and routing contract do not exist.
- [x] Update `SKILL.md` with the minimal routing and continuation contract.
- [x] Rerun the unit suite and keep earlier state/hook tests green.

### Task 2: Conditional engineering profiles

**Files:**
- Create: `skills/pala-project-finisher/references/project-intake.md`
- Create: `skills/pala-project-finisher/references/reuse-or-build.md`
- Create: `skills/pala-project-finisher/references/architecture-selection.md`
- Create: `skills/pala-project-finisher/references/greenfield-scaffolding.md`
- Create: `skills/pala-project-finisher/references/frontend-engineering.md`
- Create: `skills/pala-project-finisher/references/backend-engineering.md`
- Create: `skills/pala-project-finisher/references/modularity-budgets.md`
- Create: `skills/pala-project-finisher/references/runtime-delivery.md`
- Modify: `scripts/test_pala_tools.py`

**Interfaces:**
- Consumes: classification and selected architecture from Task 1.
- Produces: independent references loaded only when their observable condition
  applies.

- [x] Add tests for mandatory headings, reuse evidence fields, dependency
      direction, module-growth triggers, and the six-question Vibe Coder gate.
- [x] Run the unit suite and confirm the missing-reference failures.
- [x] Write each focused reference without duplicating the orchestrator.
- [x] Rerun the unit suite and inspect every reference for project-specific
      assumptions.

### Task 3: Validation and deployment

**Files:**
- Modify: `.codex-plugin/plugin.json` through the cachebuster helper.
- Verify: installed local development cache.

**Interfaces:**
- Consumes: completed source plugin.
- Produces: installed, enabled plugin whose cached files match source hashes.

- [x] Run unit tests, Ruff, Python compilation, skill validation, plugin
      validation, and JSON parsing.
- [x] Run representative static scenarios for an existing app, greenfield
      Next.js SaaS dashboard, separate-backend React dashboard, and backend-only
      API.
- [x] Replace the Codex cachebuster with the official helper.
- [x] Reinstall the local development build of `pala-project-studio`.
- [x] Compare source and installed files by SHA-256 and report the new version.

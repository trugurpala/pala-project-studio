# Design: M30 close + 0.8.1 local release ground (heavy package)

**Date:** 2026-08-09  
**Branch:** `feat/m30-vibe-codex-host-fit`  
**Authority:** Local finish only — no push, PR, tag, or `gh release` in this work.

## Goal

Close the M30 vibe/Codex host-fit branch locally, fix the checkpoint
`plugin-data` noise bug cleanly, and prepare a heavy but local-only 0.8.1
release ground package so the owner can push/tag/release later.

## Scope (approved)

### Layer A — Close the branch
- Keep excluding `.codex/plugin-data/` from checkpoint basis and commit
  materialization (same class as workflow).
- Remove debug instrumentation from `pala_state.py`.
- Keep PLAN evidence honest (no incomplete `M30-T*` task cards that break
  agent_tasks audit).
- Prove with focused unittest (checkpoint + host-fit + self_audit).

### Layer B — 0.8.1 ground
- Install/Update notes and hooks trust reminder
  (`hook_safety=passed` ≠ Codex `/hooks` UI trust).
- Owner checklist for tag/release steps (commands only; owner runs them).

### Layer C — Heavy package
- Build portable ZIP locally via `scripts/build_portable.py`; record SHA-256
  and path; do not publish.
- Rewrite CHANGELOG Unreleased / 0.8.1 narrative for readability.
- Rewrite STATUS.md to current truth (M30, open owner items, evidence labels).

## Out of scope
- `git push`, PR open/merge, `git tag`, `gh release`
- Claiming hooks UI trust = `passed`
- Soft “A/B fixed” / speed or token % claims
- Marketplace Install sync on other machines

## Success criteria
- Checkpoint test expecting two user files passes without counting v3 tickets.
- Host-fit / self_audit focused suites green.
- Portable ZIP exists locally with recorded digest.
- STATUS + CHANGELOG + release checklist readable for owner next actions.
- Working tree committed on feature branch; remote untouched.

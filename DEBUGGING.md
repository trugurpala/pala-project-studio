# Debugging log

Durable error brain for this project. Read before repeating a known failure.
No secrets, tokens, transcripts, or real user plugin data.

## Format

Each incident uses heading `### INC-YYYYMMDD-slug` and these fields:
Symptoms, Root cause, Fix criteria, Proved by, Related files, Date, Status.
Optional: Attempts (append-only notes when a fix is tried; SQLite
`kind=debug_attempt` mirrors light attempts).
Status may be `open`, `fixed`, or `wontfix`; fixed requires evidence labels
(passed | not-run | blocked | configured-not-verified), not soft done/ok.
When open INC exist, SessionStart/begin/checkpoint emit DEBUG GATE warnings.

## Incidents

### INC-20260808-stub-brain
- **Symptoms:** Root `DEBUGGING.md` was only a one-line stub; agents had no
  durable place for root cause + fix criteria after failures.
- **Root cause:** Memory contract listed DEBUGGING in read order, but format
  and fail-closed checks were never enforced.
- **Fix criteria:** `## Format` + required field labels parse; empty Incidents
  allowed; each `### INC-*` has all seven fields; self-audit `debugging_brain`
  fails closed.
- **Proved by:** `py -3 -m unittest scripts.test_pala_debugging -v`
- **Related files:** `DEBUGGING.md`, `scripts/pala_memory.py`,
  `scripts/pala_self_audit.py`, `scripts/test_pala_debugging.py`, `AGENTS.md`
- **Date:** 2026-08-08
- **Status:** fixed (`passed` — `test_pala_debugging` + self-audit `debugging_brain`)

### INC-20260808-soft-done
- **Symptoms:** Soft “bitti/done/ok” treated as completion without gate labels.
- **Root cause:** Evidence policy not consulted; chat tone over STATUS labels.
- **Fix criteria:** Use `passed|not-run|blocked|configured-not-verified` only;
  refuse soft words alone at checkpoint.
- **Proved by:** Pala evidence policy + `AGENTS.md` quality rules
- **Related files:** `AGENTS.md`, `docs/PALA_0_5_MEMORY_CONTRACT.md`,
  `scripts/pala_self_audit.py`
- **Date:** 2026-08-08
- **Status:** fixed (`passed` policy; ongoing enforcement)

### INC-20260808-stab001-gate
- **Symptoms:** STAB-001 needed a fresh local confidence gate after M21 pack.
- **Root cause:** Working tree uncommitted; historical M21 SHA not sufficient
  proof for post-brain changes.
- **Fix criteria:** Narrow unittest green, then full `verify.py` with new SHA.
- **Proved by:** `py -3 -m unittest …` (118 ok narrow) then
  `py -3 scripts/verify.py` → 227 tests + self-audit;
  ZIP SHA-256 `6044C2226439147476553B318473D15FFF3F2F9116FB53A3D4D634E96E4A6E8A`
- **Related files:** `scripts/verify.py`, `DEBUGGING.md`, `STATUS.md`
- **Date:** 2026-08-08
- **Status:** fixed (`passed` full local gate)

### INC-20260808-readme-fake-080
- **Symptoms:** README green badge + download linked `v0.8.0` while GitHub
  latest release was still `v0.7.1` (404 risk; STATUS said `not-run`).
- **Root cause:** Manifest bumped to 0.8.0 and UX contract required matching
  README release URLs without a publish-pending branch.
- **Fix criteria:** While STATUS marks `v0.8.0` release `not-run`, README must
  not use green published badge; point download at `v0.7.1`; contract test
  follows STATUS.
- **Proved by:** `py -3 scripts/verify.py` → 230 tests + self-audit;
  ZIP SHA-256 `CC8D1A33A00F1C4444FFC98AD2CF57EB509619E3A6854EE41B3293DB67EA3297`
- **Related files:** `README.md`, `STATUS.md`,
  `scripts/test_plugin_experience.py`, `docs/RELEASE_0_8_0_CHECKLIST.md`
- **Date:** 2026-08-08
- **Status:** fixed (`passed`)

### INC-20260808-skill-budget-m24
- **Symptoms:** M24 skill edit dropped exact phrase
  `Do not re-plan completed scope` and pushed word count to 451 (>450).
- **Root cause:** Task-card wording replaced the contract phrase instead of
  extending it; no pre-edit word-budget check.
- **Fix criteria:** Phrase restored; `SKILL.md` ≤450 words; both contract
  tests green inside full `verify.py`.
- **Proved by:** `py -3 scripts/verify.py` → 234 tests + self-audit;
  ZIP SHA-256 `F626B3EBDE7CF71D9A752B3CECC6B2B8019418596C83FBD976AEC7F7CF6CDC6E`
- **Related files:** `skills/pala-project-finisher/SKILL.md`,
  `scripts/test_pala_tools.py`, `scripts/test_plugin_experience.py`
- **Date:** 2026-08-08
- **Status:** fixed (`passed`)

### INC-20260808-script-path-cwd
- **Symptoms:** Live A/B / “pala kontrol et” agents ran skill-relative
  `../../scripts/pala_report.py` from the user project cwd → script not found;
  begin without `--goal` English argparse noise; complete failed with opaque
  `ticket record not found` after begin without v3 ticket row.
- **Root cause:** Skill instructed skill-tree-relative script paths; begin
  without `--session-key` wrote only v2 workflow JSON; complete always needs
  v3 ticket + session.
- **Fix criteria:** Skill/refs never instruct `../../scripts/` from project
  cwd; document marketplace `%LOCALAPPDATA%\Pala\marketplace\scripts` + repo
  `scripts/` + `PALA_SCRIPTS_DIR`; `resolve_pala_scripts_dir`; Turkish
  `--goal` error; begin always claims v3 ticket (`pala-local` default);
  complete prints actionable recovery (begin/register/session); no soft-pass.
- **Proved by:** `py -3 -m unittest scripts.test_pala_p0_friction
  scripts.test_pala_cmd_memory -v` → 18 ok; `py -3 scripts/pala_p0_smoke.py`
  → `artifacts/codex-compat/p0-smoke.json` overall `passed` (9 rows); full
  `verify.py` `not-run`.
- **Related files:** `skills/pala-project-finisher/SKILL.md`,
  `skills/pala-project-finisher/references/code-intelligence.md`,
  `scripts/pala_paths.py`, `scripts/pala_state.py`, `scripts/pala_cmd_memory.py`,
  `scripts/pala_p0_smoke.py`, `scripts/test_pala_p0_friction.py`,
  `scripts/test_plugin_experience.py`
- **Date:** 2026-08-08
- **Status:** fixed (`passed` focused + Gate0 smoke; full gate `not-run`;
  live marketplace A/B re-measure `not-run`)

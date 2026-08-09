# Systematic debugging → DEBUGGING INC-

Use on any bug, test failure, or unexpected behavior **before** proposing fixes.
Maps Superpowers-style phases onto Pala's durable error brain.

## Iron law

No fix proposals until Phase 1 produces a written root-cause hypothesis.
Read open `### INC-…` entries first; do not repeat a known failure blindly.

## Phases → INC fields

| Phase | Do | Write into INC- |
| --- | --- | --- |
| 1. Root cause | Read errors, reproduce, check recent diff, gather boundary evidence | Symptoms, Related files |
| 2. Pattern | Compare working vs broken paths | Root cause (draft) |
| 3. Hypothesis | One hypothesis; smallest test | Attempts (append-only) |
| 4. Fix | Failing check → minimal fix → verify | Fix criteria, Proved by, Status |

Required INC fields: Symptoms, Root cause, Fix criteria, Proved by,
Related files, Date, Status (`open` | `fixed` | `wontfix`).
No secrets, tokens, or transcripts.

## After three failed fixes

Stop patching. Question architecture with the user before attempt four.
`fixed` requires evidence labels, not soft done/ok.

## Verify

Before claiming fixed, follow [quality-gates.md](quality-gates.md)
verification-before-done gate.

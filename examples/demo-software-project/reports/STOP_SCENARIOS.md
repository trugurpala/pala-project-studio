# Demo stop-condition scenarios (Wave B / M28-T4)

Harness-friendly notes for feature-matrix stop rows that were `not applicable`.
Evidence labels only; no hooks UI trust claim.

| Scenario | How to prove | Expected | Label |
| --- | --- | --- | --- |
| Unregistered project | SessionStart on folder without `.codex/pala-project.json` | empty hook stdout | `passed` (`test_stop_unregistered_project_emits_nothing`) |
| Invalid / soft evidence | `checkpoint` verification `done` alone | ValueError soft done | `passed` (`test_stop_invalid_evidence_soft_done_refused`) |
| Insufficient evidence shape | verification `looks fine` | ValueError shape | `passed` (`test_stop_insufficient_evidence_shape_refused`) |
| Hooks untrusted (UI) | Doctor/file `hook_safety` vs `/hooks` UI | UI stays separate | `configured-not-verified` (`hooks_ui_trust_label`) |
| Open INC gate | `pala_debug_gate.py --surface begin` with open INC | DEBUG GATE stderr | `passed` (`test_pala_debug_gate`) |

Commands (focused; not full verify):

```text
py -3 -m unittest scripts.test_pala_debug_gate -v
py -3 scripts/pala_debug_gate.py --cwd . --surface begin
```

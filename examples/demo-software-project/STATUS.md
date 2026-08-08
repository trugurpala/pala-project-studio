# Demo Software Project — Status

- Updated: 2026-08-08
- Active milestone: M3 — Optional polish (`planned`)
- Active ticket: DEMO-005 — Owner handoff note (optional)
- Plugin/manifest note: demo only (not Pala itself)

## Verification

| Check | Result | Evidence |
| --- | --- | --- |
| Unit tests | `passed` | `py -3 -m unittest scripts.test_pala_demo -v` |
| Status HTML | `passed` | `pala_demo.prove_status_html` → Şimdi + DEMO-003 + 3 olay |
| Release ZIP | `not-run` | Out of demo scope |

## Örnek ajan → görev

| Ajan | Görev ID | Not |
| --- | --- | --- |
| Ajan-Demo-A | DEMO-005-A | Handoff metni (`STATUS` / `PROGRESS`) |
| Ajan-Demo-B | DEMO-005-B | PLAN kart netliği; seed kanıtı korunur |
| *(atanmamış)* | DEMO-005 | Üst ticket — owner handoff özeti |

## Blockers

None.

## Single next action

Optional DEMO-005: short owner handoff note without fake browser screenshots.

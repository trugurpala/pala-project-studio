# Owner demo handoff — Demo Software Project

Date: 2026-08-08  
Ticket: DEMO-005 (`passed`)

## What this demo proves

1. Pala memory files (`AGENTS` → `STATUS` → `PLAN`) keep one active ticket.
2. After `pala_demo.py seed`, Status HTML shows **Şimdi**, an active ticket, and
   three timeline events (register / begin / checkpoint).
3. No fake browser screenshots — evidence is Status HTML + unittest
   (`scripts.test_pala_demo`).

## How to re-run

```powershell
py -3 scripts\pala_demo.py seed --demo-root examples\demo-software-project --catalog-root $env:USERPROFILE\Desktop\Codex
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Status
```

## Out of scope

Commit/push/release of the real Pala plugin; ChatGPT Plus install; Codex
`/hooks` UI trust (human-only).

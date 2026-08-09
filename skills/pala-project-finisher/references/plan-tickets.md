# Plan tickets (Pala card shape)

Use when shaping new work or expanding a milestone **before** edits.
Inspired by Superpowers brainstorming / writing-plans — adapted to Pala cards.

## Design gate (short)

1. Read STATUS + open INC-; confirm one outcome.
2. Ask only material questions (scope, safety, cost, external action).
3. Offer 2–3 approaches with a recommendation; YAGNI.
4. Get explicit approval before writing PLAN cards or code.
5. Persist design notes under `docs/superpowers/specs/` only when the user
   wants a durable spec (not every micro-fix).

## Card template (`PLAN.md`)

Each card needs:

| Field | Required |
| --- | --- |
| **ID** | `M*-T*` unique |
| **Sahip ajan** | Who may edit |
| **Amaç** | One sentence outcome |
| **Dosyalar** | Exact paths to create/modify/test |
| **Bitti sayılır** | Observable acceptance |
| **Bağımlılık** | Other IDs or `none` |
| **Kanıt** | Commands + evidence labels after run |

One agent turn owns **one** ID. Closed/evidenced cards stay closed.

## Task right-size

- Prefer tickets that finish with a `ticket`-tier gate, not a release gate.
- Fold docs/setup into the ticket that needs them.
- No TBD placeholders in Dosyalar / Kanıt / Bitti sayılır.
- Global Pala constraints (evidence labels, no hook-started tests, no quota
  claims) apply to every card without restating.

## Handoff

After cards exist: update STATUS "tek sonraki iş" to the first open ID, then
follow [execute-tickets.md](execute-tickets.md).

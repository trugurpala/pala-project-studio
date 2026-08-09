# Execute tickets (one ID)

Use when PLAN already has an approved `M*-T*` card.
Inspired by Superpowers executing-plans — without mandatory subagents.

## Process

1. Load STATUS → pick the single next ID → read only that card + DEBUGGING.
2. `pala_state.py begin --ticket <ID> --goal "…"` before edits.
3. Red/green: narrowest failing check first when adding behavior
   ([quality-gates.md](quality-gates.md)).
4. Stay inside **Dosyalar**; stop on blockers instead of guessing.
5. Run the card's Kanıt commands; record labels honestly.
6. Checkpoint (`ticket` tier when the card closes) + refresh STATUS next action.

## Parallel / subagents

Only when the host already supports them **and** cards have disjoint
**Dosyalar** / owners. No new MCP required. Parent keeps one STATUS next
action; children do not invent a second store.

## Stop and ask

Missing dependency, unclear instruction, repeated verification failure, or
authority boundary (commit/push/PR). Do not "push through" on main without
explicit consent.

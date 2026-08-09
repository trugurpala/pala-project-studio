# Token-Efficient Context

Pala cannot increase a model's context window, usage allowance, or token
budget. It improves continuity by keeping irrelevant material out of the active
prompt and preserving durable facts in files.

## Loading order

1. Read the short Pala `context` output and the registered status document.
2. Open only the active ticket section in the registered plan.
3. Read product, decisions, architecture, or domain references only when the
   active ticket depends on them.
4. Inspect source and tests nearest to the change; avoid generated trees.
5. Summarize command evidence in status instead of copying long logs into chat.

Keep one chat focused on one coherent outcome. After compaction, Codex may fire
`SessionStart` with `source: compact`; Pala re-injects presence + cold packet +
active ticket + next action. Mid-turn forgetfulness without a host event has no
automatic re-inject — re-read STATUS/PLAN, ask for a cold packet, or start a
new chat. Do not pretend continuous chat memory. Start a new chat when the
outcome changes, while retaining project files as the durable handoff.

Codex currently applies progressive disclosure to skills, a configurable
combined project-instruction byte limit, and bounded model-visible hook output.
Treat these as version-sensitive host behavior: consult current official Codex
guidance before changing plugin constants. Keep Pala's SessionStart message far
below the host limit and never put test logs, full plans, secrets, or raw
transcripts into hook context.

Codex applies a hard per-value additionalContext token budget (about 1000
tokens) with middle truncation. Pala SessionStart must keep presence, active
ticket, next action, and blockers outside the truncated middle. Prefer the
cold packet over repeating the same facts in long health prose. Re-check
official Codex guidance before changing `SESSION_CONTEXT_*` constants.

Measure token or speed improvements only with comparable runs. A shorter prompt
is an optimization hypothesis, not proof of a percentage gain.

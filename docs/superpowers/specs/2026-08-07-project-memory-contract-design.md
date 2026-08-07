# Pala 0.5.0 — Project Memory Contract (Design)

**Date:** 2026-08-07  
**Base:** `main` @ `5a08e4e` (0.4.4)  
**Root:** `C:\Users\Pala-Pc\Desktop\Cursor\pala-project-studio`  
**Related GitHub:** open PR #5 `feat: add Pala 0.5A truth core` (snapshot/worktree truth) — **orthogonal**. This design does not merge or reimplement 0.5A; it evolves memory/quality continuity on current main.

## Intent

Pala is not only a code-writing aid. It is the project’s durable memory and quality steward: sessions bootstrap from **folder truth**, not chat history; “done” requires evidence; tooling honesty and ticket coherence are automatic.

## Sources / limits consulted

| Source | Takeaway |
| --- | --- |
| Local `docs/CODEX_SCOPE_AND_LIMITS.md` | SessionStart tight budget; hooks must not run tests/network/GitHub mutations; progressive disclosure |
| Local `hooks/hooks.json` | `additionalContextLimit: 800` on SessionStart |
| Local ADR-002 | Hook = paths + ticket scalars, **not** document bodies |
| Local PR #5 (0.5A) | Snapshot/worktree ownership is separate track — do not fork that design here |
| Codex Hooks docs ([learn.chatgpt.com/docs/hooks](https://learn.chatgpt.com/docs/hooks)) | `additionalContextLimit` is a **token** spill threshold (default ~2500); Pala keeps a **stricter product contract**: SessionStart message ≤ **800 characters** (existing unittest) |
| Pala 0.4 single-door | Global install ≠ personal catalog; Desktop Codex catalog is an **optional local index**, secrets-free, not a packaging dependency |

## IN SCOPE

1. **Forced read_order** (agent contract + `context` JSON):  
   `AGENTS.md` → `CURRENT_STATUS` → `PROGRESS` → active plan → `TOOLING_DECISIONS` → `DEBUGGING` → git status summary
2. **Document purpose split** in `CANDIDATES`: `status` vs `progress` vs `tooling` vs `debugging`
3. **Tool memory statuses:** `installed` | `recommended` | `installed_unverified` | `not_installed` | `unavailable` (mapped from adapters; separate from verification enums)
4. **Evidence-gated checkpoint:** structured checks; refuse soft “done”; statuses include `passed`, `not-run`, `blocked`, `configured-not-verified`, `failed`, `timeout`
5. **Ticket coherence:** active vs next mismatch → workflow flag + `CURRENT_STATUS` warning block
6. **Cross-project catalog:** `C:\Users\Pala-Pc\Desktop\Codex\pala-catalog.json` (+ `INDEX.md`), upsert on register/checkpoint/doctor
7. Skill/docs/ADR/version bump to **0.5.0**

## OUT OF SCOPE

- Rewrite-from-zero / replacing 0.4 architecture
- Merging PR #5 Truth Core / pala_snapshot
- Injecting full document bodies into SessionStart
- Installing Gemini / VS Code extensions / Xdebug (only honest status recording)
- Claiming unverified % speed/token improvements
- Network from hooks; secrets/transcripts in catalog or hook output
- Making Desktop Codex required for portable ZIP install

## LIMITS (hard)

| Limit | Rule |
| --- | --- |
| Hook size | `session_context` message ≤ 800 **characters** (tests + product) |
| Hook content | Paths, scalars, tool counts, mismatch flag — never file bodies |
| Enums | Adapter/tool-memory ≠ `VERIFICATION_STATUSES` |
| Catalog | Secrets-free; path + github + tech + phase + quality + tools summary + next + blockers |
| Hooks | No test/build/network/GitHub mutation (ADR-007) |
| YAGNI | Evolve scripts + skill; no new MCP server (ADR-001) |

## Architecture

```text
SessionStart → pala_hook.session_context
                 ← pala_memory.contract_context (read_order paths, coherence, git short)
                 ← pala_tool_memory.summary (counts only)
Agent skill → MUST read bodies in MEMORY_READ_ORDER
checkpoint → evidence gate + coherence write → CURRENT_STATUS patch → pala_catalog.upsert
```

## Layer order

1. `pala_memory.py` + CANDIDATES + `context_report.read_order` + stubs  
2. `pala_tool_memory.py` + doctor surface  
3. Evidence-gated checkpoint + verification status expand  
4. `ticket_coherence_report` + status mismatch block  
5. `pala_catalog.py`  
6. Hook / SKILL / ADR / plugin 0.5.0  
7. `scripts/verify.py` green  

## Acceptance tests (minimum)

- discover: `PROGRESS.md` is `progress`, not competing with `status`; `CURRENT_STATUS` preferred for status when present  
- `contract_context` / `context_report` expose ordered `read_order`  
- SessionStart still ≤800 chars; still omits decisions/open_source bodies/paths unless already registered in status/plan slots  
- checkpoint rejects failed / soft-done without structured evidence  
- coherence mismatch sets `memory_mismatch` and status warning  
- catalog upsert idempotent under Desktop\Codex  
- tool status mapping unit tests  
- `verify.py` full gate  

## Self-review (Phase B)

- ADR-002 preserved: hook remains progressive disclosure.  
- Six user pillars covered in IN SCOPE.  
- No rewrite; version 0.5.0 on top of 0.4.4.  
- No contradiction with 0.5A PR: we do not add snapshot store here.  
- Catalog path is machine-local convenience, not global install coupling (ADR-005 spirit).  

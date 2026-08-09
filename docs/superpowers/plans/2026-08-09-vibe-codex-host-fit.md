# Vibe Codex Host-Fit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Pala a reliable vibe-coder companion under real Codex host limits: SessionStart stays under the host’s hard additionalContext token cap, the skill stays small enough for progressive disclosure, and the first-10-minute vibe path remains evidence-honest and truncation-safe.

**Architecture:** Treat Codex as the host budget owner. Pala never enlarges context/quota; it only chooses what enters the prompt. Align constants and SessionStart composition to the host’s ~1000-token hard cap on each `additionalContext` value and ~2500-token hook-output spill. Prefer the evidence-first cold packet over duplicated legacy prose; keep `SKILL.md` thin and move the long `kontrol et` checklist into a reference. Refresh `docs/CODEX_SCOPE_AND_LIMITS.md` so engineers stop coding against stale 0.3 / 800-char assumptions.

**Tech Stack:** Python 3.10+ stdlib, Codex plugin hooks (`hooks/hooks.json` + `pala_hook.py`), skill + references, unittest, Windows `py -3`.

## Global Constraints

- Evidence labels only: `passed` | `not-run` | `blocked` | `configured-not-verified`.
- Hooks never start network, tests, builds, commit, or push (ADR-007).
- No soft speed/quota/context-enlarge claims; no invented “% faster”.
- UTF-8 no BOM, LF line endings; preserve Turkish Unicode.
- Cursor is thin reminder only; no “Pala Cursor plugin installed” or Codex hook parity claims (ADR-017).
- Commit / push / tag / `gh release` only with explicit owner authority.
- Host numbers are version-sensitive: document the source date and re-check official Codex guidance before changing constants again.

## Why this plan (review snapshot)

| Area | Today | Host reality / gap |
| --- | --- | --- |
| Product intent | Vibe coder tool: presence → one next action → working commands → DEBUGGING → Status HTML | Correct product shape |
| SessionStart budget | `SESSION_CONTEXT_LIMIT = 2048` **characters** + legacy health prose + cold packet | Codex renders each `additionalContext` with a **hard ~1000-token** middle-truncate; long messages can lose the middle (presence or next-action) |
| Limits doc | `docs/CODEX_SCOPE_AND_LIMITS.md` still says Pala 0.3 / SessionStart **800 char** | Stale vs code (`2048`) and vs host token cap |
| Skill size | `SKILL.md` ≈ **554 words**; checklist docs say ≤450; tests allow ≤650 | Progressive disclosure wants a thin skill; kontrol checklist bloated the body |
| Cold packet | `pala_cold_packet` ≤2KB minimal + budgets | Good design; must win over legacy SessionStart duplication |
| Vibe path | `docs/VIBE_FIRST_SESSION.md` exists | Needs contract tests that prove host-fit constants, not just prose |
| Runtime evidence | Gate0 / mini A/B / installed verify largely `passed` on Pala-Pc | Full source `verify.py` often `not-run`; `/hooks` UI trust still `configured-not-verified` |

### Codex host limits Pala must design around

1. **Skill discovery:** only a small skill index enters context; full `SKILL.md` loads when selected → keep body short; put detail in references.
2. **AGENTS.md chain:** finite combined project-instruction budget → keep durable rules in `AGENTS.md`, changing work in STATUS/PLAN/PROGRESS.
3. **Hook visible output:** ~2500-token spill default per handler → keep hooks local, short, secrets-free.
4. **additionalContext hard cap:** ~1000 tokens per value with middle truncation → SessionStart must stay **well under** that budget so presence + next action + blockers are not the truncated middle.
5. **Hook trust:** human `/hooks` UI step; Doctor `hook_safety=passed` ≠ UI trust.
6. **Pala cannot:** enlarge context/quota/speed; run hidden test/build/network from hooks; claim Cursor hook parity.

---

## File map

| File | Responsibility |
| --- | --- |
| `docs/CODEX_SCOPE_AND_LIMITS.md` | Host limits table (dated), Pala decisions, can/cannot |
| `docs/CODEX_PLUGIN_CHECKLIST.md` | Sync SessionStart / skill budget evidence rows |
| `docs/VIBE_FIRST_SESSION.md` | First-10-minute path; note truncation-safe SessionStart |
| `scripts/pala_tokens.py` | Shared cheap token estimate (chars/4); no % claims |
| `scripts/pala_hook.py` | SessionStart composition under token+char dual budget |
| `hooks/hooks.json` | `additionalContextLimit` matches Pala constant |
| `scripts/pala_cold_packet.py` | Reuse shared estimator; keep minimal ≤2KB |
| `skills/pala-project-finisher/SKILL.md` | Thin vibe / operating contract |
| `skills/pala-project-finisher/references/kontrol-et.md` | Numbered read-only checklist moved out of skill body |
| `skills/.../references/token-efficient-context.md` | Point at current host caps |
| `scripts/pala_self_audit.py` | Presence / limit / skill-budget checks |
| `scripts/test_pala_host_fit.py` | New contract tests for token budget + vibe markers |
| `scripts/test_plugin_experience.py` | Align skill word ceiling with thin-skill decision |
| `STATUS.md` / `PLAN.md` / `CHANGELOG.md` | Evidence only after gates run |

---

### Task 1: Refresh Codex limits doc + checklist (source of truth)

**Files:**
- Modify: `docs/CODEX_SCOPE_AND_LIMITS.md`
- Modify: `docs/CODEX_PLUGIN_CHECKLIST.md`
- Modify: `skills/pala-project-finisher/references/token-efficient-context.md`

**Interfaces:**
- Consumes: none
- Produces: documented host caps dated `2026-08-09`; engineers read this before changing hook constants

- [ ] **Step 1: Rewrite `docs/CODEX_SCOPE_AND_LIMITS.md` header + limits table**

Replace the stale “Pala 0.3 / 800 char” table with:

```markdown
# Codex Kapsamı ve Limitleri

Bu kayıt 2026-08-09 tarihinde Codex host davranışı (plugin hooks /
additionalContext rendering + skill progressive disclosure) üzerinden
yeniden hizalanmıştır. Host sürümü değişebilir; Pala bu sayıları ürün
gerçeği gibi sonsuza dondurmaz — sabitleri değiştirmeden önce resmî
Codex kaynaklarını yeniden oku.

## Doğrulanmış sınırlar (host)

| Yüzey | Codex davranışı | Pala kararı |
| --- | --- | --- |
| Skill keşfi | Skill indeksi küçük tutulur; tam `SKILL.md` seçilince yüklenir. | Tek yönlendirici skill; gövde ince; ayrıntı `references/`. |
| Proje talimatı | Birleşik `AGENTS.md` zinciri boyut sınırlıdır. | Değişen iş STATUS/PLAN/PROGRESS’te; `AGENTS.md` yalnız kalıcı kurallar. |
| Hook çıktısı | Modelin gördüğü hook çıktısı ~2500 token sonra spill dosyasına taşabilir. | Hook kısa, yerel, secretsız; test/build/ağ yok. |
| additionalContext | Her değer ~**1000 token** sert tavan; aşımda middle-truncate. | SessionStart **token+char** çift bütçe; cold packet öncelikli; presence + next action kenarda korunur. |
| Oturum sıkıştırma | `PreCompact` + sonrası `SessionStart` olabilir. | Yalnız aktif ticket / reconcile / cold packet; tam plan veya test logu yok. |
| Turn sonu | `Stop` `decision: block` otomatik devam istemi üretebilir. | Yalnız dirty aktif iş checkpoint; test/build başlatmaz. |
| Hook güveni | UI’da incelenip güvenilmeli. | Doctor `hook_safety` ≠ `/hooks` trust (`configured-not-verified` until human). |
```

Keep the existing “Pala’nın yapabildiği / yapamadığı / Token yaklaşımı / Neden MCP yok” sections, updating any “800 karakter” or “0.3” references to the dual-budget story.

- [ ] **Step 2: Sync checklist rows**

In `docs/CODEX_PLUGIN_CHECKLIST.md`, change the SessionStart and skill rows to:

```markdown
| SessionStart budget | Dual: char limit + approx-token ≤900 (host ~1000 hard) | contract tests |
| Skill body size | Thin skill; detal in `references/kontrol-et.md` | contract tests |
| `/hooks` UI trust | Human Codex Work click | `configured-not-verified` |
```

- [ ] **Step 3: Point token-efficient-context at host hard cap**

Add one short paragraph to `references/token-efficient-context.md`:

```markdown
Codex applies a hard per-value additionalContext token budget (about 1000
tokens) with middle truncation. Pala SessionStart must keep presence, active
ticket, next action, and blockers outside the truncated middle. Prefer the
cold packet over repeating the same facts in long health prose. Re-check
official Codex guidance before changing `SESSION_CONTEXT_*` constants.
```

- [ ] **Step 4: Commit (when owner authorizes)**

```bash
git add docs/CODEX_SCOPE_AND_LIMITS.md docs/CODEX_PLUGIN_CHECKLIST.md skills/pala-project-finisher/references/token-efficient-context.md
git commit -m "docs: realign Codex host limits for vibe SessionStart budget"
```

---

### Task 2: Shared cheap token estimate helper

**Files:**
- Create: `scripts/pala_tokens.py`
- Create: `scripts/test_pala_tokens.py`
- Modify: `scripts/pala_cold_packet.py` (import shared estimator; delete local duplicate)

**Interfaces:**
- Consumes: none
- Produces:
  - `approx_tokens(text: str) -> int` — `max(1, (len(text) + 3) // 4)` for non-empty; `0` for empty
  - Used by hook budget + cold packet metadata only (never as a product % claim)

- [ ] **Step 1: Write the failing test**

```python
# scripts/test_pala_tokens.py
from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pala_tokens


class PalaTokensTests(unittest.TestCase):
    def test_empty_is_zero(self) -> None:
        self.assertEqual(pala_tokens.approx_tokens(""), 0)

    def test_four_chars_one_token(self) -> None:
        self.assertEqual(pala_tokens.approx_tokens("abcd"), 1)

    def test_unicode_counts_characters(self) -> None:
        # 8 unicode chars -> 2 approx tokens
        self.assertEqual(pala_tokens.approx_tokens("Palaİşte"), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m unittest scripts.test_pala_tokens -v`  
Expected: FAIL with `ModuleNotFoundError: pala_tokens` (or import error)

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/pala_tokens.py
"""Cheap token approximations for host-budget guards (not product metrics)."""

from __future__ import annotations


def approx_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)
```

- [ ] **Step 4: Wire cold packet to shared helper**

In `scripts/pala_cold_packet.py`, replace `_estimate_tokens` body with:

```python
from pala_tokens import approx_tokens as _estimate_tokens
```

(or keep a one-line wrapper `_estimate_tokens = approx_tokens` if many call sites exist). Ensure no circular import with `pala_hook`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `py -3 -m unittest scripts.test_pala_tokens scripts.test_pala_cold_packet -v`  
Expected: PASS

- [ ] **Step 6: Commit (when owner authorizes)**

```bash
git add scripts/pala_tokens.py scripts/test_pala_tokens.py scripts/pala_cold_packet.py
git commit -m "feat: share approx token helper for Codex host budgets"
```

---

### Task 3: SessionStart dual budget under host ~1000-token cap

**Files:**
- Modify: `scripts/pala_hook.py`
- Modify: `hooks/hooks.json`
- Modify: `scripts/pala_self_audit.py`
- Modify: `scripts/test_pala_host_fit.py` (create in this task or Task 5; at least hook tests here)

**Interfaces:**
- Consumes: `pala_tokens.approx_tokens`
- Produces:
  - `SESSION_CONTEXT_CHAR_LIMIT = 1800` (char ceiling; leaves headroom vs old 2048)
  - `SESSION_CONTEXT_TOKEN_BUDGET = 900` (approx tokens; under host ~1000 hard cap)
  - `hooks.json` `additionalContextLimit` == `SESSION_CONTEXT_CHAR_LIMIT`
  - `session_context(...)` keeps `PRESENCE_LINE` prefix; prefers cold packet; trims legacy middle first

- [ ] **Step 1: Write failing host-fit tests**

```python
# scripts/test_pala_host_fit.py (initial cases)
from __future__ import annotations

import json
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pala_hook
import pala_tokens


class SessionStartHostFitTests(unittest.TestCase):
    def test_hooks_json_matches_char_limit(self) -> None:
        hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        session = hooks["hooks"]["SessionStart"][0]["hooks"][0]
        self.assertEqual(
            int(session["additionalContextLimit"]),
            pala_hook.SESSION_CONTEXT_CHAR_LIMIT,
        )

    def test_token_budget_under_host_hard_cap(self) -> None:
        self.assertLessEqual(pala_hook.SESSION_CONTEXT_TOKEN_BUDGET, 900)
        self.assertLess(pala_hook.SESSION_CONTEXT_TOKEN_BUDGET, 1000)

    def test_session_context_prefers_cold_packet_and_stays_in_budget(self) -> None:
        cold = "COLD\nnext=M30-T1\nstale-context=false\n" + ("x" * 1200)
        out = pala_hook.session_context(
            documents={"status": "STATUS.md", "plan": "PLAN.md", "project": "PROJECT.md"},
            workflow={"active_ticket": "M30-T1", "next_action": "write failing test", "dirty": False, "blockers": []},
            compacted=False,
            project_kind="software",
            health={"plugin": "loaded", "python": "ready", "git": "ready", "hook": "running"},
            cold_packet_text=cold,
        )
        msg = out["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(msg.startswith(pala_hook.PRESENCE_LINE))
        self.assertIn("COLD", msg)
        self.assertLessEqual(len(msg), pala_hook.SESSION_CONTEXT_CHAR_LIMIT)
        self.assertLessEqual(
            pala_tokens.approx_tokens(msg),
            pala_hook.SESSION_CONTEXT_TOKEN_BUDGET,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3 -m unittest scripts.test_pala_host_fit -v`  
Expected: FAIL (`SESSION_CONTEXT_CHAR_LIMIT` missing / old `SESSION_CONTEXT_LIMIT`)

- [ ] **Step 3: Implement dual-budget SessionStart**

In `scripts/pala_hook.py`:

```python
from pala_tokens import approx_tokens

PRESENCE_LINE = "Pala burada — bu oturumda yanındayım."
# Char ceiling for hooks.json additionalContextLimit (must match).
SESSION_CONTEXT_CHAR_LIMIT = 1800
# Approx-token budget under Codex hard ~1000-token additionalContext cap.
SESSION_CONTEXT_TOKEN_BUDGET = 900
# Back-compat alias for older imports/tests during migration.
SESSION_CONTEXT_LIMIT = SESSION_CONTEXT_CHAR_LIMIT


def _fit_session_message(message: str) -> str:
    """Trim legacy middle first so presence + tail (cold packet / gate) survive."""
    if (
        len(message) <= SESSION_CONTEXT_CHAR_LIMIT
        and approx_tokens(message) <= SESSION_CONTEXT_TOKEN_BUDGET
    ):
        return message
    prefix = PRESENCE_LINE
    if not message.startswith(prefix):
        # Hard clip if contract broken.
        clipped = message[: SESSION_CONTEXT_CHAR_LIMIT - 3] + "..."
        while approx_tokens(clipped) > SESSION_CONTEXT_TOKEN_BUDGET and len(clipped) > 64:
            clipped = clipped[: max(64, len(clipped) - 64)]
        return clipped
    body = message[len(prefix) :].lstrip()
    # Keep last ~40% (cold packet / gate / cmd hint) when shrinking.
    keep_tail = max(160, int(len(body) * 0.4))
    while True:
        candidate = f"{prefix} {body}"
        if (
            len(candidate) <= SESSION_CONTEXT_CHAR_LIMIT
            and approx_tokens(candidate) <= SESSION_CONTEXT_TOKEN_BUDGET
        ):
            return candidate
        if len(body) <= keep_tail + 32:
            # Last resort: presence + truncated tail only.
            tail = body[-keep_tail:] if len(body) > keep_tail else body
            candidate = f"{prefix} ...{tail}"
            if len(candidate) > SESSION_CONTEXT_CHAR_LIMIT:
                candidate = candidate[: SESSION_CONTEXT_CHAR_LIMIT - 3] + "..."
            while (
                approx_tokens(candidate) > SESSION_CONTEXT_TOKEN_BUDGET
                and len(candidate) > len(prefix) + 32
            ):
                candidate = candidate[: max(len(prefix) + 16, len(candidate) - 48)]
            return candidate
        # Drop from the middle of the legacy body.
        drop = max(48, (len(body) - keep_tail) // 4)
        head = body[: max(0, len(body) - keep_tail - drop)]
        tail = body[-keep_tail:]
        body = f"{head}...{tail}"
```

Update every trim site that used `SESSION_CONTEXT_LIMIT` to call `_fit_session_message` at the end of `session_context` before return. Prefer attaching cold packet **before** final fit so `_fit_session_message` protects presence + packet tail.

Shorten the default legacy `message = (...)` string: drop redundant “Memory read_order=…” when `cold_packet_text` is non-empty (cold packet already carries next/blocker/freshness). Keep a one-line health cue only:

```python
if cold_packet_text and str(cold_packet_text).strip():
    message = (
        f"{PRESENCE_LINE} {prefix}{health_text}"
        f"kind={kind}; active={active or 'none'}; "
        f"status={status or project}; plan={plan}. "
        f"dirty={str(dirty).lower()}; blockers={blocker_count}; "
        f"reconcile={str(needs_reconcile).lower()}({reason_count}); "
        f"debug_open={debug_open}."
    )
else:
    # existing longer legacy message for unregistered/no-packet paths
    ...
```

- [ ] **Step 4: Sync `hooks/hooks.json`**

Set SessionStart (and keep PreCompact using same script) `additionalContextLimit` to `1800`.

- [ ] **Step 5: Update `pala_self_audit.py` presence check**

Assert:

```python
if int(session.get("additionalContextLimit") or 0) != pala_hook.SESSION_CONTEXT_CHAR_LIMIT:
    return _check("presence", "failed", "additionalContextLimit mismatch")
...
if len(str(message)) > pala_hook.SESSION_CONTEXT_CHAR_LIMIT:
    return _check("presence", "failed", "session context over char limit")
if pala_tokens.approx_tokens(str(message)) > pala_hook.SESSION_CONTEXT_TOKEN_BUDGET:
    return _check("presence", "failed", "session context over token budget")
```

- [ ] **Step 6: Run focused tests**

Run:

```powershell
py -3 -m unittest scripts.test_pala_host_fit scripts.test_pala_cold_packet scripts.test_pala_self_audit scripts.test_pala_tools -v
```

Expected: PASS (update any tests still importing only `SESSION_CONTEXT_LIMIT` behavior that assumed 2048-only char trim).

- [ ] **Step 7: Commit (when owner authorizes)**

```bash
git add scripts/pala_hook.py hooks/hooks.json scripts/pala_self_audit.py scripts/test_pala_host_fit.py
git commit -m "fix(hooks): fit SessionStart under Codex additionalContext token cap"
```

---

### Task 4: Thin skill for vibe progressive disclosure

**Files:**
- Create: `skills/pala-project-finisher/references/kontrol-et.md`
- Modify: `skills/pala-project-finisher/SKILL.md`
- Modify: `scripts/test_plugin_experience.py`
- Modify: `scripts/test_pala_p0_friction.py` (if it asserts checklist text inside SKILL.md)
- Modify: `scripts/pala_p0_smoke.py` (only if it greps skill for checklist markers)

**Interfaces:**
- Consumes: none
- Produces: `SKILL.md` body ≤ **480 words** (hard contract); full numbered kontrol checklist lives in `references/kontrol-et.md`; skill still names `kontrol et` / `rapor` / `denetle` and points to the reference

- [ ] **Step 1: Write failing skill-budget test**

In `scripts/test_plugin_experience.py`, change the word ceiling and require the reference:

```python
def test_orchestrator_is_concise_and_declares_human_contract(self) -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    # Thin skill for Codex progressive disclosure (detail in references/).
    self.assertLessEqual(len(skill.split()), 480)
    ...
    self.assertIn("references/kontrol-et.md", skill)
```

Move numbered-checklist assertions from `test_kontrol_et_readonly_checklist_markers` to also read the reference file:

```python
def test_kontrol_et_readonly_checklist_markers(self) -> None:
    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    ref = (REFERENCE_ROOT / "kontrol-et.md").read_text(encoding="utf-8")
    for marker in ("kontrol et", "rapor", "denetle", "references/kontrol-et.md"):
        self.assertIn(marker, skill)
    for marker in (
        "Presence",
        "pala_report",
        "discover",
        "STATUS",
        "PLAN",
        "DEBUGGING",
        "pala-status.html",
        "do not register, begin",
    ):
        self.assertIn(marker, ref)
    for step in ("1.", "2.", "3.", "4.", "5.", "6.", "7."):
        self.assertIn(step, ref)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3 -m unittest scripts.test_plugin_experience.PluginExperienceTests.test_orchestrator_is_concise_and_declares_human_contract -v`  
Expected: FAIL (554 > 480) and/or missing reference path

- [ ] **Step 3: Create `references/kontrol-et.md`**

Move the current numbered Read-only checklist (steps 1–7) verbatim into:

```markdown
# pala kontrol et / rapor / denetle

Read-only. Do not register, begin, edit, or write state.

1. Presence — open with "Pala burada — bu oturumda yanındayım."
2. Report — `pala_report.py --cwd .` (omit `--open` unless asked); keep Status HTML path.
3. Discover — `pala_state.py discover --cwd .`, then `instructions`; if registered, `context`.
4. STATUS/PLAN — active ticket + single next action only; no invented tickets.
5. DEBUGGING — open `INC-*` / Fix criteria; do not repeat known failures.
6. Gates — honesty only (`passed`|`not-run`|`blocked`|`configured-not-verified`); never mark unrun gates `passed`.
7. Status HTML — hand off `.codex/pala-status.html` and the report `açmak için:` line.
```

- [ ] **Step 4: Slim `SKILL.md` Task Modes bullet**

Replace the long inline checklist with:

```markdown
- **Read-only audit/report** (`kontrol et` / `rapor` / `denetle`): inspect and run non-mutating checks; do not register, begin, edit, or write state. Follow [kontrol-et.md](references/kontrol-et.md).
```

Keep Human Contract, Scripts (cwd-safe), Operating Contract, and safety lines. Target ≤480 words total file split count (frontmatter + body as today’s test counts `skill.split()` on full file — match whatever the existing test measures; if the test counts the whole file, trim until that assertion passes).

- [ ] **Step 5: Fix dependent greps**

Update `test_pala_p0_friction.py` / `pala_p0_smoke.py` if they require numbered steps inside `SKILL.md` — point them at `references/kontrol-et.md` or accept skill+reference combo.

- [ ] **Step 6: Run tests**

Run:

```powershell
py -3 -m unittest scripts.test_plugin_experience scripts.test_pala_p0_friction -v
```

Expected: PASS

- [ ] **Step 7: Commit (when owner authorizes)**

```bash
git add skills/pala-project-finisher/SKILL.md skills/pala-project-finisher/references/kontrol-et.md scripts/test_plugin_experience.py scripts/test_pala_p0_friction.py scripts/pala_p0_smoke.py
git commit -m "refactor(skill): thin vibe skill; move kontrol checklist to reference"
```

---

### Task 5: Vibe first-session contract + docs touch

**Files:**
- Modify: `docs/VIBE_FIRST_SESSION.md`
- Modify: `scripts/test_pala_host_fit.py`

**Interfaces:**
- Consumes: Task 3 constants; Task 4 skill/reference
- Produces: automated “vibe path still honest” checks

- [ ] **Step 1: Extend host-fit tests for vibe markers**

```python
class VibeFirstSessionTests(unittest.TestCase):
    def test_vibe_doc_states_host_trust_boundary(self) -> None:
        text = (ROOT / "docs" / "VIBE_FIRST_SESSION.md").read_text(encoding="utf-8")
        self.assertIn("hook_safety", text)
        self.assertIn("/hooks", text)
        self.assertIn("Pala burada", text)
        self.assertIn("additionalContext", text.casefold() + "token")  # see step 2 wording

    def test_skill_points_kontrol_reference(self) -> None:
        skill = (ROOT / "skills" / "pala-project-finisher" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("references/kontrol-et.md", skill)
        self.assertNotRegex(skill, r"(?i)enlarges?\s+(context|quota)")
```

Fix the awkward assertion in implementation to two clear `assertIn` checks for `token` budget / truncation note once the doc is updated.

- [ ] **Step 2: Update vibe doc**

Add under “Beklenen ilk sonuç”:

```markdown
- SessionStart metni Codex `additionalContext` token tavanının altında kalır
  (Pala çift bütçe: char + approx-token). Uzun sağlık düzyazısı cold packet’in
  önüne geçmez; middle-truncate olsa bile presence satırı korunacak şekilde
  tasarlanır.
```

- [ ] **Step 3: Run tests**

Run: `py -3 -m unittest scripts.test_pala_host_fit -v`  
Expected: PASS

- [ ] **Step 4: Commit (when owner authorizes)**

```bash
git add docs/VIBE_FIRST_SESSION.md scripts/test_pala_host_fit.py
git commit -m "test: lock vibe first-session host-fit contracts"
```

---

### Task 6: Gate run + evidence binding (no soft claims)

**Files:**
- Modify: `STATUS.md`, `PLAN.md`, `CHANGELOG.md`, `PROGRESS.md` (only after commands run)

**Interfaces:**
- Consumes: Tasks 1–5
- Produces: evidence rows with real labels

- [ ] **Step 1: Focused regression**

```powershell
py -3 -m unittest scripts.test_pala_tokens scripts.test_pala_host_fit scripts.test_pala_cold_packet scripts.test_plugin_experience scripts.test_pala_p0_friction scripts.test_pala_self_audit -v
```

Expected: Ran N / OK; exit 0 → label `passed`

- [ ] **Step 2: Installed verify (if marketplace present on this PC)**

```powershell
py -3 scripts/verify.py --mode installed
```

Expected: exit 0 → `passed`; else `blocked` with reason (do not invent `passed`)

- [ ] **Step 3: Optional Gate0 refresh**

```powershell
py -3 scripts/pala_p0_smoke.py
```

Expected: exit 0 and update `artifacts/codex-compat/p0-smoke.json` only if script still passes; else record `failed`/`blocked` honestly.

- [ ] **Step 4: Record evidence**

Update STATUS with a short **M30 — Vibe Codex host-fit** table. Hooks UI trust remains `configured-not-verified`. Soft “A/B fixed” remains absent. Full source `verify.py` only if run; otherwise `not-run`.

- [ ] **Step 5: Commit (when owner authorizes)**

```bash
git add STATUS.md PLAN.md PROGRESS.md CHANGELOG.md artifacts/codex-compat/p0-smoke.json
git commit -m "docs: record M30 vibe Codex host-fit evidence"
```

---

## Self-review

1. **Spec coverage:** Host limits refresh → Task 1. Token helper → Task 2. SessionStart under ~1000-token cap → Task 3. Thin skill / progressive disclosure → Task 4. Vibe path lock → Task 5. Evidence → Task 6. Out of scope (bilerek): `/hooks` UI click, `v0.8.1` GitHub release, soft A/B fixed, Cursor hook parity, MCP supermarket.
2. **Placeholder scan:** No TBD/TODO; tests and code blocks are concrete.
3. **Type consistency:** `SESSION_CONTEXT_CHAR_LIMIT`, `SESSION_CONTEXT_TOKEN_BUDGET`, `approx_tokens`, `references/kontrol-et.md` names match across tasks. Alias `SESSION_CONTEXT_LIMIT` kept during migration.
4. **YAGNI:** No new dashboard, no cloud sync, no second memory store, no speed %.

## Bilerek yapılmayanlar

- Claiming Codex `/hooks` UI trust = `passed` from CLI
- Formal `v0.8.1` tag/release without owner authority
- Soft “full-product A/B fixed”
- Enlarging context/quota or promising token savings percentages
- Cursor Codex-hook parity

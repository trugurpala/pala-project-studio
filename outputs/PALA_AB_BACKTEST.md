# Pala A/B — Codex live early-stop (Wave C)

**TR / EN executive summary.** Honest labels only. No blind scores invented.

| Field | Value |
| --- | --- |
| Experiment class | `controlled-ab-early-stop` |
| Source | Owner Codex live A/B (temp profiles) |
| Measured Pala | Marketplace **`0.8.0+codex.20260808021500`** |
| Model | `gpt-5.6-terra` high (both arms) |
| Completed | Control **n=3**, Pala **n=2** |
| Blind eval | **`not-run`** (early-stop before blind) |
| Ingest | 2026-08-08 Cursor → `outputs/PALA_AB_*` |

> **Post-A/B note:** Cursor repo source already shipped P0 path / `begin --goal` / `complete` recovery as **`0.8.1`** *after* this A/B. Agents still on marketplace **0.8.0** until Update/reinstall. Do not claim this A/B measured 0.8.1.

---

## Karar / Decision

**TR:** Handoff / checkpoint / hafıza yardımcısı olarak **tutmaya değer**. Hız veya güvenilirlik yükseltmesi olarak **henüz değil**.

**EN:** **Worth keeping** as a handoff/checkpoint aid. **Not** yet a speed or reliability upgrade.

---

## Özet tablolar / Summary tables

Completed arms only (early-stop; pala vs control):

| Metric | Control (completed) | Pala (completed) | Pala vs control |
| --- | --- | --- | --- |
| Tokens | — | — | **+49.97%** |
| Commands | — | — | **+60.61%** |
| Duration | — | — | **+26.79%** |
| Tests mean (directional) | **8** | **10.5** | higher on Pala; **not blind** |
| Handoff understanding mean | **170 s** | **390 s** | Pala slower to re-orient |

No quality_% / blind rubric totals — blind eval was **`not-run`**.

Prior harness Su Takip quasi-experiment (Desktop PalaAB, n=5+5 blind) is a **separate** `quasi-experiment`; do not mix its scores into this live early-stop decision.

---

## Ne yardımcı oldu / What helped

| Area | Result | Note |
| --- | --- | --- |
| Presence / SessionStart | `passed` | Hook + skill invoked on Pala arm |
| Register | `passed` | Project docs / ticket surface |
| Context / read order | `passed` | Memory contract used |
| Checkpoint | `passed` | Evidence labels persisted |
| Handoff docs | `passed` | Session-2 could read STATUS/PLAN/DEBUGGING trail |

**TR:** Pala, oturumlar arası **devralma belgelerini** ve checkpoint izini gerçekten üretti.

**EN:** Pala actually produced cross-session handoff artifacts and checkpoints.

---

## Ne tuttu / What held back

| Area | Result | Note |
| --- | --- | --- |
| `complete` | `failed` | Ticket missing in SQLite / lifecycle break |
| Same-error non-repetition | `failed` | `../../scripts` path broken **every** Pala run |
| `begin` | `partial` | `--goal` friction / retry cost |
| DEBUGGING brain | `partial` | Present but did not stop product-path repeat |

**Cost:** more tokens, commands, and wall time on Pala completed runs — not a speed win.

---

## P0 / P1 / P2

| Pri | Item | Status vs this A/B |
| --- | --- | --- |
| **P0** | Skill script path (`../../scripts` from project cwd) | Measured **failed** on 0.8.0; **fixed in Cursor 0.8.1 source** (post-A/B) — needs marketplace Update |
| **P0** | `complete` / ticket recovery | Measured **failed** on 0.8.0; recovery DX in 0.8.1 source |
| **P0** | `begin --goal` DX | Measured **partial**; Turkish/`--goal` help in 0.8.1 source |
| **P1** | Token / command / duration overhead | Pala +50% / +61% / +27% on completed — product cost, not a win claim |
| **P1** | Handoff understanding time | Pala mean 390s vs control 170s — memory trail helps later, first re-read costlier |
| **P2** | Finish blind eval + balanced n | Early-stop left pala n=2; no blind scores |
| **P2** | Hooks `/hooks` UI trust | Still `configured-not-verified` (human) |

---

## Sınırlamalar / Limitations

1. **Early-stop** — not a full 3×2 matrix completion; control n=3, pala n=2.
2. **No blind evaluation** — test means are directional only; no fake quality_%.
3. Measured **marketplace 0.8.0**, not post-fix Cursor **0.8.1** source.
4. Temp-profile isolation (main install not uninstalled) — class `controlled-ab-early-stop`, not “uninstall race”.
5. Harness transport quirks (CLI stdin hang) affected run management; not scored as Pala product quality.
6. No statistical certainty claim; small n.

---

## Evidence labels (Wave C ingest)

| Item | Label |
| --- | --- |
| Wave C ingest (this report) | `passed` (early-stop) |
| Blind scores | `not-run` |
| Hooks UI trust | `configured-not-verified` |
| Full `verify.py` | `not-run` |
| Marketplace Update to pick up P0 | **next action** |

Push / PR / release / commit: **not done** (owner authority).

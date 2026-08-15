# Pala roadmap

Public `v1.1.2` is immutable baseline evidence. Imported M76--M79 WIP has no
current canonical completion evidence; M80 is the ordered release-ready path.

#### M44-T1 — Fresh installed host confirmation
- **Sahip ajan:** User + Codex/Pala
- **Amaç:** Restart Codex once, trust `/hooks`, and observe Pala in a new session.
- **Dosyalar:** installed marketplace, `DEBUGGING.md`, `STATUS.md`
- **Bitti sayılır:** Doctor/resolver remain `passed`; UI observation is recorded.
- **Bağımlılık:** none
- **Kanıt:** `configured-not-verified`

#### M80-T1 — WIP reconciliation and local gate
- **Sahip ajan:** Codex/Pala
- **Amaç:** Preserve WIP, create canonical M80 tasks, reconcile imported claims, and make `verify.py` network-free.
- **Dosyalar:** runtime task/Quality records, `scripts/verify.py`, root state documents
- **Bitti sayılır:** recovery manifest, canonical claim/evidence chain, concise docs, and full local verifier exit 0.
- **Bağımlılık:** M44-T1 observation may remain configured-not-verified
- **Kanıt:** `passed`

#### M80-T2 — Continuity production wiring
- **Sahip ajan:** Codex/Pala
- **Amaç:** Wire snapshot, profile, receipt and history through safe SQLite-backed production context.
- **Dosyalar:** continuity, state/history, report adapters and contracts
- **Bitti sayılır:** end-to-end privacy, migration, rollback and linked-worktree checks exit 0.
- **Bağımlılık:** M80-T1
- **Kanıt:** `passed` (12/12 current required Quality checks)

#### M80-T3 — Host and process execution wiring
- **Sahip ajan:** Codex/Pala
- **Amaç:** Connect observed host capabilities and owned process supervision to Quality execution.
- **Dosyalar:** host broker, coordinator, process supervisor, Quality runner and contracts
- **Bitti sayılır:** conflict, timeout, cancel, restart, orphan and foreign-process checks exit 0.
- **Bağımlılık:** M80-T2
- **Kanıt:** `passed` (7/7 current required Quality checks)

#### M80-T4 — Live Control Center and privacy
- **Sahip ajan:** Codex/Pala
- **Amaç:** Render bounded live read models and close source secret-scan/E2E gaps.
- **Dosyalar:** Control Center, read models, browser/security tests and CI browser setup
- **Bitti sayılır:** escaped/private-safe offline keyboard and responsive generated-page checks exit 0.
- **Bağımlılık:** M80-T3
- **Kanıt:** `passed` (10/10 current required Quality checks)

#### M80-T5 — 1.2.0 package and upgrade evidence
- **Sahip ajan:** Codex/Pala
- **Amaç:** Produce deterministic 1.2.0 identity, package and pinned upgrade/rollback evidence.
- **Dosyalar:** identity, manifest, release/SBOM/inventory, package and upgrade tests
- **Bitti sayılır:** clean-build SHA equality, Windows canary and pinned upgrade matrix exit 0.
- **Bağımlılık:** M80-T4
- **Kanıt:** source/installed/package 7/8 `passed`; commit `f54883f`; Windows branch symlink canary `configured-not-verified`

#### M81-T1 — Branch CI portability remediation
- **Sahip ajan:** Codex/Pala
- **Amaç:** Repair only the symlink, browser-cache and POSIX orphan regressions found by branch CI run 31882450222.
- **Dosyalar:** portable builder, process supervisor, Quality workflow, focused contracts and `DEBUGGING.md`
- **Bitti sayılır:** focused Windows/Linux contracts, full local verifier and replacement branch CI all exit 0.
- **Bağımlılık:** M80-T4; returns evidence to M80-T5
- **Kanıt:** run 31883582516 proved 7/8 jobs including required symlink and both OS verifies; POSIX launcher contracts, real browser journey and 764-test full verifier `passed`; replacement branch CI `not-run`

#### M80-T6 — Release-quality handoff
- **Sahip ajan:** Codex/Pala
- **Amaç:** Run required local Quality and prepare branch-CI evidence without publishing.
- **Dosyalar:** Quality mapping, ReleaseTruth, CI and release handoff
- **Bitti sayılır:** every current required Quality check exits 0 and the authorized branch CI is bound to the final commit.
- **Bağımlılık:** M80-T5 and M81-T1
- **Kanıt:** `not-run`

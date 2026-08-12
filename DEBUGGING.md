# Debugging log

Durable error brain for this project. Read before repeating a known failure.
No secrets, tokens, transcripts, or real user plugin data.

## Format

Each incident uses heading `### INC-YYYYMMDD-slug` and these fields:
Symptoms, Root cause, Fix criteria, Proved by, Related files, Date, Status.
Optional: Attempts (append-only notes when a fix is tried; SQLite
`kind=debug_attempt` mirrors light attempts).
Status may be `open`, `fixed`, or `wontfix`; fixed requires evidence labels
(passed | not-run | blocked | configured-not-verified), not soft done/ok.
When open INC exist, SessionStart/begin/checkpoint emit DEBUG GATE warnings.

## Incidents

### INC-20260811-m60-caller-forged-quality-evidence
- **Symptoms:** `pala_product_cli.py complete` accepted an arbitrary caller
  command plus a caller-reported exit code of `0`, wrote a passed Quality check,
  mapped acceptance, completed the TaskContract, and projected
  `PACKAGE_READY` although the command never executed.
- **Root cause:** The product facade replaced the approved Quality plan with a
  caller-defined check and called `record_result()` using caller data. The
  ledger validated internal consistency, but no trusted execution authority
  produced the process result.
- **Fix criteria:** Product completion accepts only an existing Quality
  ticket/check, executes that check's exact approved argv through a bounded
  shell-free runner at canonical cwd, records actual result plus current basis,
  and requires `pala-quality-runner` authority before acceptance mapping.
  Missing, non-zero, timed-out, or command/argv-mismatched checks cannot produce
  TaskContract `DONE` or project `PACKAGE_READY`.
- **Attempts:** Original six-test production suite failed exactly at the forged
  `exit_code=0` bypass and at the not-yet-implemented trusted CLI. Minimal
  Quality runner/mapping changes then passed all five process-boundary cases;
  direct runner tests cover actual zero, non-zero, timeout, command drift, and
  missing executable without storing raw output. A fresh coverage run reached
  536 tests but the 120-second outer command limit closed stdout at 122 seconds,
  causing a synthetic portable `Errno 22`; retry criterion is the unchanged
  command with a 180-second outer limit, not a product-code change. A redundant
  post-DONE checkpoint returned `owned_by_other` because canonical completion
  had already released the lease; the `completed` WorkflowStore record itself
  is the durable final checkpoint and was not reopened or overwritten.
- **Proved by:** `passed` -- 5 process-boundary + 5 direct runner forgery
  regressions; Windows command shim check; fresh 536 canonical tests (1 skip),
  Pytest 535 passed (1 skip, 44 subtests), coverage 75%, touched Ruff, critical
  Mypy, Bandit High=0, pip-audit=0, Playwright 1/1, source/portable/installed,
  healthy Doctor and official validators. Final release ledger 10/10 checks
  carries `pala-quality-runner`, actual exit, output digests and basis; canonical
  acceptance mapped 10 refs and M60-T1 became TaskContract `DONE` / WorkflowStore
  `completed`. Exact 205-entry ZIP SHA-256 is
  `3424FB0AAE6EEFBEBE937A6EB0D065705844E846737C15A4C3301E518DDE5D54`.
- **Related files:** `scripts/pala_product_cli.py`, `scripts/pala_quality.py`,
  `scripts/pala_quality_policy.py`, `scripts/pala_quality_runner.py`,
  `scripts/pala_store.py`, `scripts/test_pala_product_wiring.py`,
  `scripts/test_pala_quality.py`, `scripts/pala_product_e2e.py`.
- **Date:** 2026-08-11
- **Status:** fixed (`passed`; caller-forged completion authority removed)

### INC-20260811-m60-artifact-production-wiring
- **Symptoms:** Independent artifact audit reopened M60 because the Pala 1.0
  product modules were exercised only through direct contract construction;
  ProductSpec was not durable, the production report did not consume the owner
  cockpit projection, the browser result could be represented synthetically,
  product/plugin identity drifted, and the final evidence manifest contained
  summary labels without the required command/exit/count details.
- **Root cause:** M51-M60 proved each contract in isolation but did not add one
  public production entry path that composes the existing planner, canonical
  TaskContract/WorkflowStore/Quality authorities, persistent project contract,
  report projection, real Playwright evidence, identity contract, and release
  manifest generator. The contract-level golden suite was therefore mistaken
  for product-level E2E evidence.
- **Fix criteria:** A public production facade drives the natural-language
  fixture through durable ProductSpec, canonical task claim/evidence/completion,
  TaskPacket/provider candidate and owner cockpit; report renders that durable
  projection; real Playwright evidence is mapped by the Quality Engine; current
  identity and portable links are mechanically consistent; a complete manifest
  is generated only from fresh command results; all M60 closure gates pass.
- **Proved by:** `passed` -- the first wiring contract failed because the public
  link validator did not exist; the first full 524-test run then exposed four
  identity/install fixture mismatches. Minimal fixes were followed by 4/4
  production-wiring tests, 34 product tests, 524 canonical tests (1 skip), 523
  pytest tests (1 skip, 44 subtests), coverage 75%, real Chromium 1/1, source
  and installed verify, healthy Doctor, official plugin/skill validators and
  the final Quality/TaskContract closure evidence.
- **Related files:** `scripts/pala_product_cli.py`, `scripts/pala_product.py`,
  `scripts/pala_authority.py`, `scripts/pala_report.py`,
  `scripts/pala_owner_cockpit.py`, `scripts/pala_product_e2e.py`,
  `scripts/build_portable.py`, `scripts/test_pala_product.py`,
  `tests/product-journey.spec.js`, `AGENTS.md`, `PROJECT.md`, `GOAL.md`,
  `.codex-plugin/plugin.json`, `artifacts/final/pala-1.0-evidence-manifest.json`.
- **Date:** 2026-08-11
- **Status:** fixed (`passed`; fresh production wiring and artifact closure)

### INC-20260810-complete-legacy-active-state
- **Symptoms:** v3 ticket başarıyla tamamlanmış olsa da aynı ticket'ın clean
  legacy v2 workflow kaydı `active_ticket` ve `goal` alanlarını koruyordu. Yeni
  session/cold packet bunu aktif geliştirme işi gibi sunabiliyordu.
- **Root cause:** `complete` yalnız v3 `WorkflowStore` yaşam döngüsünü
  sonlandırıyor; güvenli eşleşme olduğunda v2 workflow uzlaştırması yapmıyordu.
- **Fix criteria:** Complete yalnız aynı ticket ve clean legacy state için active
  alanlarını temizler; next_action/evidence korunur; farklı, dirty veya owner
  uyuşmazlığı değişmeden kalır; post-complete context `active=none` olur.
- **Proved by:** `passed` — state matrix, P0 smoke, 109-test dar paket, full
  unittest discovery, source verify ve self-audit.
- **Related files:** `scripts/pala_state_core.py`, `scripts/pala_state_cli.py`,
  `scripts/pala_p0_smoke.py`, `scripts/test_pala_tools.py`, `DEBUGGING.md`.
- **Date:** 2026-08-10
- **Status:** fixed

### INC-20260810-real-legacy-rejected
- **Symptoms:** Gerçek GitHub `v0.8.0` release klasörü yönetim state'i olmadan
  `0.8.2` adayıyla yükseltilince `external_conflict` döndü; aynı gerçek paket
  yönetilen state ile `updated` oldu. Sentetik legacy testi güncel required
  helper'ları içerdiği için boşluğu göstermedi.
- **Root cause:** `plugin_status()` state olmayan legacy ağacını, aday sürümün
  bugünkü `REQUIRED_FILES` listesiyle `validate_bundle()` üzerinden kabul
  ediyordu. Tarihsel resmi paketlerin gelecekte eklenen runtime sibling'larını
  taşıması mümkün değildir; kimlik doğrulama ile güncel bundle completeness
  kontrolü yanlışlıkla aynı kapıya bağlanmıştı.
- **Fix criteria:** State olmayan gerçek-eski biçim resmi name/repository/author
  ve sürüm manifestiyle legacy kabul edilir; foreign manifest hâlâ
  `external_conflict`; gerçek `0.8.0 legacy -> 0.8.2` matrix satırı `passed`.
- **Proved by:** `passed` — gerçek GitHub `v0.8.0`/`v0.8.1` SHA-pinned
  matrix; real-shape legacy ve unattested-foreign dar sözleşme testleri;
  `427` testli final release kapısı ve gerçek local `0.8.2` Update + Doctor.
- **Related files:** `scripts/pala_installer_core.py`,
  `scripts/test_pala_installer.py`, `scripts/pala_upgrade_matrix.py`,
  `artifacts/upgrade-compat/m45-real-release-matrix.json`, `DEBUGGING.md`.
- **Date:** 2026-08-10
- **Attempts:** Release full-suite, eski sentetik legacy fixture'ının resmi
  repository/author attestasyonu taşımadığını gösterdi; gerçek ürün davranışı
  gevşetilmeden fixture güven sözleşmesine uyarlandı.
- **Status:** fixed

### INC-20260810-installed-cli-context-stale
- **Symptoms:** Portable ZIP runtime self-audit geçtiği hâlde gerçek Windows
  Update yolu `pala_installer.py` içinde `argparse` eksikliğiyle, installed
  `instructions` çağrısı `pala_state_documents.py` içinde `tomllib` eksikliğiyle
  çöktü; yeni Codex oturumu ayrıca tamamlanmış M43 yerine eski M43-T5 v2 kaydını
  güncel iş gibi gösterdi.
- **Root cause:** Facade modül ayrımında CLI'ların doğrudan kullandığı iki standart
  kitaplık importu yeni sahip modüllere taşınmadı. Session-key T8 checkpoint'i
  v3 kaydını kapattı ancak farklı ticket'taki tarihsel v2 M43-T5 kaydını haklı
  olarak değiştirmedi; yeni workflow başlangıcı yapılmadan session'sız context
  bu v2 kayda geri düştü.
- **Fix criteria:** İki CLI installed paketten exit 0; dar sözleşme testleri
  eksik importları yakalar; M44 workflow başlangıcından sonra session'sız context
  M44-T1'i gösterir; source/portable/installed kapıları geçer.
- **Proved by:** `passed` — iki dar sözleşme testi; `419` tam unittest (`1`
  skip); `pala_code_audit.py --root .`; `verify.py --mode source`; yeni portable
  clean extract; gerçek local Update + Doctor; installed verify; session'sız
  context M44-T1.
- **Related files:** `scripts/pala_installer.py`,
  `scripts/pala_state_documents.py`, `scripts/test_pala_installer.py`,
  `scripts/test_pala_tools.py`, `.codex/pala-workflow.json`, `DEBUGGING.md`.
- **Date:** 2026-08-10
- **Status:** fixed

### INC-20260810-session-checkpoint-v2-drift
- **Symptoms:** `checkpoint --session-key` cleanly checkpointed its v3 ticket
  record, but left `.codex/pala-workflow.json` dirty. The next `begin` was
  therefore refused despite a completed ticket.
- **Root cause:** The session-key branch in `pala_state.main` returned after
  `WorkflowStore.checkpoint()` and bypassed `checkpoint_work()`, which owns the
  v2 workflow lifecycle record.
- **Fix criteria:** A session checkpoint updates both v3 ownership and v2
  workflow state; after a clean completed ticket, the next `begin` succeeds
  without a second manual checkpoint. CLI/public output remains fail-closed.
- **Proved by:** `passed` — session/v2 lifecycle contract; 410 test (1 skipped)
  and source verify passed.
- **Related files:** `scripts/pala_state.py`, `scripts/pala_state_lifecycle.py`,
  `scripts/pala_state_cli.py`, `scripts/test_pala_tools.py`, `DEBUGGING.md`.
- **Date:** 2026-08-10
- **Status:** fixed (`passed` — session checkpoint updates v2 + v3)

### INC-20260808-stub-brain
- **Symptoms:** Root `DEBUGGING.md` was only a one-line stub; agents had no
  durable place for root cause + fix criteria after failures.
- **Root cause:** Memory contract listed DEBUGGING in read order, but format
  and fail-closed checks were never enforced.
- **Fix criteria:** `## Format` + required field labels parse; empty Incidents
  allowed; each `### INC-*` has all seven fields; self-audit `debugging_brain`
  fails closed.
- **Proved by:** `py -3 -m unittest scripts.test_pala_debugging -v`
- **Related files:** `DEBUGGING.md`, `scripts/pala_memory.py`,
  `scripts/pala_self_audit.py`, `scripts/test_pala_debugging.py`, `AGENTS.md`
- **Date:** 2026-08-08
- **Status:** fixed (`passed` — `test_pala_debugging` + self-audit `debugging_brain`)

### INC-20260808-soft-done
- **Symptoms:** Soft “bitti/done/ok” treated as completion without gate labels.
- **Root cause:** Evidence policy not consulted; chat tone over STATUS labels.
- **Fix criteria:** Use `passed|not-run|blocked|configured-not-verified` only;
  refuse soft words alone at checkpoint.
- **Proved by:** Pala evidence policy + `AGENTS.md` quality rules
- **Related files:** `AGENTS.md`, `docs/PALA_0_5_MEMORY_CONTRACT.md`,
  `scripts/pala_self_audit.py`
- **Date:** 2026-08-08
- **Status:** fixed (`passed` policy; ongoing enforcement)

### INC-20260808-stab001-gate
- **Symptoms:** STAB-001 needed a fresh local confidence gate after M21 pack.
- **Root cause:** Working tree uncommitted; historical M21 SHA not sufficient
  proof for post-brain changes.
- **Fix criteria:** Narrow unittest green, then full `verify.py` with new SHA.
- **Proved by:** `py -3 -m unittest …` (118 ok narrow) then
  `py -3 scripts/verify.py` → 227 tests + self-audit;
  ZIP SHA-256 `6044C2226439147476553B318473D15FFF3F2F9116FB53A3D4D634E96E4A6E8A`
- **Related files:** `scripts/verify.py`, `DEBUGGING.md`, `STATUS.md`
- **Date:** 2026-08-08
- **Status:** fixed (`passed` full local gate)

### INC-20260808-readme-fake-080
- **Symptoms:** README green badge + download linked `v0.8.0` while GitHub
  latest release was still `v0.7.1` (404 risk; STATUS said `not-run`).
- **Root cause:** Manifest bumped to 0.8.0 and UX contract required matching
  README release URLs without a publish-pending branch.
- **Fix criteria:** While STATUS marks `v0.8.0` release `not-run`, README must
  not use green published badge; point download at `v0.7.1`; contract test
  follows STATUS.
- **Proved by:** `py -3 scripts/verify.py` → 230 tests + self-audit;
  ZIP SHA-256 `CC8D1A33A00F1C4444FFC98AD2CF57EB509619E3A6854EE41B3293DB67EA3297`
- **Related files:** `README.md`, `STATUS.md`,
  `scripts/test_plugin_experience.py`, `docs/RELEASE_0_8_0_CHECKLIST.md`
- **Date:** 2026-08-08
- **Status:** fixed (`passed`)

### INC-20260808-skill-budget-m24
- **Symptoms:** M24 skill edit dropped exact phrase
  `Do not re-plan completed scope` and pushed word count to 451 (>450).
- **Root cause:** Task-card wording replaced the contract phrase instead of
  extending it; no pre-edit word-budget check.
- **Fix criteria:** Phrase restored; `SKILL.md` ≤450 words; both contract
  tests green inside full `verify.py`.
- **Proved by:** `py -3 scripts/verify.py` → 234 tests + self-audit;
  ZIP SHA-256 `F626B3EBDE7CF71D9A752B3CECC6B2B8019418596C83FBD976AEC7F7CF6CDC6E`
- **Related files:** `skills/pala-project-finisher/SKILL.md`,
  `scripts/test_pala_tools.py`, `scripts/test_plugin_experience.py`
- **Date:** 2026-08-08
- **Status:** fixed (`passed`)

### INC-20260808-script-path-cwd
- **Symptoms:** Live A/B / “pala kontrol et” agents ran skill-relative
  `../../scripts/pala_report.py` from the user project cwd → script not found;
  begin without `--goal` English argparse noise; complete failed with opaque
  `ticket record not found` after begin without v3 ticket row.
- **Root cause:** Skill instructed skill-tree-relative script paths; begin
  without `--session-key` wrote only v2 workflow JSON; complete always needs
  v3 ticket + session.
- **Fix criteria:** Skill/refs never instruct `../../scripts/` from project
  cwd; document marketplace `%LOCALAPPDATA%\Pala\marketplace\scripts` + repo
  `scripts/` + `PALA_SCRIPTS_DIR`; `resolve_pala_scripts_dir`; Turkish
  `--goal` error; begin always claims v3 ticket (`pala-local` default);
  complete prints actionable recovery (begin/register/session); no soft-pass.
- **Proved by:** `py -3 -m unittest scripts.test_pala_p0_friction
  scripts.test_pala_cmd_memory -v` → 18 ok; `py -3 scripts/pala_p0_smoke.py`
  → `artifacts/codex-compat/p0-smoke.json` overall `passed` (9 rows); full
  `verify.py` `not-run`.
- **Related files:** `skills/pala-project-finisher/SKILL.md`,
  `skills/pala-project-finisher/references/code-intelligence.md`,
  `scripts/pala_paths.py`, `scripts/pala_state.py`, `scripts/pala_cmd_memory.py`,
  `scripts/pala_p0_smoke.py`, `scripts/test_pala_p0_friction.py`,
  `scripts/test_plugin_experience.py`
- **Date:** 2026-08-08
- **Status:** fixed (`passed` focused + Gate0 smoke; full gate `not-run`;
  live marketplace A/B re-measure `not-run`)

### INC-20260809-quality-unittest-zero-discovery
- **Symptoms:** M33-T1 quality planı `py -3 -m unittest discover` önerdi;
  Pala kaynak kökünde komut exit 0 ile **0 test** çalıştırdı.
- **Root cause:** Python test varlığı bulunuyordu, fakat discovery komutu
  `scripts/test_*.py` gibi package olmayan test kökünü hedeflemiyordu.
- **Fix criteria:** `scripts/` altındaki Python testleri için plan açık
  `-s scripts -p test_*.py` kullanır; belirsiz kök `passed`a çevrilemez;
  sözleşme testi bunu sabitler.
- **Proved by:** `py -3 -m unittest scripts.test_pala_quality -v`; ardından
  gerçek plan komutu ve `py -3 scripts/verify.py --mode source`.
- **Related files:** `scripts/pala_quality.py`, `scripts/test_pala_quality.py`,
  `DEBUGGING.md`, `STATUS.md`, `PLAN.md`.
- **Date:** 2026-08-09
- **Status:** fixed (`passed` — explicit discovery + fresh source verification)

### INC-20260809-expert-worker-masks-core-install
- **Symptoms:** `Repair` çekirdeği güncelledikten sonra isteğe bağlı uzman
  worker `failed` olduğu için süreç exit 1 döndü; kurulu paket audit'i ise
  `passed` ve Doctor çekirdeği `healthy=True` gösterdi.
- **Root cause:** PowerShell installer uzman worker exit code'unu koşulsuz
  kendi exit code'u yaptı; varsayılan Repair ayrıca ağdan uzman kurulumunu
  tetikliyordu.
- **Fix criteria:** Uzman indirme yalnız açık opt-in ile başlar; uzman sonucu
  çekirdek sonucu değildir; başarısız uzmandan sonra model başlatılmaz; gerçek
  core Repair exit 0 ve runtime audit `passed` olur.
- **Proved by:** `powershell -NoProfile -ExecutionPolicy Bypass -File
  .\Install-Pala.ps1 -Mode Repair` → exit 0, `healthy=True`, `plugin=ready`,
  `experts_ready=False` / prerequisites `True`; expert contract tests → 16 OK.
- **Related files:** `Install-Pala.ps1`, `scripts/Install-Pala.ps1`,
  `scripts/test_pala_expert_installer.py`, `STATUS.md`, `PLAN.md`.
- **Date:** 2026-08-09
- **Status:** fixed (`passed` — explicit opt-in, nonfatal worker result)

### INC-20260810-checkpoint-transition-quality-drift
- **Symptoms:** A checkpoint whose `next_action` and STATUS both correctly
  named the next ticket appended a false `Memory mismatch` block. The resulting
  STATUS write changed the Delivery Quality Engine surface and blocked the
  ticket's otherwise fresh ledger.
- **Root cause:** `checkpoint_work` compared the current active ticket directly
  with its intended successor, instead of recognising a matching
  current→next transition as a normal lifecycle boundary. Delivery Quality
  discovery also treated the mutable Pala memory documents as delivery source.
- **Fix criteria:** Contract tests prove that matching checkpoint and STATUS
  successor ticket IDs do not set `needs_reconcile` or mutate STATUS, a
  genuinely different successor remains a mismatch, and the four memory
  documents are excluded from the delivery surface.
- **Proved by:** `passed` — focused state and discovery contract tests.
- **Related files:** `scripts/pala_memory.py`, `scripts/pala_state.py`,
  `scripts/pala_quality_discovery.py`, `scripts/test_pala_tools.py`,
  `scripts/test_pala_quality.py`, `STATUS.md`, `PLAN.md`.
- **Date:** 2026-08-10
- **Status:** fixed (`passed` — focused contracts)

### INC-20260811-r6-safe-runtime-smoke
- **Symptoms:** Pala's external runtime root and all local regressions pass, but
  a restricted Codex write smoke cannot create a disposable file below that root.
- **Root cause:** Codex CLI 0.146.1 rejected the legacy `workspace-write +
  --add-dir + approval=never` route before command execution. The initial custom
  profile also used obsolete `file_system.entries` syntax. Codex CLI 0.147.0
  accepts the current direct map form
  `[permissions.r6smoke.filesystem] "<absolute-runtime-path>" = "write"` and
  applies it to the Windows sandbox token.
- **Fix criteria:** One invocation-local restricted Codex profile writes under
  the declared Pala runtime root while `.git/.codex` remain denied; no global
  config edit, `--yolo`, or sandbox bypass.
- **Proved by:** `passed` local regression/integration evidence (18 + 188 tests);
  fresh Codex CLI 0.147.0 smoke writes the runtime marker and rejects `.git` and
  `.codex` markers with `UnauthorizedAccess`.
- **Related files:** `scripts/pala_authority.py`,
  `scripts/test_pala_runtime_authority.py`,
  `docs/plans/active/PALA-0.9.0-R6-runtime-integration.md`.
- **Date:** 2026-08-11
- **Status:** fixed (`passed`; invocation-local safe runtime authority verified)

### INC-20260811-github-readonly-prefix-escape
- **Symptoms:** The GitHub read-only prefix allowlist accepted `gh api`
  method/body arguments and Git branch deletion arguments although those shapes
  can request remote or local mutation.
- **Root cause:** Authorization matched only a safe-looking command prefix, not
  the complete argv shape.
- **Fix criteria:** The snapshot's plain `gh api <endpoint>` and Git remote
  read remain allowed; HTTP method/body flags and Git delete/remote-mutation
  forms are refused.
- **Proved by:** `passed` — 4 focused GitHub read-only tests and 141 affected
  integration tests, both exit 0; `git diff --check` passed.
- **Related files:** `scripts/pala_github.py`,
  `scripts/test_pala_github_readonly.py`,
  `scripts/test_code_intelligence.py`.
- **Date:** 2026-08-11
- **Status:** fixed

### INC-20260811-checkpoint-projection-write
- **Symptoms:** A session checkpoint for a v3-only task failed with
  `workflow state not found` after the active-task fallback supplied context.
- **Root cause:** The checkpoint CLI treated the fallback returned by
  `load_workflow` as a real dirty legacy workflow and then attempted a legacy
  workflow write.
- **Fix criteria:** Only an on-disk generated or legacy workflow can enter the
  legacy checkpoint branch; a v3 fallback checkpoint releases only its ticket
  lease and remains recoverable.
- **Proved by:** `passed` — 4 focused P0 lifecycle tests, including a
  quality-backed begin → checkpoint → recover → complete path.
- **Related files:** `scripts/pala_state_cli.py`,
  `scripts/test_pala_p0_friction.py`,
  `scripts/pala_state_core.py`.
- **Date:** 2026-08-11
- **Status:** fixed

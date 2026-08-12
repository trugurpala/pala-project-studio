# PALA 0.9.0 R6 — Safe Runtime Authority Integration

## Purpose

R5'te mevcut TaskContract, WorkflowStore, repository authority, Delivery Quality
Engine, dependency, scope, handoff, knowledge ve GitHub read-only parçalarını tek
production authority zincirine bağla. Pala single-host ve local-first kalır.

## Artifact profile

- Profile: `SOURCE` (`passed`: Git checkout + tracked source contract).
- Branch: `codex/r6-safe-runtime-authority`.
- R5 baseline: `docs/plans/active/M49-hardening.md`; değiştirilmez.
- Remote writes, commit, push, PR, merge, tag, release ve deploy: `not-run`.

## Current authority map

```text
pala_state CLI -> pala_state_cli -> pala_state_core -> WorkflowStore
                                               \-> optional Quality gate

TaskContract / dependency / scope / handoff / knowledge
  -> tests and isolated helpers only; not production completion authority

report / cold packet -> .codex/pala-workflow.json + STATUS.md projections
```

## Codex host findings

- Current desktop execution profile is broader than `workspace-write`; it is not
  accepted as proof of safe sandbox compatibility.
- Current canonical ticket path resolves below `<git-common-dir>/pala/...` and
  Quality/report/workflow paths resolve below `.codex`; both are protected-path
  risks to remove in M0.
- Windows Pala already owns `%LOCALAPPDATA%\Pala`; R6 runtime target is
  `%LOCALAPPDATA%\Pala\runtime\repositories\<repository-instance-id>`.
- No user-global Codex config is edited. Restricted validation uses an
  invocation-local permission profile with a direct external-runtime write rule.

## Invariants

1. TaskContract owns task semantics and completion eligibility.
2. WorkflowStore owns atomic persistence, locks, leases and compatibility reads.
3. Existing Pala Quality Engine is the only verification/evidence authority.
4. DONE requires structured acceptance, mapped current Quality evidence, no
   blocker and a valid lease.
5. Legacy `record-verification` never fabricates authoritative evidence.
6. Migration never invents acceptance, deletes source data or overwrites a
   conflict.
7. STATUS, handoff and cold packet are generated projections.
8. GitHub remains observational/read-only; Pala remains single-host.

## Progress

- [x] Discovery and A–F root-cause reproductions recorded in the approved plan.
- [x] Goal created and `R6-M0` claimed for this execution session.
- [x] M0 — Safe mutable runtime root (`passed`: restricted write smoke verified).
- [x] M1 — WorkflowStore ↔ TaskContract authority bridge (`passed`).
- [x] M2 — TaskContract ↔ Quality Engine bridge (`passed`).
- [x] M3 — Fail-closed legacy migration (`passed`).
- [x] M4 — Dependency / scope / retry / recovery (`passed`).
- [x] M5 — Handoff / knowledge / generated projections (`passed`).
- [x] M6 — AGENTS / skill alignment (`passed`).
- [x] M7 — GitHub read-only regression hardening (`passed`).
- [x] M8 — Release / knowledge hygiene (`passed`).

## Surprises & discoveries

- The checkout contains the complete uncommitted R5 candidate on `main`; a new
  worktree from HEAD would omit it. Work continues on a new branch in the same
  working tree so user changes remain intact.
- Existing `.codex/plugin-data/pala/v3` contains ticket and Quality history while
  `.git/pala` was initially absent; migration must preserve both authorities and
  fail closed on divergent duplicates.
- Runtime migration now enumerates every real worktree before writing its marker;
  otherwise a secondary worktree could finalize migration before seeing the
  primary worktree's legacy `.codex` state.
- The real local migration completed without deleting legacy sources and created
  `%LOCALAPPDATA%\Pala\runtime\repositories\be7238b248d03782a62a12d8`.
- Codex CLI 0.147.0 accepts the supported direct filesystem-map profile form:
  `permissions.<profile>.filesystem."<absolute-path>" = "write"`. This grants
  only the Pala runtime root; it does not make `.git` or `.codex` writable.

## Decision log

- 2026-08-11: Use existing `pala_authority.py` as the single path owner; do not
  introduce a parallel runtime/evidence subsystem.
- 2026-08-11: Runtime repository identity is the branch-independent SHA-256
  digest of the resolved Git common-dir path, preserving worktree sharing.
- 2026-08-11: M0 must be green before M1 starts; a broad current sandbox cannot
  substitute for restricted-host evidence.
- 2026-08-11: Do not edit user-global Codex config or weaken approval/sandbox to
  force the smoke. Codex CLI 0.147.0 supplied the required invocation-local
  direct filesystem-map support.

## M0 mutable path inventory

| Class | R6 path / owner | State |
| --- | --- | --- |
| `STATIC_CONFIG` | tracked repository/plugin files | unchanged |
| `CANONICAL_MUTABLE_STATE` | `<runtime>/tasks` | focused tests `passed` |
| lease/lock | `<runtime>/leases` | focused tests `passed` |
| `QUALITY_EVIDENCE` | `<runtime>/quality`, existing Quality Engine | focused/integration `passed` |
| `EVENT/AUDIT` | `<runtime>/events/pala.sqlite`, existing DB engine | focused tests `passed` |
| `GENERATED_READ_MODEL` | `<runtime>/generated` | focused/integration `passed` |
| `CACHE` | `<runtime>/cache` | layout test `passed` |
| `LEGACY_COMPATIBILITY` | `.git/pala`, `.codex/plugin-data`, `.codex/pala-workflow.json` | read/copy only; preserved |

## M0 verification record

- Failing regressions observed before each path/migration implementation.
- Focused: `py -3 -m unittest scripts.test_pala_runtime_authority -v` —
  `passed`, 18 tests, exit 0.
- Affected integration: state/plugin/Quality/report/cold-packet command —
  `passed`, 188 tests, exit 0.
- Diff review: `git diff --check` — `passed`, exit 0; unrelated R5 user changes
  remain preserved.
- Restricted host smoke: Codex CLI `0.147.0`, invocation-local `r6smoke`
  profile extending `:workspace` with
  `filesystem."C:/Users/.../Pala/runtime/repositories/be7238b248d03782a62a12d8" = "write"`
  — runtime `Set-Content` `passed`; disposable writes in `.git` and `.codex`
  both returned `UnauthorizedAccess` (`passed`). No `--add-dir`, sandbox bypass,
  or global config edit was used.
- M0 outcome: `passed`; M1 is the only next milestone and remains `not-run`.

## Remaining

All R6 milestones are complete locally. Remote release and deployment actions
remain `not-run` and require separate owner authority.
Preserve the M0 invocation-local profile shape; do not relocate state into
protected Git/Codex metadata or weaken the sandbox.

## Milestones

### M0 — Safe mutable runtime root

Files: `scripts/pala_authority.py`, `scripts/pala_store.py`,
`scripts/pala_quality.py`, `scripts/pala_state_core.py`,
`scripts/pala_report.py`, `scripts/pala_cold_packet.py`, focused tests.

Acceptance: task, lease, Quality, events, generated and cache paths resolve
outside `.git/.codex`; two worktrees share authority; detached HEAD works;
legacy data is copied atomically/idempotently and never deleted; second owner
cannot claim; restricted Codex write smoke is demonstrated.

### M1 — WorkflowStore ↔ TaskContract authority bridge

Acceptance: production state flow loads/persists TaskContract semantics and
missing acceptance or arbitrary legacy pass cannot produce DONE.

Outcome: `passed` — `begin --acceptance` persists explicit `not-run`
TaskContract acceptance items; WorkflowStore loads them for verification and
completion. A legacy/single passed record without mapped structured acceptance
remains `verification_required`; checkpoint releases both outer and nested
TaskContract lease ownership. Focused + affected integration: 196 tests, exit 0;
`git diff --check`: `passed`.

### M2 — TaskContract ↔ Quality Engine bridge

Acceptance: acceptance maps to required Quality check IDs; every required check
has actual exit code 0 and current surface/basis; partial evidence cannot verify.

Outcome: `passed` — WorkflowStore maps only a green existing Quality Engine
ledger into explicit `quality_check_ids`. Every mapped check must be required,
`passed`, and have exit code `0`; unmapped/partial/non-green ledger evidence is
refused. `complete --quality-ticket` invokes this mapping before completion.
Focused + affected integration: 196 tests, exit 0; `git diff --check`: `passed`.

### M3 — Fail-closed legacy migration

Acceptance: legacy completed without structured acceptance becomes existing
`NEEDS_DECISION`/typed conflict representation; source is recoverable and repeat
migration is a no-op.

Outcome: `passed` — legacy `completed`/`done` task payloads without structured
acceptance are copied (without source mutation) as `needs_decision` with typed
`legacy-completed-without-structured-acceptance` conflict and an equivalent
TaskContract state. Repeat migration uses the existing marker and is a no-op.
Focused: 19 tests; affected integration: 197 tests; diff review: `passed`.

### M4 — Dependency / scope / retry / recovery

Acceptance: missing/unfinished/cyclic dependency, scope violation, repeated
failure budget, stale lease and dirty/orphan recovery all fail closed.

Outcome: `passed` — completion reads canonical TaskContract dependency DAG state
and refuses missing, cyclic, or unfinished dependencies. Recorded changed files
are checked against contract write/deny scope before DONE. Existing repeated
verification budget and dirty/orphan lease recovery guards remain fail-closed.
Focused: 88 tests; affected integration: 199 tests; diff review: `passed`.

### M5 — Handoff / knowledge / generated projections

Acceptance: handoff, cold packet and Status derive from canonical task; completed
tasks do not re-enter active context; a fresh session resumes without transcript.

Outcome: `passed` — handoff reads the single canonical active TaskContract when
no task is supplied. Cold packet and state-core workflow consumers use a
read-only canonical fallback when no projection file exists; ambiguous multiple
active tasks remain fail-closed. Completed TaskContract state is not selected as
active. Focused: 27 tests; affected integration: 202 tests; diff review:
`passed`.

### M6 — AGENTS / skill alignment

Acceptance: agent instructions describe canonical report/task → claim → Quality
→ acceptance → DONE flow and do not require manual generated STATUS authority.

Outcome: `passed` — AGENTS and the thin Pala skill name the single
TaskContract/WorkflowStore/Quality Engine authority chain, report/context →
claim → acceptance → DONE order, and generated projections as read models only.
Focused: 36 tests; affected integration: 203 tests; diff review: `passed`.

### M7 — GitHub read-only regression hardening

Acceptance: connector → gh → redacted git fallback remains read-only; `gh api`
write method/body flags and Git/gh mutations are rejected by contract tests.

Outcome: `passed` — authorization now matches complete argv shapes: the
snapshot's plain API endpoints and remote read remain allowed, while `gh api`
method/body flags, Git branch deletion, remote mutation, and ordinary GitHub
write commands are refused. Focused: 4 tests; affected integration: 141 tests;
diff review: `passed`.

### M8 — Release / knowledge hygiene

Acceptance: 0.9.0 R6 local candidate identity is consistent; historical release
claims remain historical; source/portable/installed/knowledge gates run for their
own profiles. No remote or release mutation occurs.

Outcome: `passed` — manifest, README, and current STATUS name the `0.9.0`
local candidate while published `v0.8.1` remains historical. Source full gate:
485 tests (1 controlled skip) and reproducible ZIP SHA-256
`D048B6ED3E4453CF212037E9F514D1DA3D6FE146FED98B5EBC9CDFBD93FB8573`;
portable clean-extract and installed-profile gates passed. No remote mutation.
System plugin and skill validators also passed with machine-local PyYAML.
Post-R6 local packaging additionally passed source, portable, installed-profile,
plugin, and skill validation without remote publication.

## M47 — Quality Hardening

**Durum:** passed (2026-08-11) — local quality hardening completed; detailed
evidence and deferred baseline debt are recorded below.

**Amaç:** Mevcut Python stdlib + `unittest` + installer/portable mimarisini
framework veya production-tool migration'a çevirmeden, kritik çekirdeğin
ölçülebilir kalite ve doğrulanabilirliğini artırmak.

**Değişmez sınırlar:**

- Pydantic ve Loguru production dependency olarak eklenmez. Gerçek bir external
  validation boundary veya stdlib logging yetersizliği kanıtlanırsa ayrı
  `NEEDS_DECISION` açılır.
- Mevcut `unittest` suite korunur; Pytest ancak runner/fixture avantajı mevcut
  suite'i bozmadan kanıtlanırsa eklenir.
- `uv` yalnız proje-yerel dev environment/lock için değerlendirilir; global
  user config, installer veya portable bundle değiştirilmez.
- Hook'lar test, build, network veya GitHub mutasyonu başlatmaz.
- Ruff/Mypy uyarısı otomatik olarak gerçek issue kabul edilmez; her bulgu kod
  bağlamı ve dar kanıtla triage edilir.
- Commit, push, PR, merge, tag, release ve deploy bu milestone'ın dışındadır.

### M47-T1 — Ruff baseline ve güvenli kapsam

- **Sahip ajan:** Codex agent
- **Amaç:** Ruff'ı yalnız geliştirici kalite aracı olarak keşfetmek, mevcut
  source/portable sözleşmesini bozmadan baseline ve kural kapsamını belirlemek.
- **Dosyalar:** `pyproject.toml` veya yalnız Ruff'a ait minimal config (seçim
  baseline sonrasında), `scripts/`, kalite dokümanı ve ilgili test kanıtı.
- **Bitti sayılır:** Önce mevcut baseline/failing çıktısı alınır; gerçek
  issue'lar triage edilir; otomatik toplu fix uygulanmaz; yeni/değişen yüzey
  için ratchet kararı ve komut kanıtı kaydedilir.
- **Bağımlılık:** none
- **Kanıt:** `ruff check`/`ruff format --check` yalnız açık yetkiyle çalıştırılır;
  henüz `not-run`.

### M47-T2 — Coverage.py baseline

- **Sahip ajan:** Codex agent
- **Amaç:** Mevcut `unittest` discovery'yi koruyarak kritik çekirdek için
  ölçülebilir coverage baseline oluşturmak.
- **Dosyalar:** coverage config (gerekirse), kalite dokümanı, test komutları.
- **Bitti sayılır:** Coverage aracı proje-yerel çalışır; generated/portable
  dosyalar dışlanır; oran yalnız aynı komut ve aynı yüzey karşılaştırmasıyla
  raporlanır; hedef eşik baseline görülmeden icat edilmez.
- **Bağımlılık:** M47-T1 baseline kararı
- **Kanıt:** Coverage komutu ve rapor yolu; henüz `not-run`.

### M47-T3 — Kritik çekirdek Mypy kademesi

- **Sahip ajan:** Codex agent
- **Amaç:** Strict typing'i tüm repository'ye yaymadan kritik authority ve
  evidence çekirdeğinde küçük, kanıtlanabilir bir kapsam başlatmak.
- **Dosyalar:** Mypy config (paketleme etkisi kanıtlanırsa), yalnız şu modüller
  ve testleri: `pala_task_contract`, `pala_store`, `pala_state_core`,
  `pala_state_cli`, `pala_authority`, `pala_quality`, `pala_quality_policy`,
  `pala_quality_discovery`, `pala_dependencies`, `pala_verification_basis`,
  `pala_handoff`, `pala_cold_packet*`, `pala_github`.
- **Bitti sayılır:** Önce baseline alınır; warning'ler bağlamla triage edilir;
  geçiş kademelidir; unittest davranışı değişmez; tüm-repo strict iddiası
  yapılmaz.
- **Bağımlılık:** M47-T1
- **Kanıt:** Kritik modül listesine sabitlenmiş Mypy komutu ve exit code; henüz
  `not-run`.

### M47-T4 — uv dev environment uyumluluğu

- **Sahip ajan:** Codex agent
- **Amaç:** Mevcut installer/portable yapısını değiştirmeden, proje-yerel
  geliştirme bağımlılıklarını tekrarlanabilir hale getirme seçeneğini doğrulamak.
- **Dosyalar:** yalnız gerekirse dev metadata/lock; `Install-Pala.ps1`,
  `scripts/build_portable.py` ve portable allowlist kapsamı gözden geçirilir.
- **Bitti sayılır:** `uv` zaten kurulu olduğu için yeniden global kurulum yapılmaz;
  lock/venv eklenmesinin runtime bundle'a sızmadığı kanıtlanır. Sızma veya
  installer/portable contract değişikliği çıkarsa `NEEDS_DECISION`.
- **Bağımlılık:** M47-T1, M47-T2
- **Kanıt:** izole dev environment dry-run ve portable dışlama kanıtı; henüz
  `not-run`.

### M47-T5 — Pytest uyumluluk kararı

- **Sahip ajan:** Codex agent
- **Amaç:** Pytest'i migration değil, mevcut unittest suite üzerinde ölçülen
  runner/fixture avantajı olarak değerlendirmek.
- **Dosyalar:** dev-only test config (gerekirse), mevcut `scripts/test_*.py`,
  kalite planı.
- **Bitti sayılır:** unittest discovery aynen geçerli kalır; Pytest yalnız
  aynı test yüzeyini doğru keşfedip çalıştırdığı ve anlamlı fixture avantajı
  gösterdiği takdirde ek kapı olur; aksi halde eklenmez.
- **Bağımlılık:** M47-T2, M47-T4
- **Kanıt:** iki runner'ın aynı hedef yüzeyde karşılaştırmalı exit-code kanıtı;
  henüz `not-run`.

### M47-T6 — Release security gate

- **Sahip ajan:** Codex agent
- **Amaç:** Bandit ve pip-audit'i yalnız release-tier, açıkça çalıştırılan
  security gate olarak değerlendirmek.
- **Dosyalar:** `.github/workflows/quality.yml` (yalnız onaylı CI değişikliği),
  kalite policy/ledger ve güvenlik dokümanı.
- **Bitti sayılır:** Bandit bulguları manuel triage edilir; pip-audit yalnız
  gerçek lockfile/bağımlılık yüzeyinde çalışır; network veya lockfile yoksa
  sonuç `configured-not-verified` kalır; hooks bunları çalıştırmaz.
- **Bağımlılık:** M47-T4, M47-T5
- **Kanıt:** release komutları, exit code, rapor yolları ve güncel yüzey özeti;
  henüz `not-run`.

### M47 doğrulama sırası

Her kart için aynı döngü zorunludur: **failing/baseline evidence → minimal
config veya değişiklik → dar doğrulama → ilgili ticket kapısı → milestone
sonunda full local verification**. Bu milestone'da hiçbir araç kurulumu veya
config değişikliği, mevcut packaging/installer/portable sözleşmesi etkisi
kanıtlanmadan uygulanmaz.

### M47 completion evidence (2026-08-11)

**Durum:** `passed` for the completed local hardening scope. No production
dependency, installer/portable contract change, global configuration mutation,
or remote Git operation was made.

- **T1 Ruff:** Python 3.10 baseline was 1,260 findings before line-length
  calibration and 716 legacy findings after it. A real Python 3.10 parse defect
  in `pala_view_sections.py` was fixed with a red-to-green regression test.
  The M47 changed-surface ratchet passes; the legacy repository-wide backlog is
  deliberately not represented as a clean gate.
- **T2 Coverage:** canonical `unittest` discovery passed 488 tests (one
  controlled skip). The measured scripts baseline is 75%, and the Quality
  Engine uses that measured floor rather than an invented target.
- **T3 Mypy:** the critical-core exploratory baseline found 102 errors in
  eight files, chiefly dynamic boundary ambiguity. Strict Mypy is enabled only
  for six clean authority/evidence modules and passes there; no broad `Any`,
  cast, or architecture rewrite was used.
- **T4 uv:** `pyproject.toml`, `uv.lock`, and project-local `.venv` provide
  reproducible dev tooling. Knowledge and artifact scanners explicitly ignore
  local dev/runtime cache directories; source, portable, and installed checks
  proved they do not enter the deliverable.
- **T5 Pytest:** compatibility run passed (487 tests, one skip, 44 subtests).
  It remains an optional developer runner; `unittest` is the canonical gate.
- **T6 security:** Bandit reported no High findings; 13 Medium and 159 Low
  findings were manually triaged as bounded/known contexts. `pip-audit --path
  .venv` found no known vulnerabilities. `pip-audit --locked` does not support
  `uv.lock`, so it is not claimed as a lockfile audit.

Fresh final evidence: source verify, portable clean extract, and a separately
expanded installed profile passed; plugin and skill validators passed through
an ephemeral PyYAML environment; `git diff --check` passed. Installer Doctor
is `configured-not-verified`: it correctly reports `plugin=drifted` because
the changed source was not globally repaired/reinstalled.

## Validation

Each milestone uses: failing regression → minimal implementation → focused test
→ diff review → affected integration tests → this ExecPlan update. M0 focused
command begins with `scripts.test_pala_runtime_authority`; final source gate is
`py -3 scripts/verify.py`. A gate is `passed` only with fresh exit-code evidence.

## Recovery / idempotence

- Legacy sources remain untouched until a verified destination and migration
  marker exist; they are not deleted by R6.
- Same source/destination digest is a no-op; divergent data records
  `NEEDS_DECISION` and stops.
- Locks and writes use atomic same-directory replacement; stale leases are
  orphaned, never stolen.

## Out of scope

New UI, provider, agent platform, SaaS, multi-host coordination, GitHub write,
dependency installation, user-global config mutation, security-boundary
weakening, commit/push/PR/merge/tag/release/deploy.

## Outcome

Pala 0.9.0 R6 has one local runtime authority chain whose mutable state works in
safe Codex permissions, whose DONE decision is backed only by the existing
Quality Engine, and whose legacy/history projections remain recoverable.

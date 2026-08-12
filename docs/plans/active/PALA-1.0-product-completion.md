# PALA 1.0 Product Completion ExecPlan

## Goal

PALA 1.0 is a **Provider-Independent Local Software Delivery OS**: a
local-first, single-host product that turns user intent into an explicit
ProductSpec, capability-backed architecture, acceptance/evidence-gated task
execution, authorized delivery, live verification, and an owner-readable
handoff. The existing R6 TaskContract, WorkflowStore, and Pala Quality Engine
remain the only task, persistence/lease, and completion-evidence authorities.

## Locked product definition

- Provider-independent does not mean adding provider runtimes in 1.0. M55
  defines the interface, CodexProvider, and FakeProvider only.
- ProductSpec and project lifecycle sit above TaskContract; they do not infer
  task DONE or create a second state/evidence engine.
- GitHub stays read-only. Real remote deploy and remote publish are out of
  scope and remain `not-run`.
- M47 tooling and ratchets remain in force. No Pydantic, Loguru, production
  dependency, SaaS, database, UI framework, or multi-host coordinator is added.

## Change control

Milestone order is locked: M50 -> M51 -> M52 -> M53 -> M54 -> M55 -> M56 ->
M57 -> M58 -> M59 -> M60. A required production dependency, foreign or
modified installed tree, destructive migration, global user configuration
edit, unsafe credential boundary, security weakening, major scope change,
multi-host design, real credentials, or real remote deployment produces
`NEEDS_DECISION`.

## M50 - Source / installed truth reconciliation

- **Ticket:** M50-T1
- **Progress:** passed
- **Acceptance:** fresh M47 gates recorded; source truth passed; installed
  ownership proved; Doctor passed or honestly configured-not-verified;
  installed verify passed; P0 blockers zero.
- **Write scope:** this ExecPlan, product goal, local evidence, Pala-owned
  installer repair only after ownership proof.
- **Deny scope:** foreign installed content, global Codex config, remote Git.
- **Surprises:** the quality ledger truncated changed-file names but compared
  them to an unbounded list; generated evidence artifacts also invalidated
  their own ledger; TaskContract quality mapping captured an incomplete Git
  basis and therefore could never complete in a real repository.
- **Decisions:** preserve the single Quality Engine, cap only the displayed
  path list while retaining the full digest, ignore generated artifacts, and
  capture the canonical full Git verification basis at evidence mapping.
- **Evidence:** `passed` — 490 unittest cases (1 controlled skip), 75% coverage,
  source/portable reproducibility, Ruff touched surface, strict critical Mypy,
  Bandit High=0, pip-audit no known vulnerabilities, P0 smoke 10/10, source
  self-audit, skill/plugin validators, Pala-owned Repair, Doctor healthy, and
  installed verification. TaskContract `M50-T1` is canonical `DONE`.
- **Remaining:** none.
- **Blockers:** none.

## M51 - Product contract + project lifecycle

- **Ticket:** M51-T1
- **Progress:** passed
- **Acceptance:** ProductSpec contains every locked field; project lifecycle
  transitions are explicit and tested; task lifecycle and DONE authority stay
  unchanged; project status is never guessed from task DONE.
- **Evidence:** `passed` — four focused contract/transition tests and touched
  Ruff; canonical ticket `M51-T1` is `DONE` through Quality evidence.
- **Remaining:** none.
- **Blockers:** none.

## M52 - Product planner

- **Ticket:** M52-T1
- **Progress:** passed
- **Acceptance:** host-AI planning output validates into ProductSpec,
  Acceptance Matrix, Environment Requirements, Milestone Graph, and Task DAG;
  golden water-tracker input preserves hosting facts and explicit unknowns;
  missing/cyclic dependencies fail closed through `pala_dependencies`.
- **Evidence:** `passed` — golden facts/unknowns plus missing/cyclic dependency
  negative tests; ten cumulative product tests; canonical `M52-T1` `DONE`.
- **Remaining:** none.
- **Blockers:** none.

## M53 - Environment capability + architecture

- **Ticket:** M53-T1
- **Progress:** passed
- **Acceptance:** CapabilityProfile and ArchitectureDecision contracts use only
  observed evidence; provider names never imply capabilities; required UNKNOWN
  capabilities produce discovery-required or needs-decision state.
- **Evidence:** `passed` — thirteen cumulative tests including evidence-shape,
  UNKNOWN discovery and verified-selection cases; `M53-T1` canonical `DONE`.
- **Remaining:** none.
- **Blockers:** none.

## M54 - Context compiler / TaskPacket

- **Ticket:** M54-T1
- **Progress:** passed
- **Acceptance:** existing TaskContract/cold-packet/knowledge/handoff sources
  compile a bounded provider-neutral TaskPacket in minimal, standard, and
  milestone profiles; completed work is excluded; ambiguity fails closed.
- **Evidence:** `passed` — minimal/standard/milestone budgets, DONE exclusion
  and conflicting read-model tests; sixteen cumulative tests; `M54-T1` `DONE`.
- **Remaining:** none.
- **Blockers:** none.

## M55 - Provider-neutral agent runtime

- **Ticket:** M55-T1
- **Progress:** passed
- **Acceptance:** AgentProvider, ProviderCapability, ExecutionRequest, and
  AgentResult contracts exist; CodexProvider matches current host execution;
  FakeProvider proves a second provider needs no core rewrite; worker results
  are candidate results, never canonical DONE.
- **Evidence:** `passed` — Codex/Fake capability and candidate-authority tests;
  nineteen cumulative tests; canonical `M55-T1` `DONE`.
- **Remaining:** none.
- **Blockers:** none.

## M56 - Worktree / execution ownership

- **Ticket:** M56-T1
- **Progress:** passed
- **Acceptance:** TaskContract -> lease -> optional worktree -> provider ->
  candidate -> Quality -> completion flow uses existing R6 ownership; duplicate
  claims and write-surface conflicts fail closed; detached HEAD is valid.
- **Evidence:** `passed` — duplicate claim, overlapping surface, detached HEAD
  and candidate-before-Quality tests; twenty-one cumulative tests; `M56-T1`
  canonical `DONE`.
- **Remaining:** none.
- **Blockers:** none.

## M57 - Credential vault + external authority

- **Ticket:** M57-T1
- **Progress:** passed
- **Acceptance:** canonical state stores CredentialRef only; Windows-native
  adapter is added only if safe without a production dependency; fake provider
  tests prove no credential value reaches repo/state/log/evidence/package;
  ExternalAction requires explicit owner authority where specified.
- **Evidence:** `passed` — fake-vault reference/audit leak checks and exact
  ExternalAction authority tests; twenty-four cumulative tests; `M57-T1`
  canonical `DONE`. Windows native vault is honestly `not-run`.
- **Remaining:** native Windows vault remains optional and `not-run`.
- **Blockers:** none.

## M58 - Delivery runtime / cPanel

- **Ticket:** M58-T1
- **Progress:** passed
- **Acceptance:** generic Linux/cPanel capability and delivery contracts create
  backup, package/upload/configuration, activation, verification, and rollback
  plans; dry-run is mandatory; remote mutation cannot start without authority;
  manual delivery package remains available without SSH/API.
- **Evidence:** `passed` — complete step order, manual fallback, no-authority
  zero-call and authorized fake-adapter tests; twenty-seven cumulative tests;
  `M58-T1` canonical `DONE`.
- **Remaining:** real remote delivery remains `not-run` by scope.
- **Blockers:** none.

## M59 - Live verification + owner cockpit

- **Ticket:** M59-T1
- **Progress:** passed
- **Acceptance:** project-local Playwright is added only if needed; a local
  fixture journey covers home/register/login/create/persist/logout/login/mobile;
  DEPLOYED and LIVE_VERIFIED stay distinct; Status HTML shows project, state,
  acceptance, quality, environment, delivery, blocker, next action, and one
  plain-language owner request without AI-confidence percentages.
- **Evidence:** `passed` — twenty-nine cumulative product/cockpit tests plus
  Playwright Chromium 1/1 local journey and inspected mobile screenshot;
  `M59-T1` canonical `DONE`.
- **Remaining:** real deployed-site verification remains `not-run` by scope.
- **Blockers:** none.

## M60 - Golden E2E + product closure

- **Ticket:** M60-T1
- **Progress:** verification passed (canonical completion transition pending)
- **Acceptance:** golden scenarios A-I pass fresh; final source, portable,
  installed, quality, security, package and validator gates pass; reproducible
  artifact and `artifacts/final/pala-1.0-evidence-manifest.json` are produced;
  P0 and accepted P1 product blockers are zero.
- **Evidence:** `passed` (implementation/focused gates) -- caller command/exit
  authority is rejected; the existing Quality Engine now executes only current
  approved argv through `pala-quality-runner`, shell-free and timeout-bounded,
  with actual exit, output digests and verification basis. Five mandatory
  process-boundary cases, six direct runner cases and Windows shim resolution
  pass. Fresh canonical coverage run: 536 tests (1 controlled skip), 75%;
  pytest 535 passed (1 skip, 44 subtests); strict critical Mypy clean;
  changed-surface Ruff passed; Bandit High=0; pip-audit 0; Playwright 1/1;
  plugin and skill validators passed. No prior M60 completion evidence is
  reused.
- **Remaining:** rebuild the exact ZIP from this frozen source, regenerate the
  schema-v2 manifest, run the trusted release ledger from zero and perform the
  canonical completion transition. Remote publish and real remote deploy stay
  `not-run` by locked scope.
- **Blockers:** none.

## Final authority state

Remote publish: `not-run`. Real remote deploy: `not-run`. The strongest allowed
successful outcome is **LOCAL RELEASE CANDIDATE**, never production deployed.

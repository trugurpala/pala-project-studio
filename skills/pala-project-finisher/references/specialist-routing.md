# Specialist Routing

Use Pala as the orchestrator and current specialist skills as the source of
provider, framework, and tool-specific procedure. Do not copy volatile domain
guidance into Pala.

The user does not need to provide external links. Start with local evidence,
then inspect current official documentation, registries, releases, or
repositories only when the task needs them. Ask for a source only when the
user wants one particular template, design, dataset, or repository.

## Routing rules

- Inspect available skill and connector descriptions before a provider,
  platform, remote repository, or version-sensitive framework change.
- Load a specialist only when its trigger is present. If it is unavailable,
  use local evidence and current official sources, label anything unverified,
  and report it only when it blocks the requested outcome.
- Follow the specialist's current safety, authorization, and verification
  contract. Pala coordinates the result; it does not weaken that contract.
- Respect an explicit offline or no-external-access request.

## Known specialist boundaries

- Use `supabase:supabase` for any actual Supabase product or client task. Also
  use `supabase:supabase-postgres-best-practices` for PostgreSQL schema, SQL,
  policy, RLS, or performance work. Let those skills obtain current changelog,
  documentation, and security guidance.
- Use `github:github` and its connector for GitHub URLs, remote repositories,
  pull requests, issues, reviews, Actions, or remote state. Local Git work
  alone does not trigger GitHub.
- GitHub stage, commit, push, pull request, tag, release, and deployment are
  distinct actions. Authority for one does not authorize another.
- Prefer Pala continuity refs first: `using-pala.md`, `plan-tickets.md`,
  `execute-tickets.md`, `debugging-inc.md`, and `quality-gates.md` (verification
  before done). These own STATUS/PLAN/INC/evidence for Codex project continuity.
- If installed, optional `superpowers:` skills may fill process gaps those refs
  do not cover. Do not claim Claude-only subagent or companion flows as Codex
  features. Do not load unrelated process skills.

For other ecosystems, apply the same rule: prefer an installed current
specialist, then official version-matched documentation, then bounded local
reasoning. Record material external code through the open-source intake.

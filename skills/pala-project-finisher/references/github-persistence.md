# Git and GitHub Persistence

Git is the durable project-history layer. GitHub is optional remote storage,
review, and collaboration; Pala must remain useful offline and without a
GitHub connector.

## Safe to track

- Source, tests, lock files, CI, documentation, and license records.
- Stable `AGENTS.md` rules and secrets-free Pala document mappings.
- Product, plan, status, decisions, exact command results, durations, and
  commit identifiers.
- Secrets-free `.codex/pala-project.json`. Keep the frequently changing
  `.codex/pala-workflow.json` local by default; track it only when project
  policy explicitly wants shared live state and its contents were reviewed.

## Never track

Never store tokens, credentials, `.env` values, transcripts, raw hook output,
plugin cache/data, model-private reasoning, or real sensitive customer data.
Sanitize remote URLs that contain credentials and never print authentication
material while checking GitHub state.

## Authority and visibility

Local inspection and ordinary file edits do not authorize remote writes.
Commit, push, pull request, release, deployment, and visibility are separate
authority boundaries. If a new remote is requested but visibility is not
specified, use a private repository for non-public work and report that choice;
changing visibility later still requires explicit authority.

When GitHub is in scope, prefer an installed GitHub connector for semantic
remote actions; use authenticated `gh`/Git only when available and appropriate.
Read-only discovery may inspect remotes, authentication status without token
output, branches, CI, issues, or PRs. Never bundle a user's GitHub token or
silently add an MCP server merely to make Pala work.

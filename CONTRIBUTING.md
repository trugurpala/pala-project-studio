# Contributing to Pala Project Studio

Thanks for considering a fork or pull request. Pala is a **Codex plugin**:
skills + hooks + deterministic Python scripts. It is not a web app and does not
ship a separate MCP server by default (see `DECISIONS.md`).

## Before you change anything

1. Read `AGENTS.md`, `DECISIONS.md`, and `docs/CODEX_SCOPE_AND_LIMITS.md`.
2. Prefer the smallest change that preserves:
   - single install door (`Install-Pala.ps1`)
   - local-first / secrets-free behavior
   - no network/test/build inside hooks
   - evidence-gated “done” (no soft “bitti/ok” without structured status)
3. New behavior needs a **failing contract test first**, then the fix.

## Local setup

```powershell
git clone https://github.com/trugurpala/pala-project-studio.git
cd pala-project-studio
py -3 -m unittest scripts.test_pala_tools scripts.test_plugin_experience scripts.test_pala_memory -v
py -3 scripts\verify.py
```

Human help: [SUPPORT.md](SUPPORT.md) · Release history: [CHANGELOG.md](CHANGELOG.md) ·
Docs index: [docs/README.md](docs/README.md)

Optional install into your Codex profile (Windows):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -WhatIf
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Doctor
```

## Useful owner commands

```powershell
# Human-readable project memory
py -3 scripts\pala_state.py memory --cwd .

# Status page (sidebar + freshness + update banner)
py -3 scripts\pala_report.py --cwd . --open
# or
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1 -Mode Status
```

## Branch and PR habits

- Branch from `main` (or the open feature branch you were asked to extend).
- Keep PRs focused: one coherent outcome per PR.
- Do not commit secrets, transcripts, real project data, or generated
  `.codex/pala-status.html` / workflow state.
- Include:
  - what changed and why
  - which tests you ran (`verify.py` when behavior/contracts change)
  - any intentional non-run checks (`not-run` / `blocked` / `configured-not-verified`)

## What usually gets rejected

- Hook-side network, package install, test, or GitHub mutation
- Soft “done” without structured verification evidence
- Copying third-party tool trees into the plugin package
- Expanding scope into a second orchestrator / desktop app without a new ADR
- Measuring or claiming unverified speed/token/quality percentages

## Security

Do not open public issues with exploit details. Follow `SECURITY.md`.

## License

Contributions are accepted under the MIT license (`LICENSE`).

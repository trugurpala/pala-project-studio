# Support

## Where to get help

| Need | Where |
| --- | --- |
| Install / Doctor / Status | [docs/VIBE_FIRST_SESSION.md](docs/VIBE_FIRST_SESSION.md), [docs/PALA_EVERYWHERE.md](docs/PALA_EVERYWHERE.md) |
| Scope & limits | [docs/CODEX_SCOPE_AND_LIMITS.md](docs/CODEX_SCOPE_AND_LIMITS.md) |
| Bug report | [GitHub Issues](https://github.com/trugurpala/pala-project-studio/issues/new?template=bug_report.md) |
| Feature idea | [GitHub Issues](https://github.com/trugurpala/pala-project-studio/issues/new?template=feature_request.md) |
| Security | [SECURITY.md](SECURITY.md) — **private** report only |
| Contribute | [CONTRIBUTING.md](CONTRIBUTING.md) |

## What we can help with

- Codex CLI / ChatGPT desktop **Codex · Work** install of this plugin
- Doctor `plugin_ready` / `hook_safety` / UI `/hooks` trust confusion
- Status HTML, memory CLI, local SQLite store

## What we cannot help with (by design)

- Installing Pala into **ChatGPT Plus plain chat** (not a plugin surface)
- Bypassing Codex hook trust (`--dangerously-bypass-hook-trust` is not a product path)
- Promises of larger context windows, token quotas, or unmeasured “% faster”

## Before opening an issue

1. Run `Install-Pala.ps1 -Mode Doctor` and paste the full output.
2. Say whether you used **Codex Work** or another surface.
3. Include plugin version from Doctor / `codex plugin list`.

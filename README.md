# Pala

**Provider-Independent Local Software Delivery OS**

Pala turns a software idea or an existing repository into a durable plan,
bounded execution, verified quality evidence, and a release-ready package. It
keeps the owner in control while AI providers remain replaceable.

Codex'e sunu yaz:

> https://github.com/trugurpala/pala-project-studio eklentisini kur ve guncel oldugunu dogrula.

Codex installation contract: plugin registration alone is not success. In the
same journey Codex must resolve the installed plugin root, run its bundled Pala
installer transaction, and accept success only when Doctor reports the plugin,
runtime bundle, required Workbench, and version healthy.
The user does not need to know or run these internal steps.

Current version: **1.1.2**

[![CI](https://github.com/trugurpala/pala-project-studio/actions/workflows/quality.yml/badge.svg)](https://github.com/trugurpala/pala-project-studio/actions/workflows/quality.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What Pala does

- **Kod anlayışı:** selects fresh structural context and falls back safely to
  direct source inspection.
- **Güvenlik:** runs bounded local checks without granting a scanner completion
  authority.
- **Tarayıcı doğrulama:** captures mechanical browser evidence only when the
  selected project requires it.
- **Quality Engine:** maps real exit-code-zero checks to acceptance criteria;
  it is the only verification authority.
- **Failure Intelligence:** retains verified fixes without storing secrets,
  transcripts, or customer data.
- **ReleaseTruth:** separates local build truth, publication truth, and deploy
  truth.
- **Control Center:** provides one read-only owner view and opens only after an
  explicit request.

## Professional delivery posture

Pala keeps one canonical task active, preserves project-specific instructions,
and runs narrow checks during implementation plus full gates at release
boundaries. It never treats a soft “done” as evidence.

Commit, push, pull request, tag, release, visibility, billing, and deployment
are separate owner-authorized actions. Hooks never start tests, builds, network
requests, or GitHub mutations.

## Local-first and private

Project state and evidence stay local by default. Pala does not enlarge a
model's context window or quota. It selects only relevant context and excludes
credentials, `.env` values, transcripts, caches, generated browser state, and
machine-local installation data from packages.

## Install and update

The same natural-language request handles a clean install, repair, or safe
update. Pala inventories the existing installation, verifies ownership and
integrity, stages changes, runs health checks, activates atomically, and rolls
back on failure. A second install is a no-op only when every required dimension
is exact and healthy; matching only the plugin version is insufficient.

For an extracted portable package:

ZIP Codex Plugins'e yüklenmez; extracted portable paket yerel installer ile
çalıştırılır.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
```

See [installation](docs/VIBE_INSTALL.md), [first session](docs/VIBE_FIRST_SESSION.md),
[security](SECURITY.md), and the [documentation index](docs/README.md).

## Advanced technical details

The managed capability registry currently uses CodeGraph 1.5.0 and Semgrep
1.172.0 as required local defaults, Playwright 1.62.1 as a project profile,
Serena 1.7.0 as a lazy fallback, and Context7 4.0.2 as optional external.
Providers are advisory; they cannot mark work complete. Telemetry, shared
daemons, silent global PATH mutation, and automatic helper UI are disabled.

Read [architecture](docs/ARCHITECTURE.md), [Quality Engine](docs/QUALITY_ENGINE.md),
and [Pala 1.1.2 release notes](docs/RELEASE_1.1.2.md).

## License

[MIT](LICENSE)

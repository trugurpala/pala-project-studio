# Pala Project Studio

Pala is a **Provider-Independent Local Software Delivery OS** for planning,
coordinating, verifying, and packaging AI-assisted software projects.

Pala keeps project intent, task ownership, quality evidence, failure memory,
and release truth local and inspectable. It helps an owner move from an idea to
a verified package without inventing capabilities or silently publishing work.

Current product version: **1.0.0**
Plugin version: **1.0.0**
Release channel: **public release**
Portable asset: `pala-project-studio-1.0.0.zip`
Remote release: [v1.0.0](https://github.com/trugurpala/pala-project-studio/releases/tag/v1.0.0),
with the [latest 1.0.0 asset](https://github.com/trugurpala/pala-project-studio/releases/latest/download/pala-project-studio-1.0.0.zip).

![CI](https://github.com/trugurpala/pala-project-studio/actions/workflows/quality.yml/badge.svg)
[![Release](https://img.shields.io/badge/release-v1.0.0-2ea44f)](https://github.com/trugurpala/pala-project-studio/releases/tag/v1.0.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-index-0A66C2)](docs/README.md)

## Install

The primary path is the Codex-native CLI:

```powershell
codex plugin marketplace add trugurpala/pala-project-studio
codex plugin add pala-project-studio@pala-project-studio
```

For a local checkout, replace the marketplace URL with the checkout path. The
portable ZIP is an extract-only toolkit; it is not a Plugins ZIP-upload.
ZIP Codex Plugins'e yüklenmez; onu çıkartıp yerel kurulum aracını çalıştırın.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Pala.ps1
```

Read the [zero-knowledge install guide](docs/VIBE_INSTALL.md), then the
[first ten minutes](docs/VIBE_FIRST_SESSION.md). After installation, review
`/hooks` and open a new Codex conversation.

## Start a project

Tell Pala what you want to build or ask it to continue an existing project.
Pala discovers the applicable instructions, keeps one canonical task active,
runs the relevant quality gates, and reports the evidence needed for closure.

Pala does:

- turn intent into a durable ProductSpec and bounded task plan;
- coordinate local AI workers without creating a second task authority;
- require real verification evidence before a task is DONE;
- remember verified failure resolutions without storing secrets or transcripts;
- prepare a reproducible portable release and explain owner decisions plainly.

Pala never, without explicit owner authority:

- commits, pushes, creates PRs, tags, or publishes releases;
- changes repository visibility, billing, protections, or spending settings;
- deploys to production or a hosting provider;
- claims a test, build, release, or deployment that was not run.

## GitHub publication

When an owner asks Pala to publish a project, the generic flow is:

`quality -> hygiene -> secret scan -> version consistency -> documentation -> publication preflight -> cost/risk -> owner authority -> publish -> remote read-back`

Normal owner output answers: where we are, what Pala is doing, whether there is
a problem, and what the owner must do. Technical policy IDs, commands, exit
codes, and evidence references remain available under Advanced.

For this repository, the canonical identity is in
[product-identity.json](product-identity.json), the current release notes are
[docs/RELEASE_1.0.0.md](docs/RELEASE_1.0.0.md), and the document index is
[docs/README.md](docs/README.md).

## Safety and boundaries

Pala is local-first. It does not enlarge model context or usage quotas. Hooks
do not run tests, builds, network calls, or GitHub mutations. Real production
deployment is separate evidence and is not part of the Pala 1.0 GitHub release.

See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md),
[SUPPORT.md](SUPPORT.md), and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Safe expert workers

Optional local helpers such as Graphify, Serena, codebase-memory, and Ollama
remain bounded Pala workers. They do not replace Pala's task, evidence, or
owner-authorization authorities. Divan is the project's development
infrastructure, not a second runtime authority.

## License

[MIT](LICENSE)

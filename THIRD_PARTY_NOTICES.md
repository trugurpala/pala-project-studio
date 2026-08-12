# Third-Party Notices

Pala Project Studio's shipped runtime does not include the UI UX Pro Max CLI or
any upstream UI UX Pro Max source. The project is an external-reference donor
only; Pala's provider-neutral DesignAdvisor remains the sole advisory contract.

The donor audit is recorded in
`artifacts/governance/third-party-inventory.json` with the retrieval date,
pinned commit, release tag, license source, reviewed paths, imported files,
local hashes, and update policy. No global installation was performed and no
user-global Codex skill directory was modified.

The UI UX Pro Max repository was checked read-only on 2026-08-12. Its pinned
`main` commit and MIT license hash are recorded in the machine-readable
inventory. The upstream CLI and any surface whose distribution rights are not
independently clear remain outside the Pala package.

GitHub Actions used by historical workflows:

- `actions/checkout` v7.0.1,
  `3d3c42e5aac5ba805825da76410c181273ba90b1`, MIT License.
- `actions/setup-python` v7.0.0,
  `5fda3b95a4ea91299a34e894583c3862153e4b97`, MIT License.

Optional `code-review-graph` integration:

- Repository: https://github.com/tirth8205/code-review-graph
- Reviewed version: 2.3.7
- Reviewed commit: `6a1ee1c7063cc35cfa5ff12b8198c29360f3e4ad`
- License: MIT, Copyright (c) 2026 Tirth Kanani

Pala does not include this project's source. Its installation and update
lifecycle belongs to the `code-review-graph` project.

PALA-045 managed expert candidates are not included in the Pala package:

- Graphify `0.9.33` — Apache-2.0
- Serena `1.6.1` — MIT
- codebase-memory-mcp `0.9.0` — MIT
- Ollama `0.32.6` — MIT
- Qwen3 4B Instruct — Apache-2.0

Pala may use these only through a pinned version/integrity record and an
isolated project-external data area. Pala does not invoke their Codex
installers, hooks, daemons, or user-owned model areas.

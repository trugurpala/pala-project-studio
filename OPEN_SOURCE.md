# Open-source inventory

Pala Project Studio is distributed under the MIT License. Material third-party
runtime and tool decisions are versioned, integrity-checked, and summarized in
`artifacts/governance/third-party-inventory.json` and
`THIRD_PARTY_NOTICES.md`.

## Current managed Workbench

| Source | Version | License | Use |
| --- | --- | --- | --- |
| `colbymchenry/codegraph` | 1.5.0 | MIT | Required local structural code capability |
| `semgrep/semgrep` | 1.172.0 | LGPL-2.1-or-later | Required isolated local security capability |
| `microsoft/playwright` | 1.62.1 | Apache-2.0 | Explicit project-profile browser evidence |
| `oraios/serena` | 1.7.0 | MIT | Lazy symbol-precision fallback |
| `upstash/context7` | 4.0.2 | MIT | Optional external documentation capability |

Pala does not run third-party updaters, enable telemetry, mutate global PATH,
install shared daemons, or grant any provider edit/completion authority.

GitHub Actions use SHA-pinned official actions. No third-party source code,
credentials, proprietary assets, or customer data are copied into the release
without an explicit license and provenance record.

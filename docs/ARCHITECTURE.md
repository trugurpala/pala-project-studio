# Architecture and capability registry

Pala selects capabilities by lifecycle stage, risk, semantic need, health,
freshness, and user intent. File count does not decide routing. Providers offer
information; Pala coordinates; only the Quality Engine proves completion.

## Capability classes

- `DEFAULT`: required local code understanding and security.
- `PROJECT_PROFILE`: activated only when the selected project/task requires it.
- `LAZY_FALLBACK`: used only after defaults and direct inspection are
  insufficient.
- `OPTIONAL_EXTERNAL`: explicit user-controlled integration; never core health.

Runtime state is separate from definitions and reports `absent`, `exact`,
`old`, `external`, `foreign`, or `offline`, with version, provenance, integrity,
ownership, health, freshness, and evidence references.

## Lifecycle

Install and update use inventory → stage → checksum/provenance verification →
health probe → atomic activation → rollback. There is no global PATH mutation,
third-party installer side effect, credential logging, shared daemon, automatic
watcher, or automatic helper UI.

Code context must be fresh before use. Missing or stale structural context
falls back to direct source inspection and cannot count as Quality evidence.
Browser evidence is validated for trace, screenshot, console/network state, and
browser version only when the project profile requires it.

## Advanced provider details

| Capability | Provider | Exact version | Ownership |
| --- | --- | --- | --- |
| Structural code | CodeGraph | 1.5.0 | Pala-owned versioned Windows x64 artifact |
| Local security | Semgrep | 1.172.0 | Pala-owned hash-locked isolated environment |
| Browser tests | Playwright | 1.62.1 | Exact compatible project profile |
| Symbol fallback | Serena | 1.7.0 | Pala-owned lazy isolated environment |
| Current docs | Context7 | 4.0.2 | Optional external; never default-installed |

Exact sources, hashes, licenses, network/telemetry policies, fallbacks, and
freshness rules are machine-readable in `scripts/pala_workbench.py`.
